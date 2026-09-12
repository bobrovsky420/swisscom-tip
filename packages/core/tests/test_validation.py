"""Synthetic contract scenarios, with no claims about Swiss legal coverage."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from swisstip.core.contracts import ContextSchema, KnowledgeCatalog, LanguagePolicy
from swisstip.core.identity import seal_artifact
from swisstip.core.validation import validate_catalog, validate_request


def ref(identifier: str) -> dict[str, str]:
    return {"artifact_id": identifier, "version": "1", "sha256": "a" * 64}


def entry(identifier: str, kind: str, parent: str | None = None) -> dict:
    return {
        "entry_id": identifier, "kind": kind,
        "parent_ids": [] if parent is None else [parent], "lifecycle": "CURATED",
        "labels": {"en": {"label": identifier, "description": "Synthetic test fixture.", "provenance": [ref("test-review")]}},
    }


def fixture() -> tuple[dict, dict, dict]:
    policy = {
        "identity": ref("test-policy"), "term_languages": ["en", "de", "fr"],
        "source_languages": ["de", "fr"], "projection_languages": ["en", "de", "fr"],
        "term_aliases": {},
        "routes": [{"term_language": tag, "projection_language": tag} for tag in ["en", "de", "fr"]],
        "source_detector_mappings": {"de-CH": "de"},
        "evaluation_ref": ref("test-language-evaluation"), "approval_status": "APPROVED",
    }
    context_schema = {
        "identity": ref("test-context"),
        "fields": [
            {"name": "population", "kind": "string", "description": "Synthetic population group.", "required": True, "enum": ["group-a", "group-b"], "reason_code": "population_required"},
            {"name": "purpose", "kind": "string", "description": "Synthetic purpose.", "required": True, "enum": ["study", "work"], "reason_code": "purpose_required"},
            {"name": "work_days", "kind": "integer", "description": "Synthetic duration.", "minimum": 1, "maximum": 365, "reason_code": "duration_required"},
            {"name": "has_contract", "kind": "boolean", "description": "Synthetic contract assertion.", "reason_code": "contract_required"},
            {"name": "starts_on", "kind": "date", "description": "Synthetic start date.", "reason_code": "start_required"},
            {"name": "ends_on", "kind": "date", "description": "Synthetic end date.", "reason_code": "end_required"},
        ],
        "conditional_requirements": [{
            "when": [{"field": "purpose", "operator": "equals", "values": ["work"]}],
            "required_fields": ["work_days", "has_contract"], "reason_code": "work_details_required",
            "rule_refs": [ref("test-work-rule")], "evidence_refs": [ref("test-work-evidence")],
        }],
        "consistency_rules": [{"left_field": "starts_on", "operator": "lte", "right_field": "ends_on", "reason_code": "date_order"}],
    }
    profile = {
        "coverage_profile_id": "test-residence-profile", "release_id": "test-release-a", "catalog_ref": ref("test-catalog"),
        "knowledge_space_id": "test-space", "domain_id": "test-domain", "topic_id": "test-topic",
        "concept_ids": ["test-concept", "test-child", "test-grandchild", "test-sibling"],
        "intent": "requirements", "concept_selection_required": True,
        "jurisdiction": {"country_code": "CH", "canton_code": "CH-ZH"},
        "context_schema_ref": ref("test-context"), "scope_modes": ["exact", "descendants"],
        "max_descendant_depth": 1, "max_concepts": 5,
        "source_ids": ["test-source"], "source_languages": ["de"],
        "temporal_coverage": {"valid_from": "2026-01-01", "valid_through": "2026-12-31"},
        "term_routes": [{"term_language": tag, "projection_language": tag, "source_languages": ["de"], "evaluation_ref": ref("test-route-evaluation")} for tag in ["en", "de"]],
        "projection_languages_complete": ["en", "de"], "evaluation_ref": ref("test-coverage-evaluation"),
        "freshness_policy": {"max_age_days": 30, "policy_ref": ref("test-freshness")}, "approval_status": "APPROVED",
    }
    catalog = {
        "identity": ref("test-catalog"), "release_id": "test-release-a", "language_policy_ref": ref("test-policy"),
        "entries": [entry("test-space", "knowledge_space"), entry("test-domain", "domain", "test-space"), entry("test-topic", "topic", "test-domain"), entry("test-concept", "concept", "test-topic"), entry("test-child", "concept", "test-concept"), entry("test-grandchild", "concept", "test-child"), entry("test-sibling", "concept", "test-topic"), entry("other-topic", "topic", "test-domain"), entry("other-concept", "concept", "other-topic")],
        "context_schemas": [context_schema], "coverage_profiles": [profile],
    }
    request = {
        "schema_version": "structured-grounding/v1", "release_id": "test-release-a",
        "knowledge_space_id": "test-space", "domain_id": "test-domain", "topic_id": "test-topic",
        "concept_ids": ["test-concept"], "intent": "requirements", "jurisdiction": {"country_code": "CH", "canton_code": "CH-ZH"},
        "context": {"population": "group-a", "purpose": "study"}, "as_of": "2026-09-06", "scope_mode": "exact",
    }
    return catalog, policy, request


class FixtureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog_data, self.policy_data, self.request = fixture()

    def models(self) -> tuple[KnowledgeCatalog, LanguagePolicy]:
        catalog_data = copy.deepcopy(self.catalog_data)
        policy = seal_artifact(LanguagePolicy.model_validate(self.policy_data))
        if catalog_data["language_policy_ref"] == self.policy_data["identity"]:
            catalog_data["language_policy_ref"] = policy.identity.model_dump()
        for index, original in enumerate(catalog_data["context_schemas"]):
            schema = seal_artifact(ContextSchema.model_validate(original))
            for profile in catalog_data["coverage_profiles"]:
                if profile["context_schema_ref"] == original["identity"]:
                    profile["context_schema_ref"] = schema.identity.model_dump()
            catalog_data["context_schemas"][index] = schema.model_dump()
        return seal_artifact(KnowledgeCatalog.model_validate(catalog_data)), policy

    def assess(self):
        catalog, policy = self.models()
        return validate_request(self.request, catalog, policy, active_release_id="test-release-a")

    def assert_status(self, expected: str):
        assessment = self.assess()
        self.assertEqual(assessment.status, expected, assessment)
        return assessment


class StructuredValidationTests(FixtureTestCase):

    def test_source_language_expansion_requires_v4_policy_and_explicit_allowlist(self):
        self.policy_data['source_languages'].append('uk')
        catalog, policy = self.models()
        self.assertTrue(validate_catalog(catalog, policy))
        self.policy_data['platform_catalog'] = 'tip-language-catalog/v4'
        catalog, policy = self.models()
        self.assertFalse(validate_catalog(catalog, policy))
        self.request['source_languages'] = ['ar']
        self.assert_status('UNSUPPORTED_LANGUAGE')
        self.request['source_languages'] = ['uk']
        self.assert_status('OUT_OF_COVERAGE')

    def test_ready_is_validation_only_and_exact_scope_has_no_children(self):
        result = self.assert_status("READY")
        self.assertEqual(result.executed_concept_ids, ("test-concept",))
        self.assertIsNone(result.effective_source_languages)
        self.assertFalse(hasattr(result, "supported_portions"))

    def test_conditional_missing_fields_include_sources_and_do_not_infer_terms(self):
        self.request["context"]["purpose"] = "work"
        self.request["retrieval_terms"] = [{"text": "I have a contract for 30 work days", "language": "en"}]
        result = self.assert_status("NEEDS_CONTEXT")
        self.assertEqual({item.field for item in result.missing_context}, {"context.work_days", "context.has_contract"})
        self.assertTrue(all(item.rule_refs and item.evidence_refs and item.schema_ref for item in result.missing_context))
        self.request["context"].update(work_days=30, has_contract=False)
        self.assert_status("READY")

    def test_missing_required_context_is_not_malformed_context(self):
        self.request["context"] = {}
        result = self.assert_status("NEEDS_CONTEXT")
        self.assertEqual(result.missing_context[0].allowed_values, ("group-a", "group-b"))
        for malformed in [None, "group-a", [], {"population": {"value": "group-a"}}]:
            with self.subTest(context=malformed):
                self.request["context"] = malformed
                self.assert_status("INVALID_ARGUMENT")

    def test_unknown_context_field_beats_missing_conditional_context(self):
        self.request["context"] = {"invented": True}
        result = self.assert_status("INVALID_ARGUMENT")
        self.assertEqual(result.issues[0].reason, "unknown_field")

    def test_strict_context_scalars_enums_and_bounds(self):
        for field, value in [("work_days", True), ("work_days", "30"), ("work_days", 0), ("work_days", 366), ("population", "invented"), ("has_contract", 1), ("starts_on", "20260906"), ("starts_on", "2026-02-30"), ("work_days", None)]:
            with self.subTest(field=field, value=value):
                self.request["context"] = {"population": "group-a", "purpose": "study", field: value}
                self.assert_status("INVALID_ARGUMENT")

    def test_numbers_compare_by_value_without_treating_booleans_as_numbers(self):
        schema = self.catalog_data["context_schemas"][0]
        schema["fields"].append({"name": "amount", "kind": "number", "description": "Synthetic amount.", "reason_code": "amount_required", "enum": [1, 2.5]})
        schema["conditional_requirements"].append({"when": [{"field": "amount", "operator": "equals", "values": [1]}], "required_fields": ["has_contract"], "reason_code": "contract_required"})
        for value in [1, 1.0]:
            with self.subTest(value=value):
                self.request["context"]["amount"] = value
                self.assertEqual(self.assert_status("NEEDS_CONTEXT").missing_context[0].field, "context.has_contract")
        self.request["context"]["amount"] = True
        self.assert_status("INVALID_ARGUMENT")

    def test_boolean_condition_does_not_match_numeric_assertion(self):
        self.request["context"]["has_contract"] = 1
        self.assert_status("INVALID_ARGUMENT")

    def test_context_consistency_rejects_inverted_dates(self):
        self.request["context"].update(starts_on="2026-09-06", ends_on="2026-09-05")
        result = self.assert_status("INVALID_ARGUMENT")
        self.assertEqual(result.issues[0].reason, "date_order")

    def test_unknown_envelope_fields_and_required_fields_are_boundary_errors(self):
        original = copy.deepcopy(self.request)
        for name in ["question", "query_language", "response_language", "structured_context"]:
            self.request = {**original, name: "work"}
            self.assert_status("INVALID_ARGUMENT")
        for name in ["context", "topic_id", "intent", "release_id", "scope_mode"]:
            self.request = copy.deepcopy(original)
            del self.request[name]
            self.request["retrieval_terms"] = [{"text": "requirements test topic", "language": "en"}]
            self.assert_status("INVALID_ARGUMENT")

    def test_unknown_selector_wrong_kind_and_foreign_topic_are_errors(self):
        for concepts in [["invented-concept"], ["test-topic"], ["other-concept"]]:
            self.request["concept_ids"] = concepts
            self.assert_status("INVALID_ARGUMENT")

    def test_missing_required_concept_cannot_be_repaired_by_terms(self):
        del self.request["concept_ids"]
        self.request["retrieval_terms"] = [{"text": "test-concept", "language": "en"}]
        self.assertEqual(self.assert_status("INVALID_ARGUMENT").issues[0].reason, "missing_concept_selector")

    def test_topic_operation_may_omit_concepts_without_traversing(self):
        self.catalog_data["coverage_profiles"][0]["concept_selection_required"] = False
        del self.request["concept_ids"]
        self.assertEqual(self.assert_status("READY").executed_concept_ids, ())

    def test_unknown_intent_versus_known_unsupported_combination(self):
        self.request["intent"] = "procedure"
        self.assert_status("INVALID_ARGUMENT")
        self.request["intent"] = "requirements"
        self.request["topic_id"] = "other-topic"
        self.request["concept_ids"] = ["other-concept"]
        self.assert_status("OUT_OF_COVERAGE")

    def test_wider_profile_serves_places_inside_its_jurisdiction(self):
        profile = self.catalog_data["coverage_profiles"][0]
        profile["jurisdiction"] = {"country_code": "CH"}
        self.request["jurisdiction"] = {"country_code": "CH", "canton_code": "CH-BE"}
        self.assertEqual(self.assert_status("READY").coverage_profile_ids, ("test-residence-profile",))
        self.request["jurisdiction"] = {"country_code": "CH", "canton_code": "CH-ZH", "municipality_id": "261"}
        self.assert_status("READY")
        profile["jurisdiction"] = {"country_code": "CH", "canton_code": "CH-ZH"}
        self.assert_status("READY")
        self.request["jurisdiction"] = {"country_code": "CH"}
        gap = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual((gap.issues[0].reason, gap.issues[0].supported_values), ("more_specific_jurisdiction_required", ("CH-ZH",)))
        self.request["jurisdiction"] = {"country_code": "CH", "canton_code": "CH-BE"}
        gap = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual((gap.issues[0].reason, gap.issues[0].supported_values), ("jurisdiction_not_covered", ("CH-ZH",)))

    def test_narrowest_matching_profile_wins(self):
        federal = copy.deepcopy(self.catalog_data["coverage_profiles"][0])
        federal["coverage_profile_id"] = "test-federal-profile"
        federal["jurisdiction"] = {"country_code": "CH"}
        self.catalog_data["coverage_profiles"].append(federal)
        self.assertEqual(self.assert_status("READY").coverage_profile_ids, ("test-residence-profile",))
        self.request["jurisdiction"] = {"country_code": "CH", "canton_code": "CH-BE"}
        self.assertEqual(self.assert_status("READY").coverage_profile_ids, ("test-federal-profile",))

    def test_coverage_gaps_name_the_failing_dimension(self):
        profile = self.catalog_data["coverage_profiles"][0]
        profile["scope_modes"] = ["exact"]
        self.request["scope_mode"] = "descendants"
        gap = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual((gap.issues[0].reason, gap.issues[0].supported_values), ("scope_mode_not_offered", ("exact",)))
        self.request["scope_mode"] = "exact"
        self.request["as_of"] = "2027-01-01"
        gap = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual((gap.issues[0].reason, gap.issues[0].supported_values), ("date_outside_coverage", ("2026-01-01 to 2026-12-31",)))
        self.request["as_of"] = "2026-09-06"
        second = copy.deepcopy(profile)
        second["coverage_profile_id"] = "test-second-profile"
        second["concept_ids"] = ["test-sibling"]
        profile["concept_ids"] = ["test-concept"]
        self.catalog_data["coverage_profiles"].append(second)
        self.request["concept_ids"] = ["test-concept", "test-sibling"]
        gap = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual((gap.issues[0].reason, gap.issues[0].supported_values),
                         ("concept_set_not_published", ("test-residence-profile", "test-second-profile")))

    def test_canonical_unconfigured_jurisdiction_is_out_of_coverage(self):
        self.request["jurisdiction"]["canton_code"] = "CH-BE"
        self.assert_status("OUT_OF_COVERAGE")
        for invalid in ["Zurich", "ch-zh", "CH-XX"]:
            self.request["jurisdiction"]["canton_code"] = invalid
            self.assert_status("INVALID_ARGUMENT")

    def test_jurisdiction_never_broadens_upward(self):
        # A canton profile serves its municipalities, never its country.
        self.request["jurisdiction"]["municipality_id"] = "261"
        self.assertEqual(self.assert_status("READY").coverage_profile_ids, ("test-residence-profile",))
        self.request["jurisdiction"] = {"country_code": "CH"}
        self.assertEqual(self.assert_status("OUT_OF_COVERAGE").issues[0].reason, "more_specific_jurisdiction_required")

    def test_other_jurisdiction_schema_cannot_validate_current_context(self):
        schema = copy.deepcopy(self.catalog_data["context_schemas"][0])
        schema["identity"] = ref("test-be-context")
        schema["fields"].append({"name": "be_only", "kind": "boolean", "description": "Synthetic BE field.", "reason_code": "be_context"})
        self.catalog_data["context_schemas"].append(schema)
        profile = copy.deepcopy(self.catalog_data["coverage_profiles"][0])
        profile.update(coverage_profile_id="test-be-profile", jurisdiction={"country_code": "CH", "canton_code": "CH-BE"}, context_schema_ref=ref("test-be-context"), concept_selection_required=False)
        self.catalog_data["coverage_profiles"].append(profile)
        self.request["context"]["be_only"] = True
        self.assert_status("INVALID_ARGUMENT")
        del self.request["context"]["be_only"]
        del self.request["concept_ids"]
        self.assertEqual(self.assert_status("INVALID_ARGUMENT").issues[0].reason, "missing_concept_selector")
        self.request["jurisdiction"]["canton_code"] = "CH-BE"
        self.assert_status("READY")

    def test_outside_temporal_coverage_and_malformed_dates(self):
        self.request["as_of"] = "2027-01-01"
        self.assert_status("OUT_OF_COVERAGE")
        self.request["as_of"] = "2026-02-30"
        self.assert_status("INVALID_ARGUMENT")

    def test_unbounded_validity_accepts_any_date_and_stated_bounds_are_enforced(self):
        profile = self.catalog_data["coverage_profiles"][0]
        profile["temporal_coverage"] = {}
        for as_of in ("1990-01-01", "2026-09-24", "2099-12-31"):
            self.request["as_of"] = as_of
            self.assert_status("READY")
        profile["temporal_coverage"] = {"valid_from": "2021-01-01"}
        self.request["as_of"] = "2020-12-31"
        gap = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual((gap.issues[0].reason, gap.issues[0].supported_values), ("date_outside_coverage", ("from 2021-01-01",)))
        self.request["as_of"] = "2021-01-01"
        self.assert_status("READY")
        profile["temporal_coverage"] = {"valid_through": "2029-12-31"}
        self.request["as_of"] = "2030-01-01"
        self.assert_status("OUT_OF_COVERAGE")
        self.request["as_of"] = "2029-12-31"
        self.assert_status("READY")

    def test_language_only_terms_preserve_source_scope(self):
        self.request["retrieval_terms"] = [{"text": "Begriff", "language": "DE"}, {"text": "term", "language": "EN"}]
        result = self.assert_status("READY")
        self.assertEqual(result.term_routes[0].requested_language, "de")
        self.assertEqual(result.term_routes[0].effective_term_language, "de")
        self.assertIsNone(result.effective_source_languages)
        self.request["source_languages"] = ["de"]
        self.assertEqual(self.assert_status("READY").effective_source_languages, ("de",))
        self.request["source_languages"] = ["de-CH"]
        result = self.assert_status("UNSUPPORTED_LANGUAGE")
        self.assertEqual(result.issues[0].field, "source_languages.0")

    def test_valid_unsupported_term_is_reported_with_index(self):
        self.request["retrieval_terms"] = [{"text": "term", "language": "en"}, {"text": "Begriff", "language": "de-AT"}]
        result = self.assert_status("UNSUPPORTED_LANGUAGE")
        self.assertEqual(result.issues[0].field, "retrieval_terms.1.language")
        for unsupported in ["de-CH", "de-DE", "fr-CH", "it-CH", "rm-CH", "gsw-CH", "x-test"]:
            self.request["retrieval_terms"] = [{"text": "term", "language": unsupported}]
            self.assert_status("UNSUPPORTED_LANGUAGE")
        self.request["retrieval_terms"] = [{"text": "term", "language": "de_CH"}]
        self.assert_status("INVALID_ARGUMENT")

    def test_enabled_term_but_unevaluated_route_is_out_of_coverage(self):
        self.request["retrieval_terms"] = [{"text": "terme", "language": "fr"}]
        self.assertEqual(self.assert_status("OUT_OF_COVERAGE").issues[0].reason, "unevaluated_language_combination")

    def test_all_language_only_routes_work_when_evaluated(self):
        languages = ["en", "de", "fr", "it", "rm"]
        routes = [{"term_language": tag, "projection_language": tag} for tag in languages]
        routes[-1]["idiom_profile"] = "test-reviewed-romansh"
        routes.append({"term_language": "gsw", "projection_language": "de", "dialect_profile": "test-reviewed-dialect"})
        self.policy_data.update(
            term_languages=languages + ["gsw"], source_languages=languages,
            projection_languages=languages, routes=routes,
        )
        profile = self.catalog_data["coverage_profiles"][0]
        profile.update(
            source_languages=languages, projection_languages_complete=languages,
            term_routes=[{**route, "source_languages": languages, "evaluation_ref": ref("test-route-evaluation")} for route in routes],
        )
        for tag in languages + ["gsw"]:
            with self.subTest(tag=tag):
                self.request["retrieval_terms"] = [{"text": "synthetic term", "language": tag.upper()}]
                self.request["source_languages"] = languages
                result = self.assert_status("READY")
                self.assertEqual(result.term_routes[0].requested_language, tag)
                self.assertEqual(result.term_routes[0].effective_term_language, tag)
                self.assertEqual(result.term_routes[0].projection_language, "de" if tag == "gsw" else tag)
                self.assertEqual(result.effective_source_languages, tuple(languages))

    def test_source_filter_canonicalizes_deduplicates_and_never_falls_back(self):
        self.request["source_languages"] = ["DE", "de"]
        self.assertEqual(self.assert_status("READY").effective_source_languages, ("de",))
        self.request["source_languages"] = ["fr"]
        result = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual(result.effective_source_languages, ("fr",))
        self.assertEqual(result.issues[0].reason, "no_coverage_in_requested_source_languages")
        self.request["source_languages"] = []
        self.assert_status("INVALID_ARGUMENT")

    def test_unavailable_release_and_boundary_precedence(self):
        self.request["release_id"] = "test-release-b"
        result = self.assert_status("RELEASE_UNAVAILABLE")
        self.assertEqual(result.active_release_id, "test-release-a")
        self.assertEqual(result.request.release_id, "test-release-b")
        self.request["question"] = "anything"
        self.assert_status("INVALID_ARGUMENT")

    def test_candidate_cannot_be_a_selector(self):
        self.catalog_data["entries"].append(entry("test-candidate", "concept", "test-topic"))
        self.catalog_data["entries"][-1]["lifecycle"] = "CANDIDATE"
        self.request["concept_ids"] = ["test-candidate"]
        self.assert_status("INVALID_ARGUMENT")

    def test_descendant_depth_excludes_sibling_and_grandchild(self):
        self.request["scope_mode"] = "descendants"
        result = self.assert_status("READY")
        self.assertEqual(result.executed_concept_ids, ("test-child", "test-concept"))
        self.catalog_data["coverage_profiles"][0]["max_descendant_depth"] = 2
        self.assertEqual(self.assert_status("READY").executed_concept_ids, ("test-child", "test-concept", "test-grandchild"))
        self.catalog_data["coverage_profiles"][0]["max_concepts"] = 2
        self.assert_status("INVALID_ARGUMENT")

    def test_descendant_traversal_reaches_concepts_through_nested_topics(self):
        self.catalog_data["entries"].extend([entry("nested-topic", "topic", "test-topic"), entry("nested-concept", "concept", "nested-topic")])
        profile = self.catalog_data["coverage_profiles"][0]
        profile.update(concept_ids=["nested-concept"], concept_selection_required=False, max_descendant_depth=2)
        del self.request["concept_ids"]
        self.request["scope_mode"] = "descendants"
        self.assertEqual(self.assert_status("READY").executed_concept_ids, ("nested-concept",))
        profile["max_descendant_depth"] = 1
        self.assertEqual(self.assert_status("READY").executed_concept_ids, ())

    def test_scope_bound_is_checked_before_missing_context(self):
        self.catalog_data["coverage_profiles"][0]["max_concepts"] = 1
        self.request["concept_ids"] = ["test-concept", "test-sibling"]
        self.request["context"] = {}
        self.assert_status("INVALID_ARGUMENT")
        self.request["concept_ids"] = ["test-concept"]
        self.request["scope_mode"] = "descendants"
        self.assert_status("INVALID_ARGUMENT")

    def test_independent_profiles_do_not_imply_cross_product(self):
        second = copy.deepcopy(self.catalog_data["coverage_profiles"][0])
        second["coverage_profile_id"] = "test-second-profile"
        second["concept_ids"] = ["test-sibling"]
        self.catalog_data["coverage_profiles"][0]["concept_ids"] = ["test-concept"]
        self.catalog_data["coverage_profiles"].append(second)
        self.request["concept_ids"] = ["test-concept", "test-sibling"]
        self.assert_status("OUT_OF_COVERAGE")

    def test_overlapping_profiles_are_not_chosen_by_list_order(self):
        second = copy.deepcopy(self.catalog_data["coverage_profiles"][0])
        second["coverage_profile_id"] = "test-second-profile"
        self.catalog_data["coverage_profiles"].append(second)
        first = self.assert_status("OUT_OF_COVERAGE")
        self.assertEqual(first.issues[0].reason, "ambiguous_coverage_profiles")
        self.catalog_data["coverage_profiles"].reverse()
        self.assertEqual(first, self.assess())

    def test_non_json_numbers_are_rejected(self):
        self.request["context"]["work_days"] = float("nan")
        self.assert_status("INVALID_ARGUMENT")

    def test_python_inputs_do_not_coerce_tuples_to_json_arrays(self):
        self.request["concept_ids"] = ("test-concept",)
        self.assert_status("INVALID_ARGUMENT")

    def test_omitted_evidence_budget_respects_lower_catalog_limit(self):
        self.catalog_data["max_evidence"] = 3
        self.assertEqual(self.assert_status("READY").request.max_evidence, 3)
        self.request["max_evidence"] = 4
        self.assert_status("INVALID_ARGUMENT")

    def test_missing_fields_are_unique_when_conditions_overlap(self):
        self.catalog_data["context_schemas"][0]["fields"][2]["required"] = True
        self.request["context"]["purpose"] = "work"
        result = self.assert_status("NEEDS_CONTEXT")
        fields = [item.field for item in result.missing_context]
        self.assertEqual(fields.count("context.work_days"), 1)
        self.assertTrue(next(item for item in result.missing_context if item.field == "context.work_days").rule_refs)


class CatalogIntegrityTests(FixtureTestCase):
    def reasons(self) -> set[str]:
        return {issue.reason for issue in validate_catalog(*self.models())}

    def test_synthetic_fixture_is_referentially_closed_inline(self):
        self.assertEqual(validate_catalog(*self.models()), ())

    def test_duplicate_public_ids_and_cycles_are_rejected(self):
        self.catalog_data["entries"].append(copy.deepcopy(self.catalog_data["entries"][0]))
        self.assertIn("duplicate_id", self.reasons())
        self.catalog_data["entries"].pop()
        self.catalog_data["entries"][3]["parent_ids"] = ["test-child"]
        self.assertIn("parent_cycle", self.reasons())

    def test_wrong_parent_kind_and_dangling_parent_are_rejected(self):
        self.catalog_data["entries"][3]["parent_ids"] = ["test-space"]
        self.assertIn("invalid_hierarchy", self.reasons())
        self.catalog_data["entries"][3]["parent_ids"] = ["missing-topic"]
        self.assertIn("unknown_id", self.reasons())

    def test_schema_and_catalog_references_bind_hash_and_version(self):
        self.catalog_data["coverage_profiles"][0]["context_schema_ref"]["version"] = "2"
        self.assertIn("artifact_mismatch", self.reasons())

    def test_tampered_content_and_embedded_self_hash_are_rejected(self):
        catalog, policy = self.models()
        changed = catalog.model_dump()
        changed["entries"][0]["labels"]["en"]["label"] = "Changed label"
        self.assertIn("content_hash_mismatch", {issue.reason for issue in validate_catalog(KnowledgeCatalog.model_validate(changed), policy)})
        changed = catalog.model_dump()
        changed["coverage_profiles"][0]["catalog_ref"]["sha256"] = "f" * 64
        self.assertIn("content_hash_mismatch", {issue.reason for issue in validate_catalog(KnowledgeCatalog.model_validate(changed), policy)})

    def test_invalid_context_schema_enum_and_condition_type_are_rejected(self):
        self.catalog_data["context_schemas"][0]["fields"][2]["enum"] = [True]
        self.assertIn("invalid_context_schema", self.reasons())
        del self.catalog_data["context_schemas"][0]["fields"][2]["enum"]
        self.catalog_data["context_schemas"][0]["conditional_requirements"][0]["when"][0]["values"] = [True]
        self.assertIn("invalid_context_schema", self.reasons())

    def test_incompatible_consistency_field_types_are_rejected(self):
        self.catalog_data["context_schemas"][0]["consistency_rules"][0]["right_field"] = "work_days"
        self.assertIn("invalid_context_schema", self.reasons())

    def test_approved_profile_cannot_promote_candidate(self):
        self.catalog_data["entries"][3]["lifecycle"] = "CANDIDATE"
        self.assertIn("unreviewed_coverage", self.reasons())
        self.catalog_data["coverage_profiles"][0]["approval_status"] = "DRAFT"
        self.assertNotIn("unreviewed_coverage", self.reasons())

    def test_v3_roles_cannot_expand_from_configuration(self):
        self.policy_data["source_languages"].append("de-CH")
        self.assertIn("language_policy", self.reasons())
        self.policy_data["source_languages"].pop()
        self.policy_data["term_aliases"]["de-AT"] = "de"
        self.assertIn("language_policy", self.reasons())

    def test_incomplete_or_ambiguous_evaluated_routes_are_rejected(self):
        self.catalog_data["coverage_profiles"][0]["projection_languages_complete"] = ["de"]
        self.assertIn("incomplete_projection", self.reasons())
        self.catalog_data["coverage_profiles"][0]["term_routes"].append(copy.deepcopy(self.catalog_data["coverage_profiles"][0]["term_routes"][0]))
        self.assertIn("duplicate_route", self.reasons())

    def test_swiss_german_and_romansh_require_declared_tested_forms(self):
        for tag, projection, field in [("gsw", "de", "dialect_profile"), ("rm", "rm", "idiom_profile")]:
            with self.subTest(tag=tag):
                self.catalog_data, self.policy_data, self.request = fixture()
                self.policy_data["term_languages"].append(tag)
                if projection not in self.policy_data["projection_languages"]:
                    self.policy_data["projection_languages"].append(projection)
                self.policy_data["routes"].append({"term_language": tag, "projection_language": projection})
                self.assertIn("missing_language_profile", self.reasons())
                self.policy_data["routes"][-1][field] = "test-reviewed-form"
                self.assertNotIn("missing_language_profile", self.reasons())

    def test_external_artifact_registry_checks_rules_evidence_and_provenance(self):
        catalog, policy = self.models()
        issues = validate_catalog(catalog, policy, artifacts={})
        paths = {issue.field for issue in issues}
        self.assertTrue(any("evidence_refs" in path for path in paths))
        self.assertTrue(any("rule_refs" in path for path in paths))
        self.assertTrue(any("provenance" in path for path in paths))


if __name__ == "__main__":
    unittest.main()
