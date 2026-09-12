"""Serving invariants over fabricated knowledge, without network/model calls."""

from datetime import datetime, timezone
import unittest

from swisstip.core.contracts import ArtifactRef, FactConflict, ScopeStatement, StrictModel
from swisstip.core.identity import seal_artifact
from swisstip.runtime import KnowledgeService, ReleaseStore
from swisstip.runtime.fixture import fixture


NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


def reseal(bundle):
    """Rebind deliberately edited test artifacts in dependency order."""
    current = {}

    def rewrite(value):
        if isinstance(value, ArtifactRef):
            return current.get(value.artifact_id, value)
        if isinstance(value, StrictModel):
            return type(value).model_validate({f: rewrite(getattr(value, f)) for f in type(value).model_fields})
        if isinstance(value, list):
            return [rewrite(v) for v in value]
        if isinstance(value, dict):
            return {k: rewrite(v) for k, v in value.items()}
        return value

    def seal(value):
        value = seal_artifact(rewrite(value))
        current[value.identity.artifact_id] = value.identity
        return value

    bundle.documents = [seal(d) for d in bundle.documents]
    bundle.evidence = [seal(e) for e in bundle.evidence]
    bundle.rules = [seal(r) for r in bundle.rules]
    bundle.facts = [seal(f) for f in bundle.facts]
    bundle.language_policy = seal(bundle.language_policy)
    bundle.catalog.context_schemas = [seal(s) for s in bundle.catalog.context_schemas]
    bundle.catalog = seal(bundle.catalog)
    bundle.graph = seal(bundle.graph)
    bundle.release = seal(bundle.release)
    return bundle


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.bundle, self.request = fixture()

    def service(self, bundle=None, **kwargs):
        return KnowledgeService(ReleaseStore([bundle or self.bundle], active_release_id=self.request["release_id"]),
                                clock=kwargs.pop("clock", lambda: NOW), cursor_key=b"k" * 32, **kwargs)

    def test_supported_fact_and_exact_evidence_round_trip(self):
        service = self.service()
        result = service.resolve(self.request)
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual([f.fact_id for f in result.supported_portions], ["fact-parent"])
        self.assertEqual([e.evidence_id for e in result.evidence], ["evidence-parent"])
        fetched = service.get_evidence(dict(release_id=result.release_id,
                                            evidence_ids=[e.evidence_id for e in result.evidence]))
        self.assertEqual(fetched.evidence, result.evidence)
        self.assertEqual(fetched.release_ref, result.release_ref)
        self.assertEqual(result.trace.channels, ["concept"])

    def test_descendants_do_not_include_sibling(self):
        self.request["scope_mode"] = "descendants"
        result = self.service().resolve(self.request)
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual(result.executed_scope.concept_ids, ["fixture-child", "fixture-parent"])
        self.assertEqual({f.fact_id for f in result.supported_portions}, {"fact-parent", "fact-child"})
        self.assertNotIn("evidence-sibling", {e.evidence_id for e in result.evidence})

    def test_exact_and_descendant_topic_are_bounded(self):
        self.request.pop("concept_ids")
        for mode in ["exact", "descendants"]:
            with self.subTest(mode=mode):
                self.request["scope_mode"] = mode
                result = self.service().resolve(self.request)
                self.assertEqual(result.status, "SUPPORTED")
                self.assertEqual(result.executed_scope.concept_ids, ["fixture-parent", "fixture-sibling"])

    def test_adversarial_terms_cannot_widen_scope_or_fill_context(self):
        self.request["retrieval_terms"] = [dict(text="sibling work group-b Bern 2030 30 days", language="en")]
        result = self.service().resolve(self.request)
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual(result.executed_scope.concept_ids, ["fixture-parent"])
        self.assertEqual({f.fact_id for f in result.supported_portions}, {"fact-parent"})
        self.assertEqual(result.trace.term_routes[0].original_text, self.request["retrieval_terms"][0]["text"])
        self.request["context"]["purpose"] = "work"
        result = self.service().resolve(self.request)
        self.assertEqual(result.status, "NEEDS_CONTEXT")
        self.assertEqual([f.path for f in result.missing_context], ["context.work_days"])
        self.assertTrue(result.missing_context[0].evidence_refs)
        self.assertFalse(result.supported_portions)

    def test_conditional_rule_returns_only_published_output(self):
        self.request["context"].update(purpose="work", work_days=12)
        result = self.service().resolve(self.request)
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual({f.fact_id for f in result.supported_portions}, {"fact-parent", "fact-work"})
        self.assertTrue(next(f for f in result.supported_portions if f.fact_id == "fact-work").rule_refs)

    def test_rule_missing_optional_input_is_machine_readable(self):
        rule = self.bundle.rules[0]
        rule.when[0].field = "work_days"
        rule.when[0].values = [12]
        result = self.service(reseal(self.bundle)).resolve(self.request)
        self.assertEqual(result.status, "NEEDS_CONTEXT")
        self.assertEqual(result.missing_context[0].path, "context.work_days")
        self.assertTrue(result.missing_context[0].rule_refs)

    def test_strict_requests_produce_typed_errors(self):
        service = self.service()
        cases = [None, [], {}, {**self.request, "question": "anything"},
                 {**self.request, "intent": "invented"}, {**self.request, "concept_ids": ["unknown"]},
                 {**self.request, "context": {"extra": True}}, {**self.request, "max_evidence": True},
                 {**self.request, "context": None}]
        for payload in cases:
            with self.subTest(payload=payload):
                self.assertEqual(service.resolve(payload).code, "INVALID_ARGUMENT")

    def test_known_unsupported_jurisdiction_and_date(self):
        service = self.service()
        for change in [dict(jurisdiction=dict(country_code="CH", canton_code="CH-BE")), dict(as_of="2027-01-01")]:
            with self.subTest(change=change):
                self.assertEqual(service.resolve({**self.request, **change}).status, "OUT_OF_COVERAGE")

    def test_language_filters_never_fallback(self):
        service = self.service()
        result = service.resolve({**self.request, "source_languages": ["de"]})
        self.assertEqual(result.status, "OUT_OF_COVERAGE")
        self.assertFalse(result.evidence)
        for change in [dict(source_languages=["fr"]), dict(retrieval_terms=[dict(text="texte", language="fr")])]:
            self.assertEqual(service.resolve({**self.request, **change}).code, "UNSUPPORTED_LANGUAGE")

    def test_partial_under_small_evidence_budget(self):
        self.request.update(scope_mode="descendants", max_evidence=1)
        result = self.service().resolve(self.request)
        self.assertEqual(result.status, "PARTIALLY_SUPPORTED")
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(len(result.supported_portions), 1)
        self.assertTrue(result.unresolved_portions)

    def test_source_filter_applies_to_facts_and_excerpts_inside_profile(self):
        profile = self.bundle.catalog.coverage_profiles[0]
        profile.source_languages = ["en", "de"]
        for route in profile.term_routes:
            route.source_languages = ["en", "de"]
        self.bundle.evidence[-1].effective_source_language = "de"
        self.request["context"].update(purpose="work", work_days=12)
        self.request["source_languages"] = ["en"]
        result = self.service(reseal(self.bundle)).resolve(self.request)
        self.assertEqual(result.status, "PARTIALLY_SUPPORTED")
        self.assertEqual({e.effective_source_language for e in result.evidence}, {"en"})
        self.assertEqual([f.fact_id for f in result.supported_portions], ["fact-parent"])

    def test_unpublished_operation_evidence_cannot_enter_candidate_pool(self):
        # The work excerpt has the exact same canonical concept and source, but
        # its only operation binding is a rule that is false in this request.
        self.request["retrieval_terms"] = [dict(text="work", language="en")]
        result = self.service().resolve(self.request)
        self.assertEqual(result.trace.candidate_count, 1)
        self.assertEqual([e.evidence_id for e in result.evidence], ["evidence-parent"])

    def test_evidence_date_and_jurisdiction_are_hard_constraints(self):
        for change in ["date", "jurisdiction"]:
            with self.subTest(change=change):
                bundle, _ = fixture()
                for evidence in bundle.evidence:
                    if change == "date":
                        evidence.temporal_coverage.valid_through = "2026-08-01"
                    else:
                        evidence.jurisdiction.canton_code = "CH-BE"
                result = self.service(reseal(bundle)).resolve(self.request)
                self.assertEqual(result.status, "INSUFFICIENT_VERIFIED_EVIDENCE")
                self.assertFalse(result.evidence)

    def test_unbounded_validity_serves_any_applicability_date(self):
        bundle, _ = fixture()
        for evidence in bundle.evidence:
            evidence.temporal_coverage.valid_from = None
            evidence.temporal_coverage.valid_through = None
        for profile in bundle.catalog.coverage_profiles:
            profile.temporal_coverage.valid_from = None
            profile.temporal_coverage.valid_through = None
        service = self.service(reseal(bundle))
        for as_of in ("1990-01-01", "2026-09-24", "2099-12-31"):
            with self.subTest(as_of=as_of):
                result = service.resolve({**self.request, "as_of": as_of})
                self.assertEqual(result.status, "SUPPORTED")
                self.assertEqual([f.fact_id for f in result.supported_portions], ["fact-parent"])
        # A source-stated commencement still excludes earlier applicability dates.
        for profile in bundle.catalog.coverage_profiles:
            profile.temporal_coverage.valid_from = "2021-01-01"
        result = self.service(reseal(bundle)).resolve({**self.request, "as_of": "2020-12-31"})
        self.assertEqual(result.status, "OUT_OF_COVERAGE")

    def test_federal_profile_serves_any_canton_and_reports_its_level(self):
        bundle, _ = fixture()
        for evidence in bundle.evidence:
            evidence.jurisdiction.canton_code = None
        for profile in bundle.catalog.coverage_profiles:
            profile.jurisdiction.canton_code = None
        service = self.service(reseal(bundle))
        result = service.resolve({**self.request, "jurisdiction": {"country_code": "CH", "canton_code": "CH-BE"}})
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual(result.requested_scope.jurisdiction.canton_code, "CH-BE")
        self.assertIsNone(result.executed_scope.jurisdiction.canton_code)
        self.assertEqual([f.fact_id for f in result.supported_portions], ["fact-parent"])
        self.assertTrue(any("CH-BE specifics are not covered" in note for note in result.trust.limitations))
        self.assertLessEqual(len(result.trust.limitations), 30)
        gap = service.resolve({**self.request, "jurisdiction": {"country_code": "DE"}})
        self.assertEqual(gap.status, "OUT_OF_COVERAGE")
        self.assertEqual(gap.unresolved_portions[0].reason_code, "jurisdiction_not_covered")
        self.assertIn("Published: CH.", gap.unresolved_portions[0].limitation)

    def test_federal_evidence_requires_published_rule(self):
        for evidence in self.bundle.evidence:
            evidence.jurisdiction.canton_code = None
        service = self.service(reseal(self.bundle))
        self.assertFalse(service.resolve(self.request).evidence)
        self.request["context"].update(purpose="work", work_days=12)
        result = service.resolve(self.request)
        self.assertEqual(result.status, "PARTIALLY_SUPPORTED")
        self.assertEqual([f.fact_id for f in result.supported_portions], ["fact-work"])
        self.assertIsNone(result.evidence[0].jurisdiction.canton_code)

    def test_stale_is_based_on_read_clock_not_applicability_date(self):
        service = self.service(clock=lambda: datetime(2026, 11, 1, tzinfo=timezone.utc))
        result = service.resolve(self.request)
        self.assertEqual(result.status, "STALE")
        self.assertEqual(result.freshness.status, "STALE")
        self.assertTrue(result.supported_portions)

    def test_conflicts_survive_evidence_cap(self):
        self.bundle.graph.conflicts = [FactConflict(fact_ids=["fact-parent", "fact-work"])]
        self.request["context"].update(purpose="work", work_days=12)
        self.request["max_evidence"] = 1
        result = self.service(reseal(self.bundle)).resolve(self.request)
        self.assertEqual(result.status, "CONFLICTING_EVIDENCE")
        self.assertEqual(result.unresolved_portions[0].reason_code, "published_conflict")

    def test_excerpts_are_not_supported_facts(self):
        self.bundle.graph.plans[0].portions[0].fact_ids = []
        result = self.service(reseal(self.bundle)).resolve(self.request)
        self.assertEqual(result.status, "INSUFFICIENT_VERIFIED_EVIDENCE")
        self.assertEqual(result.trust.fact_support, "EXCERPTS_ONLY")

    def test_root_child_discovery_inline_schemas_and_sorted_pages(self):
        service = self.service()
        root = service.get_coverage({})
        self.assertEqual([e.entry_id for e in root.entries], ["fixture-space"])
        self.assertFalse(root.coverage_profiles)
        root = service.get_coverage(dict(release_id=root.release_id, knowledge_space_id="fixture-space"))
        self.assertEqual([e.entry_id for e in root.entries], ["fixture-domain"])
        request = dict(release_id=root.release_id, parent_id="fixture-topic", limit=1)
        first = service.get_coverage(request)
        self.assertEqual(first.parent.entry_id, "fixture-topic")
        self.assertEqual(first.context_schemas, self.bundle.catalog.context_schemas)
        self.assertEqual(first.coverage_profiles, self.bundle.catalog.coverage_profiles)
        second = service.get_coverage({**request, "cursor": first.next_cursor})
        self.assertEqual([e.entry_id for e in first.entries + second.entries], ["fixture-parent", "fixture-sibling"])
        self.assertIsNone(second.next_cursor)

    def test_root_coverage_summary_without_scope_statement_serves_derived_limits(self):
        service = self.service()
        root = service.get_coverage({})
        summary = root.coverage_summary
        self.assertEqual((summary.scope, summary.out_of_scope), ({}, {}))
        self.assertIn("do not call further tools", summary.out_of_scope_response)
        self.assertEqual([t.model_dump() for t in summary.topics], [dict(
            knowledge_space_id="fixture-space", domain_id="fixture-domain", topic_id="fixture-topic",
            labels={"en": "Synthetic topic"}, intents=["requirements"], concept_count=3)])
        self.assertEqual([r.model_dump() for r in summary.jurisdictions], [dict(
            jurisdictions=[dict(country_code="CH", canton_code="CH-ZH", municipality_id=None)],
            intent="requirements", concept_count=3)])
        self.assertIn("country-level profile", summary.jurisdiction_rule)
        self.assertEqual(summary.languages.model_dump(), dict(evidence=["en"], labels=["en"], retrieval_terms=["en", "de"]))
        self.assertEqual((summary.snapshot_from, summary.snapshot_through, summary.concept_count),
                         ("2026-09-06", "2026-09-06", 3))
        self.assertEqual(summary.derived_limits, [
            "Topics other than: Synthetic topic (fixture-topic).",
            "Intents other than: requirements.",
            "Countries other than: CH.",
            "Canton- or municipality-specific information for places not listed under jurisdictions.",
            "Retrieval terms are evaluated only for: de terms against en sources, en terms against en sources. "
            "Other term languages are refused and other term/source combinations are out of coverage.",
            "Dates outside source-stated validity: fixture-parent before 2026-01-01 or after 2026-12-31.",
        ])
        # The summary travels with the root page only; every child page stays as before.
        for payload in [dict(release_id=root.release_id, knowledge_space_id="fixture-space"),
                        dict(release_id=root.release_id, parent_id="fixture-topic")]:
            self.assertIsNone(service.get_coverage(payload).coverage_summary)
        # Root discovery stays small enough for a default client output cap.
        self.assertLess(len(root.model_dump_json()), 8000)

    def test_sealed_scope_statement_is_served_verbatim_and_replaces_derived_complement(self):
        self.bundle.catalog.scope = ScopeStatement(
            statements={"en": dict(in_scope="Synthetic residence rules for group A.",
                                   out_of_scope=["Taxes.", "Driving licences."])},
            provenance=[ArtifactRef(artifact_id="fixture-review", version="1", sha256="a" * 64)])
        service = self.service(reseal(self.bundle))
        summary = service.get_coverage({}).coverage_summary
        self.assertEqual(summary.scope, {"en": "Synthetic residence rules for group A."})
        self.assertEqual(summary.out_of_scope, {"en": ["Taxes.", "Driving licences."]})
        self.assertEqual(summary.derived_limits, [
            "Retrieval terms are evaluated only for: de terms against en sources, en terms against en sources. "
            "Other term languages are refused and other term/source combinations are out of coverage.",
            "Dates outside source-stated validity: fixture-parent before 2026-01-01 or after 2026-12-31."])

    def test_jurisdiction_rows_group_places_by_level_intent_and_count(self):
        profile = self.bundle.catalog.coverage_profiles[0]
        extra = []
        for canton in ["CH-BE", "CH-AG"]:
            extra.append(profile.model_copy(update={
                "coverage_profile_id": "contacts-" + canton.lower(), "intent": "contacts",
                "concept_ids": ["fixture-sibling"], "jurisdiction": dict(country_code="CH", canton_code=canton)}))
        extra.append(profile.model_copy(update={"coverage_profile_id": "federal", "concept_ids": ["fixture-parent"],
                                                "jurisdiction": dict(country_code="CH")}))
        self.bundle.catalog.coverage_profiles = [profile, *extra]
        # Every profile needs a resolution plan; one fact-free portion per profile satisfies the validator.
        portion = self.bundle.graph.plans[0].portions[0]
        self.bundle.graph.plans += [self.bundle.graph.plans[0].model_copy(update={
            "coverage_profile_id": p.coverage_profile_id,
            "portions": [portion.model_copy(update={"portion_id": "portion-" + p.coverage_profile_id,
                                                    "concept_ids": list(p.concept_ids), "fact_ids": [],
                                                    "evidence_ids": [], "rule_refs": []})]}) for p in extra]
        summary = self.service(reseal(self.bundle)).get_coverage({}).coverage_summary
        self.assertEqual([(len(r.jurisdictions), r.intent, r.concept_count,
                           [j.canton_code for j in r.jurisdictions]) for r in summary.jurisdictions],
                         [(1, "requirements", 1, [None]), (2, "contacts", 1, ["CH-AG", "CH-BE"]),
                          (1, "requirements", 3, ["CH-ZH"])])

    def test_catalog_default_limit_applies_when_omitted(self):
        self.bundle.catalog.discovery_default_limit = 1
        self.bundle.catalog.discovery_max_limit = 2
        service = self.service(reseal(self.bundle))
        request = dict(release_id=self.request["release_id"], parent_id="fixture-topic")
        self.assertEqual(len(service.get_coverage(request).entries), 1)
        self.assertEqual(service.get_coverage({**request, "limit": 3}).code, "INVALID_ARGUMENT")

    def test_invalid_discovery_and_cursors(self):
        service = self.service()
        request = dict(release_id=self.request["release_id"], parent_id="fixture-topic", limit=1)
        cursor = service.get_coverage(request).next_cursor
        for payload in [dict(parent_id="fixture-topic"), dict(cursor=cursor),
                        {**request, "parent_id": "unknown"}, {**request, "cursor": "%%%"},
                        {**request, "cursor": cursor[:-3] + "AAA"},
                        {**request, "cursor": cursor, "limit": 2},
                        {**request, "cursor": cursor, "parent_id": "fixture-parent"},
                        {**request, "knowledge_space_id": "fixture-domain"},
                        {**request, "extra": True}]:
            with self.subTest(payload=payload):
                self.assertEqual(service.get_coverage(payload).code, "INVALID_ARGUMENT")

    def test_active_release_change_and_historical_cursor(self):
        old_service = self.service()
        request = dict(release_id=self.request["release_id"], parent_id="fixture-topic", limit=1)
        cursor = old_service.get_coverage(request).next_cursor
        newer, _ = fixture("fixture-release-b")
        service = KnowledgeService(ReleaseStore([self.bundle, newer], active_release_id="fixture-release-b"),
                                   clock=lambda: NOW, cursor_key=b"k" * 32)
        self.assertEqual(service.get_coverage({}).release_id, "fixture-release-b")
        self.assertEqual(service.get_coverage({**request, "cursor": cursor}).release_id, "fixture-release-a")
        self.assertEqual(service.get_coverage({**request, "cursor": cursor, "release_id": "fixture-release-b"}).code,
                         "INVALID_ARGUMENT")
        self.assertEqual(service.resolve(self.request).release_id, "fixture-release-a")

    def test_unavailable_release_is_never_substituted(self):
        service = self.service()
        for method, payload in [(service.resolve, self.request), (service.get_coverage, {}),
                                (service.get_evidence, dict(evidence_ids=["evidence-parent"]))]:
            result = method({**payload, "release_id": "unavailable"})
            self.assertEqual(result.code, "RELEASE_UNAVAILABLE")
            self.assertEqual(result.active_release_id, self.request["release_id"])

    def test_unknown_duplicate_and_over_limit_evidence(self):
        service = self.service()
        for ids in [["unknown"], ["evidence-parent", "unknown"], ["evidence-parent"] * 2, [], [f"e-{i}" for i in range(6)]]:
            result = service.get_evidence(dict(release_id=self.request["release_id"], evidence_ids=ids))
            self.assertEqual(result.code, "INVALID_ARGUMENT")

    def test_store_and_outputs_are_defensive_snapshots(self):
        service = self.service()
        self.bundle.facts[0].statement = "Tampered outside store."
        response = service.resolve(self.request)
        response.supported_portions[0].statement = "Tampered output."
        loaded = service.store.get(self.request["release_id"])
        loaded.facts[0].statement = "Tampered read."
        self.assertEqual(service.resolve(self.request).supported_portions[0].statement,
                         "Synthetic parent requirement for fixture group A.")

    def test_tampered_release_artifacts_are_rejected(self):
        for field in ["evidence", "facts", "graph", "catalog", "release"]:
            with self.subTest(field=field):
                bundle, _ = fixture()
                artifact = getattr(bundle, field)
                if isinstance(artifact, list):
                    artifact = artifact[0]
                artifact.identity = artifact.identity.model_copy(update={"sha256": "b" * 64})
                with self.assertRaises(ValueError):
                    self.service(bundle)

    def test_valid_hash_cannot_hide_wrong_span_or_source_chain(self):
        for change in ["span", "source", "release", "section", "future_access"]:
            with self.subTest(change=change):
                bundle, _ = fixture()
                if change == "span":
                    bundle.evidence[0].original_excerpt = "X" + bundle.evidence[0].original_excerpt[1:]
                elif change == "source":
                    bundle.evidence[0].citation.source_id = "wrong-source"
                elif change == "release":
                    bundle.evidence[0].release_id = "wrong-release"
                elif change == "section":
                    bundle.evidence[0].section_id = "wrong-section"
                else:
                    bundle.evidence[0].citation.accessed_at = "2099-01-01T00:00:00Z"
                with self.assertRaises(ValueError):
                    self.service(reseal(bundle))

    def test_invalid_graph_and_rules_fail_loading(self):
        for change in ["profile", "fact", "rule", "condition", "candidate", "external"]:
            with self.subTest(change=change):
                bundle, _ = fixture()
                if change == "profile":
                    bundle.graph.plans[0].coverage_profile_id = "missing-profile"
                elif change == "fact":
                    bundle.graph.plans[0].portions[0].fact_ids = ["missing-fact"]
                elif change == "rule":
                    bundle.graph.plans[0].portions[0].fact_ids = ["fact-work"]
                elif change == "condition":
                    bundle.rules[0].when[0].field = "missing-field"
                elif change == "candidate":
                    bundle.catalog.entries[0].lifecycle = "CANDIDATE"
                else:
                    bundle.external_refs = []
                with self.assertRaises(ValueError):
                    self.service(reseal(bundle))

    def test_duplicate_release_and_unavailable_active_fail_loading(self):
        with self.assertRaises(ValueError):
            ReleaseStore([self.bundle, self.bundle], active_release_id=self.request["release_id"])
        with self.assertRaises(ValueError):
            ReleaseStore([self.bundle], active_release_id="missing")


if __name__ == "__main__":
    unittest.main()
