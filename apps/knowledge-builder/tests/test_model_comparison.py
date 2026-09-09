"""Offline Groq extraction and repeatable comparison-script checks."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error

from swisstip.builder.groq_provider import GroqHTTPError, GroqSemanticModelProvider
from swisstip.builder.concept_recovery import RecoverableProvider
from swisstip.builder.model_profiles import load_model_profiles
from swisstip.builder.provider_factory import create_semantic_model_provider, ProviderFactoryConfigurationError
from swisstip.ingestion.concepts import NormalizedPage, NormalizedSection, SemanticModelError

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("model_comparison", ROOT / "scripts/test/model_comparison/run.py")
comparison = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(comparison)
MODEL = "openai/gpt-oss-120b"


class ModelComparisonTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)
        self.opener = Mock()

    def reply(self, model=MODEL, reason="stop", content='{"concepts":[]}'):
        response = Mock()
        response.getcode.return_value = 200
        response.headers = {}
        response.read.return_value = json.dumps({"model": model, "id": "req-1", "choices": [
            {"finish_reason": reason, "message": {"content": content}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}}).encode()
        return response

    def provider(self):
        return GroqSemanticModelProvider(token="secret-sentinel", model=MODEL,
            base_url="https://api.groq.com/openai/v1", timeout_seconds=180, max_tokens=4096,
            temperature=0, opener=self.opener)

    def generate(self, provider=None):
        return (provider or self.provider()).generate_structured(system_prompt="Extract.", user_prompt="Source.",
                                                                  response_schema={"type": "object"})

    def test_groq_request_and_provenance(self):
        self.opener.open.return_value = self.reply()
        result = self.generate()
        request = self.opener.open.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.groq.com/openai/v1/chat/completions")
        self.assertEqual(request.get_header("User-agent"), "SwissTIP/0.1")
        self.assertEqual(payload["max_completion_tokens"], 4096)
        self.assertEqual(payload["reasoning_effort"], "low")
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertEqual((result.provider, result.model, result.requested_model, result.observed_model), ("groq", MODEL, MODEL, MODEL))

    def test_bad_completions_and_http_failures_do_not_become_candidates(self):
        for model, reason, content in (("wrong", "stop", "{}"), (MODEL, "length", "{}"), (MODEL, "stop", "")):
            self.opener.open.return_value = self.reply(model, reason, content)
            with self.subTest(model=model, reason=reason), self.assertRaises(SemanticModelError):
                self.generate()
        self.opener.open.side_effect = urllib.error.HTTPError("https://api.groq.com", 429, "error", {}, io.BytesIO(b"secret-sentinel"))
        with self.assertRaises(GroqHTTPError) as caught:
            self.generate()
        self.assertNotIn("secret-sentinel", str(caught.exception))

    def groq_config(self):
        for name in ("semantic-models.toml", "model-profiles.toml"):
            (self.path / name).write_bytes((ROOT / "config" / name).read_bytes())
        path = self.path / "semantic-models.toml"
        path.write_text(re.sub(r'(?m)^active_profile\s*=.*$', 'active_profile = "groq_gpt_oss_120b"',
                               path.read_text(), count=1))
        return load_model_profiles(path)

    def test_groq_named_extraction_profile_requires_its_own_key(self):
        config = self.groq_config()
        with self.assertRaisesRegex(ProviderFactoryConfigurationError, "GROQ_API_KEY"):
            create_semantic_model_provider(config, environ={})
        self.opener.open.return_value = self.reply()
        result = self.generate(create_semantic_model_provider(config, environ={"GROQ_API_KEY": "test-key"}, opener=self.opener))
        self.assertEqual(result.model, MODEL)

    def test_credential_file_is_not_evaluated_and_process_values_win(self):
        path = self.path / ".env.dev"
        path.write_text('export HF_TOKEN="hf_fixture" # comment\nGROQ_API_KEY=file-value\n'
                        'DEEPSEEK_API_KEY=literal$(command)\nOTHER=ignored\n')
        keys, origins = comparison.load_keys(path, {"GROQ_API_KEY": "process-value"})
        self.assertEqual(keys, {"HF_TOKEN": "hf_fixture", "GROQ_API_KEY": "process-value", "DEEPSEEK_API_KEY": "literal$(command)"})
        self.assertEqual(origins["GROQ_API_KEY"], "process")
        self.assertEqual(comparison.redact("hf_fixture process-value literal$(command)", keys), "[REDACTED] [REDACTED] [REDACTED]")

    def test_dry_run_freezes_source_and_models_without_network(self):
        source = self.path / "page.html"
        source.write_text('<html lang="en"><main><h1>Demo</h1><p>A form is required.</p></main></html>')
        output = self.path / "comparison"
        with patch.object(comparison.TraceOpener, "open", side_effect=AssertionError("No network in dry-run")), redirect_stdout(io.StringIO()):
            code = comparison.main(["--input", str(source), "--output", str(output), "--dry-run", "--repeats", "1"])
        self.assertEqual(code, 0)
        manifest = json.loads((output / "manifest.json").read_text())
        self.assertEqual(len(manifest["runs"]), 3)
        self.assertEqual({r["planned_request_ceiling"] for r in manifest["runs"]}, {4})
        self.assertEqual({r["http_attempts"] for r in manifest["runs"]}, {0})
        self.assertEqual((output / "source.html").read_bytes(), source.read_bytes())
        for run in manifest["runs"]:
            config = load_model_profiles(output / run["directory"] / "semantic-models.toml")
            self.assertEqual(config.recovery.max_retries, 0)
        self.assertTrue((output / "code_snapshot/scripts/test/model_comparison/README.md").is_file())
        self.assertIn("Retained candidates measure pipeline completion", (output / "summary.md").read_text())

    def test_pacing_spaces_requests_without_retrying_or_counting_wait_as_api_time(self):
        seconds, waits = [0.0], []
        def sleep(delay):
            waits.append(delay)
            seconds[0] += delay
        pacer = comparison.RequestPacer(60, io.StringIO(), now=lambda: seconds[0], sleep=sleep)
        self.assertEqual(pacer.wait(), 0)
        seconds[0] += 3
        self.assertEqual(pacer.wait(), 57)
        self.assertEqual(sum(waits), 57)
        self.assertLessEqual(max(waits), 10)

    def test_groq_transient_retry_and_checkpoint_preserve_identity(self):
        config = self.groq_config()
        page = NormalizedPage("page-1", "source.html", "Title", "en", "a" * 64,
                              (NormalizedSection("section-0001", "Heading", "Source text."),))
        waits = []
        def wrapper():
            wrapped = RecoverableProvider(self.provider(), config, checkpoint_dir=self.path / "checkpoints", sleep=waits.append)
            wrapped.begin_page(page)
            return wrapped
        self.opener.open.side_effect = [urllib.error.HTTPError("https://api.groq.com", 429, "rate limit",
                                                              {"Retry-After": "3"}, io.BytesIO()), self.reply()]
        run = wrapper()
        first = self.generate(run)
        second = self.generate(wrapper())
        self.assertEqual(first, second)
        self.assertEqual((run.attempts, run.retry_attempts), (2, 1))
        self.assertEqual(waits, [3])
        self.assertEqual(self.opener.open.call_count, 2)
        self.assertEqual(second.observed_model, MODEL)

    def test_wire_trace_redacts_credentials_and_summary_counts_rejected_usage(self):
        trace = comparison.TraceOpener(self.path / "calls", {"GROQ_API_KEY": "secret-sentinel"})
        trace.opener = self.opener
        response = self.reply(model="wrong", content="secret-sentinel")
        self.opener.open.return_value = response
        provider = self.provider()
        provider._opener = trace
        with self.assertRaises(SemanticModelError):
            self.generate(provider)
        saved = (self.path / "calls/call-01.json").read_text()
        self.assertNotIn("secret-sentinel", saved)
        self.assertNotIn("Authorization", saved)
        self.assertIn("[REDACTED]", saved)
        summary = comparison.summarize({}, trace.calls, 0, 1)
        self.assertEqual(summary["retained_candidates"], 0)
        self.assertEqual(summary["observed_models"], ["wrong"])
        self.assertEqual(summary["reported_usage"], {"prompt_tokens": 10, "completion_tokens": 20})
        summary.update(profile="groq_gpt_oss_120b", repeat=1, directory="run-1", warnings=["secret-sentinel"])
        comparison.write_summary(self.path, {"source_sha256": "a" * 64, "runs": [summary]},
                                 {"GROQ_API_KEY": "secret-sentinel"})
        self.assertNotIn("secret-sentinel", (self.path / "summary.md").read_text())


if __name__ == "__main__":
    unittest.main()
