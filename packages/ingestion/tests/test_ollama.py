from __future__ import annotations

import io
import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from swisstip.ingestion.ollama import (  # noqa: E402
    OllamaConfigurationError,
    OllamaOptions,
    OllamaProviderError,
    OllamaSemanticModelProvider,
)


class FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self._status = status
        self._body = json.dumps(payload).encode("utf-8")
        self.closed = False

    def getcode(self) -> int:
        return self._status

    def read(self, size: int = -1) -> bytes:
        return self._body if size < 0 else self._body[:size]

    def close(self) -> None:
        self.closed = True


class RawResponse(FakeResponse):
    def __init__(self, status: int, body: bytes) -> None:
        self._status = status
        self._body = body
        self.closed = False


class FakeOpener:
    def __init__(
        self,
        response: FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error
        self.request = None
        self.timeout = None

    def open(self, request, timeout=None):  # noqa: ANN001
        self.request = request
        self.timeout = timeout
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


class OllamaProviderTests(unittest.TestCase):
    def test_posts_schema_constrained_native_chat_request(self) -> None:
        response = FakeResponse(
            200,
            {
                "model": "apertus-test",
                "message": {"role": "assistant", "content": '{"concepts": []}'},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 27,
                "eval_count": 8,
            },
        )
        opener = FakeOpener(response)
        options = OllamaOptions(
            model="apertus-test",
            base_url="http://127.0.0.1:11434/",
            timeout_seconds=12.5,
            num_ctx=4096,
            num_predict=512,
            temperature=0.0,
            keep_alive="10m",
        )
        schema = {
            "type": "object",
            "properties": {"concepts": {"type": "array"}},
            "required": ["concepts"],
        }

        completion = OllamaSemanticModelProvider(
            options,
            opener=opener,  # type: ignore[arg-type]
        ).generate_structured(
            system_prompt="Extract supported concepts.",
            user_prompt="Residence permits are described here.",
            response_schema=schema,
        )

        assert opener.request is not None
        self.assertEqual(opener.request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(opener.request.get_method(), "POST")
        self.assertEqual(opener.request.get_header("Content-type"), "application/json")
        self.assertEqual(opener.request.get_header("Accept"), "application/json")
        self.assertEqual(opener.timeout, 12.5)
        payload = json.loads(opener.request.data.decode("utf-8"))
        self.assertEqual(
            payload,
            {
                "model": "apertus-test",
                "messages": [
                    {"role": "system", "content": "Extract supported concepts."},
                    {
                        "role": "user",
                        "content": "Residence permits are described here.",
                    },
                ],
                "stream": False,
                "think": False,
                "format": schema,
                "keep_alive": "10m",
                "options": {
                    "num_ctx": 4096,
                    "num_predict": 512,
                    "temperature": 0.0,
                },
            },
        )
        self.assertEqual(completion.content, '{"concepts": []}')
        self.assertEqual(completion.provider, "ollama")
        self.assertEqual(completion.model, "apertus-test")
        self.assertEqual(completion.prompt_tokens, 27)
        self.assertEqual(completion.output_tokens, 8)
        self.assertIsNone(completion.request_id)
        self.assertTrue(response.closed)

    def test_preserves_content_for_extractor_validation(self) -> None:
        opener = FakeOpener(
            FakeResponse(
                200,
                {
                    "model": "apertus-test",
                    "message": {"role": "assistant", "content": "not-json"},
                    "done": True,
                    "done_reason": "stop",
                },
            )
        )

        completion = OllamaSemanticModelProvider(
            OllamaOptions(model="apertus-test"),
            opener=opener,  # type: ignore[arg-type]
        ).generate_structured(
            system_prompt="system",
            user_prompt="page",
            response_schema={"type": "object"},
        )

        self.assertEqual(completion.content, "not-json")
        self.assertEqual(completion.model, "apertus-test")

    def test_rejects_unexpected_model_identity(self) -> None:
        provider = OllamaSemanticModelProvider(
            OllamaOptions(model="apertus-test"),
            opener=FakeOpener(
                FakeResponse(
                    200,
                    {
                        "model": "other-model",
                        "message": {"content": '{"concepts": []}'},
                        "done": True,
                        "done_reason": "stop",
                    },
                )
            ),  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(OllamaProviderError, "model identity"):
            provider.generate_structured(
                system_prompt="system",
                user_prompt="page",
                response_schema={"type": "object"},
            )

    def test_maps_http_error_to_typed_provider_error(self) -> None:
        error = urllib.error.HTTPError(
            "http://127.0.0.1:11434/api/chat",
            404,
            "not found",
            {},
            io.BytesIO(b'{"error":"model not found"}'),
        )
        opener = FakeOpener(error=error)
        provider = OllamaSemanticModelProvider(
            OllamaOptions(model="missing-model"),
            opener=opener,  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(
            OllamaProviderError, "HTTP 404: model not found"
        ) as raised:
            provider.generate_structured(
                system_prompt="system",
                user_prompt="page",
                response_schema={"type": "object"},
            )

        self.assertEqual(raised.exception.status_code, 404)

    def test_rejects_ollama_error_payload(self) -> None:
        provider = OllamaSemanticModelProvider(
            OllamaOptions(model="apertus-test"),
            opener=FakeOpener(  # type: ignore[arg-type]
                FakeResponse(200, {"error": "model failed"})
            ),
        )

        with self.assertRaisesRegex(OllamaProviderError, "model failed"):
            provider.generate_structured(
                system_prompt="system",
                user_prompt="page",
                response_schema={"type": "object"},
            )

    def test_rejects_malformed_completion_envelopes(self) -> None:
        cases = (
            (b"not-json", "malformed JSON"),
            (b"[]", "must be a JSON object"),
            (b'{"done":true,"done_reason":"stop"}', "missing message"),
            (
                b'{"done":true,"done_reason":"stop","message":{"content":42}}',
                "missing message content",
            ),
            (
                b'{"done":true,"done_reason":"stop","message":{"content":"  "}}',
                "missing message content",
            ),
        )

        for body, message in cases:
            with self.subTest(body=body):
                provider = OllamaSemanticModelProvider(
                    OllamaOptions(model="apertus-test"),
                    opener=FakeOpener(RawResponse(200, body)),  # type: ignore[arg-type]
                )
                with self.assertRaisesRegex(OllamaProviderError, message):
                    provider.generate_structured(
                        system_prompt="system",
                        user_prompt="page",
                        response_schema={"type": "object"},
                    )

    def test_rejects_incomplete_completion(self) -> None:
        provider = OllamaSemanticModelProvider(
            OllamaOptions(model="apertus-test"),
            opener=FakeOpener(
                FakeResponse(
                    200,
                    {
                        "message": {"content": '{"concepts": []}'},
                        "done": True,
                        "done_reason": "length",
                    },
                )
            ),  # type: ignore[arg-type]
        )

        with self.assertRaisesRegex(OllamaProviderError, "incomplete"):
            provider.generate_structured(
                system_prompt="system",
                user_prompt="page",
                response_schema={"type": "object"},
            )

    def test_validates_configuration(self) -> None:
        invalid_options = (
            ({"model": " "}, "model"),
            ({"model": "m", "base_url": "localhost:11434"}, "base_url"),
            ({"model": "m", "base_url": "http://user@localhost:11434"}, "credentials"),
            ({"model": "m", "base_url": "http://localhost:11434/api"}, "path"),
            ({"model": "m", "timeout_seconds": 0}, "timeout_seconds"),
            ({"model": "m", "timeout_seconds": float("nan")}, "timeout_seconds"),
            ({"model": "m", "num_ctx": 0}, "num_ctx"),
            ({"model": "m", "num_ctx": 4096.5}, "num_ctx"),
            ({"model": "m", "num_predict": 0}, "num_predict"),
            ({"model": "m", "num_predict": True}, "num_predict"),
            ({"model": "m", "temperature": -0.1}, "temperature"),
            ({"model": "m", "temperature": float("inf")}, "temperature"),
            ({"model": "m", "keep_alive": " "}, "keep_alive"),
        )

        for values, message in invalid_options:
            with self.subTest(values=values):
                with self.assertRaisesRegex(OllamaConfigurationError, message):
                    OllamaOptions(**values)  # type: ignore[arg-type]

    def test_default_transport_ignores_proxies_and_redirects(self) -> None:
        provider = OllamaSemanticModelProvider(OllamaOptions(model="apertus-test"))
        handlers = provider._opener.handlers  # type: ignore[attr-defined]
        proxy_handlers = [
            handler
            for handler in handlers
            if isinstance(handler, urllib.request.ProxyHandler)
        ]
        redirect_handlers = [
            handler
            for handler in handlers
            if isinstance(handler, urllib.request.HTTPRedirectHandler)
        ]

        # Supplying ProxyHandler({}) suppresses the environment proxy handler;
        # urllib does not retain the empty handler because it has no protocols.
        self.assertEqual(proxy_handlers, [])
        self.assertEqual(len(redirect_handlers), 1)
        self.assertIsNone(
            redirect_handlers[0].redirect_request(
                urllib.request.Request("http://127.0.0.1:11434/api/chat"),
                None,
                302,
                "Found",
                {},
                "http://other.example/",
            )
        )


if __name__ == "__main__":
    unittest.main()
