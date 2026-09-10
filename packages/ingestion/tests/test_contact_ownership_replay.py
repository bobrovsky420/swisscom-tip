"""Replay rejected contact ownership without treating structural validity as approval."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from swisstip.ingestion import claim_contracts as contracts
from swisstip.ingestion.concepts import (
    CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection,
)
from swisstip.ingestion.structured_extraction import StructuredExtraction


def partitioned_control(completion):
    """Hand-authored test repair; production extraction never partitions these claims."""
    original, = completion["concepts"]
    completion["concepts"] = [
        dict(copy.deepcopy(original), label="Synthetic telephone control",
             primary_section_id="section-0088", claims=copy.deepcopy(original["claims"][:2])),
        dict(copy.deepcopy(original), label="Synthetic electronic-contact control",
             primary_section_id="section-0092", claims=copy.deepcopy(original["claims"][2:3])),
        dict(copy.deepcopy(original), label="Synthetic responsibility control",
             primary_section_id="section-0098", claims=copy.deepcopy(original["claims"][3:])),
    ]


def synthetic_population_review(payload, population_decision):
    """Isolate the population review gate; all assessments are synthetic controls."""
    supported = {"decision": "supported", "reason": "Synthetic test control, not a model source assessment."}
    population = {"decision": population_decision,
        "reason": "Synthetic control: an ownership-valid concept does not establish population applicability."}
    concepts, evidence = payload["concepts"], payload["untrusted_source"]["evidence"]
    return {"schema_version": contracts.REVIEW_VERSION,
        "concept_reviews": [{"concept_index": index,
            "claim_support": [dict(supported, claim_id=claim["claim_id"],
                condition_logic=dict(supported,
                    source_applicability="conditional" if claim["conditions"] else "unconditional"),
                scope_fields={field: dict(population if field == "population" else supported)
                              for field in contracts.SCOPE_FIELDS}) for claim in concept["claims"]],
            "scope": dict(supported), "completeness": dict(supported),
            "questions": [dict(supported, question_index=q) for q in range(len(concept["questions"]))]}
            for index, concept in enumerate(concepts)],
        "block_coverage": [{"section_id": block["section_id"],
            "decision": "covered" if any(ref in contracts.evidence_references(c) for c in concepts) else "missing",
            "concept_indices": [i for i, concept in enumerate(concepts) if ref in contracts.evidence_references(concept)],
            "reason": "Synthetic citation-routing control, not a model coverage assessment."}
            for ref, block in evidence.items()]}


class SavedContactProvider:
    def __init__(self, saved, *, synthetic_repair=False, initial_mutation=None, population_decision="uncertain"):
        self.saved = saved
        self.synthetic_repair = synthetic_repair
        self.initial_mutation = initial_mutation
        self.population_decision = population_decision
        self.requests, self.review_requests = [], []

    def generate_structured(self, **request):
        payload = json.loads(request["user_prompt"])
        self.requests.append(payload)
        if "concepts" in payload:
            self.review_requests.append(payload)
            content = json.dumps(synthetic_population_review(payload, self.population_decision))
        else:
            repairing = payload["repair"] is not None
            content = self.saved["raw_repaired_completion" if repairing else "raw_initial_completion"]
            if (repairing and self.synthetic_repair) or self.initial_mutation:
                changed = json.loads(content)
                partitioned_control(changed)
                if self.initial_mutation:
                    self.initial_mutation(changed)
                content = json.dumps(changed, ensure_ascii=False)
        return ModelCompletion(content, "synthetic-offline-contact-replay", "synthetic-offline-contact-replay")


class ContactOwnershipReplayTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).parent / "fixtures/deepseek_v4_zh_b5ec2579_contacts.json"
        self.saved = json.loads(self.path.read_text(encoding="utf-8"))

    def replay(self, *, max_repair_attempts=1, **options):
        before = copy.deepcopy(self.saved)
        provenance = self.saved["provenance"]
        page = NormalizedPage("saved-zurich-contact-packet", "saved-fixture", "Zurich", "de",
            provenance["input_hash"],
            tuple(NormalizedSection(block["section_id"], block["heading_path"], block["text"],
                block_kind=block["kind"], scope_id=block["scope_id"],
                structure_issues=tuple(block["structure_issues"])) for block in self.saved["source_blocks"]),
            normalization_version=provenance["normalization_version"], source_sha256=provenance["source_sha256"])
        provider = SavedContactProvider(self.saved, **options)
        engine = CandidateConceptExtractor(provider, active_profile="synthetic-offline-contact-replay",
            prompt_profile="concept_extraction_v4", chunk_content_characters=6400,
            max_concepts_per_chunk=6, max_model_requests_per_page=12,
            max_review_input_characters=64000, max_repair_input_characters=64000,
            max_repair_attempts=max_repair_attempts)
        packets, _ = StructuredExtraction(engine).plan(page)
        self.assertEqual(packets, [list(page.sections)], "Preserve the saved fourth packet boundary")
        report = engine.extract(page)
        self.assertLessEqual(len(provider.requests), engine.planned_request_count(page))
        for request in provider.requests:
            self.assertEqual(request["untrusted_source"]["evidence"], self.saved["evidence"])
            self.assertEqual(request["untrusted_source"]["scope_ids"],
                             ["scope-0047", "scope-0048", "scope-0050"])
        self.assertEqual(self.saved, before)
        self.assertFalse(report.candidates, "No synthetic control may approve the saved contact proposals")
        self.assertFalse(report.quality_metrics["publication_eligible"])
        self.assertFalse(report.quality_metrics["coverage_complete"])
        return provider, report

    def test_saved_fixture_preserves_exact_identical_completions_and_ownership_failure(self):
        self.assertEqual(self.saved["raw_initial_completion"], self.saved["raw_repaired_completion"])
        for key, metadata in zip(("raw_initial_completion", "raw_repaired_completion"),
                                 self.saved["provenance"]["completions"], strict=True):
            self.assertEqual(hashlib.sha256(self.saved[key].encode("utf-8")).hexdigest(),
                             metadata["raw_completion_sha256"])
        concept, = json.loads(self.saved["raw_initial_completion"])["concepts"]
        self.assertEqual(len(concept["claims"]), 4)
        evidence = self.saved["evidence"]
        self.assertEqual({evidence[ref]["scope_id"] for ref in contracts.evidence_references(concept)},
                         {"scope-0047", "scope-0048", "scope-0050"})
        for claim in concept["claims"]:
            self.assertEqual(len({evidence[ref]["scope_id"]
                                  for ref in contracts.evidence_references({"claims": [claim]})}), 1)
        for revision in self.saved["original_rejections"]:
            rejection, = revision
            self.assertEqual(rejection["proposal"], concept)
            self.assertEqual(rejection["errors"], [
                {"path": "claims", "reason": "evidence crosses unrelated source ownership groups"}])

    def test_unchanged_initial_and_repair_are_rejected_before_semantic_review(self):
        provider, report = self.replay()
        self.assertEqual(len(provider.requests), 2)
        self.assertFalse(provider.review_requests)
        self.assertEqual(report.quality_metrics["review_request_count"], 0)
        self.assertEqual(report.quality_metrics["repair_request_count"], 1)
        history = report.semantic_reviews[0]["history"]
        self.assertEqual([item["structural_rejections"] for item in history], self.saved["original_rejections"])
        self.assertEqual([item["review_skipped"] for item in history],
                         ["repairing structural errors", "no structurally valid proposals"])
        feedback = provider.requests[1]["repair"]
        self.assertEqual(feedback["proposals"], history[0]["proposals"])
        self.assertEqual(feedback["failure_stage"], "structural_validation")
        self.assertEqual(feedback["structural_rejections"][0]["errors"],
                         self.saved["original_rejections"][0][0]["errors"])
        self.assertEqual({row["status"] for row in report.source_inventory}, {"invalid_response"})
        self.assertEqual(len(report.rejected_candidates), 1)
        self.assertEqual(report.rejected_candidates[0]["stage"], "structural_validation")

    def test_manual_partition_reaches_review_but_population_failures_retain_nothing(self):
        original, = json.loads(self.saved["raw_initial_completion"])["concepts"]
        for decision in ("uncertain", "unsupported"):
            with self.subTest(population_decision=decision):
                provider, report = self.replay(synthetic_repair=True, population_decision=decision)
                self.assertEqual(len(provider.requests), 3)
                self.assertEqual(report.quality_metrics["review_request_count"], 1)
                self.assertEqual(report.quality_metrics["repair_request_count"], 1)
                review, = provider.review_requests
                self.assertEqual(len(review["concepts"]), 3)
                self.assertEqual([claim for concept in review["concepts"] for claim in concept["claims"]],
                                 original["claims"], "Preserve all claim text, scope values and citations")
                history = report.semantic_reviews[0]["history"]
                self.assertTrue(history[0]["structural_rejections"])
                self.assertFalse(history[1]["structural_rejections"])
                self.assertEqual(len(report.rejected_candidates), 3)
                self.assertTrue(all(item["stage"] == "structured_review" for item in report.rejected_candidates))
                for assessment in history[1]["review"]["concept_reviews"]:
                    self.assertFalse(contracts.review_passes(assessment))
                    self.assertEqual(assessment["scope"]["decision"], "supported")
                    self.assertEqual(assessment["completeness"]["decision"], "supported")
                    for claim in assessment["claim_support"]:
                        self.assertEqual(claim["decision"], "supported")
                        self.assertEqual(claim["scope_fields"]["population"]["decision"], decision)
                        self.assertIn("Synthetic control", claim["scope_fields"]["population"]["reason"])

    def test_partition_control_cannot_hide_cross_scope_evidence_or_unsupported_primary(self):
        cross_ref = "section-0092:0:97"
        phone_ref = "section-0088:0:92"

        def claim_evidence(result):
            result["concepts"][0]["claims"][0]["evidence_ids"].append(cross_ref)

        def scope_evidence(result):
            result["concepts"][0]["claims"][0]["scope_evidence_ids"].append(cross_ref)

        def add_condition(result, ref):
            claim = result["concepts"][0]["claims"][0]
            claim["conditions"] = [{"condition_id": "synthetic-condition",
                "text": self.saved["evidence"][ref]["text"], "evidence_ids": [ref],
                "subject": "synthetic", "operator": "stated", "value": "unspecified",
                "unit": "unspecified", "time_window": "unspecified"}]
            claim["condition_root"] = "synthetic-condition"
            return claim

        def condition_evidence(result):
            add_condition(result, cross_ref)

        def group_evidence(result):
            claim = add_condition(result, phone_ref)
            claim["condition_groups"] = [{"group_id": "synthetic-group", "operator": "AND",
                "members": ["synthetic-condition"], "evidence_ids": [cross_ref]}]
            claim["condition_root"] = "synthetic-group"

        def exception_evidence(result):
            result["concepts"][0]["claims"][0]["exceptions"] = [{
                "text": self.saved["evidence"][cross_ref]["text"], "evidence_ids": [cross_ref]}]

        def unsupported_primary(result):
            result["concepts"][0]["primary_section_id"] = "section-0089"

        mutations = [(mutation, "evidence crosses unrelated source ownership groups") for mutation in (
            claim_evidence, scope_evidence, condition_evidence, group_evidence, exception_evidence)]
        mutations.append((unsupported_primary, "primary section has no supporting evidence"))
        for mutation, reason in mutations:
            with self.subTest(mutation=mutation.__name__):
                provider, report = self.replay(initial_mutation=mutation, max_repair_attempts=0)
                self.assertEqual(len(provider.requests), 2)
                rejection, = [item for item in report.rejected_candidates if item["stage"] == "structural_validation"]
                self.assertEqual(rejection["proposal_index"], 0)
                self.assertEqual(rejection["reason"], reason)
                review, = provider.review_requests
                self.assertEqual([concept["primary_section_id"] for concept in review["concepts"]],
                                 ["section-0092", "section-0098"])


if __name__ == "__main__":
    unittest.main()
