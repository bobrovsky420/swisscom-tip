from __future__ import annotations

import copy
from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path

from swisstip.ingestion import claim_contracts as contracts
from swisstip.ingestion.concepts import (
    CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection, SemanticModelError,
    STRUCTURED_PROMPT_PROFILE, normalize_downloaded_page,
)
from swisstip.ingestion.structured_extraction import StructuredExtraction
from swisstip.ingestion.source_structure import VERSION as NORMALIZATION_VERSION


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
    return {"schema_version": contracts.REVIEW_VERSION, "concept_reviews": [{"concept_index": i,
             "claim_support": [dict(supported, claim_id=c["claim_id"],
                 condition_logic=dict(supported, source_applicability="conditional" if c["conditions"] else "unconditional"),
                 scope_fields={field: dict(supported) for field in contracts.SCOPE_FIELDS}) for c in item["claims"]],
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
    def test_schema_invalid_completion_is_in_repair_feedback_and_not_reviewed(self):
        def generate(result, payload):
            if payload["repair"] is None:
                item = result["concepts"][0]
                del item["questions"]
                item["scope_evidence_ids"] = item["claims"][0].pop("scope_evidence_ids")
            else:
                feedback = payload["repair"]
                self.assertEqual(feedback["failure_stage"], "extraction_validation")
                self.assertIn("missing=['questions']", feedback["validation_error"])
                self.assertIn("unknown=['scope_evidence_ids']", feedback["validation_error"])
                self.assertFalse(feedback["invalid_completion_truncated"])
                bad = json.loads(feedback["invalid_completion"])
                self.assertIn("scope_evidence_ids", bad["concepts"][0])
                self.assertNotIn("questions", bad["concepts"][0])
        provider = Provider(generate=generate)
        report = self.engine(provider).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(provider.discarded, 1)
        self.assertEqual(len(json.loads(provider.calls[2]["user_prompt"])["concepts"]), 1)

    def test_schema_repair_feedback_is_bounded_and_marks_truncation(self):
        def generate(result, payload):
            if payload["repair"] is None:
                result["unknown"] = "x" * 9000
            else:
                feedback = payload["repair"]
                self.assertEqual(len(feedback["invalid_completion"]), 6000)
                self.assertTrue(feedback["invalid_completion_truncated"])
        provider = Provider(generate=generate)
        report = self.engine(provider).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual(len(report.candidates), 1)

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

    def test_sem_navigation_components_stay_in_inventory_but_not_model_evidence(self):
        page = self.page('''<html><head><title>Residence</title></head><body>
            <header role="banner"><p>Federal site menu</p><nav>Languages</nav></header>
            <div class="mod mod-mainnavigation"><h2>Main Navigation</h2>
              <ul class="nav navbar-nav"><li>Entry and work</li></ul></div>
            <div class="mod mod-breadcrumb"><h2>Breadcrumb</h2><ol><li>Home</li></ol></div>
            <div class="mod mod-leftnavigation"><h2>Subnavigation</h2><p>Back</p></div>
            <h1>Residence</h1><p>Apply online.</p>
            <div class="mod mod-breadcrumb"><h2>Menu between conditions</h2><p>Back</p></div>
            <ul><li>Attach proof.</li></ul>
            </body></html>''')
        provider = Provider()
        report = self.engine(provider).extract(page)
        excluded = [r for r in report.source_inventory if r["status"] == "excluded_policy"]
        excluded_text = "\n".join(r["text"] for r in excluded)
        for text in ("Federal site menu", "Main Navigation", "Breadcrumb", "Subnavigation", "Menu between conditions"):
            self.assertIn(text, excluded_text)
            self.assertNotIn(text, "\n".join(call["user_prompt"] for call in provider.calls))
        evidence = json.loads(provider.calls[0]["user_prompt"])["untrusted_source"]["evidence"]
        self.assertEqual({v["text"] for v in evidence.values()},
                         {"Residence\nApply online.", "Residence\nAttach proof."})
        substantive = [b for b in page.sections if b.block_kind in {"paragraph", "list"}]
        self.assertEqual(substantive[0].scope_id, substantive[1].scope_id)
        self.assertEqual(page.normalization_version, NORMALIZATION_VERSION)

    def test_zurich_navigation_preserves_article_header_wrapper_conditions_and_contacts(self):
        page = self.page('''<body>
            <header id="header"><h1>Navigation</h1><div class="mdl-skiplinks">Skip links</div>
              <div><p>Search error placeholder</p></div></header>
            <main><header class="mdl-page-header"><h1>Residence</h1><p>Introductory requirement.</p>
              <div class="mdl-page-header__logo-container">Site logo</div></header>
            <div class="mdl-page-header__breadcrumb"><nav>Home breadcrumb</nav></div>
            <div class="mdl-anchornav__wrapper">
              <div class="mdl-anchornav"><h2>On this page</h2><ul><li>Contents link</li></ul></div>
              <section><header id="header"><h2>Permit A</h2><p>Permit scope.</p></header>
                <ul><li>Income</li><li>Housing</li></ul></section>
              <section><h2>Permit B</h2><p>Different requirement.</p></section>
            </div>
            <div class="breadcrumb-guidance"><p>Keep this similarly named component.</p></div>
            </main><footer><ul class="mdl-footer__menu"><li>Jobs menu</li></ul>
              <address>Office: <a href="mailto:office@example.test">Email</a></address></footer>
            </body>''')
        jobs, inventory = StructuredExtraction(self.engine(None)).plan(page)
        planned = "\n".join(b.evidence_text for job in jobs for b in job)
        for text in ("Navigation", "Skip links", "Search error placeholder", "Site logo", "Home breadcrumb", "On this page", "Jobs menu"):
            self.assertNotIn(text, planned)
            self.assertTrue(any(text in r["text"] and r["status"] == "excluded_policy" for r in inventory))
        for text in ("Introductory requirement.", "Permit scope.", "Income", "Housing", "Different requirement.",
                     "Keep this similarly named component.", "mailto:office@example.test"):
            self.assertIn(text, planned)
        conditions = next(b for b in page.sections if "Income" in b.text)
        self.assertEqual(conditions.block_kind, "list")
        self.assertEqual(conditions.heading_path, "Residence > Permit A")
        other = next(b for b in page.sections if b.text == "Different requirement.")
        self.assertNotEqual(conditions.scope_id, other.scope_id)

    def test_navigation_marker_on_atomic_element_precedes_list_flattening(self):
        for attribute in ('class="navbar-nav"', 'class="breadcrumb"', 'role="navigation"'):
            with self.subTest(attribute=attribute):
                page = self.page(f'<h1>Residence</h1><ul {attribute}><li>Menu link</li></ul><p>Apply online.</p>')
                jobs, inventory = StructuredExtraction(self.engine(None)).plan(page)
                self.assertEqual([b.text for job in jobs for b in job], ["Apply online."])
                self.assertEqual(next(r for r in inventory if "Menu link" in r["text"])["status"], "excluded_policy")

    def test_navigation_controls_and_sitemap_preserve_substantive_links_and_footer_contacts(self):
        page = self.page('''<h1>Residence</h1>
            <p><a href="#context-sidebar" class="icon icon--root">Navigation</a></p>
            <p><small><a href="#" class="icon--power">Top of page</a></small></p>
            <ul class="nav nav-tabs"><li>Favorites tab</li></ul>
            <div class="tab-content"><p>Application guidance.</p></div>
            <div class="mod mod-socialshare">Social share controls</div>
            <p>Required procedure: <a href="#apply">Apply online</a>.</p>
            <p>Keep this prose beside <a href="#context-sidebar" class="icon--root">Navigation</a>.</p>
            <footer><div class="site-map"><h2>Footer menu</h2><ul><li>Asylum</li></ul></div>
              <address><a href="mailto:office@example.test">Office contact</a></address></footer>''')
        jobs, inventory = StructuredExtraction(self.engine(None)).plan(page)
        planned = "\n".join(b.evidence_text for job in jobs for b in job)
        for text in ("Top of page", "Favorites tab", "Social share controls", "Footer menu", "Asylum"):
            self.assertNotIn(text, planned)
            self.assertTrue(any(text in r["text"] and r["status"] == "excluded_policy" for r in inventory))
        for text in ("Application guidance.", "Required procedure: Apply online.",
                     "Keep this prose beside Navigation.", "mailto:office@example.test"):
            self.assertIn(text, planned)

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
        page = replace(page, provenance={"source_url": "https://example.gov/permit", "sha256": "b" * 64})
        provider = Provider()
        report = self.engine(provider).extract(page)
        self.assertEqual(report.to_dict()["provenance"], page.provenance)
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

    def test_structural_repair_precedes_review_and_preserves_condition_errors(self):
        for repair_succeeds in (False, True):
            with self.subTest(repair_succeeds=repair_succeeds):
                def generate(result, payload):
                    claim = result["concepts"][0]["claims"][0]
                    refs = claim["evidence_ids"]
                    claim["conditions"] = [dict(
                        condition_id=identity, text=text, evidence_ids=refs,
                        subject="unspecified", operator="eq", value="unspecified",
                        unit="unspecified", time_window="unspecified")
                        for identity, text in (("online", "Apply online"), ("post", "apply by post"))]
                    claim["condition_groups"] = [dict(group_id="either", operator="OR",
                                                       members=["online", "post"], evidence_ids=refs)]
                    claim["condition_root"] = "either" if repair_succeeds and payload["repair"] else "online"

                def review(result, payload):
                    self.assertTrue(repair_succeeds)
                    self.assertEqual(len(payload["concepts"]), 1)

                provider = Provider(generate, review)
                progress = []
                report = self.engine(provider, progress=progress.append).extract(
                    self.page("<p>Apply online or apply by post.</p>"))
                self.assertEqual(len(provider.calls), 3 if repair_succeeds else 2)
                first = report.semantic_reviews[0]["history"][0]
                self.assertEqual(first["error"], "1 proposal(s) failed structural validation")
                self.assertEqual(first["failure_stage"], "structural_validation")
                self.assertEqual(first["structural_rejections"][0]["reason"], "unconnected conditions or groups")
                self.assertEqual(first["proposals"][0]["claims"][0]["condition_root"], "online")
                self.assertNotIn("review", first)
                repair = json.loads(provider.calls[1]["user_prompt"])["repair"]
                self.assertEqual(repair["validation_error"], first["error"])
                self.assertEqual(repair["failure_stage"], "structural_validation")
                self.assertEqual(repair["proposals"], first["proposals"])
                self.assertEqual(repair["structural_rejections"], [dict(
                    proposal_index=0, reason="unconnected conditions or groups",
                    errors=[{"path": "claims[0].condition_root", "reason": "unconnected conditions or groups"}])])
                self.assertNotIn("raw_completion", repair)
                self.assertTrue(any("unconnected conditions or groups" in line for line in progress))
                self.assertTrue(any("semantic review skipped" in warning for warning in report.warnings))
                self.assertEqual(provider.discarded, 0)  # Schema-valid extraction checkpoints remain reusable.
                if repair_succeeds:
                    self.assertEqual(len(report.candidates), 1)
                    self.assertEqual(report.candidates[0].structured_claims[0]["condition_root"], "either")
                    self.assertFalse(report.rejected_candidates)
                else:
                    self.assertFalse(report.candidates)
                    self.assertEqual(report.rejected_candidates[0]["reason"], "unconnected conditions or groups")
                    self.assertEqual(report.quality_metrics["rejected_proposals"], 1)
                    self.assertEqual(report.source_inventory[0]["status"], "invalid_response")

    def test_review_provider_failure_preserves_structural_rejections(self):
        def generate(result, payload):
            result["concepts"][0]["claims"][0]["condition_root"] = "missing"

        def review(result, payload):
            raise SemanticModelError("fixture review outage")

        provider = Provider(generate, review)
        # With no repair available, still review the valid subset of a mixed packet.
        report = self.engine(provider, max_repair_attempts=0).extract(
            self.page("<p>Apply online.</p><p>Bring proof.</p>"))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(provider.discarded, 0)
        self.assertFalse(report.candidates)
        record = report.semantic_reviews[0]["history"][0]
        self.assertEqual(record["failure_stage"], "review")
        self.assertEqual(record["provider_error"], "fixture review outage")
        self.assertEqual(record["structural_rejections"][0]["reason"], "conditions require a valid explicit root")
        self.assertEqual(report.rejected_candidates[0]["proposal"], record["proposals"][0])

    def test_failed_repair_does_not_reuse_previous_revision_proposals(self):
        def generate(result, payload):
            if payload["repair"]:
                result["unexpected"] = True
            else:
                result["concepts"][0]["claims"][0]["condition_root"] = "missing"

        def review(result, payload):
            result["block_coverage"][0]["decision"] = "covered"

        provider = Provider(generate, review)
        report = self.engine(provider).extract(self.page("<p>Apply online.</p>"))
        self.assertEqual(len(provider.calls), 2)
        history = report.semantic_reviews[0]["history"]
        self.assertTrue(history[0]["structural_rejections"])
        self.assertEqual(history[1]["failure_stage"], "extraction_validation")
        self.assertEqual(history[1]["proposals"], [])
        self.assertEqual(history[1]["structural_rejections"], [])
        self.assertFalse(report.candidates)

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

    def saved_residence(self, suffix="d1b9c10e"):
        path = Path(__file__).parent / f"fixtures/apertus_v4_residence_{suffix}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def residence_page(self, saved):
        # Replay exact normalized evidence and ownership, omitting navigation
        # that was never sent to the model. No network or local job is needed.
        return NormalizedPage("saved-residence", "fixture", "Residence", "en", "saved-evidence",
            tuple(NormalizedSection(b["section_id"], "", b["text"], block_kind="paragraph",
                                    scope_id=b["scope_id"]) for b in saved["evidence"].values()),
            normalization_version=NORMALIZATION_VERSION,
            source_sha256=saved["provenance"]["source_sha256"])

    def test_saved_root_and_quote_errors_are_reported_together_without_mutation(self):
        saved = self.saved_residence("8d0e4648")
        sections = {b["section_id"]: b["scope_id"] for b in saved["evidence"].values()}
        for key in ("initial_proposals", "repaired_proposals"):
            with self.subTest(revision=key):
                item = saved[key][0]
                original = copy.deepcopy(item)
                with self.assertRaises(contracts.ConceptValidationError) as raised:
                    contracts.validate_concept(item, saved["evidence"], sections)
                errors = raised.exception.errors
                self.assertEqual([e["path"] for e in errors],
                    ["claims[0].condition_root", "claims[0].conditions[0].text"])
                self.assertIn("defined group", errors[0]["hint"])
                self.assertEqual(errors[1]["reason"], "condition text must be an exact source excerpt")
                self.assertEqual(item, original)

    def test_saved_failed_repair_uses_two_calls_and_never_reviews_invalid_proposals(self):
        saved = self.saved_residence("8d0e4648")
        def generate(result, payload):
            key = "repaired_proposals" if payload["repair"] else "initial_proposals"
            result["concepts"] = copy.deepcopy(saved[key])
        def review(result, payload):
            self.fail("No review may be requested for these invalid proposals")
        provider = Provider(generate, review)
        report = self.engine(provider).extract(self.residence_page(saved))
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(report.quality_metrics["review_request_count"], 0)
        self.assertEqual(report.quality_metrics["repair_request_count"], 1)
        self.assertFalse(report.candidates)
        self.assertEqual(provider.discarded, 0)
        feedback = json.loads(provider.calls[1]["user_prompt"])["repair"]
        self.assertEqual(feedback["proposals"], saved["initial_proposals"])
        self.assertNotIn("proposal", feedback["structural_rejections"][0])
        self.assertEqual(len(feedback["structural_rejections"][0]["errors"]), 2)
        self.assertNotIn("raw_completion", feedback)
        self.assertEqual(report.rejected_candidates[0]["proposal"], saved["repaired_proposals"][0])
        self.assertEqual(len(report.rejected_candidates[0]["errors"]), 2)
        self.assertTrue(all(row["status"] == "invalid_response" for row in report.source_inventory))
        self.assertFalse(report.quality_metrics["coverage_complete"])

    def test_fixed_structure_reaches_review_but_unsupported_roles_still_block_retention(self):
        saved = self.saved_residence("8d0e4648")
        def generate(result, payload):
            result["concepts"] = copy.deepcopy(saved["initial_proposals"])
            if payload["repair"]:
                # Assistant-authored structural control, not Apertus output.
                claim = result["concepts"][0]["claims"][0]
                claim["condition_root"] = "either"
                claim["condition_groups"] = [{"group_id": "either", "operator": "OR",
                    "members": [c["condition_id"] for c in claim["conditions"]],
                    "evidence_ids": claim["evidence_ids"]}]
                claim["conditions"][0]["text"] = "works during his/her stay in Switzerland"
        def review(result, payload):
            self.assertEqual(len(provider.calls), 3)
            claim = payload["concepts"][0]["claims"][0]
            self.assertEqual(claim["condition_root"], "either")
            self.assertEqual(claim["conditions"][0]["text"], "works during his/her stay in Switzerland")
            result["concept_reviews"][0]["claim_support"][0]["scope_fields"]["recipient"].update(
                decision="unsupported", reason="Issuance does not establish an application recipient.")
        provider = Provider(generate, review)
        report = self.engine(provider).extract(self.residence_page(saved))
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(report.quality_metrics["review_request_count"], 1)
        self.assertFalse(report.candidates)
        self.assertEqual(report.rejected_candidates[0]["stage"], "structured_review")
        self.assertEqual(report.semantic_reviews[0]["history"][0]["failure_stage"], "structural_validation")
        self.assertIn("review", report.semantic_reviews[0]["history"][1])

    def test_invalid_duplicate_proposals_keep_both_clause_and_duplicate_errors(self):
        saved = self.saved_residence("8d0e4648")
        def generate(result, payload):
            result["concepts"] = copy.deepcopy(saved["initial_proposals"] * 2)
        report = self.engine(Provider(generate), max_repair_attempts=0).extract(self.residence_page(saved))
        self.assertEqual(report.request_count, 1)
        self.assertEqual(len(report.rejected_candidates), 2)
        self.assertEqual(len(report.rejected_candidates[0]["errors"]), 2)
        self.assertEqual([e["reason"] for e in report.rejected_candidates[1]["errors"]],
            ["conditions require a valid explicit root", "condition text must be an exact source excerpt", "duplicate proposal"])

    def test_mixed_packet_repairs_first_then_reviews_only_final_valid_subset(self):
        def generate(result, payload):
            result["concepts"][0]["claims"][0]["condition_root"] = "missing"
        def review(result, payload):
            self.assertEqual(len(provider.calls), 3)
            self.assertEqual(len(payload["concepts"]), 1)
            self.assertEqual(payload["concepts"][0]["primary_section_id"], "section-0002")
        provider = Provider(generate, review)
        report = self.engine(provider).extract(self.page("<p>Apply online.</p><p>Bring proof.</p>"))
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(len(report.rejected_candidates), 1)
        self.assertEqual(report.source_inventory[0]["status"], "missing")
        self.assertEqual(report.source_inventory[1]["status"], "covered")

    def test_early_structural_repair_preserves_later_packets_budget(self):
        def generate(result, payload):
            if next(iter(payload["untrusted_source"]["evidence"].values()))["text"].startswith("A\n"):
                result["concepts"][0]["claims"][0]["condition_root"] = "missing"
        page = self.page("<h1>A</h1><p>" + "word " * 700 + "</p><h1>B</h1><p>" + "word " * 700 + "</p>")
        provider = Provider(generate)
        engine = self.engine(provider, max_model_requests_per_page=4)
        report = engine.extract(page)
        self.assertEqual(engine.planned_request_count(page), 4)
        self.assertEqual(len(provider.calls), 3)
        self.assertEqual(report.quality_metrics["repair_request_count"], 0)
        self.assertEqual(report.quality_metrics["review_request_count"], 1)
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(report.candidates[0].primary_section_id, "section-0004")

    def test_early_repair_does_not_exceed_preview_or_disabled_repair_limit(self):
        for schema_invalid in (False, True):
            for page_budget, repairs in ((3, 1), (12, 0)):
                with self.subTest(schema_invalid=schema_invalid, page_budget=page_budget, repairs=repairs):
                    def generate(result, payload):
                        if schema_invalid:
                            result["unknown"] = True
                        else:
                            result["concepts"][0]["claims"][0]["condition_root"] = "missing"
                    provider = Provider(generate)
                    engine = self.engine(provider, max_model_requests_per_page=page_budget, max_repair_attempts=repairs)
                    page = self.page("<p>Apply online.</p>")
                    report = engine.extract(page)
                    self.assertEqual(engine.planned_request_count(page), 2)
                    self.assertEqual(len(provider.calls), 1)
                    self.assertEqual(report.quality_metrics["review_request_count"], 0)
                    self.assertFalse(report.candidates)

    def test_independent_errors_in_later_claims_survive_bad_root_and_reference(self):
        evidence = {"e1": {"section_id": "s1", "text": "Apply online."}}
        item = concept("e1", evidence["e1"])
        first = item["claims"][0]
        first["condition_root"] = "missing"
        first["conditions"] = [{"condition_id": "c1", "text": "Invented quote", "evidence_ids": ["e1", "unknown"],
            "operator": "gt", "value": "NaN", "subject": "unspecified", "unit": "days", "time_window": "unspecified"}]
        second = copy.deepcopy(first)
        second["claim_id"] = "claim-2"
        second["conditions"][0]["value"] = "not numeric"
        item["claims"].append(second)
        with self.assertRaises(contracts.ConceptValidationError) as raised:
            contracts.validate_concept(item, evidence, {"s1": "scope1"})
        errors = raised.exception.errors
        self.assertEqual(errors[0]["reason"], "unknown or out-of-scope evidence reference")
        self.assertEqual({e["path"] for e in errors}, {"claims", "claims[0].condition_root", "claims[1].condition_root",
            "claims[0].conditions[0].value", "claims[0].conditions[0].text",
            "claims[1].conditions[0].value", "claims[1].conditions[0].text"})

    def test_tree_diagnostics_still_reject_cycles_dangling_and_repeated_nodes(self):
        evidence = {"e1": {"section_id": "s1", "text": "Apply online."}}
        base = concept("e1", evidence["e1"])
        claim = base["claims"][0]
        claim["conditions"] = [{"condition_id": "c1", "text": "Apply online.", "evidence_ids": ["e1"],
            "operator": "stated", "value": "unspecified", "subject": "unspecified", "unit": "unspecified", "time_window": "unspecified"}]
        claim["condition_groups"] = [{"group_id": "g1", "operator": "AND", "members": ["c1"], "evidence_ids": ["e1"]}]
        claim["condition_root"] = "g1"
        contracts.validate_concept(base, evidence, {"s1": "scope1"})
        for members, reason in ((["g1"], "cyclic or dangling"), (["absent"], "cyclic or dangling"),
                                (["c1", "c1"], "duplicate logical operands")):
            with self.subTest(members=members):
                item = copy.deepcopy(base)
                item["claims"][0]["condition_groups"][0]["members"] = members
                with self.assertRaises(contracts.ConceptValidationError) as raised:
                    contracts.validate_concept(item, evidence, {"s1": "scope1"})
                self.assertTrue(any(reason in e["reason"] for e in raised.exception.errors))
        claim["condition_groups"].append({"group_id": "g2", "operator": "AND", "members": ["c1"], "evidence_ids": ["e1"]})
        claim["condition_groups"][0]["members"].append("g2")
        with self.assertRaisesRegex(contracts.ConceptValidationError, "repeated condition subtree"):
            contracts.validate_concept(base, evidence, {"s1": "scope1"})

    def flag_saved_residence_errors(self, result, payload):
        # Assistant-authored assessment, NOT a newly observed model response.
        # Deliberately leave every broad summary supported to exercise the gate.
        first = result["concept_reviews"][0]["claim_support"][0]
        first["condition_logic"].update(source_applicability="conditional", decision="unsupported",
            reason="Work OR a stay longer than three months is missing from the condition tree.")
        for review in result["concept_reviews"]:
            review["claim_support"][0]["scope_fields"]["actor"].update(decision="unsupported",
                reason="The office is the actor of a separate issuance assertion, not this assertion.")
        result["block_coverage"][0].update(decision="partial",
            reason="The office's issuing action is not represented by a claim.")
        for block in result["block_coverage"][1:]:
            block.update(decision="not_substantive", concept_indices=[], reason="Saved ancillary block.")

    def test_saved_legacy_review_cannot_satisfy_detailed_contract(self):
        saved = self.saved_residence()
        blocks = [b["section_id"] for b in saved["evidence"].values()]
        with self.assertRaisesRegex(ValueError, "schema_version"):
            contracts.parse_review(json.dumps(saved["initial_review"]), saved["initial_proposals"], blocks)
        # A legacy broad approval must not be reused as a detailed approval.
        legacy = copy.deepcopy(saved["initial_review"]["concept_reviews"][0])
        legacy["scope"]["decision"] = legacy["completeness"]["decision"] = "supported"
        self.assertFalse(contracts.review_passes(legacy))

    def test_saved_proposals_fail_detailed_checks_and_preserve_repair_feedback(self):
        saved = self.saved_residence()
        def generate(result, payload):
            key = "repaired_proposals" if payload["repair"] else "initial_proposals"
            result["concepts"] = copy.deepcopy(saved[key])
        provider = Provider(generate, self.flag_saved_residence_errors)
        report = self.engine(provider).extract(self.residence_page(saved))
        self.assertEqual(len(provider.calls), 4)
        self.assertFalse(report.candidates)
        self.assertEqual(len(report.rejected_candidates), 2)
        self.assertEqual(provider.discarded, 0)  # Valid negative audits are retained.
        feedback = json.loads(provider.calls[2]["user_prompt"])["repair"]
        self.assertEqual(feedback["proposals"], saved["initial_proposals"])
        detail = feedback["review"]["concept_reviews"][0]["claim_support"][0]
        self.assertEqual(detail["decision"], "supported")
        self.assertEqual(detail["condition_logic"]["decision"], "unsupported")
        self.assertEqual(detail["scope_fields"]["actor"]["decision"], "unsupported")
        self.assertEqual(report.semantic_reviews[0]["review_contract_version"], contracts.REVIEW_VERSION)
        self.assertEqual(report.semantic_reviews[0]["history"][1]["proposals"], saved["repaired_proposals"])

    def test_each_detailed_failure_blocks_a_supported_summary(self):
        for field in ("condition_logic", *contracts.SCOPE_FIELDS):
            with self.subTest(field=field):
                def review(result, payload):
                    claim = result["concept_reviews"][0]["claim_support"][0]
                    check = claim[field] if field == "condition_logic" else claim["scope_fields"][field]
                    check.update(decision="unsupported", reason="Deliberate isolated negative control.")
                report = self.engine(Provider(review=review), max_repair_attempts=0).extract(self.page("<p>Apply online.</p>"))
                self.assertFalse(report.candidates)
                self.assertEqual(report.rejected_candidates[0]["stage"], "structured_review")

    def test_missing_per_claim_checks_are_rejected_instead_of_defaulting_to_supported(self):
        for missing in ("condition_logic", "scope_fields", *contracts.SCOPE_FIELDS):
            with self.subTest(missing=missing):
                def review(result, payload):
                    item = result["concept_reviews"][0]["claim_support"][0]
                    del (item if missing in {"condition_logic", "scope_fields"} else item["scope_fields"])[missing]
                provider = Provider(review=review)
                report = self.engine(provider, max_repair_attempts=0).extract(self.page("<p>Apply online.</p>"))
                self.assertFalse(report.candidates)
                self.assertEqual(provider.discarded, 1)
                self.assertEqual(report.semantic_reviews[0]["history"][0]["failure_stage"], "review_validation")

    def test_saved_empty_conditions_cannot_receive_supported_conditional_review(self):
        saved = self.saved_residence()
        for revision in ("initial_proposals", "repaired_proposals"):
            with self.subTest(revision=revision):
                provider = Provider(generate=lambda result, payload: result.update(concepts=copy.deepcopy(saved[revision])),
                    review=lambda result, payload: result["concept_reviews"][0]["claim_support"][0]["condition_logic"].update(
                        source_applicability="conditional"))
                report = self.engine(provider, max_repair_attempts=0).extract(self.residence_page(saved))
                self.assertFalse(report.candidates)
                self.assertEqual(provider.discarded, 1)
                error = report.semantic_reviews[0]["history"][0]["error"]
                self.assertIn("claim claim-0001", error)
                self.assertIn("empty conditions", error)

    def test_unconditional_obligation_and_issuance_fact_can_have_empty_conditions(self):
        def generate(result, payload):
            claim = result["concepts"][0]["claims"][0]
            claim.update(kind="requirement", statement="Visitors must wear badges.")
            claim["scope"]["actor"] = "visitors"
            issuance = copy.deepcopy(claim)
            issuance.update(claim_id="issuer", kind="fact", statement="The Site Office issues badges.")
            issuance["scope"]["actor"] = "Site Office"
            result["concepts"][0]["claims"].append(issuance)
        report = self.engine(Provider(generate)).extract(self.page(
            "<p>Visitors must wear badges. The Site Office issues badges.</p>"))
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(len(report.candidates[0].structured_claims), 2)
        self.assertFalse(report.quality_metrics["publication_eligible"])

    def test_uncertain_applicability_cannot_receive_supported_logic(self):
        provider = Provider(review=lambda result, payload: result["concept_reviews"][0]["claim_support"][0]["condition_logic"].update(
            source_applicability="uncertain"))
        report = self.engine(provider, max_repair_attempts=0).extract(self.page("<p>Apply online.</p>"))
        self.assertFalse(report.candidates)
        self.assertIn("uncertain source applicability", report.semantic_reviews[0]["history"][0]["error"])

    def test_unconditional_review_cannot_approve_added_conditions(self):
        def generate(result, payload):
            claim = result["concepts"][0]["claims"][0]
            claim["conditions"] = [{"condition_id": "invented", "text": "Apply online.",
                "evidence_ids": claim["evidence_ids"], "subject": "unspecified", "operator": "stated",
                "value": "unspecified", "unit": "unspecified", "time_window": "unspecified"}]
            claim["condition_root"] = "invented"
        provider = Provider(generate, lambda result, payload: result["concept_reviews"][0]["claim_support"][0]["condition_logic"].update(
            source_applicability="unconditional"))
        report = self.engine(provider, max_repair_attempts=0).extract(self.page("<p>Apply online.</p>"))
        self.assertFalse(report.candidates)
        self.assertIn("supported added conditions", report.semantic_reviews[0]["history"][0]["error"])


if __name__ == "__main__":
    unittest.main()
