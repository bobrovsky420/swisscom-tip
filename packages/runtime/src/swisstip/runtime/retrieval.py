"""Scoped hybrid retrieval. Providers only see already eligible evidence.

Adapters own bounded I/O/timeouts. Their outputs are untrusted relevance signals:
identity, dimensions, finite scores and exact candidate membership are checked.
No adapter can create facts, evidence IDs, applicability or source filters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re
import unicodedata
from typing import Protocol

from swisstip.core.contracts import EvidenceSelection, ProviderDegradation


def tokens(text):
    return set(re.findall(r"\w+", unicodedata.normalize("NFKC", text).casefold()))


@dataclass(frozen=True)
class RetrievalQuery:
    # (effective term language, original text, projection language)
    terms: tuple[tuple[str, str, str], ...]
    concept_ids: tuple[str, ...]


@dataclass(frozen=True)
class RankingCandidate:
    evidence_id: str
    original_excerpt: str
    source_language: str
    projections: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class EmbeddingResponse:
    model: str
    vectors: tuple[tuple[float, ...], ...]


@dataclass(frozen=True)
class RankingResponse:
    model: str
    scores: dict[str, float]


class EmbeddingProvider(Protocol):
    provider_id: str
    def embed(self, texts: tuple[str, ...], *, model: str) -> EmbeddingResponse: ...


class SemanticRankingProvider(Protocol):
    provider_id: str
    def rank(self, query: RetrievalQuery, candidates: tuple[RankingCandidate, ...],
             *, model: str) -> RankingResponse: ...


class RetrievalFailure(Exception):
    """A permitted provider execution path could not complete."""


@dataclass
class RetrievalResult:
    ordered_ids: list[str]
    scores: dict[str, float]
    representative: dict[str, str]
    selections: list[EvidenceSelection]
    channels: list[str]
    degradations: list[ProviderDegradation]
    projection_refs: list
    excerpt_ids: set[str]


def _finite(value):
    return type(value) in {int, float} and math.isfinite(value)


def _unit(values, dimensions):
    if len(values) != dimensions or not all(_finite(v) for v in values):
        raise RetrievalFailure("invalid_embedding_response")
    norm = math.hypot(*values)
    if not norm or not math.isfinite(norm):
        raise RetrievalFailure("invalid_embedding_response")
    return tuple(v / norm for v in values)


class HybridRetriever:
    def __init__(self, embedding_provider: EmbeddingProvider | None = None,
                 ranking_provider: SemanticRankingProvider | None = None):
        self.embedding_provider = embedding_provider
        self.ranking_provider = ranking_provider

    def retrieve(self, bundle, profile, routes, selected, candidates, required_evidence=(), *, checked_at=None) -> RetrievalResult:
        config = bundle.retrieval_configuration
        query = RetrievalQuery(tuple((r.effective_term_language, r.original_text, r.projection_language)
                                     for r in routes), tuple(sorted(selected)))
        original = set().union(*(tokens(t[1]) for t in query.terms)) if query.terms else set()
        if config is None:
            scores = {i: float(len(original & tokens(e.original_excerpt))) for i, e in candidates.items()}
            return RetrievalResult(sorted(scores, key=lambda i: (-scores[i], i)), scores,
                                   {i: i for i in candidates}, [],
                                   ["concept", "lexical"] if original else ["concept"], [], [], set(candidates))

        projections = {}
        used_refs = []
        languages = {r.projection_language for r in routes}
        if not routes:
            languages = set(profile.projection_languages_complete)
        eligible_refs = {e.identity: i for i, e in candidates.items()}
        for projection in bundle.projections:
            if projection.evidence_ref in eligible_refs and projection.language in languages:
                identifier = eligible_refs[projection.evidence_ref]
                projections.setdefault(identifier, []).append((projection.language, projection.text))
                used_refs.append(projection.identity)

        expanded = {language: set() for language in languages}
        matched_concepts = set()
        published_routes = {r.term_language: r for r in profile.term_routes}
        embedding_texts = []
        for language, text, projection_language in query.terms:
            words = tokens(text)
            expanded[projection_language].update(words)
            aliases = []
            allowed_terms = set(published_routes[language].terminology_refs)
            for term in bundle.terminology:
                if term.identity in allowed_terms and term.concept_id in selected and any(tokens(t) <= words for t in term.terms):
                    matched_concepts.add(term.concept_id)
                    aliases.extend(term.terms)
            expanded[projection_language].update(tokens(" ".join(aliases)))
            # Bounded original query plus reviewed aliases; no translation call.
            embedding_texts.append((text + " " + " ".join(aliases))[:4000].strip())
        if not embedding_texts:
            entries = {e.entry_id: e for e in bundle.catalog.entries}
            embedding_texts = [entries[c].labels[sorted(entries[c].labels)[0]].label for c in sorted(selected)]

        lexical, concept = {}, {}
        lexical_words = original | set().union(*expanded.values()) if expanded else original
        for identifier, item in candidates.items():
            lexical[identifier] = float(len(lexical_words & tokens(item.original_excerpt)) + sum(
                len(expanded.get(language, set()) & tokens(text)) for language, text in projections.get(identifier, [])))
            concept[identifier] = float(len(set(item.canonical_concept_ids) & selected)
                                        + len(set(item.canonical_concept_ids) & matched_concepts)
                                        + (identifier in required_evidence))

        all_evidence = {e.identity: e.evidence_id for e in bundle.evidence}
        group_for = {}
        groups = {}
        for group in bundle.equivalences:
            members = [all_evidence[r] for r in group.evidence_refs]
            admitted = [i for i in members if i in candidates]
            if admitted:
                groups[group.identity.artifact_id] = (group, members, admitted)
                group_for.update((i, group.identity.artifact_id) for i in admitted)

        def bucket(identifier):
            # Tagged keys prevent a group ID colliding with an evidence ID.
            return ("group", group_for[identifier]) if identifier in group_for else ("evidence", identifier)

        def pool(channels):
            fused = {}
            for scores in channels:
                best = {}
                for identifier in sorted(scores, key=lambda i: (-scores[i], i)):
                    best.setdefault(bucket(identifier), identifier)
                for rank, key in enumerate(list(best)[:config.channel_limit], 1):
                    fused[key] = fused.get(key, 0.0) + 1 / (config.rrf_constant + rank)
            keys = sorted(fused, key=lambda k: (-fused[k], k))[:config.candidate_limit]
            admitted = [i for i in candidates if bucket(i) in keys]
            return admitted, {i: fused[bucket(i)] for i in admitted}

        channels = ["lexical", "concept", "vector", "semantic_ranking"]
        degradations = []
        stage = "vector"
        try:
            if not self.embedding_provider:
                raise RetrievalFailure("provider_unavailable")
            providers, index = bundle.retrieval_providers, bundle.retrieval_index
            if self.embedding_provider.provider_id != providers.embedding_provider:
                raise RetrievalFailure("provider_identity_mismatch")
            response = self.embedding_provider.embed(tuple(embedding_texts), model=providers.embedding_model)
            if response.model != providers.embedding_model or len(response.vectors) != len(embedding_texts):
                raise RetrievalFailure("embedding_identity_or_count_mismatch")
            vectors = [_unit(v, index.dimensions) for v in response.vectors]
            vector_scores = {}
            for vector in index.vectors:
                if vector.evidence_ref in eligible_refs:
                    unit = _unit(vector.values, index.dimensions)
                    vector_scores[eligible_refs[vector.evidence_ref]] = max(
                        (sum(a * b for a, b in zip(unit, q)) for q in vectors), default=0.0)
            admitted, scores = pool([{i: s for i, s in lexical.items() if s > 0}, concept,
                                     {i: s for i, s in vector_scores.items() if s > 0}])
            stage = "semantic_ranking"
            if not self.ranking_provider or self.ranking_provider.provider_id != providers.ranking_provider:
                raise RetrievalFailure("ranking_provider_unavailable_or_mismatched")
            inputs = tuple(RankingCandidate(i, candidates[i].original_excerpt,
                                            candidates[i].effective_source_language,
                                            tuple(projections.get(i, []))) for i in sorted(admitted))
            response = self.ranking_provider.rank(query, inputs, model=providers.ranking_model)
            if response.model != providers.ranking_model or set(response.scores) != set(admitted) or not all(
                    _finite(v) for v in response.scores.values()):
                raise RetrievalFailure("invalid_ranking_response")
            scores = dict(response.scores)
            qualified_excerpts = {i for i, score in scores.items()
                                  if config.minimum_semantic_score is None or score >= config.minimum_semantic_score}
        except Exception as exc:
            # Adapters may throw transport-specific exceptions. No failed path
            # becomes a factual coverage result; restart the evaluated baseline.
            fallback = next((f for f in config.fallbacks if f.coverage_profile_id == profile.coverage_profile_id), None)
            if fallback is None:
                raise RetrievalFailure("retrieval_provider_failed") from exc
            admitted, scores = pool([{i: s for i, s in lexical.items() if s > 0}, concept])
            channels = ["lexical", "concept"]
            qualified_excerpts = {i for i in admitted if fallback.minimum_lexical_score is None
                                  or lexical[i] >= fallback.minimum_lexical_score}
            degradations = [ProviderDegradation(reason_code=stage + "_failed",
                                                omitted_channels=["vector", "semantic_ranking"],
                                                evaluated_fallback_ref=fallback.evaluation_ref)]

        representatives = {i: i for i in admitted}
        selections = []
        now = checked_at if checked_at is not None else datetime.now(timezone.utc)

        def stale(identifier):
            accessed = datetime.fromisoformat(candidates[identifier].citation.accessed_at.replace("Z", "+00:00"))
            return now > accessed + timedelta(days=profile.freshness_policy.max_age_days)

        for group, members, eligible_members in groups.values():
            available = [i for i in eligible_members if i in scores]
            if not available:
                continue
            # Current evidence and rank win before language. Access time only
            # determines staleness, never whether a source revision is newer.
            chosen = min(available, key=lambda i: (stale(i), -scores[i], candidates[i].effective_source_language != "de", i))
            representatives.update((i, chosen) for i in members)
            tied = [i for i in available if stale(i) == stale(chosen) and scores[i] == scores[chosen]]
            reason = ("only_eligible_equivalent" if len(available) == 1 else
                      "fresher_equivalent" if not stale(chosen) and any(stale(i) for i in available) else
                      "german_equivalent_tie" if len(tied) > 1 and candidates[chosen].effective_source_language == "de" else
                      "higher_ranked_equivalent" if len(tied) == 1 else "stable_equivalent_tie")
            selections.append(EvidenceSelection(mapping_ref=group.identity, representative_id=chosen,
                                                alternate_ids=[i for i in members if i != chosen],
                                                fact_ids=group.fact_ids, reason_code=reason))
        ordered = sorted({representatives[i] for i in admitted}, key=lambda i: (-scores[i], i))
        return RetrievalResult(ordered, scores, representatives, selections, channels, degradations,
                               sorted(set(used_refs), key=lambda r: r.artifact_id)[:100],
                               {i for i in ordered if i in qualified_excerpts})
