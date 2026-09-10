"""Replay saved date proposals through validation, never as approved knowledge."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from swisstip.ingestion import claim_contracts as contracts
from swisstip.ingestion.concepts import CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection
from swisstip.ingestion.structured_extraction import StructuredExtraction
import test_structured_extraction as helpers


def uncertain_date_review(payload):
    """Synthetic control: calendar validity does not establish source meaning."""
    control = {"decision": "uncertain", "reason": "Synthetic offline control, not a model source assessment."}
    temporal = {"decision": "uncertain", "source_applicability": "uncertain",
                "reason": "Synthetic control: date validity does not establish the compared event, "
                          "assertion validity period, or eligibility interpretation."}
    return {"schema_version": contracts.REVIEW_VERSION,
        "concept_reviews": [{"concept_index": i,
            "claim_support": [dict(control, claim_id=c["claim_id"],
                condition_logic=dict(temporal),
                scope_fields={field: dict(control) for field in contracts.SCOPE_FIELDS})
                for c in item["claims"]],
            "scope": dict(control), "completeness": dict(control),
            "questions": [dict(control, question_index=q) for q in range(len(item["questions"]))]}
            for i, item in enumerate(payload["concepts"])],
        "block_coverage": [dict(control, section_id=b["section_id"], concept_indices=[])
            for b in payload["untrusted_source"]["evidence"].values()]}


class SavedDateProvider:
    def __init__(self, saved, mutation=None):
        self.saved, self.mutation = saved, mutation
        self.calls, self.review_requests = [], []

    def generate_structured(self, **request):
        self.calls.append(request)
        payload = json.loads(request["user_prompt"])
        if "concepts" in payload:
            self.review_requests.append(payload)
            content = json.dumps(uncertain_date_review(payload))
        else:
            key = "raw_repaired_completion" if payload["repair"] else "raw_initial_completion"
            content = self.saved[key]
            if self.mutation:
                changed = json.loads(content)
                self.mutation(changed)
                content = json.dumps(changed, ensure_ascii=False)
        return ModelCompletion(content, "synthetic-offline-date-replay", "synthetic-offline-date-replay")


class DateComparisonReplayTests(unittest.TestCase):
    def setUp(self):
        self.saved = json.loads((Path(__file__).parent /
            "fixtures/deepseek_v4_zh_9210329d_dates.json").read_text(encoding="utf-8"))

    def replay(self, mutation=None, max_repair_attempts=1):
        original = copy.deepcopy(self.saved)
        provenance = self.saved["provenance"]
        page = NormalizedPage("saved-zurich-group-3", "saved-fixture", "Zurich", "de",
            provenance["input_hash"],
            tuple(NormalizedSection(b["section_id"], b["heading_path"], b["text"],
                block_kind=b["kind"], scope_id=b["scope_id"], structure_issues=tuple(b["structure_issues"]))
                for b in self.saved["source_blocks"]),
            normalization_version=provenance["normalization_version"],
            source_sha256=provenance["source_sha256"])
        provider = SavedDateProvider(self.saved, mutation)
        engine = CandidateConceptExtractor(provider, active_profile="synthetic-offline-date-replay",
            prompt_profile="concept_extraction_v4", chunk_content_characters=6400,
            max_concepts_per_chunk=6, max_model_requests_per_page=12,
            max_review_input_characters=64000, max_repair_input_characters=64000,
            max_repair_attempts=max_repair_attempts)
        packets, _ = StructuredExtraction(engine).plan(page)
        self.assertEqual(packets, [list(page.sections)], "Keep the exact saved G3 request boundary")
        ceiling = engine.planned_request_count(page)
        report = engine.extract(page)
        self.assertLessEqual(len(provider.calls), ceiling)
        self.assertEqual(self.saved, original)
        return provider, report

    def test_original_and_repaired_dates_reach_review_unchanged_without_approval(self):
        provider, report = self.replay()
        self.assertEqual(len(provider.calls), 4)
        self.assertEqual(report.quality_metrics["review_request_count"], 2)
        self.assertEqual(report.quality_metrics["repair_request_count"], 1)
        self.assertEqual(report.claim_contract_version, "swisstip.structured-claims/v2")
        self.assertEqual(report.normalization_version, "swisstip.logical-blocks/v3")
        self.assertEqual(self.saved["provenance"]["claim_contract_version"], "swisstip.structured-claims/v1")
        self.assertFalse(report.candidates, "Synthetic uncertain reviews must not approve saved proposals")
        self.assertFalse(report.quality_metrics["publication_eligible"])
        self.assertEqual(len(report.rejected_candidates), 4)
        self.assertTrue(all(r["stage"] == "structured_review" for r in report.rejected_candidates))
        history = report.semantic_reviews[0]["history"]
        self.assertEqual(len(history), 2)
        self.assertEqual(len(provider.review_requests), 2)
        for revision, key in enumerate(("raw_initial_completion", "raw_repaired_completion")):
            expected = json.loads(self.saved[key])["concepts"]
            request = provider.review_requests[revision]
            self.assertEqual(len(expected), 4)
            dates = [condition for c in expected for claim in c["claims"]
                     for condition in claim["conditions"] if condition["unit"] == "date"]
            self.assertEqual(len(dates), 4)
            self.assertEqual(request["concepts"],
                [dict(c, rendered_description=contracts.describe(c)) for c in expected])
            self.assertEqual(request["untrusted_source"]["evidence"], self.saved["evidence"])
            self.assertEqual(history[revision]["proposals"], expected)
            self.assertFalse(history[revision]["structural_rejections"])
            for review in history[revision]["review"]["concept_reviews"]:
                for claim in review["claim_support"]:
                    self.assertEqual(claim["condition_logic"]["decision"], "uncertain")
                    self.assertIn("Synthetic control", claim["condition_logic"]["reason"])

    def test_fixture_preserves_original_numeric_rejections_and_completion_hashes(self):
        provenance = self.saved["provenance"]
        self.assertEqual(provenance["normalization_version"], "swisstip.logical-blocks/v3")
        self.assertEqual(provenance["claim_contract_version"], "swisstip.structured-claims/v1")
        self.assertEqual(len(self.saved["original_rejections"]), 3)
        errors = [e for rejection in self.saved["original_rejections"] for e in rejection["errors"]]
        self.assertEqual(len(errors), 4)
        self.assertTrue(all(e["reason"] == "numeric comparison requires a finite numeric value" for e in errors))
        for metadata, key in zip(provenance["completions"],
                                 ("raw_initial_completion", "raw_repaired_completion")):
            self.assertEqual(hashlib.sha256(self.saved[key].encode("utf-8")).hexdigest(),
                             metadata["raw_completion_sha256"])

    def test_date_support_does_not_bypass_calendar_quote_or_ownership_validation(self):
        def malformed_date(result):
            result["concepts"][0]["claims"][1]["conditions"][0]["value"] = "2020-02-30"

        def altered_quote(result):
            result["concepts"][0]["claims"][1]["conditions"][0]["text"] = "bis zum 30. Dezember 2020"

        def cross_scope(result):
            result["concepts"][0]["claims"][0]["evidence_ids"].append("section-0071:0:391")

        for mutation, reason in ((malformed_date, "date"),
                                 (altered_quote, "exact source excerpt"),
                                 (cross_scope, "unrelated source ownership groups")):
            with self.subTest(mutation=mutation.__name__):
                provider, report = self.replay(mutation, max_repair_attempts=0)
                self.assertEqual(len(provider.calls), 2)
                rejection, = [r for r in report.rejected_candidates if r["stage"] == "structural_validation"]
                self.assertEqual(rejection["proposal_index"], 0)
                self.assertEqual(rejection["stage"], "structural_validation")
                self.assertIn(reason, rejection["reason"])
                review, = provider.review_requests
                self.assertEqual(len(review["concepts"]), 3)
                self.assertNotIn("Brexit", [c["label"] for c in review["concepts"]])
                self.assertFalse(report.candidates)
                self.assertFalse(report.quality_metrics["publication_eligible"])

    def test_contract_version_changes_identity_for_unchanged_synthetic_nondated_claim(self):
        helper = helpers.StructuredTests()
        page = helper.page("<p>Apply online.</p>")
        with patch.object(contracts, "VERSION", "swisstip.structured-claims/v1"):
            old = helper.engine(helpers.Provider(), max_repair_attempts=0).extract(page)
        current = helper.engine(helpers.Provider(), max_repair_attempts=0).extract(page)
        self.assertEqual(old.claim_contract_version, "swisstip.structured-claims/v1")
        self.assertEqual(current.claim_contract_version, "swisstip.structured-claims/v2")
        self.assertEqual(old.candidates[0].structured_claims, current.candidates[0].structured_claims)
        self.assertNotEqual(old.candidates[0].candidate_id, current.candidates[0].candidate_id)
        self.assertNotEqual(old.human_review_queue[0]["revision_hash"],
                            current.human_review_queue[0]["revision_hash"])
        self.assertFalse(current.quality_metrics["publication_eligible"])


if __name__ == "__main__":
    unittest.main()
