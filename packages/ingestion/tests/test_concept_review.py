from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from swisstip.ingestion.concept_review import parse_verdicts
from swisstip.ingestion.concepts import (
    CandidateConceptExtractor, ConceptExtractionError, ModelCompletion,
    NormalizedPage, NormalizedSection, REVIEW_PROMPT_PROFILE, SPAN_PROMPT_PROFILE,
    normalize_downloaded_page, select_content_sections,
)


class ReviewProvider:
    def __init__(self, *, decision="supported", issue="none", alter=None, empty=False):
        self.calls = []
        self.decision, self.issue, self.alter, self.empty = decision, issue, alter, empty

    def generate_structured(self, **request):
        self.calls.append(request)
        payload = json.loads(request["user_prompt"])
        if "untrusted_review" in payload:
            result = {"verdicts": [{"review_id": 1, "decision": self.decision,
                                   "issue": self.issue, "reason": "Test evidence assessment."}]}
        else:
            span = payload["untrusted_page"]["evidence_spans"][0]
            candidate = {
                "preferred_label": "Aufenthaltsbewilligung", "alternative_labels": [],
                "concept_type": "DOCUMENT", "granularity": "ANSWERABLE",
                "description": "Eine Bewilligung ist erforderlich.",
                "scope": "Aufenthalt > 3 Monate oder > 90 Arbeitstage",
                "user_questions": ["Ist eine Bewilligung erforderlich?"], "confidence": 0.8,
                "evidence": [{"evidence_id": span["evidence_id"]}], "relations": [],
            }
            if "primary_section_id" in request["response_schema"]["properties"]["concepts"]["items"]["properties"]:
                candidate["primary_section_id"] = span["section_id"]
            if self.alter:
                self.alter(candidate, payload["untrusted_page"])
            result = {"concepts": [] if self.empty else [candidate]}
        return ModelCompletion(json.dumps(result), "fake", "fake", prompt_tokens=10, output_tokens=5)


def page(*sections):
    return NormalizedPage("page-1", "permit.html", "Aufenthalt", "de", "a" * 64,
                          sections or (NormalizedSection("section-0001", "Aufenthalt", "Eine Bewilligung ist erforderlich."),))


def extractor(provider, **kwargs):
    return CandidateConceptExtractor(provider, active_profile="fake",
                                     prompt_profile=REVIEW_PROMPT_PROFILE, **kwargs)


class ReviewExtractionTests(unittest.TestCase):
    def test_html_link_detection_keeps_explanatory_prose_and_non_generic_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text("<h1>Aufenthalt</h1><h2>Links</h2><ul>"
                            "<li><a href='/banks'><span>Bewilligte Banken</span></a></li>"
                            "<li><a href='/abroad'>Schweizer Vertretungen</a></li></ul>"
                            "<h2>Related links</h2><p>Apply within 14 days.</p><a href='/apply'>Apply</a>"
                            "<h2>Requirements</h2><a href='/rule'>A permit is required.</a>", encoding="utf-8")
            source = normalize_downloaded_page(path, preserve_structure=True)
        marked = [s.heading_path for s in source.sections if s.generic_link_only]
        self.assertEqual(marked, ["Aufenthalt > Links"])

    def test_skipping_middle_chunk_preserves_other_prompts_and_original_numbering(self):
        source = page(NormalizedSection("section-0001", "Rules", "word " * 80),
                      NormalizedSection("section-0002", "Links", "Bank list\nRepresentations", True),
                      NormalizedSection("section-0003", "Other rules", "word " * 80))
        provider = ReviewProvider()
        engine = extractor(provider, chunk_content_characters=500, chunk_overlap_characters=0)
        sections, _ = engine._content_sections(source)
        chunks = engine._chunks(sections)
        self.assertEqual(len(chunks), 3)
        expected = [engine._user_prompt(source, chunks[i], i + 1, 3) for i in (0, 2)]
        self.assertEqual(engine.planned_request_count(source), 4)
        report = engine.extract(source)
        self.assertEqual([provider.calls[i]["user_prompt"] for i in (0, 2)], expected)
        self.assertEqual(report.request_count, 4)
        self.assertEqual(report.skipped_chunks[0]["chunk_index"], 2)
        self.assertEqual(report.skipped_chunks[0]["reason"], "generic_link_only")

    def test_entire_link_only_page_is_empty_without_model_calls(self):
        source = page(NormalizedSection("section-0001", "Links", "Bank list", True))
        provider = ReviewProvider()
        engine = extractor(provider)
        self.assertEqual(engine.planned_request_count(source), 0)
        report = engine.extract(source)
        self.assertEqual(provider.calls, [])
        self.assertEqual(report.candidates, ())
        self.assertEqual(report.request_count, 0)
        self.assertEqual((report.prompt_tokens, report.output_tokens), (0, 0))
        self.assertEqual((report.provider, report.model), ("not_called", "not_called"))
        self.assertEqual(report.model_identities, ())

    def test_mixed_chunks_and_legacy_prompts_are_not_skipped(self):
        source = page(NormalizedSection("section-0001", "Rules", "Apply online."),
                      NormalizedSection("section-0002", "Links", "Bank list", True))
        engine = extractor(ReviewProvider())
        report = engine.extract(source)
        self.assertEqual(report.skipped_chunks, ())
        legacy = CandidateConceptExtractor(ReviewProvider(), active_profile="fake", prompt_profile=SPAN_PROMPT_PROFILE)
        self.assertEqual(legacy.planned_request_count(page(source.sections[1])), 1)

    def test_supported_proposal_has_primary_section_and_combined_usage(self):
        provider = ReviewProvider()
        engine = extractor(provider)
        self.assertEqual(engine.planned_request_count(page()), 2)
        report = engine.extract(page())
        self.assertEqual(report.request_count, 2)
        self.assertEqual((report.prompt_tokens, report.output_tokens), (20, 10))
        self.assertEqual(report.candidates[0].primary_section_id, "section-0001")
        self.assertEqual(report.quality_metrics["review_request_count"], 1)
        self.assertEqual(report.semantic_reviews[0]["decision"], "supported")

    def test_report_preserves_requested_and_observed_generation_and_review_identity(self):
        class IdentityProvider(ReviewProvider):
            def generate_structured(self, **request):
                completion = super().generate_structured(**request)
                return replace(
                    completion,
                    requested_model="fake:provider-route",
                    observed_model="Fake/Model" if len(self.calls) == 1 else "fake-model",
                    request_id=f"request-{len(self.calls)}",
                )

        report = extractor(IdentityProvider()).extract(page())
        self.assertEqual(report.model, "fake")
        expected_identities = [
            {
                "provider": "fake",
                "model": "fake",
                "requested_model": "fake:provider-route",
                "observed_model": "Fake/Model",
                "request_id": "request-1",
            },
            {
                "provider": "fake",
                "model": "fake",
                "requested_model": "fake:provider-route",
                "observed_model": "fake-model",
                "request_id": "request-2",
            },
        ]
        self.assertEqual(report.model_identities, tuple(expected_identities))
        self.assertEqual(
            json.loads(json.dumps(report.to_dict()))["model_identities"],
            expected_identities,
        )

    def test_reviewer_rejections_and_uncertainty_are_retained_as_diagnostics(self):
        for decision, issue in (("unsupported", "unsupported_claim"), ("unsupported", "wrong_language"),
                                ("unsupported", "wrong_scope"), ("uncertain", "insufficient_context")):
            with self.subTest(issue=issue):
                result = extractor(ReviewProvider(decision=decision, issue=issue)).extract(page())
                self.assertFalse(result.candidates)
                self.assertEqual(result.quality_metrics["semantic_rejection_count"], 1)
                self.assertIn(issue, result.rejected_candidates[0]["reason"])
                self.assertEqual(result.rejected_candidates[0]["stage"], "semantic_review")

    def test_primary_section_prevents_cross_section_evidence(self):
        source = page(NormalizedSection("section-0001", "Angehoerige", "Eltern benoetigen Unterstuetzung."),
                      NormalizedSection("section-0002", "Ehevorbereitung", "Keine Scheinehe."))
        for alter in (
            lambda c, p: c.update(primary_section_id="section-9999"),
            lambda c, p: c.update(evidence=[{"evidence_id": p["evidence_spans"][-1]["evidence_id"]}]),
        ):
            provider = ReviewProvider(alter=alter)
            result = extractor(provider).extract(source)
            self.assertFalse(result.candidates)
            self.assertEqual(len(provider.calls), 1)
        provider = ReviewProvider()
        extractor(provider).extract(source)
        context = json.loads(provider.calls[1]["user_prompt"])["untrusted_review"]
        self.assertEqual([s["section_id"] for s in context["primary_sections"]], ["section-0001"])
        self.assertNotIn("Keine Scheinehe", provider.calls[1]["user_prompt"])

    def test_budget_is_reserved_before_calls_and_empty_generation_skips_review(self):
        provider = ReviewProvider()
        with self.assertRaisesRegex(ConceptExtractionError, "requires 2 model requests"):
            extractor(provider, max_model_requests_per_page=1).extract(page())
        self.assertEqual(provider.calls, [])
        result = extractor(ReviewProvider(empty=True)).extract(page())
        self.assertEqual(result.request_count, 1)
        self.assertEqual(result.quality_metrics["review_request_count"], 0)

    def test_numeric_scope_comparison_is_valid_but_breadcrumbs_are_not(self):
        for scope, valid in (("Aufenthalt > 3 Monate", True), ("Aufenthalt >= 90 Tage", True),
                             ("Residence > Rules", False), ("SECTION-0001", False)):
            provider = ReviewProvider(alter=lambda c, p: c.update(scope=scope))
            result = CandidateConceptExtractor(provider, active_profile="fake",
                        prompt_profile=SPAN_PROMPT_PROFILE).extract(page())
            self.assertEqual(bool(result.candidates), valid, scope)

    def test_embedded_news_is_removed_but_news_page_is_not(self):
        source = page(NormalizedSection("section-0001", "Aufenthalt > News > Sozialhilfe", "Update."),
                      NormalizedSection("section-0002", "News > Sozialhilfe", "Article."))
        kept, excluded = select_content_sections(source, exclude_embedded_news=True)
        self.assertEqual([s.section_id for s in kept], ["section-0002"])
        self.assertEqual(excluded[0]["reason"], "embedded_news")

    def test_structure_keeps_rows_lists_and_abbreviations_with_exact_offsets(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.html"
            path.write_text("<html lang='de'><h1>Bewilligungen</h1><p>Eltern bzw. Grosseltern, z.B. bei Pflegebedarf.</p>"
                            "<ul><li>Unterhalt</li><li>Wohnraum</li></ul><table>"
                            "<tr><th>Typ</th><th>Bedeutung</th></tr>"
                            "<tr><td><p>B</p></td><td><div>Aufenthalt</div></td></tr>"
                            "<tr><td>C</td><td>Niederlassung</td></tr></table></html>", encoding="utf-8")
            source = normalize_downloaded_page(path, preserve_structure=True)
        provider = ReviewProvider()
        extractor(provider).extract(source)
        spans = json.loads(provider.calls[0]["user_prompt"])["untrusted_page"]["evidence_spans"]
        quotes = [s["text"] for s in spans]
        self.assertTrue(any("Eltern bzw. Grosseltern, z.B. bei Pflegebedarf." in q for q in quotes))
        self.assertIn("B | Aufenthalt |", quotes)
        self.assertIn("C | Niederlassung |", quotes)
        self.assertIn("Unterhalt", quotes)
        self.assertIn("Wohnraum", quotes)
        for span in spans:
            section_id, start, end = span["evidence_id"].split(":")
            section = next(s for s in source.sections if s.section_id == section_id)
            self.assertEqual(section.evidence_text[int(start):int(end)], span["text"])

    def test_review_contract_fails_closed(self):
        valid = {"review_id": 1, "decision": "supported", "issue": "none", "reason": "Supported."}
        for content, count in (("not json", 1), (json.dumps({"verdicts": []}), 1),
                               (json.dumps({"verdicts": [valid, valid]}), 2),
                               (json.dumps({"verdicts": [dict(valid, issue="wrong_scope")]}), 1),
                               (json.dumps({"verdicts": [dict(valid, review_id=True)]}), 1)):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_verdicts(content, count)


if __name__ == "__main__":
    unittest.main()
