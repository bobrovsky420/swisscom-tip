from __future__ import annotations

import unittest
from dataclasses import replace

from swisstip.builder.concept_batch import summarize_reports
from swisstip.ingestion.concepts import CandidateConcept, ConceptProposalReport, EvidenceSpan


def report(source, scope="EU/EFTA residents", description="Apply online."):
    candidate = CandidateConcept(
        "candidate-1", "Permit application", (), "PROCESS", "ANSWERABLE",
        description, scope, ("How do I apply?",), 0.8,
        (EvidenceSpan("section-0001", "Apply online.", 0, 13),), (),
    )
    return ConceptProposalReport(
        "swisstip.concept-proposal-report/v1", "page-1", source, "Permit", "en",
        "input-hash", "output-hash", "fake", "fake", "fake", "extraction",
        "concept_extraction_v2", "2026-09-05T12:00:00Z", 1, 10, 5, (),
        (candidate,), (), quality_metrics={"accepted_proposals": 1, "rejected_proposals": 0},
    )


class BatchQualityTests(unittest.TestCase):
    def test_aliases_and_wording_variants_are_suggested_not_merged(self):
        first = report("one.html")
        alias = replace(first, source="alias.html", candidates=(replace(
            first.candidates[0], preferred_label="Residence application",
            alternative_labels=("Permit application",), scope="Other residents"),))
        variant = replace(first, source="variant.html", candidates=(replace(
            first.candidates[0], preferred_label="Online permit application"),))
        result = summarize_reports([first, alias, variant])
        self.assertEqual(len(result["consolidated_concepts"]), 3)
        pairs = result["duplicate_review_pairs"]
        self.assertTrue(any(p["reason"] == "shared_label_or_alias" and not p["same_scope"] for p in pairs))
        self.assertTrue(any(p["reason"] == "similar_label_tokens" for p in pairs))

    def test_matching_claims_consolidate_and_retain_both_sources(self):
        result = summarize_reports([report("one.html"), report("two.html")])
        groups = result["consolidated_concepts"]
        self.assertEqual(len(groups), 1)
        self.assertEqual([m["source"] for m in groups[0]["members"]], ["one.html", "two.html"])
        self.assertTrue(all(m["candidate"]["evidence"] for m in groups[0]["members"]))
        self.assertEqual(result["quality_summary"]["candidate_count"], 2)
        self.assertEqual(result["quality_summary"]["prompt_tokens"], 20)

    def test_different_scope_and_conflicting_claims_are_preserved_for_review(self):
        reports = [report("eu.html"), report("third.html", "Third-country residents"),
                   report("conflict.html", description="Apply in person.")]
        result = summarize_reports(reports)
        self.assertEqual(len(result["consolidated_concepts"]), 3)
        self.assertEqual(len(result["duplicate_review_groups"]), 1)
        self.assertEqual(len(result["duplicate_review_groups"][0]["group_ids"]), 3)

    def test_unknown_usage_and_empty_output_are_not_reported_as_success_metrics(self):
        empty = replace(report("empty.html"), candidates=(), prompt_tokens=None,
                        quality_metrics={"accepted_proposals": 0, "rejected_proposals": 0})
        metrics = summarize_reports([empty])["quality_summary"]
        self.assertIsNone(metrics["prompt_tokens"])
        self.assertIsNone(metrics["rejection_rate"])
        self.assertEqual(metrics["empty_page_count"], 1)


if __name__ == "__main__":
    unittest.main()
