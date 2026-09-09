"""The provider nesting workaround must preserve the closed review contract."""
import copy
import json
from pathlib import Path
import unittest

from swisstip.ingestion import claim_contracts as contracts


class ReviewNormalizationTests(unittest.TestCase):
    def setUp(self):
        saved = json.loads((Path(__file__).parent / "fixtures/deepseek_v4_residence_f6c00785.json").read_text(encoding="utf-8"))
        self.concepts = saved["initial_proposals"]
        self.blocks = [b["section_id"] for b in saved["evidence"].values()]
        self.nested = json.loads(saved["raw_reviews"][0])

    def parse(self, review, changes=None, concepts=None):
        return contracts.parse_review(json.dumps(review), self.concepts if concepts is None else concepts,
                                      self.blocks, normalizations=changes)

    def test_canonical_review_is_unchanged_and_schema_remains_strict(self):
        canonical = copy.deepcopy(self.nested)
        for review in canonical["concept_reviews"]:
            for claim in review["claim_support"]:
                claim["scope_fields"] = claim["condition_logic"].pop("scope_fields")
        changes = []
        self.assertEqual(self.parse(canonical, changes), canonical)
        self.assertEqual(changes, [])
        with self.assertRaisesRegex(ValueError, "scope_fields"):
            contracts.decode(json.dumps(self.nested), contracts.review_schema(self.concepts, self.blocks))

    def test_mixed_canonical_and_nested_claims_record_exact_move_paths(self):
        original = copy.deepcopy(self.nested)
        claim = self.nested["concept_reviews"][0]["claim_support"][0]
        claim["scope_fields"] = claim["condition_logic"].pop("scope_fields")
        changes = []
        parsed = self.parse(self.nested, changes)
        self.assertEqual(changes, [
            {"from": f"response.concept_reviews[0].claim_support[{index}].condition_logic.scope_fields",
             "to": f"response.concept_reviews[0].claim_support[{index}].scope_fields"}
            for index in (1, 2)])
        for index, assessment in enumerate(parsed["concept_reviews"][0]["claim_support"]):
            original_claim = original["concept_reviews"][0]["claim_support"][index]
            self.assertEqual(assessment["scope_fields"], original_claim["condition_logic"]["scope_fields"])

    def test_incomplete_conflicting_and_unknown_fields_fail_closed(self):
        def duplicate_sibling(claim):
            claim["scope_fields"] = copy.deepcopy(claim["condition_logic"]["scope_fields"])

        mutations = {
            "missing_scope": lambda c: c["condition_logic"].pop("scope_fields"),
            "missing_scope_field": lambda c: c["condition_logic"]["scope_fields"].pop("actor"),
            "missing_decision": lambda c: c["condition_logic"]["scope_fields"]["actor"].pop("decision"),
            "wrong_scope_type": lambda c: c["condition_logic"].update(scope_fields=[]),
            "wrong_assessment_type": lambda c: c["condition_logic"]["scope_fields"].update(actor="supported"),
            "unknown_scope_field": lambda c: c["condition_logic"]["scope_fields"].update(extra={}),
            "unknown_decision": lambda c: c["condition_logic"]["scope_fields"]["actor"].update(decision="approved"),
            "unknown_logic_field": lambda c: c["condition_logic"].update(extra="unknown"),
            "unknown_claim_field": lambda c: c.update(extra="unknown"),
            "missing_logic_field": lambda c: c["condition_logic"].pop("decision"),
            "oversized_reason": lambda c: c["condition_logic"]["scope_fields"]["actor"].update(reason="x" * 501),
            "duplicate_sibling": duplicate_sibling,
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                review = copy.deepcopy(self.nested)
                mutate(review["concept_reviews"][0]["claim_support"][0])
                changes = []
                with self.assertRaises(ValueError):
                    self.parse(review, changes)
                self.assertEqual(changes, [])

    def test_duplicate_json_properties_are_rejected_before_normalization(self):
        content = json.dumps(self.nested).replace('"scope_fields": {', '"scope_fields": {}, "scope_fields": {', 1)
        with self.assertRaisesRegex(ValueError, "duplicate JSON property: scope_fields"):
            contracts.parse_review(content, self.concepts, self.blocks)

    def test_negative_and_uncertain_assessments_survive_and_block_approval(self):
        for decision in ("unsupported", "uncertain"):
            for field in ("condition_logic", *contracts.SCOPE_FIELDS):
                with self.subTest(decision=decision, field=field):
                    review = copy.deepcopy(self.nested)
                    logic = review["concept_reviews"][0]["claim_support"][0]["condition_logic"]
                    assessment = logic if field == "condition_logic" else logic["scope_fields"][field]
                    assessment.update(decision=decision, reason="Deliberate negative control.")
                    parsed = self.parse(review)
                    self.assertFalse(contracts.review_passes(parsed["concept_reviews"][0]))

    def test_normalization_does_not_bypass_semantic_or_reference_validation(self):
        mutations = {
            "unknown_claim": lambda r: r["concept_reviews"][0]["claim_support"][0].update(claim_id="absent"),
            "uncertain_logic": lambda r: r["concept_reviews"][0]["claim_support"][0]["condition_logic"].update(
                source_applicability="uncertain"),
            "invented_conditions": lambda r: r["concept_reviews"][0]["claim_support"][0]["condition_logic"].update(
                source_applicability="unconditional"),
            "missing_question": lambda r: r["concept_reviews"][0]["questions"].pop(),
            "duplicate_question": lambda r: r["concept_reviews"][0]["questions"][1].update(question_index=0),
            "missing_block": lambda r: r["block_coverage"].pop(),
            "missing_reference": lambda r: r["block_coverage"][0].update(concept_indices=[]),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                review = copy.deepcopy(self.nested)
                mutate(review)
                with self.assertRaises(ValueError):
                    self.parse(review)
        concepts = copy.deepcopy(self.concepts)
        concepts[0]["claims"][0].update(conditions=[], condition_groups=[], condition_root="")
        with self.assertRaisesRegex(ValueError, "empty conditions"):
            self.parse(self.nested, concepts=concepts)


if __name__ == "__main__":
    unittest.main()
