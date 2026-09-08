"""BUILD-05 integration gates over synthetic data and deterministic providers."""

from datetime import datetime, timezone
import unittest

from swisstip.core.contracts import FactConflict
from swisstip.runtime import KnowledgeService, ReleaseStore
from swisstip.runtime.hybrid_fixture import (
    LANGUAGES, TERMS, SyntheticSemanticProvider, hybrid_fixture, seal_fixture,
)
from swisstip.runtime.retrieval import EmbeddingResponse, RankingResponse


NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


class SpyProvider(SyntheticSemanticProvider):
    def __init__(self, *, embedding_error=None, ranking_error=None, scores=None):
        self.inputs = []
        self.queries = []
        self.embedding_error, self.ranking_error, self.scores = embedding_error, ranking_error, scores

    def embed(self, texts, *, model):
        self.queries.append(texts)
        if self.embedding_error:
            raise self.embedding_error
        return super().embed(texts, model=model)

    def rank(self, query, candidates, *, model):
        self.inputs.append(candidates)
        if self.ranking_error:
            raise self.ranking_error
        response = super().rank(query, candidates, model=model)
        if self.scores:
            response.scores.update(self.scores)
        return response


class RetrievalTests(unittest.TestCase):
    def test_external_vector_store_only_receives_scoped_evidence(self):
        bundle, request = hybrid_fixture(fallback=False)
        provider = SpyProvider()
        eligible = []

        class VectorStore:
            def score_vectors(self, loaded, identifiers, vectors):
                eligible.extend(identifiers)
                return {identifier: 1.0 for identifier in identifiers}

        service = KnowledgeService(ReleaseStore([bundle], active_release_id=bundle.release.release_id),
                                   embedding_provider=provider, ranking_provider=provider,
                                   vector_store=VectorStore(), clock=lambda: NOW)
        result = service.resolve({**request, 'source_languages': ['de']})
        self.assertEqual(result.status, 'SUPPORTED')
        self.assertTrue(eligible)
        by_id = {e.evidence_id: e for e in bundle.evidence}
        self.assertTrue(all(by_id[eid].effective_source_language == 'de' for eid in eligible))

    def test_external_vector_store_cannot_add_ids_or_trigger_silent_memory_fallback(self):
        bundle, request = hybrid_fixture(fallback=False)
        provider = SpyProvider()

        class VectorStore:
            def score_vectors(self, loaded, identifiers, vectors):
                return {**{identifier: 1.0 for identifier in identifiers}, 'invented': 1.0}

        service = KnowledgeService(ReleaseStore([bundle], active_release_id=bundle.release.release_id),
                                   embedding_provider=provider, ranking_provider=provider,
                                   vector_store=VectorStore(), clock=lambda: NOW)
        self.assertEqual(service.resolve(request).code, 'OPERATIONAL_ERROR')
        self.assertEqual(provider.inputs, [])

    def setUp(self):
        self.bundle, self.request = hybrid_fixture()
        self.provider = SpyProvider()

    def service(self, bundle=None, provider=None):
        return KnowledgeService(ReleaseStore([bundle or self.bundle], active_release_id=self.request["release_id"]),
                                embedding_provider=provider or self.provider, ranking_provider=provider or self.provider,
                                clock=lambda: NOW)

    def test_multilingual_top20_top5_and_original_citation_matrix(self):
        service = self.service()
        for language, term in TERMS.items():
            for source in LANGUAGES:
                with self.subTest(term=language, source=source):
                    result = service.resolve({**self.request, "retrieval_terms": [dict(text=term, language=language)],
                                              "source_languages": [source]})
                    self.assertEqual(result.status, "SUPPORTED")
                    self.assertEqual(result.trace.channels, ["lexical", "concept", "vector", "semantic_ranking"])
                    expected = "evidence-parent" if source == "en" else "evidence-" + source
                    self.assertIn(expected, result.trace.candidate_ids[:20])
                    self.assertIn(expected, [e.evidence_id for e in result.evidence[:5]])
                    self.assertEqual([f.fact_id for f in result.supported_portions], ["fact-parent"])
                    self.assertTrue(all(e.effective_source_language == source for e in result.evidence))
                    fetched = service.get_evidence(dict(release_id=result.release_id,
                                                        evidence_ids=[e.evidence_id for e in result.evidence]))
                    self.assertEqual(fetched.evidence, result.evidence)
                    self.assertTrue(all("example.invalid" in e.citation.url for e in result.evidence))
                    self.assertTrue(all(c.source_language == source for c in self.provider.inputs[-1]))

    def test_equivalent_translations_use_one_slot_and_preserve_fact_identity(self):
        result = self.service().resolve({**self.request, "max_evidence": 1})
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual(result.evidence[0].effective_source_language, "de")
        self.assertEqual(result.supported_portions[0], self.bundle.facts[0])
        selection = result.trace.selections[0]
        self.assertEqual(selection.reason_code, "german_equivalent_tie")
        self.assertEqual(len(selection.alternate_ids), 4)
        self.assertIn("evidence-parent", selection.alternate_ids)
        self.assertEqual(selection.mapping_ref, self.bundle.equivalences[0].identity)

    def test_better_non_german_wins_before_language(self):
        self.provider.scores = {"evidence-fr": 2.0}
        result = self.service().resolve({**self.request, "max_evidence": 1})
        self.assertEqual(result.evidence[0].effective_source_language, "fr")
        self.assertEqual(result.trace.selections[0].reason_code, "higher_ranked_equivalent")

    def test_no_german_and_explicit_english_filter(self):
        for sources, expected in [(["fr", "it"], "fr"), (["en"], "en")]:
            result = self.service().resolve({**self.request, "source_languages": sources, "max_evidence": 1,
                                              "retrieval_terms": [dict(text=TERMS["de"], language="de")]})
            self.assertEqual(result.status, "SUPPORTED")
            self.assertEqual(result.evidence[0].effective_source_language, expected)
            self.assertEqual(result.trace.effective_source_languages, sorted(sources))

    def test_source_and_scope_filters_before_provider(self):
        for evidence in self.bundle.evidence:
            if evidence.evidence_id == "evidence-noise-00":
                evidence.jurisdiction.canton_code = "CH-BE"
            if evidence.evidence_id == "evidence-noise-01":
                evidence.temporal_coverage.valid_through = "2026-02-01"
        self.bundle = seal_fixture(self.bundle)
        request = {**self.request, "retrieval_terms": [dict(text="sibling work Bern 2030 group-b", language="en")]}
        result = self.service().resolve(request)
        seen = {c.evidence_id for c in self.provider.inputs[-1]}
        self.assertFalse(seen & {"evidence-noise-00", "evidence-noise-01", "evidence-sibling", "evidence-child", "evidence-work"})
        self.assertEqual(result.executed_scope.concept_ids, ["fixture-parent"])
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual(result.supported_portions[0].fact_id, "fact-parent")

    def test_rules_and_context_stay_ahead_of_retrieval(self):
        request = {**self.request, "context": dict(population="group-a", purpose="work")}
        service = self.service()
        self.assertEqual(service.resolve(request).status, "NEEDS_CONTEXT")
        self.assertFalse(self.provider.queries)
        request["context"]["work_days"] = 10
        result = service.resolve(request)
        self.assertEqual({f.fact_id for f in result.supported_portions}, {"fact-parent", "fact-work"})
        self.assertIn("evidence-work", {c.evidence_id for c in self.provider.inputs[-1]})

    def test_inactive_rule_evidence_cannot_enter_excerpt_channel(self):
        self.bundle.graph.plans[0].portions[0].evidence_ids.append("evidence-work")
        result = self.service(seal_fixture(self.bundle)).resolve(self.request)
        self.assertNotIn("evidence-work", result.trace.candidate_ids)
        self.assertNotIn("evidence-work", {c.evidence_id for c in self.provider.inputs[-1]})

    def test_fallback_restarts_only_evaluated_lexical_concept_path(self):
        for stage in ["embedding_error", "ranking_error"]:
            provider = SpyProvider(**{stage: TimeoutError("offline injected outage")})
            service = self.service(provider=provider)
            for language, term in TERMS.items():
                result = service.resolve({**self.request, "retrieval_terms": [dict(text=term, language=language)],
                                          "source_languages": ["en"]})
                self.assertEqual(result.status, "SUPPORTED")
                self.assertEqual(result.trace.channels, ["lexical", "concept"])
                self.assertEqual(result.trace.degradations[0].omitted_channels, ["vector", "semantic_ranking"])
                self.assertEqual(result.trace.degradations[0].evaluated_fallback_ref,
                                 self.bundle.retrieval_configuration.fallbacks[0].evaluation_ref)
                self.assertTrue(all(e.effective_source_language == "en" for e in result.evidence))
                self.assertLessEqual(len(result.trace.candidate_ids), 20)

    def test_missing_provider_or_unevaluated_fallback_is_operational_error(self):
        bundle, request = hybrid_fixture(fallback=False)
        store = ReleaseStore([bundle], active_release_id=request["release_id"])
        self.assertEqual(KnowledgeService(store).resolve(request).code, "OPERATIONAL_ERROR")
        for stage in ["embedding_error", "ranking_error"]:
            provider = SpyProvider(**{stage: RuntimeError("outage")})
            self.assertEqual(self.service(bundle, provider).resolve(request).code, "OPERATIONAL_ERROR")

    def test_invalid_scores_and_foreign_ids_cannot_leak(self):
        for scores in [{"evidence-sibling": 1000.0}, {"invented": 1000.0}, {"evidence-parent": float("nan")},
                       {"evidence-parent": float("inf")}, {"evidence-parent": True}]:
            provider = SpyProvider(scores=scores)
            result = self.service(provider=provider).resolve(self.request)
            self.assertEqual(result.trace.channels, ["lexical", "concept"])
            self.assertFalse({e.evidence_id for e in result.evidence} & {"evidence-sibling", "invented"})

    def test_provider_and_observed_model_identities_are_checked(self):
        class WrongEmbedding(SpyProvider):
            def embed(self, texts, *, model):
                return EmbeddingResponse("wrong-model", tuple((1.0, 0.0) for _ in texts))
        class WrongRanking(SpyProvider):
            def rank(self, query, candidates, *, model):
                return RankingResponse("wrong-model", {c.evidence_id: 1.0 for c in candidates})
        wrong_adapter = SpyProvider()
        wrong_adapter.provider_id = "unapproved/v1"
        for provider in [WrongEmbedding(), WrongRanking(), wrong_adapter]:
            result = self.service(provider=provider).resolve(self.request)
            self.assertTrue(result.trace.degradations)
            self.assertEqual(result.trace.channels, ["lexical", "concept"])

    def test_invalid_embeddings_fail_closed(self):
        for vector in [(), (1.0,), (0.0, 0.0), (float("nan"), 1.0), (True, 0.0)]:
            class InvalidEmbedding(SpyProvider):
                def embed(self, texts, *, model):
                    return EmbeddingResponse(model, tuple(vector for _ in texts))
            result = self.service(provider=InvalidEmbedding()).resolve(self.request)
            self.assertTrue(result.trace.degradations)

    def test_mixed_terms_keep_independent_routes_and_aliases(self):
        result = self.service().resolve({**self.request, "retrieval_terms": [
            dict(text="Aufenthaltserlaubnis", language="de"), dict(text=TERMS["gsw"], language="gsw"),
            dict(text=TERMS["fr"], language="fr")]})
        self.assertEqual([r.projection_language for r in result.trace.term_routes], ["de", "de", "fr"])
        self.assertEqual(result.trace.effective_source_languages, sorted(LANGUAGES))
        self.assertIn(TERMS["de"], self.provider.queries[-1][0])

    def test_terms_are_optional_and_descendant_scope_is_preserved(self):
        result = self.service().resolve({**self.request, "scope_mode": "descendants"})
        self.assertEqual(result.status, "SUPPORTED")
        self.assertEqual({f.fact_id for f in result.supported_portions}, {"fact-parent", "fact-child"})
        self.assertNotIn("evidence-sibling", result.trace.candidate_ids)

    def test_vector_channel_recovers_zero_lexical_match_and_ranking_selects_it(self):
        # The rare target sorts below 20 same-concept distractors. It has no
        # lexical/projection match and is not required by a published fact.
        target = "evidence-noise-29"
        refs = {e.identity: e.evidence_id for e in self.bundle.evidence}
        for vector in self.bundle.retrieval_index.vectors:
            vector.values = [1.0, 0.0] if refs[vector.evidence_ref] == target else [0.0, 1.0]
        self.bundle.graph.plans[0].portions[0].fact_ids = []
        self.bundle = seal_fixture(self.bundle)
        class RareProvider(SpyProvider):
            def embed(self, texts, *, model):
                return EmbeddingResponse(model, tuple((1.0, 0.0) for _ in texts))
            def rank(self, query, candidates, *, model):
                return RankingResponse(model, {c.evidence_id: 5.0 if c.evidence_id == target else 0.0 for c in candidates})
        request = {**self.request, "source_languages": ["en"], "max_evidence": 1,
                   "retrieval_terms": [dict(text="rare-vector-only-term", language="en")]}
        result = self.service(provider=RareProvider()).resolve(request)
        self.assertIn(target, result.trace.candidate_ids[:20])
        self.assertEqual(result.evidence[0].evidence_id, target)
        self.assertEqual(result.status, "INSUFFICIENT_VERIFIED_EVIDENCE")
        baseline = self.service(provider=SpyProvider(embedding_error=TimeoutError())).resolve(request)
        self.assertNotIn(target, baseline.trace.candidate_ids[:20])

    def test_evaluation_enforces_declared_relevance_and_nonempty_gates(self):
        from swisstip.runtime.evaluation import RetrievalGoldCase, evaluate
        # Disable the optional-excerpt threshold to exercise a bad release
        # profile. The evaluator must reject its irrelevant spare evidence.
        self.bundle.retrieval_configuration.minimum_semantic_score = None
        self.bundle = seal_fixture(self.bundle)
        case = RetrievalGoldCase(
            case_id="test-gate", release_ref=self.bundle.release.identity,
            request={**self.request, "source_languages": ["en"]},
            required_evidence_groups=[["evidence-parent"]], required_fact_ids=["fact-parent"],
            eligible_evidence_ids=[e.evidence_id for e in self.bundle.evidence],
            relevant_evidence_ids=["evidence-parent"], minimum_precision_at_5=1.0)
        service = self.service()
        # Four spare excerpts are irrelevant to this narrow gold case.
        self.assertFalse(evaluate(service, [case])["passed"])
        case.request.max_evidence = 1
        self.assertTrue(evaluate(service, [case])["passed"])
        case.required_fact_ids = ["fact-child"]
        self.assertFalse(evaluate(service, [case])["passed"])
        with self.assertRaises(ValueError):
            evaluate(service, [])

    def test_direct_support_cutoff_rejects_lower_grades_without_creating_facts(self):
        target = "evidence-noise-00"  # An optional excerpt, not required by a published fact.
        self.bundle.graph.plans[0].portions[0].fact_ids = []
        self.bundle.retrieval_configuration.minimum_semantic_score = 3
        self.bundle.retrieval_configuration.fallbacks = []
        self.bundle = seal_fixture(self.bundle)
        for grade in (0, 1, 2, 3):
            class GradedProvider(SpyProvider):
                def rank(self, query, candidates, *, model):
                    return RankingResponse(model, {c.evidence_id: grade if c.evidence_id == target else 0
                                                   for c in candidates})
            result = self.service(provider=GradedProvider()).resolve(
                {**self.request, "source_languages": ["en"], "max_evidence": 1})
            self.assertEqual(result.status, "INSUFFICIENT_VERIFIED_EVIDENCE")
            self.assertFalse(result.supported_portions)
            self.assertEqual([e.evidence_id for e in result.evidence], [target] if grade == 3 else [])
            self.assertEqual(result.trust.fact_support, "EXCERPTS_ONLY" if grade == 3 else "NONE")

    def test_same_concept_partial_translation_is_not_equivalence(self):
        group = self.bundle.equivalences[0]
        french = next(e for e in self.bundle.evidence if e.evidence_id == "evidence-fr")
        group.evidence_refs.remove(french.identity)
        self.bundle = seal_fixture(self.bundle)
        result = self.service().resolve({**self.request, "source_languages": ["fr"]})
        self.assertEqual(result.status, "INSUFFICIENT_VERIFIED_EVIDENCE")
        self.assertFalse(result.supported_portions)
        self.assertFalse(result.trace.selections)

    def test_newer_non_german_revision_is_not_collapsed_or_overridden(self):
        group = self.bundle.equivalences[0]
        german = next(e for e in self.bundle.evidence if e.evidence_id == "evidence-de")
        group.evidence_refs.remove(german.identity)
        german.temporal_coverage.valid_through = "2026-08-31"
        result = self.service(seal_fixture(self.bundle)).resolve({**self.request, "max_evidence": 1})
        self.assertEqual(result.status, "SUPPORTED")
        self.assertNotEqual(result.evidence[0].effective_source_language, "de")
        self.assertNotIn("evidence-de", result.trace.candidate_ids)

    def test_stale_german_does_not_displace_fresh_equivalent(self):
        german = next(e for e in self.bundle.evidence if e.evidence_id == "evidence-de")
        german.citation.accessed_at = "2026-07-01T00:00:00Z"
        self.provider.scores = {"evidence-de": 10.0}
        result = self.service(seal_fixture(self.bundle)).resolve({**self.request, "max_evidence": 1})
        self.assertEqual(result.status, "SUPPORTED")
        self.assertNotEqual(result.evidence[0].effective_source_language, "de")
        self.assertEqual(result.trace.selections[0].reason_code, "fresher_equivalent")

    def test_conflicting_facts_survive_ranking_and_evidence_cap(self):
        fact = self.bundle.facts[0].model_copy(deep=True)
        from swisstip.runtime.fixture import ref
        fact.fact_id = "fact-conflict"
        fact.identity = ref("fact-conflict")
        fact.statement = "A different synthetic requirement."
        fact.evidence_ids = ["evidence-noise-00"]
        self.bundle.facts.append(fact)
        self.bundle.release.fact_refs.append(fact.identity)
        self.bundle.graph.plans[0].portions[0].fact_ids.append(fact.fact_id)
        self.bundle.graph.conflicts.append(FactConflict(fact_ids=["fact-parent", fact.fact_id]))
        result = self.service(seal_fixture(self.bundle)).resolve({**self.request, "max_evidence": 1})
        self.assertEqual(result.status, "CONFLICTING_EVIDENCE")

    def test_tampered_and_incomplete_retrieval_assets_fail_loading(self):
        mutations = [
            lambda b: setattr(b.projections[0], "text", "tampered"),
            lambda b: setattr(b.retrieval_index.vectors[0], "values", [1.0]),
            lambda b: b.projections.pop(),
            lambda b: b.retrieval_index.vectors.pop(),
            lambda b: b.terminology.pop(),
            lambda b: b.retrieval_configuration.evaluation_refs.clear(),
            lambda b: b.equivalences[0].fact_ids.clear(),
            lambda b: b.equivalences[0].fact_refs.clear(),
            lambda b: setattr(b.evidence[4].temporal_coverage, "valid_through", "2026-08-31"),
        ]
        for mutate in mutations:
            bundle = self.bundle.model_copy(deep=True)
            mutate(bundle)
            with self.subTest(mutation=mutate):
                with self.assertRaises(ValueError):
                    self.service(bundle)
                if mutate != mutations[0]:
                    with self.assertRaises(ValueError):
                        self.service(seal_fixture(bundle))


if __name__ == "__main__":
    unittest.main()
