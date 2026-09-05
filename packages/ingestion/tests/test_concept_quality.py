from __future__ import annotations

import json
import unittest

from swisstip.ingestion.concepts import (
    CandidateConceptExtractor, ModelCompletion, NormalizedPage, NormalizedSection,
    SPAN_PROMPT_PROFILE, select_content_sections,
)


class SpanProvider:
    def __init__(self, alter=None):
        self.calls = []
        self.alter = alter

    def generate_structured(self, **request):
        self.calls.append(request)
        spans = json.loads(request["user_prompt"])["untrusted_page"]["evidence_spans"]
        candidate = {
            "preferred_label": "Permit application", "alternative_labels": [],
            "concept_type": "PROCESS", "granularity": "ANSWERABLE",
            "description": "Apply online.", "scope": "Residents of Zurich",
            "user_questions": ["How do I apply?"], "confidence": 0.8,
            "evidence": [{"evidence_id": spans[-1]["evidence_id"]}], "relations": [],
        }
        if self.alter:
            self.alter(candidate)
        return ModelCompletion(json.dumps({"concepts": [candidate]}), "fake", "fake")


def page_with(*sections):
    return NormalizedPage("page-1", "permit.html", "Permit", "de", "a" * 64, sections)


class SpanExtractionTests(unittest.TestCase):
    def test_conflicting_claims_keep_distinct_candidate_ids_for_review(self):
        class ConflictingProvider(SpanProvider):
            def generate_structured(self, **request):
                completion = super().generate_structured(**request)
                payload = json.loads(completion.content)
                second = dict(payload["concepts"][0], description="Apply in person.")
                payload["concepts"].append(second)
                return ModelCompletion(json.dumps(payload), "fake", "fake")

        page = page_with(NormalizedSection("section-0001", "", "Apply online."))
        result = CandidateConceptExtractor(
            ConflictingProvider(), active_profile="fake", prompt_profile=SPAN_PROMPT_PROFILE,
        ).extract(page)
        self.assertEqual(len(result.candidates), 2)
        self.assertEqual(len({c.candidate_id for c in result.candidates}), 2)
        self.assertIn("semantic_support_requires_review", result.quality_metrics["evidence_validation"])

    def test_exact_unicode_spans_and_repeated_sentences_resolve_by_position(self):
        text = "Zürich: Antrag nötig. Apply online. Apply online."
        page = page_with(NormalizedSection("section-0001", "Requirements", text))
        provider = SpanProvider()
        report = CandidateConceptExtractor(
            provider, active_profile="fake", prompt_profile=SPAN_PROMPT_PROFILE,
        ).extract(page)
        self.assertEqual(report.warnings, ())
        evidence = report.candidates[0].evidence[0]
        source = page.sections[0].evidence_text
        self.assertEqual(source[evidence.start:evidence.end], evidence.quote)
        self.assertEqual(evidence.start, source.rfind("Apply online."))
        request = provider.calls[0]
        schema = request["response_schema"]["properties"]["concepts"]["items"]["properties"]
        allowed = schema["evidence"]["items"]["properties"]["evidence_id"]["enum"]
        supplied = json.loads(request["user_prompt"])["untrusted_page"]["evidence_spans"]
        self.assertEqual(allowed, [s["evidence_id"] for s in supplied])

    def test_rejects_forged_ids_legacy_quotes_and_bad_scope_with_diagnostics(self):
        cases = [
            ("evidence", [{"evidence_id": "section-9999:0:1"}], "unknown evidence_id"),
            ("evidence", [{"section_id": "section-0001", "quote": "Apply online."}], "select an evidence_id"),
            ("user_questions", [], "user question"),
            ("scope", "section-0001", "scope must describe"),
            ("scope", "page", "scope must describe"),
        ]
        for key, value, reason in cases:
            with self.subTest(key=key, value=value):
                provider = SpanProvider(lambda c: c.update({key: value}))
                page = page_with(NormalizedSection("section-0001", "", "Apply online."))
                report = CandidateConceptExtractor(
                    provider, active_profile="fake", prompt_profile=SPAN_PROMPT_PROFILE,
                ).extract(page)
                self.assertFalse(report.candidates)
                self.assertIn(reason, report.rejected_candidates[0]["reason"])
                self.assertEqual(report.rejected_candidates[0]["proposal"][key], value)
                self.assertEqual(report.quality_metrics["rejected_proposals"], 1)

    def test_filters_contact_branch_but_keeps_substantive_support_and_shared_rules(self):
        page = page_with(
            NormalizedSection("section-0001", "Permit > Rules", "Apply online."),
            NormalizedSection("section-0002", "Permit > Kontakt > Telefon", "+41 123456"),
            NormalizedSection("section-0003", "Permit > Opferhilfe", "Get help."),
            NormalizedSection("section-0004", "Permit > More rules", "Apply online."),
            NormalizedSection("section-0005", "Navigation > Hauptnavigation > Suche", "Site search."),
            NormalizedSection("section-0006", "Permit > Bitte geben Sie uns Feedback > Vielen Dank!", "Send feedback."),
        )
        kept, excluded = select_content_sections(page)
        self.assertEqual([s.section_id for s in kept], ["section-0001", "section-0003", "section-0004"])
        self.assertEqual(excluded[0]["section_id"], "section-0002")
        provider = SpanProvider()
        extractor = CandidateConceptExtractor(provider, active_profile="fake", prompt_profile=SPAN_PROMPT_PROFILE)
        planned = extractor.planned_request_count(page)
        report = extractor.extract(page)
        self.assertEqual(report.request_count, planned)
        self.assertNotIn("+41 123456", provider.calls[0]["user_prompt"])
        self.assertEqual(report.input_hash, page.content_hash)
        self.assertEqual(report.quality_metrics["excluded_section_count"], 3)

    def test_long_spans_are_bounded_and_cannot_cite_another_chunk(self):
        page = page_with(NormalizedSection("section-0001", "", "word " * 350))
        provider = SpanProvider()
        extractor = CandidateConceptExtractor(
            provider, active_profile="fake", prompt_profile=SPAN_PROMPT_PROFILE,
            chunk_content_characters=500, chunk_overlap_characters=0,
        )
        report = extractor.extract(page)
        self.assertGreater(report.request_count, 1)
        all_ids = []
        for request in provider.calls:
            spans = json.loads(request["user_prompt"])["untrusted_page"]["evidence_spans"]
            self.assertTrue(all(0 < len(s["text"]) <= 500 for s in spans))
            all_ids.append({s["evidence_id"] for s in spans})
        self.assertFalse(all_ids[0] & all_ids[-1])
        first_id = next(iter(all_ids[0]))
        forged = SpanProvider(lambda c: c.update({"evidence": [{"evidence_id": first_id}]}))
        failed = CandidateConceptExtractor(
            forged, active_profile="fake", prompt_profile=SPAN_PROMPT_PROFILE,
            chunk_content_characters=500, chunk_overlap_characters=0,
        ).extract(page)
        self.assertGreater(len(failed.rejected_candidates), 0)


if __name__ == "__main__":
    unittest.main()
