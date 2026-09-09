from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict, replace
from pathlib import Path
from unittest.mock import patch

from swisstip.builder.concept_cli import main
from swisstip.builder.concept_batch import summarize_reports
from swisstip.builder.extraction_review import export_packet, import_decisions
from swisstip.builder.model_profiles import load_model_profiles, ModelProfileConfigurationError
from swisstip.builder.concept_recovery import RecoverableProvider, CHECKPOINT_VERSION, _digest
from swisstip.ingestion.concepts import normalize_downloaded_page, ModelCompletion
from swisstip.ingestion.claim_contracts import REVIEW_VERSION, SCOPE_FIELDS
from test_concept_batch import report
from test_model_profiles import VALID_CONFIG


class StructuredWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "models.toml"
        self.config.write_text(VALID_CONFIG, encoding="utf-8")
        self.source = self.root / "page.html"
        self.source.write_text("<h1>Application</h1><p>Apply online.</p>", encoding="utf-8")

    def test_dry_run_never_constructs_provider_and_accounts_for_source(self):
        stream = io.StringIO()
        with patch("swisstip.builder.concept_cli.create_semantic_model_provider") as provider, redirect_stdout(stream):
            result = main([str(self.source), "--config", str(self.config), "--structured", "--dry-run"])
        self.assertEqual(result, 0)
        provider.assert_not_called()
        plan = json.loads(stream.getvalue())
        self.assertEqual(plan["prompt_profile"], "concept_extraction_v4")
        self.assertEqual(plan["model_requests_sent"], 0)
        self.assertEqual(plan["planned_request_ceiling"], 4)
        self.assertEqual([b["status"] for b in plan["pages"][0]["source_inventory"]], ["excluded_policy", "pending"])
        self.assertEqual(len(plan["pages"][0]["source_sha256"]), 64)

    def test_repair_configuration_is_strict_and_optional(self):
        self.assertEqual(load_model_profiles(self.config).extraction.max_repair_attempts, 1)
        for value in ("0", "1", "2", "true", '"1"'):
            self.config.write_text(VALID_CONFIG.replace("[extraction]", f"[extraction]\nmax_repair_attempts = {value}"), encoding="utf-8")
            if value in ("0", "1"):
                self.assertEqual(load_model_profiles(self.config).extraction.max_repair_attempts, int(value))
            else:
                with self.assertRaises(ModelProfileConfigurationError):
                    load_model_profiles(self.config)

    def test_legacy_checkpoint_identity_is_preserved_and_structured_is_separate(self):
        config = load_model_profiles(self.config)
        source = normalize_downloaded_page(self.source)
        provider = RecoverableProvider(None, config)
        provider.begin_page(source)
        legacy_context = provider.context
        legacy_page = {key: getattr(source, key) for key in
                       ("document_id", "source", "title", "language", "content_hash")}
        legacy_page["sections"] = tuple({"section_id": b.section_id, "heading_path": b.heading_path,
                                         "text": b.text} for b in source.sections)
        expected = _digest({"version": CHECKPOINT_VERSION, "page": legacy_page,
                            "profile": asdict(config.active_profile), "generation": asdict(config.generation),
                            "extraction": {key: getattr(config.extraction, key) for key in (
                                "prompt_profile", "chunk_content_characters", "chunk_overlap_characters", "max_concepts_per_chunk")}})
        self.assertEqual(legacy_context, expected)
        provider.begin_page(normalize_downloaded_page(self.source, logical_blocks=True))
        self.assertNotEqual(provider.context, legacy_context)

    def test_structured_cli_runs_empty_extraction_and_coverage_through_checkpoints(self):
        class EmptyProvider:
            def __init__(self):
                self.calls = 0

            def generate_structured(self, **request):
                self.calls += 1
                payload = json.loads(request["user_prompt"])
                result = {"concepts": [], "saturated": False}
                if "concepts" in payload:
                    result = {"schema_version": REVIEW_VERSION, "concept_reviews": [], "block_coverage": [
                        {"section_id": b["section_id"], "decision": "missing", "concept_indices": [],
                         "reason": "Fixture omission."} for b in payload["untrusted_source"]["evidence"].values()]}
                model = load_model_profiles(self_config).active_profile.model
                return ModelCompletion(json.dumps(result), "ollama", model,
                                       requested_model=model, observed_model=model)
        self_config = self.config
        provider = EmptyProvider()
        argv = [str(self.source), "--config", str(self.config), "--structured",
                "--checkpoint-dir", str(self.root / "checkpoints")]
        for iteration in range(2):
            stream = io.StringIO()
            with patch("swisstip.builder.concept_cli.create_semantic_model_provider", return_value=provider), redirect_stdout(stream):
                self.assertEqual(main(argv), 0)
            result = json.loads(stream.getvalue())
            self.assertEqual(result["reports"][0]["source_inventory"][-1]["status"], "missing")
            self.assertEqual(result["reports"][0]["quality_metrics"]["repair_request_count"], 1)
        # Identical empty audits also reuse a checkpoint within the first run.
        self.assertEqual(provider.calls, 3)

    def test_structured_predicates_do_not_merge_when_prose_matches(self):
        original = report("one.html")
        first = replace(original, candidates=(replace(original.candidates[0], structured_claims=({"operator": "gt", "value": "90"},)),))
        second = replace(original, candidates=(replace(original.candidates[0], structured_claims=({"operator": "gte", "value": "90"},)),))
        self.assertEqual(len(summarize_reports([first, second])["consolidated_concepts"]), 2)

    def test_structurally_invalid_extraction_checkpoints_replay_without_review_calls(self):
        self.source.write_text("<p>Anyone who works during his/her stay requires a permit.</p>", encoding="utf-8")
        model = load_model_profiles(self.config).active_profile.model
        class InvalidTreeProvider:
            def __init__(self):
                self.calls = 0

            def generate_structured(self, **request):
                self.calls += 1
                payload = json.loads(request["user_prompt"])
                if "concepts" in payload:
                    raise AssertionError("Invalid extraction must not trigger a review call")
                ref, block = next(iter(payload["untrusted_source"]["evidence"].items()))
                claim = {"claim_id": "requirement", "kind": "requirement", "statement": block["text"],
                    "evidence_ids": [ref], "scope_evidence_ids": [ref],
                    "scope": {field: "unspecified" for field in SCOPE_FIELDS},
                    "conditions": [{"condition_id": "works", "text": "works during their stay",
                        "evidence_ids": [ref], "subject": "person", "operator": "stated", "value": "works",
                        "unit": "unspecified", "time_window": "unspecified"}],
                    "condition_groups": [], "condition_root": "OR", "exceptions": [], "limitations": []}
                result = {"concepts": [{"label": "Permit", "concept_type": "RULE",
                    "primary_section_id": block["section_id"], "claims": [claim], "questions": [], "limitations": []}],
                    "saturated": False}
                return ModelCompletion(json.dumps(result), "ollama", model, requested_model=model, observed_model=model)

        provider = InvalidTreeProvider()
        checkpoint_dir = self.root / "checkpoints"
        argv = [str(self.source), "--config", str(self.config), "--structured", "--checkpoint-dir", str(checkpoint_dir)]
        saved_checkpoints = None
        for iteration in range(2):
            stream = io.StringIO()
            with patch("swisstip.builder.concept_cli.create_semantic_model_provider", return_value=provider), redirect_stdout(stream):
                self.assertEqual(main(argv), 0)
            result = json.loads(stream.getvalue())
            page = result["reports"][0]
            self.assertFalse(page["candidates"])
            self.assertEqual(page["quality_metrics"]["request_attempt_count"], 2)
            self.assertEqual(page["quality_metrics"]["review_request_count"], 0)
            self.assertEqual(len(page["rejected_candidates"][0]["errors"]), 2)
            self.assertEqual(result["execution"]["checkpoint_hits"], 2 if iteration else 0)
            self.assertEqual(result["execution"]["network_attempts"], 0 if iteration else 2)
            checkpoint_bytes = {p.name: p.read_bytes() for p in checkpoint_dir.glob("*.json")}
            self.assertEqual(len(checkpoint_bytes), 2)
            if saved_checkpoints is not None:
                self.assertEqual(checkpoint_bytes, saved_checkpoints)
            saved_checkpoints = checkpoint_bytes
        self.assertEqual(provider.calls, 2)

    def test_legacy_serialization_keeps_original_candidate_and_report_shape(self):
        original = report("legacy.html")
        self.assertNotIn("structured_claims", original.candidates[0].to_dict())
        serialized = original.to_dict()
        self.assertNotIn("source_inventory", serialized)
        self.assertNotIn("structured_claims", serialized["candidates"][0])
        self.assertEqual(summarize_reports([original])["consolidation_policy"],
                         "exact_normalized_label_scope_type_granularity_description_language")

    def packet(self):
        path = self.root / "report.json"
        payload = {"schema_version": "swisstip.concept-proposal-report/v2",
                   "prompt_profile": "concept_extraction_v4", "source": "page.html",
                   "input_hash": "input-1", "output_hash": "output-1",
                   "candidates": [{"candidate_id": "candidate-1", "preferred_label": "<script>alert(1)</script>",
                                   "description": "Apply online."}],
                   "source_inventory": [{"section_id": "section-2", "text": "Missing condition.", "status": "missing"}],
                   "human_review_queue": [{"candidate_id": "candidate-1"}, {"section_id": "section-2"}]}
        path.write_text(json.dumps(payload), encoding="utf-8")
        directory = self.root / "review"
        export_packet(path, directory)
        return directory

    def rows(self, directory):
        with (directory / "decisions.csv").open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def write_rows(self, directory, rows):
        with (directory / "decisions.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_packet_escapes_source_and_preserves_original(self):
        directory = self.packet()
        self.assertEqual((directory / "report.json").read_bytes(), (self.root / "report.json").read_bytes())
        markup = (directory / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;", markup)
        with self.assertRaises(FileExistsError):
            export_packet(directory / "report.json", directory)

    def test_valid_import_records_decisions_without_promoting_or_certifying_coverage(self):
        directory = self.packet()
        rows = self.rows(directory)
        rows[0]["decision"] = "accept"
        rows[1].update(decision="correction", notes="Include this missing condition in a new revision.")
        self.write_rows(directory, rows)
        result = import_decisions(directory / "report.json", directory / "decisions.csv", "human-1")
        self.assertEqual(result["pending_count"], 0)
        self.assertFalse(result["publication_eligible"])
        self.assertFalse(result["verified_coverage"])
        self.assertTrue(all(d["input_hash"] == "input-1" for d in result["decisions"]))

    def test_import_rejects_stale_report_duplicate_items_and_missing_items(self):
        directory = self.packet()
        rows = self.rows(directory)
        for altered in (rows[:1], [rows[0], rows[0]], [{**rows[0], "report_sha256": "stale"}, rows[1]]):
            self.write_rows(directory, altered)
            with self.assertRaises(ValueError):
                import_decisions(directory / "report.json", directory / "decisions.csv", "human-1")
        self.write_rows(directory, rows)
        original = directory / "report.json"
        original.write_bytes(original.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "unknown"):
            import_decisions(original, directory / "decisions.csv", "human-1")

    def test_import_requires_reviewer_and_correction_notes(self):
        directory = self.packet()
        with self.assertRaisesRegex(ValueError, "identity"):
            import_decisions(directory / "report.json", directory / "decisions.csv", "")
        rows = self.rows(directory)
        rows[0]["decision"] = "correction"
        self.write_rows(directory, rows)
        with self.assertRaisesRegex(ValueError, "notes"):
            import_decisions(directory / "report.json", directory / "decisions.csv", "human-1")


if __name__ == "__main__":
    unittest.main()
