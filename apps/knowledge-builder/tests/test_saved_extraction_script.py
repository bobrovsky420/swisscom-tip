"""Offline checks for repeating saved GUI extractions from the command line."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from swisstip.builder.model_profiles import load_model_profiles


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("saved_extraction", ROOT / "scripts/admin/extract.py")
saved_extraction = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(saved_extraction)
TOKEN_NAME = "DEEPSEEK_API_KEY"


class SavedExtractionScriptTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)
        self.job = self.path / "saved-job"
        self.job.mkdir()
        for name in ("semantic-models.toml", "model-profiles.toml"):
            (self.job / name).write_bytes((ROOT / "config" / name).read_bytes())
        config = self.job / "semantic-models.toml"
        config.write_text(re.sub(r'(?m)^active_profile\s*=.*$', 'active_profile = "deepseek_v4_pro"',
                                 config.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        (self.job / "page.html").write_text(
            '<html lang="en"><main><h1>Residence</h1><p>A permit is required.</p></main></html>',
            encoding="utf-8")
        (self.job / "result.json").write_text('{"original":true}', encoding="utf-8")
        (self.job / "progress.log").write_text("Original job log\n", encoding="utf-8")
        self.original_files = {p.name: p.read_bytes() for p in self.job.iterdir()}
        self.output = self.path / "new-run"
        self.env_file = self.path / ".env.dev"

    def arguments(self, *extra):
        return ["--job-dir", str(self.job), "--output", str(self.output),
                "--env-file", str(self.env_file), *extra]

    def assert_original_unchanged(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.job.iterdir()}, self.original_files)

    def test_dry_run_copies_inputs_and_resolves_config_without_provider_or_key(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(saved_extraction, "create_semantic_model_provider",
                             side_effect=AssertionError("Dry-run must not construct a provider")) as provider, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = saved_extraction.main(self.arguments("--dry-run"))
        self.assertEqual(code, 0)
        provider.assert_not_called()
        self.assert_original_unchanged()
        self.assertEqual((self.output / "inputs/page.html").read_bytes(), self.original_files["page.html"])
        self.assertEqual([p.name for p in (self.output / "inputs").iterdir()], ["page.html"])
        plan = json.loads((self.output / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["model_requests_sent"], 0)
        self.assertEqual(plan["planned_request_ceiling"], 4)
        self.assertEqual(len(plan["pages"]), 1)
        config = load_model_profiles(self.output / "semantic-models.toml")
        self.assertEqual(config.active_profile.name, "deepseek_v4_pro")
        self.assertEqual(config.recovery.max_retries, 0)
        manifest = json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["credential_source"], "missing")
        self.assertEqual(manifest["source_sha256"], {"page.html": saved_extraction.digest(self.original_files["page.html"])})
        self.assertEqual(manifest["original_config_sha256"], saved_extraction.digest(self.original_files["semantic-models.toml"]))
        for argument in ("--structured", "--fresh-inference", "--checkpoint-dir", "--dry-run"):
            self.assertIn(argument, manifest["arguments"])
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["extraction_status"], "planned")

    def test_process_credential_has_priority_without_reading_env_file(self):
        with patch.dict(os.environ, {TOKEN_NAME: "process-sentinel"}, clear=True), \
                patch.object(Path, "is_file", side_effect=AssertionError("Process credential must win")):
            credentials, origin = saved_extraction.load_credential(TOKEN_NAME, self.env_file)
        self.assertEqual(credentials, {TOKEN_NAME: "process-sentinel"})
        self.assertEqual(origin, "process")

    def test_corpus_input_keeps_manifest_and_provenance_in_repeat(self):
        target = self.job / 'asset-one'
        target.mkdir()
        path = target / 'response.html'
        (self.job / 'page.html').rename(path)
        snapshot = dict(relative_path='response.html', sha256=saved_extraction.digest(path.read_bytes()),
                        requested_url='https://example.gov/permit', final_url='https://example.gov/permit',
                        retrieved_at='2026-09-10T00:00:00Z', content_type='text/html', review_flags=[])
        manifest = dict(corpus_id='hackathon-test', corpus_path='pages/test/attempt-001/response.html', snapshots=[snapshot])
        (target / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(saved_extraction.main(self.arguments('--dry-run')), 0)
        result = json.loads((self.output / 'result.json').read_text())
        self.assertEqual(result['pages'][0]['provenance']['corpus_id'], 'hackathon-test')
        self.assertEqual(result['model_requests_sent'], 0)
        self.assertEqual((self.output / 'inputs/asset-one/manifest.json').read_bytes(), (target / 'manifest.json').read_bytes())

    def test_env_credential_is_literal_and_only_selected_key_is_loaded(self):
        literal = "literal$(command)`other`"
        self.env_file.write_text('HF_TOKEN=ignored\nexport DEEPSEEK_API_KEY="' + literal +
                                 '" # comment\nGROQ_API_KEY=also-ignored\n', encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            credentials, origin = saved_extraction.load_credential(TOKEN_NAME, self.env_file)
        self.assertEqual(credentials, {TOKEN_NAME: literal})
        self.assertEqual(origin, self.env_file.name)
        self.assertEqual(saved_extraction.redact(f"token={literal}", credentials), "token=[REDACTED]")

    def test_missing_credential_stops_before_creating_output_or_calling_builder(self):
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(saved_extraction, "extract_main") as builder, \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            saved_extraction.main(self.arguments())
        self.assertEqual(caught.exception.code, 2)
        builder.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assert_original_unchanged()

    def test_usable_draft_with_policy_warning_matches_gui_attention_and_redacts_artifacts(self):
        secret = 'secret-"sentinel"\\12345'
        warning = "Human review required; coverage assessments and model approvals do not publish knowledge."
        result = {"quality_summary": {"candidate_count": 1}, "reports": [{
            "candidates": [{"preferred_label": "Residence permits"}],
            "warnings": [warning], "rejected_candidates": [],
            "semantic_reviews": [{"history": [{"error": "Diagnostic " + secret}]}],
        }], "execution": {"network_attempts": 2}}
        console, errors = io.StringIO(), io.StringIO()

        def fake_builder(arguments, *, provider_factory):
            self.assertIn("--fresh-inference", arguments)
            self.assertNotIn("--dry-run", arguments)
            provider_factory("resolved-config")
            sys.stderr.write("Provider diagnostic: " + secret[:8])
            sys.stderr.flush()
            sys.stderr.write(secret[8:] + "\n")
            print(json.dumps(result))
            return 0

        with patch.dict(os.environ, {TOKEN_NAME: secret, "HF_TOKEN": "unrelated"}, clear=True), \
                patch.object(saved_extraction, "create_semantic_model_provider") as provider, \
                patch.object(saved_extraction, "extract_main", side_effect=fake_builder), \
                redirect_stdout(console), redirect_stderr(errors):
            code = saved_extraction.main(self.arguments())
        self.assertEqual(code, 0)
        provider.assert_called_once_with("resolved-config", environ={TOKEN_NAME: secret})
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["extraction_status"], "draft_ready")
        self.assertEqual(summary["gui_equivalent_status"], "needs_attention")
        self.assertEqual(summary["candidate_labels"], ["Residence permits"])
        self.assertEqual(summary["history_failures"], ["Diagnostic [REDACTED]"])
        self.assertEqual(summary["warnings"], [warning])
        for text in [console.getvalue(), errors.getvalue(), *[
                (self.output / name).read_text(encoding="utf-8")
                for name in ("result.json", "progress.log", "summary.json", "manifest.json")]]:
            self.assertNotIn(secret, text)
            self.assertNotIn(json.dumps(secret)[1:-1], text)
        self.assertIn("[REDACTED]", errors.getvalue())
        self.assert_original_unchanged()

    def test_zero_candidates_returns_nonzero_even_when_builder_succeeds(self):
        def fake_builder(arguments, *, provider_factory):
            print(json.dumps({"quality_summary": {"candidate_count": 0}, "reports": [{
                "candidates": [], "warnings": ["Review validation failed"],
            }]}))
            return 0

        with patch.dict(os.environ, {TOKEN_NAME: "fixture-key"}, clear=True), \
                patch.object(saved_extraction, "extract_main", side_effect=fake_builder), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = saved_extraction.main(self.arguments())
        self.assertEqual(code, 2)
        summary = json.loads((self.output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["builder_exit_code"], 0)
        self.assertEqual(summary["script_exit_code"], 2)
        self.assertEqual(summary["gui_equivalent_status"], "needs_attention")
        self.assertEqual(summary["extraction_status"], "no_usable_draft_for_some_pages")
        self.assert_original_unchanged()

    def test_existing_output_is_preserved_without_starting_builder(self):
        self.output.mkdir()
        sentinel = self.output / "result.json"
        sentinel.write_text("Previous report", encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(saved_extraction, "extract_main") as builder, \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            saved_extraction.main(self.arguments("--dry-run"))
        builder.assert_not_called()
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "Previous report")
        self.assert_original_unchanged()


if __name__ == "__main__":
    unittest.main()
