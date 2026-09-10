"""Replay large Zurich proposals without fabricating live review verdicts."""
import copy
import json
from pathlib import Path
import unittest

from swisstip.ingestion import claim_contracts as contracts
from swisstip.ingestion.concepts import CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection
from swisstip.ingestion.source_structure import VERSION as NORMALIZATION_VERSION
from test_structured_extraction import Provider
import test_structured_extraction as helpers


def uncertain_review(payload):
    """Assistant-authored control: exercise schema without approving any claims."""
    uncertain = {"decision": "uncertain", "reason": "Offline control, not a model source assessment."}
    return {"schema_version": contracts.REVIEW_VERSION,
        "concept_reviews": [
            {"concept_index": i,
             "claim_support": [dict(uncertain, claim_id=c["claim_id"],
                 condition_logic=dict(uncertain, source_applicability="uncertain"),
                 scope_fields={field: dict(uncertain) for field in contracts.SCOPE_FIELDS})
                 for c in item["claims"]],
             "scope": dict(uncertain), "completeness": dict(uncertain),
             "questions": [dict(uncertain, question_index=q) for q in range(len(item["questions"]))]}
            for i, item in enumerate(payload["concepts"])],
        "block_coverage": [dict(uncertain, section_id=b["section_id"], concept_indices=[])
            for b in payload["untrusted_source"]["evidence"].values()]}


class ReplayProvider:
    def __init__(self, saved):
        self.saved, self.calls, self.review_requests = saved, [], []

    def generate_structured(self, **request):
        self.calls.append(request)
        payload = json.loads(request["user_prompt"])
        if "concepts" in payload:
            self.review_requests.append(request)
            content = json.dumps(uncertain_review(payload))
        else:
            content = self.saved["raw_repaired_completion" if payload["repair"] else "raw_initial_completion"]
        return ModelCompletion(content, "offline-replay", "offline-replay")


class ReviewInputLimitTests(unittest.TestCase):
    def setUp(self):
        self.saved = json.loads((Path(__file__).parent / "fixtures/deepseek_v4_zh_e4f1f67a.json").read_text(encoding="utf-8"))

    def replay(self, group, limit):
        original = copy.deepcopy(group)
        provider = ReplayProvider(group)
        page = NormalizedPage("saved-zurich", "fixture", "Zurich", "de", "saved-evidence",
            tuple(NormalizedSection(b["section_id"], "", b["text"], block_kind="paragraph", scope_id=b["scope_id"])
                for b in group["evidence"].values()), normalization_version=NORMALIZATION_VERSION,
            source_sha256=self.saved["provenance"]["source_sha256"])
        engine = CandidateConceptExtractor(provider, active_profile="offline-replay",
            prompt_profile="concept_extraction_v4", max_concepts_per_chunk=6,
            max_review_input_characters=limit)
        ceiling = engine.planned_request_count(page)
        report = engine.extract(page)
        self.assertEqual(group, original)
        self.assertLessEqual(len(provider.calls), ceiling)
        return provider, report

    def test_saved_repaired_bundles_reach_full_review_without_approving_them(self):
        for group in self.saved["groups"]:
            with self.subTest(failure=group["original_failures"][0]):
                old_provider, old_report = self.replay(group, 25600)
                self.assertEqual(len(old_provider.calls), 2)
                self.assertEqual(old_report.quality_metrics["review_request_count"], 0)
                self.assertTrue(any("max_review_input_characters=25600" in w for w in old_report.warnings))
                provider, report = self.replay(group, 64000)
                self.assertEqual(len(provider.calls), 3)
                self.assertEqual(report.quality_metrics["review_request_count"], 1)
                self.assertEqual(report.quality_metrics["repair_request_count"], 1)
                request, = provider.review_requests
                self.assertGreater(len(request["user_prompt"]), 25600)
                self.assertLessEqual(len(request["user_prompt"]), 64000)
                payload = json.loads(request["user_prompt"])
                expected = json.loads(group["raw_repaired_completion"])["concepts"]
                self.assertEqual(payload["concepts"],
                    [dict(c, rendered_description=contracts.describe(c)) for c in expected])
                evidence = payload["untrusted_source"]["evidence"]
                self.assertEqual({ref: {k:b[k] for k in ("section_id", "scope_id", "text")}
                                  for ref, b in evidence.items()}, group["evidence"])
                self.assertIn("review", report.semantic_reviews[0]["history"][-1])
                self.assertFalse(report.candidates, "Uncertain controls must not approve saved proposals")
                self.assertFalse(report.quality_metrics["publication_eligible"])

    def test_complete_serialized_review_boundary_counts_rendered_description(self):
        helper = helpers.StructuredTests()
        page = helper.page("<p>Apply online.</p>")
        provider = Provider()
        helper.engine(provider, max_repair_attempts=0).extract(page)
        request = provider.calls[1]["user_prompt"]
        payload = json.loads(request)
        self.assertIn("rendered_description", payload["concepts"][0])
        for cap, expected_calls, expected_candidates in ((len(request), 2, 1), (len(request) - 1, 1, 0)):
            with self.subTest(cap=cap):
                provider = Provider()
                report = helper.engine(provider, max_repair_attempts=0, max_review_input_characters=cap).extract(page)
                self.assertEqual(len(provider.calls), expected_calls)
                self.assertEqual(len(report.candidates), expected_candidates)
                if expected_calls == 1:
                    self.assertIn(f"{len(request)} characters > max_review_input_characters={cap}", report.warnings[0])

    def test_large_review_allowance_does_not_expand_extraction_feedback_limit(self):
        helper = helpers.StructuredTests()
        def generate(result, payload):
            result["concepts"][0]["claims"][0]["statement"] = "x" * 900
            result["saturated"] = True
        provider = Provider(generate=generate)
        report = helper.engine(provider, chunk_content_characters=500, chunk_overlap_characters=0,
                               max_review_input_characters=64000).extract(helper.page("<p>Apply online.</p>"))
        self.assertEqual(len(provider.calls), 2)
        self.assertTrue(any("extraction input exceeds bounded source/feedback allowance" in w for w in report.warnings))
        self.assertEqual(report.quality_metrics["repair_request_count"], 0)

    def test_review_validation_feedback_counts_against_the_same_limit(self):
        helper = helpers.StructuredTests()
        def review(result, payload):
            if "review_validation_feedback" not in payload:
                result["unknown"] = "Trigger one invalid review for the offline boundary check."
        page = helper.page("<p>Apply online.</p>")
        baseline = Provider(review=review)
        helper.engine(baseline).extract(page)
        first, second = [r["user_prompt"] for r in baseline.calls if "concepts" in json.loads(r["user_prompt"])]
        self.assertGreater(len(second), len(first))
        self.assertIn("review_validation_feedback", json.loads(second))
        provider = Provider(review=review)
        report = helper.engine(provider, max_review_input_characters=len(second) - 1).extract(page)
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(report.quality_metrics["review_request_count"], 1)
        self.assertEqual(report.semantic_reviews[0]["history"][-1]["failure_stage"], "review_input")
        self.assertFalse(report.candidates)

    def test_review_limit_rejects_non_positive_or_non_integer_values(self):
        for cap in (0, -1, True, 64000.0, "64000"):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                CandidateConceptExtractor(None, active_profile="fixture", max_review_input_characters=cap)


if __name__ == "__main__":
    unittest.main()
