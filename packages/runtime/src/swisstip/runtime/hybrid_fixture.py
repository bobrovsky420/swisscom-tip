"""Synthetic BUILD-05 integration data, not reviewed Swiss knowledge or model quality.

The deterministic semantic double deliberately maps fabricated multilingual
terms to two dimensions. It tests channel plumbing, never qualifies a live model.
"""

import argparse
from pathlib import Path

from swisstip.core.contracts import (
    ArtifactRef, StrictModel, LanguagePolicy, RetrievalProjection, ReviewedTerminology,
    EvidenceEquivalence, RetrievalIndex, RetrievalProviders, RetrievalConfiguration,
)
from swisstip.core.identity import seal_artifact

from .fixture import fixture, ref
from .retrieval import EmbeddingResponse, RankingResponse, tokens


TERMS = {
    "en": "residence permit", "de": "Aufenthaltsbewilligung", "fr": "permis de sejour",
    "it": "permesso di soggiorno", "rm": "permissiun da dimora", "gsw": "Uufenthaltsbewilligung",
}
LANGUAGES = ["en", "de", "fr", "it", "rm"]


def seal_fixture(bundle):
    """Rebind synthetic dependencies only. This does not review or publish data."""
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

    for field in ["documents", "evidence", "rules", "facts", "projections", "terminology", "equivalences"]:
        setattr(bundle, field, [seal(v) for v in getattr(bundle, field)])
    bundle.language_policy = seal(bundle.language_policy)
    bundle.catalog.context_schemas = [seal(s) for s in bundle.catalog.context_schemas]
    bundle.catalog = seal(bundle.catalog)
    bundle.graph = seal(bundle.graph)
    for field in ["retrieval_providers", "retrieval_index", "retrieval_configuration", "release"]:
        value = getattr(bundle, field)
        if value is not None:
            setattr(bundle, field, seal(value))
    external = {}

    def collect(value):
        if isinstance(value, ArtifactRef):
            if value.artifact_id not in current:
                external[value.artifact_id] = value
        elif isinstance(value, StrictModel):
            for f in type(value).model_fields:
                if f != "external_refs":
                    collect(getattr(value, f))
        elif isinstance(value, (list, dict)):
            for v in value.values() if isinstance(value, dict) else value:
                collect(v)

    collect(bundle)
    bundle.external_refs = sorted(external.values(), key=lambda r: r.artifact_id)
    return bundle


def hybrid_fixture(*, distractors=30, fallback=True):
    bundle, request = fixture()
    template, document = bundle.evidence[0], bundle.documents[0]
    for suffix, language in [(language, language) for language in LANGUAGES[1:]] + [
            (f"noise-{i:02d}", "en") for i in range(distractors)]:
        identifier = "evidence-" + suffix
        text = ("Synthetic unrelated parking timetable " + suffix if suffix.startswith("noise")
                else "Synthetic " + TERMS[language] + " requirement for fixture group A.")
        doc = document.model_copy(deep=True)
        doc.identity = ref("document-" + suffix)
        doc.snapshot_ref = ref("snapshot-" + suffix)
        doc.text = text
        doc.sections[0].section_id = "section-" + suffix
        doc.sections[0].end_offset = len(text)
        doc = seal_artifact(doc)
        item = template.model_copy(deep=True)
        item.identity = ref(identifier)
        item.evidence_id = identifier
        item.snapshot_ref = doc.snapshot_ref
        item.normalized_document_ref = doc.identity
        item.section_id = doc.sections[0].section_id
        item.end_offset = len(text)
        item.original_excerpt = text
        item.effective_source_language = language
        item.declared_language = [language]
        item.detected_language = language
        item.citation.url = "https://example.invalid/" + suffix
        bundle.documents.append(doc)
        bundle.evidence.append(seal_artifact(item))
    parent = bundle.graph.plans[0].portions[0]
    parent.evidence_ids.extend(e.evidence_id for e in bundle.evidence[4:])
    routes = [dict(term_language=language, projection_language="de" if language == "gsw" else language,
                   dialect_profile="fixture-zurich" if language == "gsw" else None,
                   idiom_profile="fixture-rumantsch-grischun" if language == "rm" else None)
              for language in TERMS]
    bundle.language_policy = LanguagePolicy(
        identity=ref("fixture-hybrid-policy"), term_languages=list(TERMS), source_languages=LANGUAGES,
        projection_languages=LANGUAGES, routes=routes, approval_status="APPROVED",
        evaluation_ref=ref("fixture-language-evaluation"))
    bundle.terminology = [seal_artifact(ReviewedTerminology(
        identity=ref("fixture-terms-" + language), concept_id="fixture-parent", term_language=language,
        terms=[text, "Aufenthaltserlaubnis"] if language == "de" else [text], review_ref=ref("fixture-review")))
        for language, text in TERMS.items()]
    for route, terminology in zip(routes, bundle.terminology):
        route["terminology_refs"] = [terminology.identity]
    bundle.language_policy.routes = [type(bundle.language_policy.routes[0]).model_validate(r) for r in routes]
    profile = bundle.catalog.coverage_profiles[0]
    profile.source_languages = LANGUAGES
    profile.projection_languages_complete = LANGUAGES
    profile.term_routes = [type(profile.term_routes[0]).model_validate(
        {**r, "source_languages": LANGUAGES, "evaluation_ref": ref("fixture-route-evaluation")}) for r in routes]
    bundle.catalog.language_policy_ref = bundle.language_policy.identity
    bundle.release.language_policy_ref = bundle.language_policy.identity
    target_ids = {"evidence-parent", *["evidence-" + l for l in LANGUAGES[1:]]}
    bundle.equivalences = [seal_artifact(EvidenceEquivalence(
        identity=ref("fixture-parent-equivalence"), evidence_refs=[e.identity for e in bundle.evidence if e.evidence_id in target_ids],
        fact_ids=["fact-parent"], fact_refs=[bundle.facts[0].identity], review_ref=ref("fixture-review")))]
    bundle.projections = [seal_artifact(RetrievalProjection(
        identity=ref(e.evidence_id + "-projection-" + language), evidence_ref=e.identity,
        language=language, text=TERMS[language] if e.evidence_id in target_ids else "Synthetic unrelated timetable",
        provenance_refs=[ref("fixture-review")])) for e in bundle.evidence for language in LANGUAGES]
    bundle.retrieval_providers = seal_artifact(RetrievalProviders(
        identity=ref("fixture-hybrid-providers"), embedding_model="synthetic-embedding-v1", ranking_model="synthetic-ranking-v1",
        embedding_provider="synthetic/v1", ranking_provider="synthetic/v1"))
    bundle.retrieval_index = seal_artifact(RetrievalIndex(
        identity=ref("fixture-hybrid-index"), embedding_model="synthetic-embedding-v1", dimensions=2,
        projection_refs=[p.identity for p in bundle.projections],
        vectors=[dict(evidence_ref=e.identity, values=[1.0, 0.0] if e.evidence_id in target_ids else [0.0, 1.0])
                 for e in bundle.evidence]))
    bundle.retrieval_configuration = seal_artifact(RetrievalConfiguration(
        identity=ref("fixture-hybrid-ranking"), provider_configuration_ref=bundle.retrieval_providers.identity,
        index_ref=bundle.retrieval_index.identity, equivalence_refs=[g.identity for g in bundle.equivalences],
        evaluation_refs={profile.coverage_profile_id: profile.evaluation_ref},
        minimum_semantic_score=0.5,
        fallbacks=[dict(coverage_profile_id=profile.coverage_profile_id,
                        evaluation_ref=ref("fixture-fallback-evaluation"), minimum_lexical_score=1.0)] if fallback else []))
    bundle.release.snapshot_refs = [d.snapshot_ref for d in bundle.documents]
    bundle.release.normalized_document_refs = [d.identity for d in bundle.documents]
    bundle.release.evidence_refs = [e.identity for e in bundle.evidence]
    bundle.release.projection_refs = [p.identity for p in bundle.projections]
    bundle.release.terminology_refs = [t.identity for t in bundle.terminology]
    bundle.release.index_refs = [bundle.retrieval_index.identity]
    bundle.release.provider_configuration_ref = bundle.retrieval_providers.identity
    bundle.release.ranking_configuration_ref = bundle.retrieval_configuration.identity
    return seal_fixture(bundle), request


class SyntheticSemanticProvider:
    provider_id = "synthetic/v1"

    def embed(self, texts, *, model):
        return EmbeddingResponse(model, tuple((1.0, 0.0) if any(tokens(t) <= tokens(text) for t in TERMS.values())
                                               else (0.0, 1.0) for text in texts))

    def rank(self, query, candidates, *, model):
        targets = {"evidence-parent", *["evidence-" + l for l in LANGUAGES[1:]]}
        return RankingResponse(model, {c.evidence_id: 1.0 if c.evidence_id in targets else 0.0 for c in candidates})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    bundle, _ = hybrid_fixture()
    from .release import validate_release
    validate_release(bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(bundle.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Wrote synthetic hybrid fixture; evaluations and semantic vectors are fabricated.")


if __name__ == "__main__":
    main()
