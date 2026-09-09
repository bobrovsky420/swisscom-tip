"""Official DeepSeek JSON protocol and bounded failures, with no remote calls."""

import io
import json
import unittest
from unittest.mock import Mock
import urllib.error

from swisstip.core.deepseek import (
    DeepSeekClient, DeepSeekError, DeepSeekHTTPError, DeepSeekIncompleteCompletionError,
    DeepSeekTransportError, MAX_BYTES, MODEL, validate_settings,
)


def response(content='{"status":"ready"}', **overrides):
    return {"model": MODEL, "id": "request-1", "choices": [{"finish_reason": "stop",
            "message": {"role": "assistant", "content": content, "reasoning_content": "not-the-answer"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 4}, **overrides}


REQUEST = {"system_prompt": "Extract supported claims.", "user_prompt": "Untrusted source text.",
           "response_schema": {"type": "object", "properties": {"status": {"type": "string"}}},
           "max_tokens": 4096}


class DeepSeekProtocolTests(unittest.TestCase):
    def client(self, payload=None):
        self.reply = Mock()
        self.reply.getcode.return_value = 200
        self.reply.headers = {}
        self.reply.read.return_value = json.dumps(response() if payload is None else payload).encode()
        self.opener = Mock()
        self.opener.open.return_value = self.reply
        return DeepSeekClient(token="secret-sentinel", opener=self.opener)

    def test_request_uses_direct_model_json_object_and_bounded_nonthinking_output(self):
        result = self.client().complete(**REQUEST)
        request = self.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-sentinel")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], MODEL)
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertFalse(payload["stream"])
        self.assertNotIn("max_completion_tokens", payload)
        self.assertNotIn("reasoning_effort", payload)
        self.assertIn(json.dumps(REQUEST["response_schema"], separators=(",", ":")), payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][1]["content"], REQUEST["user_prompt"])
        self.assertEqual((result.model, result.prompt_tokens, result.output_tokens, result.request_id), (MODEL, 10, 4, "request-1"))
        self.assertEqual(result.content, '{"status":"ready"}')
        self.reply.close.assert_called_once()

    def test_wrong_identity_refusal_empty_content_and_malformed_json_fail_closed(self):
        cases = [response(model="deepseek-v4-flash"), response(model=None), response(choices=[]),
                 response(choices=[{}, {}]), response(""), response("[]"), response("not JSON"),
                 response('{"id":1,"id":2}'), response('{"id":NaN}'), response('{"id":1e999}'),
                 response(choices=[{"finish_reason": "stop", "message": {"content": "{}", "refusal": "no"}}])]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(DeepSeekError):
                self.client(payload).complete(**REQUEST)

    def test_non_stop_responses_never_return_partial_content(self):
        for reason in ("length", "content_filter", "tool_calls", "insufficient_system_resource", None):
            payload = response()
            payload["choices"][0]["finish_reason"] = reason
            with self.subTest(reason=reason), self.assertRaises(DeepSeekIncompleteCompletionError) as caught:
                self.client(payload).complete(**REQUEST)
            self.assertNotIn("ready", str(caught.exception))
            self.assertEqual(caught.exception.diagnostics["max_output_tokens"], 4096)

    def test_http_auth_throttle_and_redirect_errors_are_redacted_and_not_retried(self):
        for status in (302, 401, 403, 429, 503):
            client = self.client()
            error = urllib.error.HTTPError("https://api.deepseek.com", status, "private failure",
                                           {"Retry-After": "7"}, io.BytesIO(b"secret-sentinel"))
            self.opener.open.side_effect = error
            with self.subTest(status=status), self.assertRaises(DeepSeekHTTPError) as caught:
                client.complete(**REQUEST)
            self.assertEqual(caught.exception.status_code, status)
            self.assertEqual(caught.exception.retry_after, "7")
            self.assertNotIn("secret-sentinel", str(caught.exception))
            self.opener.open.assert_called_once()
            self.assertTrue(error.closed)

    def test_transport_and_body_limits(self):
        client = self.client()
        self.opener.open.side_effect = TimeoutError("secret-sentinel")
        with self.assertRaises(DeepSeekTransportError) as caught:
            client.complete(**REQUEST)
        self.assertNotIn("secret-sentinel", str(caught.exception))
        client = self.client()
        self.reply.read.return_value = b" " * (MAX_BYTES + 1)
        with self.assertRaisesRegex(DeepSeekError, "byte limit"):
            client.complete(**REQUEST)
        self.reply.read.assert_called_once_with(MAX_BYTES + 1)
        self.reply.close.assert_called_once()
        client = self.client()
        with self.assertRaisesRegex(DeepSeekError, "request exceeded"):
            client.complete(**{**REQUEST, "user_prompt": "x" * MAX_BYTES})
        self.opener.open.assert_not_called()

    def test_configuration_is_checked_before_any_request(self):
        for url in ("http://api.deepseek.com", "https://user:secret@api.deepseek.com", "https://api.deepseek.com?token=x",
                    "https://api.deepseek.com#fragment", "https://api.deepseek.com:70000", "https://api.deepseek.com/ bad"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_settings(MODEL, url, 60)
        for timeout in (0, -1, 301, True, float("nan")):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                validate_settings(MODEL, "https://api.deepseek.com", timeout)
        for token in ("", " ", "key\r\nInjected: value"):
            with self.subTest(token=token), self.assertRaises(ValueError):
                DeepSeekClient(token=token)


if __name__ == "__main__":
    unittest.main()
