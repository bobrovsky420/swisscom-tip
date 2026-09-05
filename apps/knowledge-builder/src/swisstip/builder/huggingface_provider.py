"""Hugging Face Inference Providers adapter for structured model calls."""

from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping
from typing import Any, Protocol

from swisstip.ingestion.concepts import (
    ModelCompletion,
    SemanticModelError,
    SemanticModelProvider,
)


DEFAULT_BASE_URL = "https://router.huggingface.co/v1"
_MAX_ERROR_BODY_BYTES = 4_096
_MAX_RESPONSE_BYTES = 1_000_000


class HuggingFaceConfigurationError(ValueError):
    """Raised when the router adapter is configured unsafely or incompletely."""


class HuggingFaceProviderError(SemanticModelError):
    """Base class for Hugging Face request and response failures."""


class HuggingFaceTransportError(HuggingFaceProviderError):
    """Raised when the router cannot be reached."""


class HuggingFaceHTTPError(HuggingFaceProviderError):
    """Raised when the router returns an unsuccessful HTTP status."""

    def __init__(
        self,
        status_code: int,
        *,
        request_id: str | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(f"Hugging Face router returned HTTP {status_code}")
        self.status_code = status_code
        self.request_id = request_id
        self.retry_after = retry_after


class HuggingFaceAuthenticationError(HuggingFaceHTTPError):
    """Raised when the supplied token cannot authorize the request."""


class HuggingFaceRateLimitError(HuggingFaceHTTPError):
    """Raised when the selected account or provider is rate limited."""


class HuggingFaceResponseError(HuggingFaceProviderError):
    """Raised when a successful response does not match the chat contract."""


class _Opener(Protocol):
    def open(self, request: urllib.request.Request, *, timeout: float) -> Any: ...


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prevent a router redirect from forwarding the bearer token."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class HuggingFaceRouterProvider(SemanticModelProvider):
    """Call an explicitly selected provider through the Hugging Face router."""

    def __init__(
        self,
        *,
        token: str,
        model: str,
        provider: str,
        base_url: str = DEFAULT_BASE_URL,
        bill_to: str | None = None,
        timeout_seconds: float = 60.0,
        max_tokens: int = 1_500,
        temperature: float = 0.0,
        opener: _Opener | None = None,
    ) -> None:
        self._token = _required_value("token", token)
        self._model = _separate_identifier("model", model)
        self._provider = _separate_identifier("provider", provider)
        self._base_url = _validated_base_url(base_url)
        self._bill_to = _optional_header_value("bill_to", bill_to)
        self._timeout_seconds = _positive_number("timeout_seconds", timeout_seconds)
        self._max_tokens = _positive_integer("max_tokens", max_tokens)
        self._temperature = _non_negative_number("temperature", temperature)
        self._opener = opener or urllib.request.build_opener(_NoRedirectHandler())

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Mapping[str, object],
    ) -> ModelCompletion:
        """Generate one non-streaming response constrained by a JSON Schema."""

        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise HuggingFaceConfigurationError("system_prompt cannot be empty")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise HuggingFaceConfigurationError("user_prompt cannot be empty")
        if not isinstance(response_schema, Mapping) or not response_schema:
            raise HuggingFaceConfigurationError("response_schema must be a non-empty mapping")

        payload = {
            "model": f"{self._model}:{self._provider}",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "swisstip_structured_response",
                    "schema": dict(response_schema),
                    "strict": True,
                },
            },
            "stream": False,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        try:
            encoded_payload = json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise HuggingFaceConfigurationError(
                "response_schema must contain only JSON-serializable values"
            ) from exc

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        if self._bill_to is not None:
            headers["X-HF-Bill-To"] = self._bill_to

        request = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=encoded_payload,
            headers=headers,
            method="POST",
        )
        try:
            response = self._opener.open(request, timeout=self._timeout_seconds)
        except urllib.error.HTTPError as exc:
            try:
                exc.read(_MAX_ERROR_BODY_BYTES)
            except OSError:
                pass
            finally:
                exc.close()
            _raise_http_error(exc.code, exc.headers)
        except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
            raise HuggingFaceTransportError(
                "Hugging Face router request failed before a response was received"
            ) from exc

        try:
            status_code = int(response.getcode())
            response_headers = response.headers
            response_body = response.read(_MAX_RESPONSE_BYTES + 1)
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise HuggingFaceTransportError(
                "Hugging Face router response could not be read"
            ) from exc
        finally:
            response.close()

        if status_code < 200 or status_code >= 300:
            _raise_http_error(status_code, response_headers)
        if not isinstance(response_body, bytes):
            raise HuggingFaceResponseError(
                "Hugging Face router returned a non-byte response body"
            )
        if len(response_body) > _MAX_RESPONSE_BYTES:
            raise HuggingFaceResponseError(
                "Hugging Face router response exceeded the size limit"
            )

        return self._decode_completion(response_body, response_headers)

    def _decode_completion(
        self,
        response_body: bytes,
        response_headers: Mapping[str, str] | Any,
    ) -> ModelCompletion:
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HuggingFaceResponseError(
                "Hugging Face router returned an invalid JSON response"
            ) from exc
        if not isinstance(payload, dict):
            raise HuggingFaceResponseError(
                "Hugging Face router response must be a JSON object"
            )

        response_model = payload.get("model")
        if not isinstance(response_model, str) or response_model not in {
            self._model,
            f"{self._model}:{self._provider}",
        }:
            raise HuggingFaceResponseError(
                "Hugging Face router returned an unexpected model identity"
            )

        try:
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice["finish_reason"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HuggingFaceResponseError(
                "Hugging Face router response is missing completion state or content"
            ) from exc
        if not isinstance(finish_reason, str) or finish_reason not in {
            "stop",
            "eos_token",
            "stop_sequence",
        }:
            raise HuggingFaceResponseError(
                "Hugging Face router returned an incomplete completion"
            )
        if not isinstance(content, str) or not content.strip():
            raise HuggingFaceResponseError(
                "Hugging Face router response has invalid assistant content"
            )

        usage = payload.get("usage")
        if not isinstance(usage, Mapping):
            usage = {}
        request_id = _header(response_headers, "X-Request-Id")
        if request_id is None and isinstance(payload.get("id"), str):
            request_id = payload["id"]

        return ModelCompletion(
            content=content,
            provider=self._provider,
            model=self._model,
            prompt_tokens=_optional_token_count(
                usage.get("prompt_tokens", usage.get("input_tokens"))
            ),
            output_tokens=_optional_token_count(
                usage.get("completion_tokens", usage.get("output_tokens"))
            ),
            request_id=request_id,
        )


def _required_value(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HuggingFaceConfigurationError(f"{name} cannot be empty")
    if value != value.strip() or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise HuggingFaceConfigurationError(f"{name} contains invalid whitespace")
    return value


def _separate_identifier(name: str, value: str) -> str:
    result = _required_value(name, value)
    if ":" in result or any(character.isspace() for character in result):
        raise HuggingFaceConfigurationError(
            f"{name} must not include whitespace or a provider separator"
        )
    return result


def _optional_header_value(name: str, value: str | None) -> str | None:
    if value is None:
        return None
    return _required_value(name, value)


def _validated_base_url(value: str) -> str:
    result = _required_value("base_url", value).rstrip("/")
    parsed = urllib.parse.urlsplit(result)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise HuggingFaceConfigurationError("base_url must be an absolute HTTPS URL")
    try:
        parsed.port
    except ValueError as exc:
        raise HuggingFaceConfigurationError("base_url contains an invalid port") from exc
    if parsed.username is not None or parsed.password is not None:
        raise HuggingFaceConfigurationError("base_url must not contain credentials")
    if parsed.query or parsed.fragment:
        raise HuggingFaceConfigurationError("base_url must not contain a query or fragment")
    if any(character.isspace() for character in result):
        raise HuggingFaceConfigurationError("base_url must not contain whitespace")
    return result


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise HuggingFaceConfigurationError(f"{name} must be a positive integer")
    return value


def _positive_number(name: str, value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise HuggingFaceConfigurationError(f"{name} must be greater than zero")
    return float(value)


def _non_negative_number(name: str, value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 2
    ):
        raise HuggingFaceConfigurationError(f"{name} must be between 0 and 2")
    return float(value)


def _header(headers: Mapping[str, str] | Any, name: str) -> str | None:
    getter = getattr(headers, "get", None)
    if getter is None:
        return None
    value = getter(name)
    if value is None:
        value = getter(name.lower())
    return value if isinstance(value, str) and value else None


def _raise_http_error(status_code: int, headers: Mapping[str, str] | Any) -> None:
    error_type: type[HuggingFaceHTTPError]
    if status_code in {401, 403}:
        error_type = HuggingFaceAuthenticationError
    elif status_code == 429:
        error_type = HuggingFaceRateLimitError
    else:
        error_type = HuggingFaceHTTPError
    raise error_type(
        status_code,
        request_id=_header(headers, "X-Request-Id"),
        retry_after=_header(headers, "Retry-After"),
    )


def _optional_token_count(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value
