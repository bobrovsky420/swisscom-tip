"""Replay the DeepSeek GUI review failure without model calls or relaxed checks."""
import copy
import json
from pathlib import Path
import unittest

from swisstip.ingestion.concepts import CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection


class SavedReviewProvider:
    def __init__(self, saved, *, correct_second=False, negative=False, long_error=False):
        self.saved, self.correct_second, self.negative, self.long_error = saved, correct_second, negative, long_error
        self.calls, self.discarded, self.reviews = [], 0, 0

    def discard_last_checkpoint(self):
        self.discarded += 1

    def generate_structured(self, **request):
        self.calls.append(request)
        payload = json.loads(request["user_prompt"])
        if "concepts" in payload:
            content = self.saved["raw_reviews"][min(self.reviews, 1)]
            if self.reviews and self.correct_second:
                # Assistant-authored format-only control. This is NOT a newly
                # observed model correction, and is never applied in production.
                review = json.loads(content)
                for concept in review["concept_reviews"]:
                    for claim in concept["claim_support"]:
                        claim["scope_fields"] = claim["condition_logic"].pop("scope_fields")
                if self.negative:
                    review["concept_reviews"][0]["claim_support"][0]["scope_fields"]["actor"].update(
                        decision="unsupported", reason="Offline negative control: do not retain this claim.")
                content = json.dumps(review)
            if not self.reviews and self.long_error:
                review = json.loads(content)
                review["x" * 5000] = "untrusted model value"
                content = json.dumps(review)
            self.reviews += 1
        else:
            key = "repaired_proposals" if payload["repair"] else "initial_proposals"
            content = json.dumps({"concepts": self.saved[key], "saturated": False})
        return ModelCompletion(content, "offline-replay", "offline-replay")


class ReviewValidationFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.saved = json.loads((Path(__file__).parent / "fixtures/deepseek_v4_residence_f6c00785.json").read_text(encoding="utf-8"))
        self.original = copy.deepcopy(self.saved)
        self.page = NormalizedPage("saved-residence", "fixture", "Residence", "en", "saved-evidence",
            tuple(NormalizedSection(b["section_id"], "", b["text"], block_kind="paragraph", scope_id=b["scope_id"])
                  for b in self.saved["evidence"].values()), normalization_version="swisstip.logical-blocks/v2",
            source_sha256=self.saved["provenance"]["source_sha256"])

    def run_saved(self, *, options=None, **provider_options):
        provider = SavedReviewProvider(self.saved, **provider_options)
        engine = CandidateConceptExtractor(provider, active_profile="offline-replay",
            prompt_profile="concept_extraction_v4", chunk_content_characters=6400, **(options or {}))
        report = engine.extract(self.page)
        self.assertEqual(self.saved, self.original)
        return provider, report

    def test_both_saved_reviews_still_fail_and_second_reviewer_gets_its_error(self):
        provider, report = self.run_saved()
        self.assertEqual(len(provider.calls), 4)
        self.assertEqual(len(report.candidates), 0)
        self.assertEqual(provider.discarded, 2)
        self.assertEqual(report.quality_metrics["repair_request_count"], 1)
        first, second = (json.loads(provider.calls[i]["user_prompt"]) for i in (1, 3))
        self.assertNotIn("review_validation_feedback", first)
        feedback = second.pop("review_validation_feedback")
        self.assertEqual(first, second)
        self.assertEqual(feedback, {"previous_revision": 0, "validation_error": self.saved["errors"][0],
                                    "validation_error_truncated": False})
        self.assertNotEqual(provider.calls[1]["user_prompt"], provider.calls[3]["user_prompt"])
        self.assertEqual(provider.calls[1]["response_schema"], provider.calls[3]["response_schema"])
        history = report.semantic_reviews[0]["history"]
        self.assertEqual([h["raw_completion"] for h in history], self.saved["raw_reviews"])
        self.assertEqual([h["failure_stage"] for h in history], ["review_validation", "review_validation"])

    def test_format_only_control_retains_but_negative_assessment_still_blocks(self):
        for negative in (False, True):
            with self.subTest(negative=negative):
                provider, report = self.run_saved(correct_second=True, negative=negative)
                self.assertEqual(len(provider.calls), 4)
                self.assertEqual(provider.discarded, 1)
                self.assertEqual(len(report.candidates), 0 if negative else 1)
                self.assertFalse(report.quality_metrics["publication_eligible"])
                self.assertEqual(report.semantic_reviews[0]["history"][1]["proposals"], self.saved["repaired_proposals"])

    def test_disabled_repair_and_odd_budget_send_no_extra_review(self):
        for options in ({"max_repair_attempts": 0}, {"max_model_requests_per_page": 3}):
            with self.subTest(options=options):
                provider, report = self.run_saved(options=options)
                self.assertEqual(len(provider.calls), 2)
                self.assertEqual(len(report.candidates), 0)
                self.assertEqual(report.quality_metrics["repair_request_count"], 0)

    def test_model_controlled_validation_error_is_bounded_in_review_request(self):
        provider, report = self.run_saved(long_error=True, correct_second=True)
        feedback = json.loads(provider.calls[3]["user_prompt"])["review_validation_feedback"]
        # The current validator also bounds reported field names before the
        # pipeline applies its independent feedback size limit.
        self.assertLessEqual(len(feedback["validation_error"]), 2000)
        self.assertNotIn("x" * 5000, feedback["validation_error"])
        self.assertLessEqual(len(provider.calls[3]["user_prompt"]), 6400 * 4)
        self.assertIn("x" * 5000, report.semantic_reviews[0]["history"][0]["raw_completion"])


if __name__ == "__main__":
    unittest.main()
