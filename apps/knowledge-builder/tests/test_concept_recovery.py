from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import patch

from swisstip.builder.concept_recovery import RecoverableProvider
from swisstip.builder.huggingface_provider import (
    HuggingFaceHTTPError, HuggingFaceResponseError, HuggingFaceTransportError, HuggingFaceIncompleteCompletionError,
)
from swisstip.builder.model_profiles import RecoveryConfig, load_model_profiles, ModelProfileConfigurationError
from swisstip.ingestion.concepts import ModelCompletion, NormalizedPage, NormalizedSection, SemanticModelError

ROOT = Path(__file__).resolve().parents[3]
REQUEST = {"system_prompt": "Extract", "user_prompt": "Source", "response_schema": {"type": "object"}}
PAGE = NormalizedPage("page-1", "source.html", "Title", "en", "a" * 64,
                      (NormalizedSection("section-0001", "Heading", "Content"),))
COMPLETION = ModelCompletion('{"concepts": []}', "fake", "fake", 10, 5, "request-1")


class Provider:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def generate_structured(self, **request):
        self.calls += 1
        outcome = self.outcomes.pop(0) if self.outcomes else COMPLETION
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)
        self.config = load_model_profiles(ROOT / "config/semantic-models.toml")
        self.waits, self.logs = [], []

    def wrapper(self, provider, **kwargs):
        config = kwargs.pop("config", self.config)
        wrapper = RecoverableProvider(provider, config, checkpoint_dir=self.path,
                                      sleep=self.waits.append, progress=self.logs.append, **kwargs)
        wrapper.begin_page(PAGE)
        return wrapper

    def test_resume_only_calls_unfinished_request_and_separates_usage(self):
        first = self.wrapper(Provider(COMPLETION, HuggingFaceHTTPError(403)))
        self.assertEqual(first.generate_structured(**REQUEST), COMPLETION)
        second_request = dict(REQUEST, system_prompt="Review")
        with self.assertRaises(HuggingFaceHTTPError):
            first.generate_structured(**second_request)
        provider = Provider()
        resumed = self.wrapper(provider)
        self.assertEqual(resumed.generate_structured(**REQUEST), COMPLETION)
        resumed.generate_structured(**second_request)
        self.assertEqual(provider.calls, 1)
        stats = resumed.statistics()
        self.assertEqual(stats["checkpoint_hits"], 1)
        self.assertEqual(stats["network_attempts"], 1)
        self.assertEqual(stats["new_completion_prompt_tokens"], 10)

    def test_transient_failures_retry_with_exponential_backoff(self):
        for error in (HuggingFaceHTTPError(504), HuggingFaceHTTPError(429), HuggingFaceTransportError("timeout")):
            with self.subTest(error=error):
                self.waits.clear()
                provider = Provider(error, error, COMPLETION)
                run = self.wrapper(provider, fresh=True)
                run.generate_structured(**REQUEST)
                self.assertEqual(provider.calls, 3)
                self.assertEqual(self.waits, [2, 4])
                self.assertEqual(run.statistics()["retry_attempts"], 2)

    def test_nontransient_and_invalid_responses_are_not_retried_or_saved(self):
        for error in (HuggingFaceHTTPError(400), HuggingFaceHTTPError(401), HuggingFaceHTTPError(403),
                      HuggingFaceResponseError("Invalid response"), ValueError("Invalid schema")):
            with self.subTest(error=error):
                provider = Provider(error)
                run = self.wrapper(provider)
                with self.assertRaises(type(error)):
                    run.generate_structured(**REQUEST)
                self.assertEqual(provider.calls, 1)
                self.assertEqual(list(self.path.glob("*.json")), [])
        self.assertEqual(self.waits, [])

    def test_truncated_completion_usage_is_accounted_without_caching_or_retry(self):
        error = HuggingFaceIncompleteCompletionError(finish_reason="length", prompt_tokens=100,
                    output_tokens=4096, content_characters=5000, response_bytes=5200, max_output_tokens=4096)
        provider = Provider(error)
        run = self.wrapper(provider)
        with self.assertRaises(HuggingFaceIncompleteCompletionError):
            run.generate_structured(**REQUEST)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(self.waits, [])
        self.assertEqual(list(self.path.glob("*.json")), [])
        self.assertEqual(run.statistics()["incomplete_completions"][0]["output_tokens"], 4096)
        self.assertTrue(any('"content_characters": 5000' in line for line in self.logs))

    def test_derived_link_hint_does_not_change_checkpoint_identity(self):
        self.wrapper(Provider()).generate_structured(**REQUEST)
        provider = Provider()
        resumed = self.wrapper(provider)
        resumed.begin_page(replace(PAGE, sections=(replace(PAGE.sections[0], generic_link_only=True),)))
        resumed.generate_structured(**REQUEST)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(resumed.hits, 1)

    def test_per_run_and_page_budgets_count_failed_attempts(self):
        for field in ("max_model_requests_per_run", "max_model_requests_per_page"):
            with self.subTest(field=field):
                config = replace(self.config, extraction=replace(self.config.extraction, **{field: 2}))
                provider = Provider(HuggingFaceHTTPError(504), COMPLETION)
                run = self.wrapper(provider, config=config, fresh=True)
                run.generate_structured(**REQUEST)
                with self.assertRaisesRegex(SemanticModelError, "budget exhausted"):
                    run.generate_structured(**dict(REQUEST, system_prompt="Review"))
                self.assertEqual(provider.calls, 2)

    def test_retry_exhaustion_and_long_retry_after_stop_without_more_calls(self):
        for header, expected in ((None, 3), ("301", 1)):
            self.waits.clear()
            errors = [HuggingFaceHTTPError(503, retry_after=header) for _ in range(4)]
            provider = Provider(*errors)
            run = self.wrapper(provider)
            with self.assertRaises(HuggingFaceHTTPError):
                run.generate_structured(**REQUEST)
            self.assertEqual(provider.calls, expected)
        self.assertEqual(self.waits, [])

    def test_retry_after_is_respected(self):
        run = self.wrapper(Provider(HuggingFaceHTTPError(429, retry_after="7"), COMPLETION))
        run.generate_structured(**REQUEST)
        self.assertEqual(self.waits, [7])

    def test_long_provider_waits_have_heartbeats_and_preserve_attempt_budget(self):
        for seconds in (60, 120, 300):
            with self.subTest(seconds=seconds):
                self.waits.clear()
                self.logs.clear()
                provider = Provider(HuggingFaceHTTPError(504, retry_after=str(seconds)), COMPLETION)
                run = self.wrapper(provider, fresh=True)
                run.generate_structured(**REQUEST)
                self.assertEqual(sum(self.waits), seconds)
                self.assertTrue(all(0 < wait <= 15 for wait in self.waits))
                self.assertEqual(provider.calls, 2)
                self.assertEqual(run.statistics()["retry_attempts"], 1)
                self.assertIn(f"Provider Retry-After='{seconds}'; max_retry_after_seconds=300", self.logs)
                self.assertEqual(sum(line.startswith("Retry wait:") for line in self.logs), seconds // 15)
                self.assertTrue(any("0s remaining" in line for line in self.logs))

    def test_http_date_past_date_and_invalid_headers(self):
        now = datetime(2026, 9, 5, 12, 0, tzinfo=UTC)
        for header, expected in ((format_datetime(now + timedelta(seconds=65), usegmt=True), 65),
                                 (format_datetime(now - timedelta(seconds=10), usegmt=True), 2),
                                 ("invalid", 2), ("-1", 2), ("", 2), ("0", 2)):
            with self.subTest(header=header):
                self.waits.clear()
                run = self.wrapper(Provider(HuggingFaceHTTPError(503, retry_after=header), COMPLETION),
                                   fresh=True, now=lambda: now)
                run.generate_structured(**REQUEST)
                self.assertEqual(sum(self.waits), expected)

    def test_retry_after_is_logged_even_when_attempt_budget_is_exhausted(self):
        config = replace(self.config, extraction=replace(self.config.extraction, max_model_requests_per_run=1))
        provider = Provider(HuggingFaceHTTPError(504, retry_after="120"))
        run = self.wrapper(provider, config=config)
        with self.assertRaises(HuggingFaceHTTPError):
            run.generate_structured(**REQUEST)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(self.waits, [])
        self.assertTrue(any("Retry-After='120'" in line for line in self.logs))

    def test_oversized_wait_stops_safely_and_header_cannot_inject_log_lines(self):
        for header in ("9" * 500, "bad\nInjected line"):
            provider = Provider(HuggingFaceHTTPError(504, retry_after=header), COMPLETION)
            run = self.wrapper(provider, fresh=True)
            if header.isdigit():
                with self.assertRaises(HuggingFaceHTTPError):
                    run.generate_structured(**REQUEST)
                self.assertEqual(self.waits, [])
            else:
                run.generate_structured(**REQUEST)
        self.assertTrue(all("\n" not in line for line in self.logs))

    def test_interrupting_wait_preserves_previous_checkpoint_and_makes_no_retry(self):
        self.wrapper(Provider()).generate_structured(**REQUEST)
        provider = Provider(HuggingFaceHTTPError(504, retry_after="120"))
        run = self.wrapper(provider)
        with patch.object(run, "sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                run.generate_structured(**dict(REQUEST, system_prompt="Review"))
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(list(self.path.glob("*.json"))), 1)

    def test_input_settings_model_and_prompt_changes_invalidate_cache(self):
        self.wrapper(Provider()).generate_structured(**REQUEST)
        configurations = [
            replace(self.config, active_profile=replace(self.config.active_profile, model="other-model")),
            replace(self.config, active_profile=replace(self.config.active_profile, base_url="https://example.org/v1")),
            replace(self.config, generation=replace(self.config.generation, temperature=0.5)),
            replace(self.config, extraction=replace(self.config.extraction, chunk_content_characters=6000)),
        ]
        for config in configurations:
            provider = Provider()
            self.wrapper(provider, config=config).generate_structured(**REQUEST)
            self.assertEqual(provider.calls, 1)
        for changed in (replace(PAGE, content_hash="b" * 64), replace(PAGE, language="de")):
            provider = Provider()
            run = self.wrapper(provider)
            run.begin_page(changed)
            run.generate_structured(**REQUEST)
            self.assertEqual(provider.calls, 1)
        for request in (dict(REQUEST, system_prompt="Other"), dict(REQUEST, user_prompt="Other"),
                        dict(REQUEST, response_schema={"type": "array"})):
            provider = Provider()
            self.wrapper(provider).generate_structured(**request)
            self.assertEqual(provider.calls, 1)

    def test_fresh_mode_bypasses_cache_and_corruption_is_not_reused(self):
        self.wrapper(Provider()).generate_structured(**REQUEST)
        provider = Provider()
        self.wrapper(provider, fresh=True).generate_structured(**REQUEST)
        self.assertEqual(provider.calls, 1)
        path = next(self.path.glob("*.json"))
        data = json.loads(path.read_text(encoding="utf-8"))
        data["completion"]["content"] = "Corrupted"
        path.write_text(json.dumps(data), encoding="utf-8")
        provider = Provider()
        self.wrapper(provider).generate_structured(**REQUEST)
        self.assertEqual(provider.calls, 1)
        self.assertTrue(any("invalid checkpoint" in line for line in self.logs))

    def test_retry_policy_and_budget_changes_preserve_completed_work(self):
        self.wrapper(Provider()).generate_structured(**REQUEST)
        config = replace(self.config, recovery=RecoveryConfig(max_retries=1, max_retry_after_seconds=450),
                         extraction=replace(self.config.extraction, max_model_requests_per_run=40))
        provider = Provider()
        resumed = self.wrapper(provider, config=config)
        resumed.generate_structured(**REQUEST)
        self.assertEqual(provider.calls, 0)
        self.assertEqual(resumed.hits, 1)

    def test_invalid_structural_completion_can_be_evicted_without_losing_previous_stage(self):
        run = self.wrapper(Provider())
        run.generate_structured(**REQUEST)
        run.generate_structured(**dict(REQUEST, system_prompt="Review"))
        run.discard_last_checkpoint()
        self.assertEqual(len(list(self.path.glob("*.json"))), 1)
        resumed = self.wrapper(Provider())
        resumed.generate_structured(**REQUEST)
        self.assertEqual(resumed.hits, 1)

    def test_checkpoint_write_failure_stops_immediately(self):
        run = self.wrapper(Provider())
        with patch("swisstip.builder.concept_recovery.os.replace", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(SemanticModelError, "Cannot save model checkpoint"):
                run.generate_structured(**REQUEST)
        self.assertEqual(run.attempts, 1)
        self.assertEqual(list(self.path.iterdir()), [])

    def test_secret_token_is_not_written(self):
        with patch.dict("os.environ", {"HF_TOKEN": "hf_test_secret_never_write"}):
            self.wrapper(Provider()).generate_structured(**REQUEST)
        self.assertNotIn("hf_test_secret_never_write", "".join(p.read_text() for p in self.path.glob("*.json")))

    def test_recovery_configuration_is_strict_and_bounded(self):
        original = (ROOT / "config/semantic-models.toml").read_text(encoding="utf-8")
        for old, new in (("max_retries = 2", "max_retries = 6"),
                         ("max_retries = 2", "max_retries = true"),
                         ("backoff_seconds = 2.0", "backoff_seconds = 0.0"),
                         ("max_backoff_seconds = 30.0", "max_backoff_seconds = 61.0"),
                         ("max_retry_after_seconds = 300.0", "max_retry_after_seconds = 0.0"),
                         ("max_retry_after_seconds = 300.0", "max_retry_after_seconds = 3601.0"),
                         ("max_retry_after_seconds = 300.0", "max_retry_after_seconds = nan"),
                         ("max_retry_after_seconds = 300.0", "max_retry_after_seconds = true"),
                         ("review_fallback_batch_size = 2", "review_fallback_batch_size = 0"),
                         ("review_fallback_batch_size = 2", "review_fallback_batch_size = 11"),
                         ("review_fallback_batch_size = 2", "review_fallback_batch_size = true")):
            path = self.path / "config.toml"
            path.write_text(original.replace(old, new), encoding="utf-8")
            with self.assertRaises(ModelProfileConfigurationError):
                load_model_profiles(path)


if __name__ == "__main__":
    unittest.main()
