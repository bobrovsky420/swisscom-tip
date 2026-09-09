"""DeepSeek V4 Pro JSON chat protocol shared by extraction and ranking.

Protocol: https://api-docs.deepseek.com/api/create-chat-completion/
JSON-object output is not schema enforcement. Callers validate their own schema.
Thinking is explicitly disabled to keep output within the caller's token budget.
"""

from dataclasses import dataclass
import http.client
import json
import math
from urllib.parse import urlsplit
import urllib.error
import urllib.request


MODEL = "deepseek-v4-pro"
BASE_URL = "https://api.deepseek.com"
MAX_BYTES = 1_000_000


class DeepSeekError(RuntimeError):
    """Provider failure containing no response content or credentials."""


class DeepSeekHTTPError(DeepSeekError):
    def __init__(self, status_code, retry_after=None):
        super().__init__(f"DeepSeek returned HTTP {status_code}")
        self.status_code = status_code
        self.retry_after = retry_after


class DeepSeekTransportError(DeepSeekError):
    pass


class DeepSeekIncompleteCompletionError(DeepSeekError):
    def __init__(self, finish_reason, max_tokens):
        self.diagnostics = {"finish_reason": finish_reason if isinstance(finish_reason, str) else "invalid",
                            "max_output_tokens": max_tokens}
        super().__init__(f"DeepSeek returned an incomplete completion (finish_reason={self.diagnostics['finish_reason']!r})")


@dataclass(frozen=True)
class DeepSeekCompletion:
    content: str
    model: str
    prompt_tokens: int | None
    output_tokens: int | None
    request_id: str | None


def validate_settings(model, base_url, timeout, *, allow_loopback=False):
    if model != MODEL:
        raise ValueError(f"DeepSeek adapter requires model {MODEL!r}")
    parsed = urlsplit(base_url)
    secure = parsed.scheme == "https" or (allow_loopback and parsed.scheme == "http" and
                                         parsed.hostname in {"localhost", "127.0.0.1", "::1"})
    if (not secure or not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in base_url)):
        raise ValueError("DeepSeek base_url must be an absolute HTTPS URL without credentials, query or fragment")
    parsed.port  # Reject invalid ports during configuration loading.
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 300:
        raise ValueError("DeepSeek timeout must be greater than zero and at most 300 seconds")


def request_payload(*, model, system_prompt, user_prompt, response_schema, max_tokens, temperature=0.0):
    if model != MODEL:
        raise ValueError(f"DeepSeek adapter requires model {MODEL!r}")
    if any(not isinstance(p, str) or not p.strip() for p in (system_prompt, user_prompt)):
        raise ValueError("DeepSeek prompts must be non-empty strings")
    if not isinstance(response_schema, dict) or not response_schema:
        raise ValueError("DeepSeek response_schema must be a non-empty object")
    if type(max_tokens) is not int or not 1 <= max_tokens <= 393216:
        raise ValueError("DeepSeek max_tokens must be a positive integer at most 393216")
    if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
        raise ValueError("DeepSeek temperature must be between 0 and 2")
    contract = json.dumps(response_schema, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return {
        "model": model, "stream": False, "thinking": {"type": "disabled"},
        "response_format": {"type": "json_object"}, "max_tokens": max_tokens, "temperature": temperature,
        "messages": [{"role": "system", "content": system_prompt +
                      "\nReturn only a complete compact JSON object, without Markdown or commentary. "
                      "Follow this trusted JSON Schema (validated locally):\n" + contract},
                     {"role": "user", "content": user_prompt}],
    }


def _json(text):
    def distinct(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DeepSeekError("DeepSeek returned duplicate JSON keys")
            result[key] = value
        return result

    def invalid_constant(_):
        raise DeepSeekError("DeepSeek returned a non-finite JSON number")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            invalid_constant(value)
        return number

    try:
        return json.loads(text, object_pairs_hook=distinct, parse_constant=invalid_constant, parse_float=finite_float)
    except (ValueError, UnicodeError, TypeError) as exc:
        raise DeepSeekError("DeepSeek returned invalid JSON") from exc


def decode_completion(data, *, model, max_tokens):
    if not isinstance(data, dict) or data.get("model") != model:
        raise DeepSeekError("DeepSeek returned an unexpected or missing model identity")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise DeepSeekError("DeepSeek must return exactly one completion")
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        raise DeepSeekIncompleteCompletionError(choice.get("finish_reason"), max_tokens)
    message = choice.get("message")
    if (not isinstance(message, dict) or message.get("refusal") or message.get("tool_calls")
            or message.get("role", "assistant") != "assistant"):
        raise DeepSeekError("DeepSeek returned no usable assistant message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip() or not isinstance(_json(content), dict):
        raise DeepSeekError("DeepSeek returned no JSON object content")
    usage = data.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    count = lambda key: usage[key] if type(usage.get(key)) is int and usage[key] >= 0 else None
    return DeepSeekCompletion(content, data["model"], count("prompt_tokens"), count("completion_tokens"),
                              data.get("id") if isinstance(data.get("id"), str) else None)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class DeepSeekClient:
    """Bounded non-streaming request, without redirects or implicit retries."""

    def __init__(self, *, token, model=MODEL, base_url=BASE_URL, timeout=180.0, opener=None):
        validate_settings(model, base_url, timeout)
        if not isinstance(token, str) or not token or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in token):
            raise ValueError("DeepSeek requires a non-empty API key without whitespace")
        self._token, self._model, self._url, self._timeout = token, model, base_url.rstrip("/"), timeout
        self._opener = opener or urllib.request.build_opener(_NoRedirect())

    def complete(self, **kwargs):
        payload = request_payload(model=self._model, **kwargs)
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(body) > MAX_BYTES:
            raise DeepSeekError("DeepSeek request exceeded the byte limit")
        request = urllib.request.Request(self._url + "/chat/completions", data=body, method="POST",
                                        headers={"Authorization": "Bearer " + self._token,
                                                 "Content-Type": "application/json", "Accept": "application/json"})
        try:
            response = self._opener.open(request, timeout=self._timeout)
            try:
                if response.getcode() != 200:
                    raise DeepSeekHTTPError(response.getcode(), response.headers.get("Retry-After"))
                raw = response.read(MAX_BYTES + 1)
            finally:
                response.close()
        except urllib.error.HTTPError as exc:
            exc.close()
            raise DeepSeekHTTPError(exc.code, exc.headers.get("Retry-After") if exc.headers else None) from exc
        except (OSError, urllib.error.URLError, http.client.HTTPException) as exc:
            raise DeepSeekTransportError("DeepSeek request could not be completed") from exc
        if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
            raise DeepSeekError("DeepSeek response exceeded the byte limit or was not bytes")
        return decode_completion(_json(raw), model=self._model, max_tokens=payload["max_tokens"])
