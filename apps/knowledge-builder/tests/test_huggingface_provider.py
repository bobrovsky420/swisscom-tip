from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
import urllib.request
from email.message import Message
from pathlib import Path

APP_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = APP_ROOT.parents[1]
sys.path.insert(0, str(APP_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "packages" / "ingestion" / "src"))

from swisstip.builder.huggingface_provider import (  # noqa: E402
    HuggingFaceAuthenticationError,
    HuggingFaceConfigurationError,
    HuggingFaceRateLimitError,
    HuggingFaceResponseError,
    HuggingFaceRouterProvider,
    HuggingFaceTransportError,
)


def response_headers(**values: str) -> Message:
    headers = Message()
    for name, value in values.items():
        headers[name.replace("_", "-")] = value
    return headers


class FakeResponse:
    def __init__(
        self,
        payload: object,
        *,
        status: int = 200,
        headers: Message | None = None,
    ) -> None:
        self.status = status
        self.headers = headers or Message()
        self.closed = False
        if isinstance(payload, bytes):
            self.body = payload
        else:
            self.body = json.dumps(payload).encode("utf-8")

    def getcode(self) -> int:
        return self.status

    def read(self, amount: int | None = None) -> bytes:
        return self.body if amount is None else self.body[:amount]

    def close(self) -> None:
        self.closed = True


class FakeOpener:
    def __init__(self, result: FakeResponse | Exception) -> None:
        self.result = result
        self.requests: list[urllib.request.Request] = []
        self.timeouts: list[float] = []

    def open(self, request: urllib.request.Request, *, timeout: float) -> FakeResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make_provider(opener: FakeOpener, **overrides: object) -> HuggingFaceRouterProvider:
    arguments: dict[str, object] = {
        "token": "hf_test_secret",
        "model": "swiss-ai/Apertus-70B-Instruct-2509",
        "provider": "publicai",
        "base_url": "https://router.example/v1/",
        "timeout_seconds": 12.5,
        "max_tokens": 321,
        "temperature": 0.2,
        "opener": opener,
    }
    arguments.update(overrides)
    return HuggingFaceRouterProvider(**arguments)  # type: ignore[arg-type]


class HuggingFaceRouterProviderTests(unittest.TestCase):
    def test_builds_strict_non_streaming_chat_request_and_decodes_completion(self) -> None:
        response = FakeResponse(
            {
                "id": "body-completion-id",
                "model": "swiss-ai/Apertus-70B-Instruct-2509:publicai",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": '{"concepts":[{"label":"Residence permit"}]}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 42, "completion_tokens": 17},
            },
            headers=response_headers(X_Request_Id="router-request-id"),
        )
        opener = FakeOpener(response)
        provider = make_provider(opener, bill_to="trusted-team")
        schema = {
            "type": "object",
            "properties": {"concepts": {"type": "array"}},
            "required": ["concepts"],
            "additionalProperties": False,
        }

        completion = provider.generate_structured(
            system_prompt="Propose grounded concepts.",
            user_prompt="Normalized page text",
            response_schema=schema,
        )

        self.assertEqual(len(opener.requests), 1)
        request = opener.requests[0]
        self.assertEqual(request.full_url, "https://router.example/v1/chat/completions")
        self.assertEqual(request.method, "POST")
        headers = {name.lower(): value for name, value in request.header_items()}
        self.assertEqual(headers["authorization"], "Bearer hf_test_secret")
        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["user-agent"], "SwissTIP/0.1")
        self.assertEqual(headers["x-hf-bill-to"], "trusted-team")
        self.assertEqual(opener.timeouts, [12.5])

        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(
            payload["model"],
            "swiss-ai/Apertus-70B-Instruct-2509:publicai",
        )
        self.assertEqual(
            payload["messages"],
            [
                {"role": "system", "content": "Propose grounded concepts."},
                {"role": "user", "content": "Normalized page text"},
            ],
        )
        self.assertFalse(payload["stream"])
        self.assertEqual(payload["max_tokens"], 321)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertEqual(payload["response_format"]["json_schema"]["schema"], schema)
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])

        self.assertEqual(
            completion.content,
            '{"concepts":[{"label":"Residence permit"}]}',
        )
        self.assertEqual(completion.provider, "publicai")
        self.assertEqual(completion.model, "swiss-ai/Apertus-70B-Instruct-2509")
        self.assertEqual(completion.prompt_tokens, 42)
        self.assertEqual(completion.output_tokens, 17)
        self.assertEqual(completion.request_id, "router-request-id")
        self.assertTrue(response.closed)

    def test_omits_bill_to_and_accepts_alternate_usage_names(self) -> None:
        opener = FakeOpener(
            FakeResponse(
                {
                    "id": "completion-id",
                    "model": "swiss-ai/apertus-8b-instruct",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": "{}"},
                        }
                    ],
                    "usage": {"input_tokens": 5, "output_tokens": 2},
                }
            )
        )
        completion = make_provider(
            opener,
            model="swiss-ai/Apertus-8B-Instruct-2509",
        ).generate_structured(
            system_prompt="System",
            user_prompt="User",
            response_schema={"type": "object"},
        )

        request_headers = {
            name.lower(): value for name, value in opener.requests[0].header_items()
        }
        self.assertNotIn("x-hf-bill-to", request_headers)
        request_payload = json.loads(opener.requests[0].data.decode("utf-8"))
        self.assertEqual(
            request_payload["model"],
            "swiss-ai/Apertus-8B-Instruct-2509:publicai",
        )
        self.assertEqual(completion.prompt_tokens, 5)
        self.assertEqual(completion.output_tokens, 2)
        self.assertEqual(completion.request_id, "completion-id")

    def test_maps_authentication_errors_without_exposing_response_body(self) -> None:
        url = "https://router.example/v1/chat/completions"
        error = urllib.error.HTTPError(
            url,
            401,
            "Unauthorized",
            response_headers(X_Request_Id="auth-request-id"),
            io.BytesIO(b'{"error":"secret server detail"}'),
        )
        provider = make_provider(FakeOpener(error))

        with self.assertRaises(HuggingFaceAuthenticationError) as raised:
            provider.generate_structured(
                system_prompt="System",
                user_prompt="User",
                response_schema={"type": "object"},
            )

        self.assertEqual(raised.exception.status_code, 401)
        self.assertEqual(raised.exception.request_id, "auth-request-id")
        self.assertNotIn("secret server detail", str(raised.exception))

    def test_maps_rate_limit_metadata(self) -> None:
        error = urllib.error.HTTPError(
            "https://router.example/v1/chat/completions",
            429,
            "Too Many Requests",
            response_headers(X_Request_Id="rate-request-id", Retry_After="7"),
            io.BytesIO(b"limited"),
        )
        provider = make_provider(FakeOpener(error))

        with self.assertRaises(HuggingFaceRateLimitError) as raised:
            provider.generate_structured(
                system_prompt="System",
                user_prompt="User",
                response_schema={"type": "object"},
            )

        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.request_id, "rate-request-id")
        self.assertEqual(raised.exception.retry_after, "7")

    def test_maps_network_and_invalid_response_failures(self) -> None:
        transport_provider = make_provider(
            FakeOpener(urllib.error.URLError("offline"))
        )
        with self.assertRaises(HuggingFaceTransportError):
            transport_provider.generate_structured(
                system_prompt="System",
                user_prompt="User",
                response_schema={"type": "object"},
            )

        response_provider = make_provider(FakeOpener(FakeResponse(b"not-json")))
        with self.assertRaises(HuggingFaceResponseError):
            response_provider.generate_structured(
                system_prompt="System",
                user_prompt="User",
                response_schema={"type": "object"},
            )

        missing_identity_provider = make_provider(
            FakeOpener(
                FakeResponse(
                    {
                        "model": "",
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {"content": "{}"},
                            }
                        ],
                    }
                )
            )
        )
        with self.assertRaisesRegex(HuggingFaceResponseError, "model identity"):
            missing_identity_provider.generate_structured(
                system_prompt="System",
                user_prompt="User",
                response_schema={"type": "object"},
            )

    def test_rejects_truncated_completion(self) -> None:
        provider = make_provider(
            FakeOpener(
                FakeResponse(
                    {
                        "model": "swiss-ai/Apertus-70B-Instruct-2509",
                        "choices": [
                            {
                                "finish_reason": "length",
                                "message": {"content": '{"concepts": []}'},
                            }
                        ]
                    }
                )
            )
        )

        with self.assertRaisesRegex(
            HuggingFaceResponseError,
            "incomplete completion .*finish_reason='length'",
        ):
            provider.generate_structured(
                system_prompt="System",
                user_prompt="User",
                response_schema={"type": "object"},
            )

    def test_default_transport_disables_redirects(self) -> None:
        provider = HuggingFaceRouterProvider(
            token="hf_test_secret",
            model="swiss-ai/Apertus-8B-Instruct-2509",
            provider="publicai",
        )

        redirect_handlers = [
            handler
            for handler in provider._opener.handlers  # type: ignore[attr-defined]
            if isinstance(handler, urllib.request.HTTPRedirectHandler)
        ]
        self.assertEqual(len(redirect_handlers), 1)
        self.assertIsNone(
            redirect_handlers[0].redirect_request(
                urllib.request.Request(
                    "https://router.huggingface.co/v1/chat/completions",
                    headers={"Authorization": "Bearer hf_test_secret"},
                ),
                None,
                302,
                "Found",
                {},
                "https://attacker.example/",
            )
        )

    def test_rejects_combined_model_provider_and_unsafe_url(self) -> None:
        opener = FakeOpener(FakeResponse({}))
        with self.assertRaises(HuggingFaceConfigurationError):
            make_provider(
                opener,
                model="swiss-ai/Apertus-70B-Instruct-2509:publicai",
            )
        with self.assertRaises(HuggingFaceConfigurationError):
            make_provider(opener, base_url="http://router.example/v1")
        with self.assertRaises(HuggingFaceConfigurationError):
            make_provider(opener, base_url="https://router.example:70000/v1")
        with self.assertRaises(HuggingFaceConfigurationError):
            make_provider(opener, temperature=2.1)


if __name__ == "__main__":
    unittest.main()
