from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from swisstip.ingestion import claim_contracts as contracts
from swisstip.ingestion.concepts import (
    CandidateConceptExtractor, ModelCompletion, SemanticModelError,
    STRUCTURED_PROMPT_PROFILE, normalize_downloaded_page,
)
from swisstip.ingestion.structured_extraction import StructuredExtraction


def concept(ref, block):
    return {"label": "Application", "concept_type": "PROCESS",
            "primary_section_id": block["section_id"], "questions": [], "limitations": [],
            "claims": [{"claim_id": "claim-1", "kind": "procedure", "statement": "Apply online.",
                        "evidence_ids": [ref], "scope_evidence_ids": [ref],
                        "scope": {k: "unspecified" for k in (
                            "population", "jurisdiction", "permit_status", "actor", "recipient", "procedure_branch")},
                        "conditions": [], "condition_groups": [], "condition_root": "",
                        "exceptions": [], "limitations": []}]}


def audit(concepts, evidence):
    supported = {"decision": "supported", "reason": "Fixture assessment."}
    return {"concept_reviews": [{"concept_index": i,
             "claim_support": [dict(supported, claim_id=c["claim_id"]) for c in item["claims"]],
             "scope": dict(supported), "completeness": dict(supported),
             "questions": [dict(supported, question_index=q) for q in range(len(item["questions"]))]}
             for i, item in enumerate(concepts)],
            "block_coverage": [{"section_id": b["section_id"],
                "decision": "covered" if any(ref in contracts.evidence_references(c) for c in concepts) else "missing",
                "concept_indices": [i for i, c in enumerate(concepts) if ref in contracts.evidence_references(c)],
                "reason": "Fixture coverage assessment."} for ref, b in evidence.items()]}


class Provider:
    def __init__(self, generate=None, review=None, fail=False):
        self.calls, self.discarded = [], 0
        self.generate, self.review, self.fail = generate, review, fail

    def discard_last_checkpoint(self):
        self.discarded += 1

    def generate_structured(self, **request):
        self.calls.append(request)
        if self.fail:
            raise SemanticModelError("fixture provider unavailable")
        payload = json.loads(request["user_prompt"])
        evidence = payload["untrusted_source"]["evidence"]
        if "concepts" in payload:
            result = audit(payload["concepts"], evidence)
            if self.review:
                self.review(result, payload)
        else:
            result = {"concepts": [concept(ref, block) for ref, block in evidence.items()], "saturated": False}
            if self.generate:
                self.generate(result, payload)
        return ModelCompletion(json.dumps(result), "fixture", "fixture", prompt_tokens=10, output_tokens=5)


class StructuredTests(unittest.TestCase):
    def test_custom_prompts_are_used_for_extraction_review_and_repair(self):
        from swisstip.ingestion.prompt_templates import load_prompts
        with tempfile.TemporaryDirectory() as directory:
            extraction, review = Path(directory) / "extract.md", Path(directory) / "review.md"
            extraction.write_text("Custom structured extraction.", encoding="utf-8")
            review.write_text("Custom structured review.", encoding="utf-8")
            prompts = load_prompts(STRUCTURED_PROMPT_PROFILE, extraction_prompt_file=extraction,
                                   review_prompt_file=review)
        provider = Provider(generate=lambda result, payload: result.update(saturated=True))
        report = self.engine(provider, prompts=prompts).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual([call["system_prompt"] for call in provider.calls],
                         [prompts.extraction.text, prompts.review.text] * 2)
        self.assertEqual(report.to_dict()["effective_prompts"], prompts.to_dict())

    def page(self, html):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.html"
            path.write_text(html, encoding="utf-8")
            return normalize_downloaded_page(path, logical_blocks=True)

    def engine(self, provider, **options):
        return CandidateConceptExtractor(provider, active_profile="fixture",
                                         prompt_profile=STRUCTURED_PROMPT_PROFILE, **options)

    def test_infobox_heading_does_not_own_continued_condition_list(self):
        page = self.page("<h1>Family</h1><p>Conditions:</p><ul><li>Income</li></ul>"
                         "<aside><h2>Information</h2><p>Proof is required.</p></aside>"
                         "<ul><li>Housing</li><li>Language</li></ul>")
        blocks = [b for b in page.sections if b.block_kind != "heading"]
        self.assertEqual(len({b.scope_id for b in blocks}), 1)
        self.assertEqual(blocks[-1].heading_path, "Family")
        self.assertIn("Housing", blocks[-1].text)
        self.assertIn("Language", blocks[-1].text)
        self.assertEqual(blocks[-1].block_kind, "list")

    def test_sibling_panels_are_separate_scopes_and_contacts_remain(self):
        page = self.page("<h1>Residence</h1><section><h2>Permit A</h2><p>Rule A.</p></section>"
                         "<section><h2>Permit B</h2><p>Rule B.</p></section>"
                         "<footer><h2>Contact</h2><address>Office: 0123456</address></footer>")
        blocks = [b for b in page.sections if b.block_kind != "heading"]
        self.assertEqual(len({b.scope_id for b in blocks}), 3)
        _, inventory = StructuredExtraction(self.engine(None)).plan(page)
        self.assertEqual(next(r for r in inventory if r["kind"] == "address")["status"], "pending")

    def test_table_rows_preserved_and_complex_spans_quarantined(self):
        page = self.page("<table><tr><th>Permit</th><th>Duration</th></tr>"
                         "<tr><td>A</td><td>30 days</td></tr></table>")
        self.assertIn("A | 30 days |", page.sections[0].text)
        complex_page = self.page("<table><tr><td colspan='2'>Ambiguous</td></tr></table>")
        provider = Provider()
        report = self.engine(provider).extract(complex_page)
        self.assertFalse(provider.calls)
        self.assertEqual(report.source_inventory[0]["status"], "unresolved_structure")
        self.assertTrue(report.human_review_queue)

    def test_contact_link_targets_are_preserved_without_fetching_them(self):
        page = self.page("<address><a href='mailto:office@example.test'>Email</a> "
                         "<a href='tel:+410000000'>Call</a></address>")
        self.assertIn("mailto:office@example.test", page.sections[0].text)
        self.assertIn("tel:+410000000", page.sections[0].text)

    def test_oversized_group_is_visible_and_never_partially_extracted(self):
        page = self.page("<h1>Conditions</h1><ul><li>" + "word " * 200 + "</li></ul>")
        provider = Provider()
        report = self.engine(provider, chunk_content_characters=500, chunk_overlap_characters=0).extract(page)
        self.assertFalse(provider.calls)
        self.assertEqual(report.source_inventory[-1]["status"], "not_processed_size")

    def test_positive_control_retains_claims_and_requires_human_approval(self):
        page = self.page("<html lang='de'><h1>Antrag</h1><p>Apply online.</p></html>")
        provider = Provider()
        report = self.engine(provider).extract(page)
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(len(report.candidates), 1)
        candidate = report.candidates[0]
        self.assertTrue(candidate.structured_claims)
        self.assertEqual(candidate.validation_state, "CANDIDATE")
        span = candidate.evidence[0]
        block = next(b for b in page.sections if b.section_id == span.section_id)
        self.assertEqual(block.evidence_text[span.start:span.end], span.quote)
        self.assertFalse(report.quality_metrics["coverage_complete"])
        self.assertFalse(report.human_review_queue[0]["publication_eligible"])
        self.assertEqual(report.prompt_tokens, 20)

    def test_empty_extraction_still_audits_all_source_blocks_and_repairs_once(self):
        provider = Provider(generate=lambda result, payload: result.update(concepts=[]))
        report = self.engine(provider).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual(len(provider.calls), 4)
        self.assertEqual(report.quality_metrics["review_request_count"], 2)
        self.assertEqual(report.source_inventory[0]["status"], "missing")
        self.assertEqual(len(report.semantic_reviews[0]["history"]), 2)

    def test_failed_dimension_repairs_then_retains_revised_proposal(self):
        def first_failure(result, payload):
            if len(provider.calls) == 2:
                result["concept_reviews"][0]["scope"]["decision"] = "unsupported"
        provider = Provider(review=first_failure)
        report = self.engine(provider).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual(len(provider.calls), 4)
        self.assertEqual(len(report.candidates), 1)
        self.assertIn("repair", json.loads(provider.calls[2]["user_prompt"]))
        self.assertEqual(report.semantic_reviews[0]["history"][0]["review"]["concept_reviews"][0]["scope"]["decision"], "unsupported")

    def test_missing_claim_assessment_rejects_response_and_discards_checkpoint(self):
        provider = Provider(review=lambda result, payload: result["concept_reviews"][0].update(claim_support=[]))
        report = self.engine(provider, max_repair_attempts=0).extract(self.page("<p>Apply online.</p>"))
        self.assertFalse(report.candidates)
        self.assertEqual(provider.discarded, 1)
        self.assertEqual(report.source_inventory[0]["status"], "invalid_response")

    def test_failed_question_does_not_hide_supported_claim(self):
        def question(result, payload):
            result["concepts"][0]["questions"] = ["Am I eligible?"]
        def reject_question(result, payload):
            result["concept_reviews"][0]["questions"][0]["decision"] = "unsupported"
        report = self.engine(Provider(question, reject_question), max_repair_attempts=0).extract(self.page("<p>Apply online.</p>"))
        self.assertFalse(report.candidates)
        self.assertEqual(report.rejected_candidates[0]["review"]["claim_support"][0]["decision"], "supported")

    def test_budget_reserves_coverage_for_later_groups_before_repairs(self):
        page = self.page("<h1>A</h1><p>" + "word " * 700 + "</p><h1>B</h1><p>" + "word " * 700 + "</p>")
        provider = Provider(generate=lambda result, payload: result.update(concepts=[]))
        engine = self.engine(provider, max_model_requests_per_page=4)
        self.assertEqual(engine.planned_request_count(page), 4)
        report = engine.extract(page)
        self.assertEqual(len(provider.calls), 4)
        self.assertEqual(len(report.semantic_reviews), 2)
        self.assertEqual(report.quality_metrics["repair_request_count"], 0)

    def test_provider_failure_is_reported_and_does_not_claim_coverage(self):
        provider = Provider(fail=True)
        report = self.engine(provider).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual(len(provider.calls), 1)
        self.assertFalse(report.candidates)
        self.assertEqual(report.source_inventory[0]["status"], "provider_failure")

    def test_cross_scope_evidence_is_rejected_even_in_same_packet(self):
        def borrow(result, payload):
            result["concepts"][0]["claims"][0]["evidence_ids"] = list(payload["untrusted_source"]["evidence"])
        report = self.engine(Provider(generate=borrow), max_repair_attempts=0).extract(
            self.page("<h1>A</h1><p>Apply online.</p><h1>B</h1><p>Different procedure.</p>"))
        self.assertEqual(len(report.candidates), 1)
        self.assertIn("ownership", report.rejected_candidates[0]["reason"])

    def test_saturation_remains_visible_after_bounded_repair(self):
        provider = Provider(generate=lambda result, payload: result.update(saturated=True))
        report = self.engine(provider).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual(len(provider.calls), 4)
        self.assertEqual(report.source_inventory[0]["status"], "saturated_requires_review")

    def test_logic_preserves_or_and_rejects_cycles_and_invented_quotes(self):
        evidence = {"e1": {"section_id": "s1", "text": "More than 90 working days. More than 3 months."}}
        item = concept("e1", evidence["e1"])
        claim = item["claims"][0]
        claim["conditions"] = [{"condition_id": identity, "text": text, "evidence_ids": ["e1"],
                                "subject": "stay", "operator": "gt", "value": value,
                                "unit": unit, "time_window": "unspecified"}
                               for identity, text, value, unit in (
                                   ("days", "More than 90 working days.", "90", "working days"),
                                   ("months", "More than 3 months.", "3", "months"))]
        claim["condition_groups"] = [{"group_id": "either", "operator": "OR", "members": ["days", "months"], "evidence_ids": ["e1"]}]
        claim["condition_root"] = "either"
        contracts.validate_concept(item, evidence, {"s1": "scope1"})
        self.assertIn("working days. OR More than 3 months.", contracts.describe(item))
        broken = copy.deepcopy(item)
        broken["claims"][0]["condition_groups"][0]["members"].append("either")
        with self.assertRaisesRegex(ValueError, "cyclic"):
            contracts.validate_concept(broken, evidence, {"s1": "scope1"})
        claim["conditions"][0]["text"] = "At least 90 days."
        with self.assertRaisesRegex(ValueError, "exact source"):
            contracts.validate_concept(item, evidence, {"s1": "scope1"})

    def test_duplicate_keys_and_non_boolean_saturation_rejected(self):
        schema = contracts.extraction_schema(["e1"], 6)
        for raw in ('{"concepts":[],"saturated":false,"saturated":true}', '{"concepts":[],"saturated":1}'):
            with self.assertRaises(ValueError):
                contracts.decode(raw, schema)


if __name__ == "__main__":
    unittest.main()
