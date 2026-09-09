"""Groq GPT-OSS extraction/review using strict structured output.

Protocol: https://console.groq.com/docs/structured-outputs
The caller retains local schema, evidence, logic and coverage validation.
"""

import json
import math
import http.client
from urllib.parse import urlsplit
import urllib.error
import urllib.request

from swisstip.ingestion.concepts import ModelCompletion, SemanticModelError


class GroqHTTPError(SemanticModelError):
    def __init__(self, status_code, retry_after=None):
        super().__init__(f"Groq returned HTTP {status_code}")
        self.status_code, self.retry_after = status_code, retry_after


class GroqTransportError(SemanticModelError):
    pass


class GroqIncompleteCompletionError(SemanticModelError):
    def __init__(self, finish_reason, usage, max_tokens):
        count = lambda key: usage[key] if type(usage.get(key)) is int and usage[key] >= 0 else None
        self.diagnostics = {"finish_reason": finish_reason if isinstance(finish_reason, str) else "invalid",
                            "prompt_tokens": count("prompt_tokens"), "output_tokens": count("completion_tokens"),
                            "max_output_tokens": max_tokens}
        super().__init__(f"Groq returned an incomplete completion (finish_reason={self.diagnostics['finish_reason']!r})")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GroqSemanticModelProvider:
    def __init__(self, *, token, model, base_url, timeout_seconds, max_tokens, temperature,
                 response_mode="json_schema", opener=None):
        if not token or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in token):
            raise ValueError("Groq requires an API key without whitespace")
        if model not in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"} or response_mode != "json_schema":
            raise ValueError("Groq extraction requires GPT-OSS and json_schema response mode")
        parsed = urlsplit(base_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in base_url)):
            raise ValueError("Groq base_url must be HTTPS without credentials, query or fragment")
        parsed.port
        if (type(timeout_seconds) not in {int, float} or not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 300
                or type(max_tokens) is not int or max_tokens < 1 or type(temperature) not in {int, float}
                or not 0 <= temperature <= 2):
            raise ValueError("Invalid Groq generation limits")
        self._token, self._model, self._base_url = token, model, base_url.rstrip("/")
        self._timeout, self._max_tokens, self._temperature = timeout_seconds, max_tokens, temperature
        self._opener = opener or urllib.request.build_opener(_NoRedirect())

    def generate_structured(self, *, system_prompt, user_prompt, response_schema):
        payload = {"model": self._model, "stream": False, "temperature": self._temperature,
                   "reasoning_effort": "low", "max_completion_tokens": self._max_tokens,
                   "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                   "response_format": {"type": "json_schema", "json_schema": {
                       "name": "swisstip_structured_response", "strict": True, "schema": dict(response_schema)}}}
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(body) > 1_000_000:
            raise SemanticModelError("Groq request exceeded the byte limit")
        request = urllib.request.Request(self._base_url + "/chat/completions", data=body, method="POST",
                                        headers={"Authorization": "Bearer " + self._token, "Content-Type": "application/json",
                                                 "Accept": "application/json", "User-Agent": "SwissTIP/0.1"})
        try:
            response = self._opener.open(request, timeout=self._timeout)
            try:
                if response.getcode() != 200:
                    raise GroqHTTPError(response.getcode(), response.headers.get("Retry-After"))
                raw = response.read(1_000_001)
            finally:
                response.close()
        except urllib.error.HTTPError as exc:
            exc.close()
            raise GroqHTTPError(exc.code, exc.headers.get("Retry-After") if exc.headers else None) from exc
        except (OSError, http.client.HTTPException) as exc:
            raise GroqTransportError("Groq request could not be completed") from exc
        if not isinstance(raw, bytes) or len(raw) > 1_000_000:
            raise SemanticModelError("Groq response exceeded the byte limit or was not bytes")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise SemanticModelError("Groq returned invalid JSON") from exc
        if not isinstance(data, dict) or data.get("model") != self._model:
            raise SemanticModelError("Groq returned an unexpected or missing model identity")
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise SemanticModelError("Groq must return exactly one completion")
        choice = choices[0]
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
        if choice.get("finish_reason") != "stop":
            raise GroqIncompleteCompletionError(choice.get("finish_reason"), usage, self._max_tokens)
        message = choice.get("message")
        if not isinstance(message, dict) or message.get("refusal") or message.get("tool_calls"):
            raise SemanticModelError("Groq returned no usable assistant message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise SemanticModelError("Groq returned empty assistant content")
        count = lambda key: usage[key] if type(usage.get(key)) is int and usage[key] >= 0 else None
        return ModelCompletion(content=content, provider="groq", model=self._model,
                               requested_model=self._model, observed_model=data["model"],
                               prompt_tokens=count("prompt_tokens"), output_tokens=count("completion_tokens"),
                               request_id=data.get("id") if isinstance(data.get("id"), str) else None)
