"""DeepSeek factory, schema modes and recoverable extraction provenance."""

import io
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import urllib.error

from swisstip.builder.concept_recovery import RecoverableProvider
from swisstip.builder.deepseek_provider import DeepSeekProviderError
from swisstip.builder.model_profiles import ModelProfileConfigurationError, load_model_profiles
from swisstip.builder.provider_factory import ProviderFactoryConfigurationError, create_semantic_model_provider
from swisstip.ingestion.concepts import NormalizedPage, NormalizedSection


ROOT = Path(__file__).resolve().parents[3]
MODEL = "deepseek-v4-pro"
REQUEST = {"system_prompt": "Extract.", "user_prompt": "Source text.", "response_schema": {"type": "object"}}
PAGE = NormalizedPage("page-1", "source.html", "Title", "en", "a" * 64,
                      (NormalizedSection("section-0001", "Heading", "Source text."),))


class DeepSeekBuilderTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)
        for name in ("semantic-models.toml", "model-profiles.toml"):
            (self.path / name).write_bytes((ROOT / "config" / name).read_bytes())
        self.config_path = self.path / "semantic-models.toml"
        text = re.sub(r'(?m)^active_profile\s*=.*$', 'active_profile = "deepseek_v4_pro"',
                      self.config_path.read_text(encoding="utf-8"), count=1)
        self.config_path.write_text(text, encoding="utf-8")
        self.config = load_model_profiles(self.config_path)
        self.opener = Mock()

    def reply(self, *, model=MODEL, finish="stop", content='{"concepts":[]}'):
        reply = Mock()
        reply.getcode.return_value = 200
        reply.headers = {}
        reply.read.return_value = json.dumps({"model": model, "choices": [{"finish_reason": finish,
                                            "message": {"content": content}}],
                                            "usage": {"prompt_tokens": 10, "completion_tokens": 4}}).encode()
        return reply

    def run_provider(self, config=None):
        config = config or self.config
        provider = create_semantic_model_provider(config, environ={"DEEPSEEK_API_KEY": "test-only-token"}, opener=self.opener)
        self.waits = []
        run = RecoverableProvider(provider, config, checkpoint_dir=self.path / "checkpoints", sleep=self.waits.append)
        run.begin_page(PAGE)
        return run

    def test_factory_requires_selected_key_and_preserves_v4_defaults(self):
        self.assertEqual(self.config.active_profile.adapter, "deepseek")
        self.assertEqual(self.config.active_profile.response_mode, "json_object")
        self.assertEqual(self.config.extraction.prompt_profile, "concept_extraction_v4")
        with self.assertRaisesRegex(ProviderFactoryConfigurationError, "DEEPSEEK_API_KEY"):
            create_semantic_model_provider(self.config, environ={"HF_TOKEN": "wrong-provider-token"}, opener=self.opener)
        self.opener.open.assert_not_called()

    def test_checkpoint_round_trip_retains_direct_identity_and_never_needs_a_second_call(self):
        self.opener.open.return_value = self.reply()
        first = self.run_provider().generate_structured(**REQUEST)
        second = self.run_provider().generate_structured(**REQUEST)
        self.assertEqual(first, second)
        self.assertEqual((first.provider, first.model, first.requested_model, first.observed_model), ("deepseek", MODEL, MODEL, MODEL))
        self.opener.open.assert_called_once()
        self.assertNotIn("test-only-token", "".join(p.read_text() for p in (self.path / "checkpoints").rglob("*.json")))

    def test_flash_profile_preserves_identity_and_rejects_pro_responses(self):
        text = self.config_path.read_text(encoding="utf-8").replace(
            'active_profile = "deepseek_v4_pro"', 'active_profile = "deepseek_v4_1_flash"')
        self.config_path.write_text(text, encoding="utf-8")
        config = load_model_profiles(self.config_path)
        provider = create_semantic_model_provider(
            config, environ={"DEEPSEEK_API_KEY": "test-only-token"}, opener=self.opener)
        self.opener.open.return_value = self.reply(model="deepseek-flash")
        result = provider.generate_structured(**REQUEST)
        self.assertEqual((result.model, result.requested_model, result.observed_model),
                         ("deepseek-flash",) * 3)
        payload = json.loads(self.opener.open.call_args.args[0].data)
        self.assertEqual(payload["model"], "deepseek-flash")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.opener.open.return_value = self.reply(model=MODEL)
        with self.assertRaises(DeepSeekProviderError):
            provider.generate_structured(**REQUEST)

    def test_transient_retry_uses_shared_attempt_budget(self):
        failure = urllib.error.HTTPError("https://api.deepseek.com", 429, "rate limit", {"Retry-After": "3"}, io.BytesIO())
        self.opener.open.side_effect = [failure, self.reply()]
        run = self.run_provider()
        run.generate_structured(**REQUEST)
        self.assertEqual((run.attempts, run.retry_attempts), (2, 1))
        self.assertEqual(self.waits, [3])

    def test_auth_failure_is_not_retried_or_checkpointed(self):
        self.opener.open.side_effect = urllib.error.HTTPError("https://api.deepseek.com", 401, "auth", {}, io.BytesIO())
        with self.assertRaises(DeepSeekProviderError):
            self.run_provider().generate_structured(**REQUEST)
        self.opener.open.assert_called_once()
        self.assertEqual(list((self.path / "checkpoints").rglob("*.json")), [])

    def test_incomplete_or_wrong_model_response_is_not_retried_or_cached(self):
        for model, finish in ((MODEL, "length"), ("deepseek-v4-flash", "stop")):
            with self.subTest(model=model, finish=finish):
                self.opener.reset_mock()
                self.opener.open.return_value = self.reply(model=model, finish=finish)
                run = self.run_provider()
                with self.assertRaises(DeepSeekProviderError):
                    run.generate_structured(**REQUEST)
                self.opener.open.assert_called_once()
                self.assertEqual(list((self.path / "checkpoints").rglob("*.json")), [])

    def test_unsupported_response_modes_fail_when_loading(self):
        original = self.config_path.read_text(encoding="utf-8")
        for mode in ("json_schema", "prompt_only"):
            self.config_path.write_text(original.replace('response_mode = "json_object"', f'response_mode = "{mode}"'), encoding="utf-8")
            with self.assertRaisesRegex(ModelProfileConfigurationError, "json_object"):
                load_model_profiles(self.config_path)


if __name__ == "__main__":
    unittest.main()
