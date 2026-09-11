"""Offline structural contract checks; fixtures do not claim real coverage."""

import copy
import json
from pathlib import Path
import tempfile
import unittest

from pydantic import ValidationError

from swisstip.core.contracts import (
    ArtifactRef, CatalogEntry, ContextSchema, DateRange, EvidenceObject,
    GetCoverageRequest, GetEvidenceRequest, GetEvidenceResult, Jurisdiction,
    LanguagePolicy, StructuredGroundingRequest, StructuredGroundingResult,
    canonical_language_tag,
)
from swisstip.core.schemas import main as export_schemas, schema_documents


def artifact(name="synthetic-artifact"):
    return {"artifact_id": name, "version": "1", "sha256": "a" * 64}


def request_payload():
    return {
        "schema_version": "structured-grounding/v1", "release_id": "synthetic-release",
        "knowledge_space_id": "synthetic-space", "domain_id": "synthetic-domain",
        "topic_id": "synthetic-topic", "concept_ids": ["synthetic-concept"],
        "intent": "requirements", "jurisdiction": {"country_code": "CH", "canton_code": "CH-ZH"},
        "context": {}, "as_of": "2026-09-06", "scope_mode": "exact",
    }


def evidence_payload():
    return {
        "identity": artifact("synthetic-evidence"), "evidence_id": "synthetic-evidence",
        "release_id": "synthetic-release", "snapshot_ref": artifact("synthetic-snapshot"),
        "normalized_document_ref": artifact("synthetic-normalized"), "section_id": "synthetic-section",
        "start_offset": 3, "end_offset": 8, "original_excerpt": "Hello",
        "citation": {"source_id": "synthetic-source", "authority": "Synthetic authority",
                     "url": "https://example.invalid/source", "title": "Synthetic fixture",
                     "accessed_at": "2026-09-06T00:00:00Z"},
        "declared_language": ["en"], "detected_language": "en", "effective_source_language": "en",
        "language_detection_method": "synthetic-fixture", "language_confidence": 1.0,
        "canonical_concept_ids": ["synthetic-concept"], "jurisdiction": {"country_code": "CH"},
        "temporal_coverage": {"valid_from": "2026-09-06"}, "provenance_refs": [artifact("synthetic-provenance")],
    }


class RequestContractTests(unittest.TestCase):
    def test_additional_evidence_languages_require_explicit_v2_opt_in(self):
        payload = {**evidence_payload(), "effective_source_language": "uk"}
        with self.assertRaises(ValidationError):
            EvidenceObject.model_validate(payload)
        value = EvidenceObject.model_validate({**payload, "schema_version": "evidence-object/v2"})
        self.assertEqual(value.effective_source_language, "uk")
        for unknown in ["und", "mul", "zxx"]:
            with self.subTest(language=unknown), self.assertRaises(ValidationError):
                EvidenceObject.model_validate({**payload, "schema_version": "evidence-object/v2",
                                              "effective_source_language": unknown})

    def test_required_envelope_fields_and_no_conversation_fields(self):
        request = request_payload()
        for name in ("schema_version", "release_id", "knowledge_space_id", "domain_id", "topic_id", "intent", "jurisdiction", "context", "as_of", "scope_mode"):
            with self.subTest(missing=name), self.assertRaises(ValidationError):
                StructuredGroundingRequest.model_validate({key: value for key, value in request.items() if key != name})
        for name in ("question", "query_language", "response_language", "history", "structured_context"):
            with self.subTest(extra=name), self.assertRaises(ValidationError):
                StructuredGroundingRequest.model_validate({**request, name: "unexpected"})

    def test_strict_types_at_each_boundary(self):
        for name, value in (("max_evidence", True), ("max_evidence", "5"), ("max_evidence", 2.0), ("context", "nationality: example"), ("context", {"nested": {"value": 1}}), ("retrieval_terms", [{"text": 42, "language": "en"}]), ("jurisdiction", {"country_code": "CH", "typo": "ZH"})):
            with self.subTest(field=name, value=value), self.assertRaises(ValidationError):
                StructuredGroundingRequest.model_validate({**request_payload(), name: value})

    def test_scalar_context_preserves_types_and_rejects_nonfinite(self):
        values = {"flag": True, "count": 2, "fraction": 2.5, "text": "2", "unknown": None}
        request = StructuredGroundingRequest.model_validate({**request_payload(), "context": values})
        for key, value in values.items():
            self.assertIs(type(request.context[key]), type(value))
        for value in (float("inf"), float("nan"), "a" * 1001):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                StructuredGroundingRequest.model_validate({**request_payload(), "context": {"field": value}})

    def test_source_filter_canonicalization_and_null_semantics(self):
        for value in (None, ["DE", "de", "FR"]):
            request = StructuredGroundingRequest.model_validate({**request_payload(), "source_languages": value})
            self.assertEqual(request.source_languages, None if value is None else ["de", "fr"])
        self.assertIsNone(StructuredGroundingRequest.model_validate(request_payload()).source_languages)
        with self.assertRaises(ValidationError):
            StructuredGroundingRequest.model_validate({**request_payload(), "source_languages": []})

    def test_well_formed_unsupported_languages_reach_semantic_validation(self):
        request = StructuredGroundingRequest.model_validate({**request_payload(), "retrieval_terms": [{"text": "example", "language": "de-AT"}], "source_languages": ["fr-CH"]})
        self.assertEqual(request.retrieval_terms[0].language, "de-AT")
        self.assertEqual(request.source_languages, ["fr-CH"])

    def test_bounded_terms_ids_and_evidence(self):
        cases = [
            {"max_evidence": 0}, {"max_evidence": 6}, {"concept_ids": ["duplicate", "duplicate"]},
            {"concept_ids": [f"concept-{i}" for i in range(51)]},
            {"retrieval_terms": [{"text": "x", "language": "en"}] * 21},
            {"retrieval_terms": [{"text": " ", "language": "en"}]},
            {"retrieval_terms": [{"text": "x" * 121, "language": "en"}]},
            {"domain_id": "Immigration"}, {"domain_id": "a--b"}, {"domain_id": "a_b"},
        ]
        for patch in cases:
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                StructuredGroundingRequest.model_validate({**request_payload(), **patch})

    def test_canonical_dates_in_python_and_json_input(self):
        self.assertEqual(StructuredGroundingRequest.model_validate_json(json.dumps(request_payload())).as_of, "2026-09-06")
        for value in ("2026-9-6", "2026-02-30", "2026-09-06T00:00:00Z", 1788652800):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                StructuredGroundingRequest.model_validate({**request_payload(), "as_of": value})
        with self.assertRaises(ValidationError):
            DateRange(valid_from="2026-09-06", valid_through="2026-09-05")

    def test_date_range_bounds_are_open_unless_stated(self):
        unbounded = DateRange()
        self.assertIsNone(unbounded.valid_from)
        self.assertIsNone(unbounded.valid_through)
        for day in ("1990-01-01", "2026-09-24", "2099-12-31"):
            self.assertTrue(unbounded.covers(day))
        commenced = DateRange(valid_from="2021-01-01")
        self.assertFalse(commenced.covers("2020-12-31"))
        self.assertTrue(commenced.covers("2021-01-01"))
        self.assertTrue(commenced.covers("2035-01-01"))
        expiring = DateRange(valid_through="2029-12-31")
        self.assertTrue(expiring.covers("1990-01-01"))
        self.assertFalse(expiring.covers("2030-01-01"))
        self.assertEqual(DateRange.model_validate_json("{}"), unbounded)
        with self.assertRaises(ValidationError):
            DateRange(valid_from="2026-9-6")


class IdentifierAndLanguageTests(unittest.TestCase):
    def test_artifact_ref_is_pinned_and_frozen(self):
        ref = ArtifactRef.model_validate(artifact())
        with self.assertRaises(ValidationError):
            ref.version = "2"
        for patch in ({"sha256": "a" * 63}, {"sha256": "A" * 64}, {"version": ""}, {"extra": "field"}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                ArtifactRef.model_validate({**artifact(), **patch})

    def test_canonical_language_grammar(self):
        for before, after in (("DE-de", "de-DE"), ("ZH-hant-tw", "zh-Hant-TW"), ("gsw-ch", "gsw-CH"), ("rm-CH", "rm-CH"), ("en-US-u-ca-gregory", "en-US-u-ca-gregory"), ("X-private", "x-private")):
            self.assertEqual(canonical_language_tag(before), after)
        for value in ("", "de_CH", "en-", " fr", "d", "en-a", "en-x", "en-1996-1996", "en-u-ca-u-nu"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_language_tag(value)

    def test_jurisdiction_hierarchy_and_casing(self):
        self.assertEqual(Jurisdiction(country_code="CH", canton_code="CH-ZH", municipality_id="261").municipality_id, "261")
        for payload in ({"country_code": "ch"}, {"country_code": "CH", "canton_code": "ZH"}, {"country_code": "CH", "canton_code": "CH-XX"}, {"country_code": "DE", "canton_code": "CH-ZH"}, {"country_code": "CH", "municipality_id": "261"}, {"country_code": "CH", "canton_code": "CH-ZH", "municipality_id": 261}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                Jurisdiction.model_validate(payload)

    def test_label_changes_do_not_change_public_identity(self):
        payload = {"entry_id": "synthetic-concept", "kind": "concept", "parent_ids": ["synthetic-topic"], "labels": {"en": {"label": "First label", "description": "A synthetic concept", "provenance": [artifact()]}}}
        first = CatalogEntry.model_validate(payload)
        payload["labels"]["en"]["label"] = "Changed label"
        second = CatalogEntry.model_validate(payload)
        self.assertEqual(first.entry_id, second.entry_id)
        self.assertEqual(first.lifecycle, "CANDIDATE")


class ContextSchemaTests(unittest.TestCase):
    def payload(self):
        return {"identity": artifact(), "fields": [
            {"name": "purpose", "kind": "string", "description": "Synthetic purpose", "required": True, "reason_code": "purpose_required", "enum": ["work", "study"]},
            {"name": "duration", "kind": "integer", "description": "Synthetic duration", "reason_code": "duration_required", "minimum": 1, "maximum": 100},
        ], "conditional_requirements": [{"when": [{"field": "purpose", "operator": "equals", "values": ["work"]}], "required_fields": ["duration"], "reason_code": "work_requires_duration"}]}

    def test_closed_subset_round_trips(self):
        schema = ContextSchema.model_validate(self.payload())
        self.assertEqual(ContextSchema.model_validate_json(schema.model_dump_json()), schema)
        self.assertFalse(schema.additional_properties)

    def test_rejects_undeclared_fields_and_unsupported_keywords(self):
        cases = []
        payload = self.payload()
        payload["conditional_requirements"][0]["required_fields"] = ["typo"]
        cases.append(payload)
        payload = self.payload()
        payload["conditional_requirements"][0]["when"][0]["values"] = []
        cases.append(payload)
        payload = self.payload()
        payload["fields"].append(copy.deepcopy(payload["fields"][0]))
        cases.append(payload)
        cases.extend({**self.payload(), key: value} for key, value in (("additional_properties", True), ("additional_properties", 0), ("anyOf", [])))
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                ContextSchema.model_validate(payload)

    def test_rejects_inverted_or_irrelevant_bounds(self):
        for patch in ({"minimum": 101}, {"min_length": 1}, {"kind": "boolean"}):
            payload = self.payload()
            payload["fields"][1].update(patch)
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                ContextSchema.model_validate(payload)


class DiscoveryEvidenceAndSchemaTests(unittest.TestCase):
    def test_discovery_pin_required_for_children_and_cursors(self):
        self.assertEqual(GetCoverageRequest().limit, 20)
        for patch in ({"cursor": "opaque"}, {"parent_id": "synthetic-topic"}, {"limit": 101}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                GetCoverageRequest.model_validate(patch)
        self.assertEqual(GetCoverageRequest(release_id="synthetic-release", cursor="opaque").cursor, "opaque")

    def test_evidence_is_original_and_release_bound(self):
        evidence = EvidenceObject.model_validate(evidence_payload())
        self.assertEqual(evidence.original_excerpt, "Hello")
        GetEvidenceResult(release_id="synthetic-release", release_ref=ArtifactRef.model_validate(artifact()), evidence=[evidence])
        for patch in ({"end_offset": 9}, {"original_excerpt": ""}, {"translated_excerpt": "Hallo"}, {"effective_source_language": "de-CH"}, {"effective_source_language": "gsw"}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                EvidenceObject.model_validate({**evidence_payload(), **patch})
        with self.assertRaises(ValidationError):
            GetEvidenceResult(release_id="another-release", release_ref=ArtifactRef.model_validate(artifact()), evidence=[evidence])
        for ids in ([], ["same", "same"], [f"evidence-{i}" for i in range(6)]):
            with self.subTest(ids=ids), self.assertRaises(ValidationError):
                GetEvidenceRequest(release_id="synthetic-release", evidence_ids=ids)

    def test_source_declaration_alias_set_is_closed(self):
        payload = {"identity": artifact(), "term_languages": [], "source_languages": [], "projection_languages": [], "routes": []}
        self.assertEqual(LanguagePolicy.model_validate(payload).approval_status, "DRAFT")
        with self.assertRaises(ValidationError):
            LanguagePolicy.model_validate({**payload, "source_declaration_aliases": {"de-CH": "de"}})
        with self.assertRaises(ValidationError):
            LanguagePolicy.model_validate({**payload, "approval_status": "APPROVED"})

    def test_evidence_uses_language_only_codes_and_preserves_raw_tags(self):
        for language in ("en", "de", "fr", "it", "rm"):
            with self.subTest(language=language):
                raw_tag = language + "-CH"
                evidence = EvidenceObject.model_validate({
                    **evidence_payload(), "declared_language": [raw_tag],
                    "detected_language": raw_tag, "effective_source_language": language,
                })
                self.assertEqual(evidence.effective_source_language, language)
                self.assertEqual(evidence.declared_language, [raw_tag])
                self.assertEqual(evidence.detected_language, raw_tag)

    def test_result_cannot_claim_complete_support_with_gaps(self):
        request = request_payload()
        scope = {key: value for key, value in request.items() if key not in {"schema_version", "release_id", "context"}}
        payload = {
            "release_id": "synthetic-release", "release_ref": artifact("synthetic-release"), "catalog_ref": artifact("synthetic-catalog"),
            "requested_scope": scope, "executed_scope": scope, "coverage_profile_ids": ["synthetic-profile"],
            "status": "SUPPORTED", "supported_portions": [{"identity": artifact("synthetic-fact"), "fact_id": "synthetic-fact", "statement": "Hello", "language": "en", "evidence_ids": ["synthetic-evidence"]}],
            "unresolved_portions": [], "evidence": [evidence_payload()], "missing_context": [],
            "freshness": {"status": "FRESH", "checked_at": "2026-09-06T00:00:00Z", "policy_ref": artifact("synthetic-freshness")},
            "trust": {"source_authorities": ["Synthetic authority"], "evaluation_ref": artifact("synthetic-evaluation"), "fact_support": "PUBLISHED_FACTS_OR_RULES", "limitations": []},
            "trace": None,
        }
        self.assertEqual(StructuredGroundingResult.model_validate(payload).status, "SUPPORTED")
        for patch in ({"evidence": []}, {"supported_portions": []}, {"executed_scope": None}, {"status": "NEEDS_CONTEXT"}, {"status": "PARTIALLY_SUPPORTED"}, {"answer": "Unsupported generated answer"}, {"unresolved_portions": [{"concept_ids": ["synthetic-concept"], "reason_code": "missing_support", "limitation": "Synthetic gap"}]}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                StructuredGroundingResult.model_validate({**payload, **patch})
        stale = copy.deepcopy(payload)
        stale["freshness"]["status"] = "STALE"
        with self.assertRaises(ValidationError):
            StructuredGroundingResult.model_validate(stale)

    def test_schema_bundle_is_deterministic_and_has_shared_definitions(self):
        documents = schema_documents()
        self.assertEqual(documents, schema_documents())
        self.assertEqual(len(documents), 1)
        schema = json.loads(next(iter(documents.values())))
        self.assertIn("StructuredGroundingRequest", schema["x-contracts"])
        self.assertFalse(schema["$defs"]["StructuredGroundingRequest"]["additionalProperties"])
        self.assertIn("schema_version", schema["$defs"]["StructuredGroundingRequest"]["required"])
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(export_schemas(["--output", temporary]), 0)
            self.assertEqual(export_schemas(["--output", temporary, "--check"]), 0)
            (Path(temporary) / next(iter(documents))).write_text("{}", encoding="utf-8")
            self.assertEqual(export_schemas(["--output", temporary, "--check"]), 1)


if __name__ == "__main__":
    unittest.main()
