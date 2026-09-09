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
    HuggingFaceHTTPError,
    HuggingFaceRateLimitError,
    HuggingFaceResponseError,
    HuggingFaceIncompleteCompletionError,
    HuggingFaceModelIdentityError,
    HuggingFaceRouterProvider,
    HuggingFaceTokenLimitError,
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
    def test_publicai_disables_fallbacks_and_cache_in_both_response_modes(self) -> None:
        model = "swiss-ai/Apertus-70B-Instruct-2509"
        for provider in ("publicai", "another-provider"):
            for response_mode in ("json_schema", "prompt_only"):
                with self.subTest(provider=provider, response_mode=response_mode):
                    response = FakeResponse({"model": model, "choices": [
                        {"finish_reason": "stop", "message": {"content": "{}"}},
                    ]})
                    opener = FakeOpener(response)
                    make_provider(
                        opener, provider=provider, response_mode=response_mode,
                    ).generate_structured(
                        system_prompt="System", user_prompt="User",
                        response_schema={"type": "object"},
                    )

                    payload = json.loads(opener.requests[0].data)
                    self.assertEqual(payload["model"], f"{model}:{provider}")
                    if provider == "publicai":
                        self.assertIs(payload["disable_fallbacks"], True)
                        self.assertEqual(payload["cache"], {"no-cache": True, "no-store": True})
                    else:
                        self.assertNotIn("disable_fallbacks", payload)
                        self.assertNotIn("cache", payload)

    def test_publicai_still_rejects_qwen_with_fallbacks_disabled(self) -> None:
        observed = "Qwen/Qwen3-235B-A22B-Instruct-2507"
        for response_mode in ("json_schema", "prompt_only"):
            with self.subTest(response_mode=response_mode):
                response = FakeResponse({"model": observed, "choices": [
                    {"finish_reason": "stop", "message": {"content": "private Qwen output"}},
                ]})
                opener = FakeOpener(response)
                with self.assertRaises(HuggingFaceModelIdentityError) as raised:
                    make_provider(opener, response_mode=response_mode).generate_structured(
                        system_prompt="System", user_prompt="User",
                        response_schema={"type": "object"},
                    )
                self.assertEqual(
                    raised.exception.requested_model,
                    "swiss-ai/Apertus-70B-Instruct-2509:publicai",
                )
                self.assertEqual(raised.exception.observed_model, observed)
                self.assertNotIn("private Qwen output", str(raised.exception))
                self.assertTrue(response.closed)

    def test_prompt_only_sends_schema_in_prompt_without_api_format_constraint(self) -> None:
        response = FakeResponse({"model": "swiss-ai/apertus-70b-instruct", "choices": [
            {"finish_reason": "stop", "message": {"content": '{"status":"ready"}'}},
        ]})
        opener = FakeOpener(response)
        schema = {"type": "object", "properties": {"status": {"type": "string"}}}
        completion = make_provider(opener, response_mode="prompt_only").generate_structured(
            system_prompt="Extract.", user_prompt="Source text.", response_schema=schema,
        )
        payload = json.loads(opener.requests[0].data)
        self.assertNotIn("response_format", payload)
        self.assertIn(json.dumps(schema, separators=(",", ":")), payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][1], {"role": "user", "content": "Source text."})
        self.assertEqual(payload["max_tokens"], 321)
        self.assertEqual(completion.observed_model, "swiss-ai/apertus-70b-instruct")

    def test_prompt_only_still_rejects_incomplete_output_and_wrong_identity(self) -> None:
        for model, reason, error in (
            ("swiss-ai/apertus-70b-instruct", "length", HuggingFaceIncompleteCompletionError),
            ("another/model", "stop", HuggingFaceModelIdentityError),
        ):
            with self.subTest(model=model, reason=reason):
                response = FakeResponse({"model": model, "choices": [
                    {"finish_reason": reason, "message": {"content": "{}"}},
                ]})
                with self.assertRaises(error):
                    make_provider(FakeOpener(response), response_mode="prompt_only").generate_structured(
                        system_prompt="System", user_prompt="User", response_schema={"type": "object"},
                    )

    def test_unknown_response_mode_is_rejected(self) -> None:
        with self.assertRaisesRegex(HuggingFaceConfigurationError, "response_mode"):
            make_provider(FakeOpener(FakeResponse({})), response_mode="automatic")

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
        self.assertEqual(completion.requested_model, "swiss-ai/Apertus-70B-Instruct-2509:publicai")
        self.assertEqual(completion.observed_model, completion.requested_model)
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
        self.assertEqual(completion.requested_model, "swiss-ai/Apertus-8B-Instruct-2509:publicai")
        self.assertEqual(completion.observed_model, "swiss-ai/apertus-8b-instruct")

    def test_publicai_70b_alias_preserves_requested_and_observed_identity(self) -> None:
        observed = "swiss-ai/apertus-70b-instruct"
        response = FakeResponse({"model": observed, "choices": [
            {"finish_reason": "stop", "message": {"content": "{}"}},
        ]})
        completion = make_provider(FakeOpener(response)).generate_structured(
            system_prompt="System", user_prompt="User", response_schema={"type": "object"},
        )
        self.assertEqual(completion.model, "swiss-ai/Apertus-70B-Instruct-2509")
        self.assertEqual(completion.requested_model, "swiss-ai/Apertus-70B-Instruct-2509:publicai")
        self.assertEqual(completion.observed_model, observed)

    def test_publicai_70b_alias_is_scoped_to_provider_size_and_revision(self) -> None:
        for provider, model, observed in (
            ("another-provider", "swiss-ai/Apertus-70B-Instruct-2509", "swiss-ai/apertus-70b-instruct"),
            ("publicai", "swiss-ai/Apertus-8B-Instruct-2509", "swiss-ai/apertus-70b-instruct"),
            ("publicai", "swiss-ai/Apertus-70B-Instruct-2609", "swiss-ai/apertus-70b-instruct"),
            ("publicai", "swiss-ai/Apertus-70B-Instruct-2509", "swiss-ai/apertus-8b-instruct"),
            ("publicai", "swiss-ai/Apertus-70B-Instruct-2509", "swiss-ai/apertus-70b-instruct-2509"),
        ):
            with self.subTest(provider=provider, model=model, observed=observed):
                response = FakeResponse({"model": observed, "choices": [
                    {"finish_reason": "stop", "message": {"content": "{}"}},
                ]})
                with self.assertRaises(HuggingFaceModelIdentityError):
                    make_provider(FakeOpener(response), model=model, provider=provider).generate_structured(
                        system_prompt="System", user_prompt="User", response_schema={"type": "object"},
                    )

    def test_exact_model_identity_with_or_without_router_suffix(self) -> None:
        for model in ("swiss-ai/Apertus-8B-Instruct-2509", "swiss-ai/Apertus-70B-Instruct-2509",
                      "another/exact-model"):
            for observed in (model, f"{model}:publicai"):
                with self.subTest(model=model, observed=observed):
                    response = FakeResponse({"model": observed, "choices": [
                        {"finish_reason": "stop", "message": {"content": "{}"}},
                    ]})
                    completion = make_provider(FakeOpener(response), model=model).generate_structured(
                        system_prompt="System", user_prompt="User", response_schema={"type": "object"},
                    )
                    self.assertEqual(completion.model, model)
                    self.assertEqual(completion.requested_model, f"{model}:publicai")
                    self.assertEqual(completion.observed_model, observed)

    def test_unexplained_model_mismatches_retain_identity_and_reject_content(self) -> None:
        model = "swiss-ai/Apertus-8B-Instruct-2509"
        for provider, observed in (
            ("publicai", "completely-different/model"),
            ("publicai", "swiss-ai/Apertus-70B-Instruct-2509"),
            ("publicai", "swiss-ai/Apertus-8B-Instruct-2609"),
            ("publicai", "swiss-ai/apertus-8b-instruct-2509"),
            ("publicai", f"{model}:another-provider"),
            ("publicai", f" {model}"),
            ("another-provider", "swiss-ai/apertus-8b-instruct"),
        ):
            with self.subTest(provider=provider, observed=observed):
                response = FakeResponse({"model": observed, "choices": [
                    {"finish_reason": "stop", "message": {"content": "private completion"}},
                ]})
                adapter = make_provider(FakeOpener(response), model=model, provider=provider)
                with self.assertRaises(HuggingFaceModelIdentityError) as raised:
                    adapter.generate_structured(
                        system_prompt="System", user_prompt="User", response_schema={"type": "object"},
                    )
                self.assertEqual(raised.exception.requested_model, f"{model}:{provider}")
                self.assertEqual(raised.exception.observed_model, observed)
                self.assertNotIn("private completion", str(raised.exception))
                self.assertTrue(response.closed)

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

    def test_token_quota_errors_preserve_metadata_without_exposing_body(self) -> None:
        messages: set[str] = set()
        for path in ("http_error", "response"):
            for field in ("message", "code"):
                with self.subTest(path=path, field=field):
                    secret = f"private-provider-detail-{path}-{field}"
                    code = (
                        "litellm.RateLimitError: RateLimitError: OpenAIException - maximum_token_reached"
                        if field == "message" else "maximum_token_reached"
                    )
                    body = json.dumps({"error": {
                        field: code,
                        "detail": secret,
                        "api_key": "hf_test_secret",
                    }}).encode("utf-8")
                    body += b" " * (4096 - len(body))
                    headers = response_headers(X_Request_Id="quota-request-id", Retry_After="60")
                    if path == "http_error":
                        result = urllib.error.HTTPError(
                            "https://router.example/v1/chat/completions", 429,
                            "Too Many Requests", headers, io.BytesIO(body),
                        )
                    else:
                        result = FakeResponse(body, status=429, headers=headers)
                    with self.assertRaises(HuggingFaceTokenLimitError) as raised:
                        make_provider(FakeOpener(result)).generate_structured(
                            system_prompt="System", user_prompt="User",
                            response_schema={"type": "object"},
                        )

                    error = raised.exception
                    self.assertIsInstance(error, HuggingFaceRateLimitError)
                    self.assertEqual(error.status_code, 429)
                    self.assertEqual(error.request_id, "quota-request-id")
                    self.assertEqual(error.retry_after, "60")
                    self.assertEqual(error.upstream_error_code, "maximum_token_reached")
                    self.assertIn("token", str(error).lower())
                    for diagnostic in (str(error), repr(error), str(vars(error))):
                        self.assertNotIn(secret, diagnostic)
                        self.assertNotIn("hf_test_secret", diagnostic)
                    messages.add(str(error))
        self.assertEqual(len(messages), 1, "quota diagnostics should use a fixed safe message")

    def test_upstream_rate_limit_is_distinct_from_token_limit_and_redacts_body(self) -> None:
        for path in ("http_error", "response"):
            for field in ("message", "code"):
                with self.subTest(path=path, field=field):
                    value = (
                        "litellm.RateLimitError: RateLimitError: OpenAIException - "
                        "rate_limit_exceeded see: https://provider.example/private-detail"
                        if field == "message" else "rate_limit_exceeded"
                    )
                    body = json.dumps({"error": {
                        field: value, "detail": "private-detail", "api_key": "hf_test_secret",
                    }}).encode("utf-8")
                    headers = response_headers(X_Request_Id="rate-request-id", Retry_After="7")
                    if path == "http_error":
                        result = urllib.error.HTTPError(
                            "https://router.example/v1/chat/completions", 429,
                            "Too Many Requests", headers, io.BytesIO(body),
                        )
                    else:
                        result = FakeResponse(body, status=429, headers=headers)
                    with self.assertRaises(HuggingFaceRateLimitError) as raised:
                        make_provider(FakeOpener(result)).generate_structured(
                            system_prompt="System", user_prompt="User",
                            response_schema={"type": "object"},
                        )
                    error = raised.exception
                    self.assertIs(type(error), HuggingFaceRateLimitError)
                    self.assertEqual(error.upstream_error_code, "rate_limit_exceeded")
                    self.assertEqual(error.status_code, 429)
                    self.assertEqual(error.request_id, "rate-request-id")
                    self.assertEqual(error.retry_after, "7")
                    self.assertIn("rate_limit_exceeded", str(error))
                    for diagnostic in (str(error), repr(error), str(vars(error))):
                        self.assertNotIn("private-detail", diagnostic)
                        self.assertNotIn("hf_test_secret", diagnostic)

    def test_unrecognized_or_oversized_429_bodies_remain_generic(self) -> None:
        quota_body = b'{"error":{"message":"maximum_token_reached"}}'
        bodies = {
            "malformed_json": b'{"error":{"message":"maximum_token_reached"}',
            "oversized_valid_json": quota_body + b" " * (4097 - len(quota_body)),
            "unknown_code": b'{"error":{"code":"another_limit","detail":"private-detail"}}',
            "unrelated_field": b'{"error":{"detail":"maximum_token_reached"}}',
            "top_level_message": b'{"message":"maximum_token_reached"}',
            "string_error": b'{"error":"maximum_token_reached"}',
            "invalid_field_type": b'{"error":{"code":["maximum_token_reached"]}}',
            "different_code_suffix": b'{"error":{"message":"maximum_token_reached_later"}}',
            "different_code_prefix": b'{"error":{"message":"not_maximum_token_reached"}}',
            "non_object_body": b'["maximum_token_reached"]',
            "deeply_nested_json": b'{"error":' + b"[" * 1100 + b"0" + b"]" * 1100 + b"}",
            "invalid_utf8": b'\xff{"error":{"code":"maximum_token_reached"}}',
        }
        for path in ("http_error", "response"):
            for case, body in bodies.items():
                with self.subTest(path=path, case=case):
                    headers = response_headers(X_Request_Id="rate-request-id", Retry_After="7")
                    if path == "http_error":
                        result = urllib.error.HTTPError(
                            "https://router.example/v1/chat/completions", 429,
                            "Too Many Requests", headers, io.BytesIO(body),
                        )
                    else:
                        result = FakeResponse(body, status=429, headers=headers)
                    with self.assertRaises(HuggingFaceRateLimitError) as raised:
                        make_provider(FakeOpener(result)).generate_structured(
                            system_prompt="System", user_prompt="User",
                            response_schema={"type": "object"},
                        )
                    self.assertIs(type(raised.exception), HuggingFaceRateLimitError)
                    self.assertEqual(raised.exception.status_code, 429)
                    self.assertEqual(raised.exception.request_id, "rate-request-id")
                    self.assertEqual(raised.exception.retry_after, "7")
                    self.assertIsNone(raised.exception.upstream_error_code)
                    self.assertNotIn("private-detail", str(raised.exception))

    def test_known_token_quota_code_does_not_reclassify_other_http_statuses(self) -> None:
        body = b'{"error":{"code":"maximum_token_reached"}}'
        for path in ("http_error", "response"):
            for status, error_type in (
                (401, HuggingFaceAuthenticationError),
                (403, HuggingFaceAuthenticationError),
                (500, HuggingFaceHTTPError),
            ):
                with self.subTest(path=path, status=status):
                    headers = response_headers(X_Request_Id="failure-request-id")
                    if path == "http_error":
                        result = urllib.error.HTTPError(
                            "https://router.example/v1/chat/completions", status,
                            "Request failed", headers, io.BytesIO(body),
                        )
                    else:
                        result = FakeResponse(body, status=status, headers=headers)
                    with self.assertRaises(error_type) as raised:
                        make_provider(FakeOpener(result)).generate_structured(
                            system_prompt="System", user_prompt="User",
                            response_schema={"type": "object"},
                        )
                    self.assertIs(type(raised.exception), error_type)
                    self.assertEqual(raised.exception.status_code, status)
                    self.assertEqual(raised.exception.request_id, "failure-request-id")
                    self.assertIsNone(raised.exception.upstream_error_code)

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

    def test_truncation_carries_usage_and_sizes_without_partial_content(self) -> None:
        partial = 'secret-partial-content-\u00fc'
        response = FakeResponse({
            "model": "swiss-ai/Apertus-70B-Instruct-2509",
            "choices": [{"finish_reason": "length", "message": {"content": partial}}],
            "usage": {"input_tokens": 123, "output_tokens": 4096},
        })
        provider = make_provider(FakeOpener(response))
        with self.assertRaises(HuggingFaceIncompleteCompletionError) as raised:
            provider.generate_structured(system_prompt="System", user_prompt="User", response_schema={"type": "object"})
        diagnostics = raised.exception.diagnostics
        self.assertEqual(diagnostics["prompt_tokens"], 123)
        self.assertEqual(diagnostics["output_tokens"], 4096)
        self.assertEqual(diagnostics["content_characters"], len(partial))
        self.assertEqual(diagnostics["response_bytes"], len(response.body))
        self.assertNotIn(partial, str(raised.exception))
        self.assertNotIn(partial, json.dumps(diagnostics))

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
