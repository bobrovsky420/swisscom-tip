"""Ollama adapter for structured semantic-model generation."""

from __future__ import annotations

import json
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Mapping

from .concepts import ModelCompletion, SemanticModelError, SemanticModelProvider


_MAX_RESPONSE_BYTES = 1_000_000


class OllamaConfigurationError(ValueError):
    """Raised when the Ollama adapter configuration is invalid."""


class OllamaProviderError(SemanticModelError):
    """Raised when Ollama cannot provide a valid completion envelope."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class OllamaOptions:
    """Runtime options for one local Ollama model profile."""

    model: str
    base_url: str = "http://127.0.0.1:11434"
    timeout_seconds: float = 180.0
    num_ctx: int = 4096
    num_predict: int = 1024
    temperature: float = 0.0
    keep_alive: str = "5m"

    def __post_init__(self) -> None:
        if not isinstance(self.model, str):
            raise OllamaConfigurationError("model must be a string")
        if not isinstance(self.base_url, str):
            raise OllamaConfigurationError("base_url must be a string")
        if not isinstance(self.keep_alive, str):
            raise OllamaConfigurationError("keep_alive must be a string")
        model = self.model.strip()
        base_url = self.base_url.strip().rstrip("/")
        keep_alive = self.keep_alive.strip()
        if not model:
            raise OllamaConfigurationError("model cannot be empty")
        if model != self.model or any(character.isspace() for character in model):
            raise OllamaConfigurationError("model contains invalid whitespace")
        if not base_url:
            raise OllamaConfigurationError("base_url cannot be empty")
        if self.base_url != self.base_url.strip():
            raise OllamaConfigurationError("base_url contains invalid whitespace")

        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise OllamaConfigurationError(
                "base_url must be an absolute HTTP(S) URL"
            )
        if parsed.username or parsed.password:
            raise OllamaConfigurationError("credentials are not allowed in base_url")
        try:
            parsed.port
        except ValueError as exc:
            raise OllamaConfigurationError("base_url contains an invalid port") from exc
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise OllamaConfigurationError(
                "base_url must not contain a path, query, or fragment"
            )
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise OllamaConfigurationError("timeout_seconds must be greater than zero")
        if (
            isinstance(self.num_ctx, bool)
            or not isinstance(self.num_ctx, int)
            or self.num_ctx < 1
        ):
            raise OllamaConfigurationError("num_ctx must be at least 1")
        if (
            isinstance(self.num_predict, bool)
            or not isinstance(self.num_predict, int)
            or self.num_predict < 1
        ):
            raise OllamaConfigurationError("num_predict must be at least 1")
        if (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or not math.isfinite(self.temperature)
            or not 0 <= self.temperature <= 2
        ):
            raise OllamaConfigurationError("temperature must be between 0 and 2")
        if not keep_alive:
            raise OllamaConfigurationError("keep_alive cannot be empty")
        if keep_alive != self.keep_alive:
            raise OllamaConfigurationError("keep_alive contains invalid whitespace")
        if any(ord(character) < 32 or ord(character) == 127 for character in keep_alive):
            raise OllamaConfigurationError("keep_alive contains control characters")

        object.__setattr__(self, "model", model)
        object.__setattr__(self, "base_url", base_url)
        object.__setattr__(self, "keep_alive", keep_alive)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class OllamaSemanticModelProvider(SemanticModelProvider):
    """Generate schema-constrained content with Ollama's native chat API."""

    def __init__(
        self,
        options: OllamaOptions,
        *,
        opener: urllib.request.OpenerDirector | None = None,
    ) -> None:
        self.options = options
        self._opener = opener or urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirectHandler(),
        )

    def generate_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: Mapping[str, object],
    ) -> ModelCompletion:
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise OllamaConfigurationError("system_prompt cannot be empty")
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise OllamaConfigurationError("user_prompt cannot be empty")
        if not isinstance(response_schema, Mapping) or not response_schema:
            raise OllamaConfigurationError(
                "response_schema must be a non-empty mapping"
            )
        payload = {
            "model": self.options.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "think": False,
            "format": dict(response_schema),
            "keep_alive": self.options.keep_alive,
            "options": {
                "num_ctx": self.options.num_ctx,
                "num_predict": self.options.num_predict,
                "temperature": self.options.temperature,
            },
        }
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise OllamaProviderError(
                "Ollama request is not JSON serializable"
            ) from exc

        request = urllib.request.Request(
            f"{self.options.base_url}/api/chat",
            data=body,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            response = self._opener.open(
                request,
                timeout=self.options.timeout_seconds,
            )
        except urllib.error.HTTPError as exc:
            detail = self._read_http_error(exc)
            raise OllamaProviderError(
                f"Ollama returned HTTP {exc.code}{detail}",
                status_code=exc.code,
            ) from exc
        except (OSError, urllib.error.URLError) as exc:
            raise OllamaProviderError(
                f"Ollama request failed: {type(exc).__name__}"
            ) from exc

        try:
            status_code = int(response.getcode())
            response_body = response.read(_MAX_RESPONSE_BYTES + 1)
        except (AttributeError, OSError, TypeError, ValueError) as exc:
            raise OllamaProviderError(
                f"Ollama response failed: {type(exc).__name__}"
            ) from exc
        finally:
            response.close()

        if not isinstance(response_body, bytes):
            raise OllamaProviderError("Ollama returned a non-byte response body")
        if len(response_body) > _MAX_RESPONSE_BYTES:
            raise OllamaProviderError("Ollama response exceeded the size limit")
        if not 200 <= status_code < 300:
            raise OllamaProviderError(
                f"Ollama returned HTTP {status_code}",
                status_code=status_code,
            )

        envelope = self._decode_envelope(response_body)
        provider_error = envelope.get("error")
        if isinstance(provider_error, str) and provider_error.strip():
            raise OllamaProviderError(f"Ollama returned an error: {provider_error}")
        if envelope.get("done") is not True or envelope.get("done_reason") != "stop":
            raise OllamaProviderError("Ollama returned an incomplete completion")

        message = envelope.get("message")
        if not isinstance(message, dict):
            raise OllamaProviderError("Ollama response is missing message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise OllamaProviderError("Ollama response is missing message content")

        response_model = envelope.get("model")
        if response_model != self.options.model:
            raise OllamaProviderError("Ollama returned an unexpected model identity")
        request_id = envelope.get("id")
        return ModelCompletion(
            content=content,
            provider="ollama",
            model=self.options.model,
            prompt_tokens=self._optional_count(envelope.get("prompt_eval_count")),
            output_tokens=self._optional_count(envelope.get("eval_count")),
            request_id=(
                request_id.strip()
                if isinstance(request_id, str) and request_id.strip()
                else None
            ),
        )

    @staticmethod
    def _decode_envelope(response_body: bytes) -> dict[str, object]:
        try:
            decoded = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise OllamaProviderError("Ollama returned malformed JSON") from exc
        if not isinstance(decoded, dict):
            raise OllamaProviderError("Ollama response must be a JSON object")
        return decoded

    @staticmethod
    def _optional_count(value: object) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return None
        return value

    @staticmethod
    def _read_http_error(error: urllib.error.HTTPError) -> str:
        try:
            body = error.read(4097)
        except OSError:
            return ""
        finally:
            error.close()
        if len(body) > 4096:
            return ""
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ""
        detail = decoded.get("error") if isinstance(decoded, dict) else None
        return f": {detail}" if isinstance(detail, str) and detail.strip() else ""
