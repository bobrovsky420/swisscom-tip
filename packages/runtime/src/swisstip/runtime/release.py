"""Validated local release reader, independent of the future publication workflow.

External references declare build-owned dependencies; this reader does not attest
their contents or human review. Loaded serving artifacts are hash/span checked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field

from swisstip.core.contracts import (
    ArtifactRef, EvidenceObject, KnowledgeCatalog, KnowledgeRelease, LanguagePolicy,
    NormalizedEvidenceDocument, PublishedFact, PublishedRule, ResolutionGraph,
    StrictModel, RetrievalProjection, ReviewedTerminology, EvidenceEquivalence,
    RetrievalIndex, RetrievalProviders, RetrievalConfiguration,
)
from swisstip.core.identity import verify_artifact
from swisstip.core.validation import validate_catalog, validate_context


class ReleaseBundle(StrictModel):
    schema_version: Literal["serving-release/v1"] = "serving-release/v1"
    release: KnowledgeRelease
    catalog: KnowledgeCatalog
    language_policy: LanguagePolicy
    graph: ResolutionGraph
    documents: Annotated[list[NormalizedEvidenceDocument], Field(max_length=100000)]
    evidence: Annotated[list[EvidenceObject], Field(max_length=100000)]
    facts: Annotated[list[PublishedFact], Field(max_length=100000)]
    rules: Annotated[list[PublishedRule], Field(max_length=100000)]
    external_refs: Annotated[list[ArtifactRef], Field(max_length=100000)] = Field(default_factory=list)
    projections: Annotated[list[RetrievalProjection], Field(max_length=100000)] = Field(default_factory=list)
    terminology: Annotated[list[ReviewedTerminology], Field(max_length=10000)] = Field(default_factory=list)
    equivalences: Annotated[list[EvidenceEquivalence], Field(max_length=100000)] = Field(default_factory=list)
    retrieval_index: RetrievalIndex | None = None
    retrieval_providers: RetrievalProviders | None = None
    retrieval_configuration: RetrievalConfiguration | None = None


def validate_release(bundle: ReleaseBundle) -> None:
    """Fail closed on invalid serving content, rather than weaken client scope."""
    release, catalog, policy, graph = bundle.release, bundle.catalog, bundle.language_policy, bundle.graph

    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)

    def unique(items, key):
        result = {getattr(item, key): item for item in items}
        require(len(result) == len(items), f"duplicate_{key}")
        return result

    artifacts = [release, catalog, policy, graph, *catalog.context_schemas,
                 *bundle.documents, *bundle.evidence, *bundle.facts, *bundle.rules,
                 *bundle.projections, *bundle.terminology, *bundle.equivalences,
                 *[a for a in [bundle.retrieval_index, bundle.retrieval_providers,
                               bundle.retrieval_configuration] if a is not None]]
    registry = unique([item.identity for item in artifacts] + bundle.external_refs, "artifact_id")
    for artifact in artifacts:
        require(verify_artifact(artifact), f"content_hash_mismatch: {artifact.identity.artifact_id}")

    def check_refs(value):
        if isinstance(value, ArtifactRef):
            require(registry.get(value.artifact_id) == value, f"artifact_mismatch: {value.artifact_id}")
        elif isinstance(value, StrictModel):
            for name in type(value).model_fields:
                check_refs(getattr(value, name))
        elif isinstance(value, dict):
            for child in value.values():
                check_refs(child)
        elif isinstance(value, list):
            for child in value:
                check_refs(child)

    check_refs(bundle)
    require(not validate_catalog(catalog, policy, artifacts=registry), "invalid_catalog")
    require(release.release_id == catalog.release_id == graph.release_id, "release_mismatch")
    require(release.catalog_ref == catalog.identity and release.language_policy_ref == policy.identity,
            "release_catalog_or_policy_mismatch")
    require(release.concept_graph_ref == graph.identity, "release_graph_mismatch")
    require(policy.approval_status == "APPROVED", "unapproved_language_policy")
    require(all(p.approval_status == "APPROVED" for p in catalog.coverage_profiles), "unapproved_coverage")
    require(all(e.lifecycle in {"CURATED", "VERIFIED_AUTOMATIC"} for e in catalog.entries),
            "unreviewed_catalog_entry")
    for refs, items in [(release.context_schema_refs, catalog.context_schemas),
                        (release.normalized_document_refs, bundle.documents),
                        (release.evidence_refs, bundle.evidence),
                        (release.fact_refs, bundle.facts), (release.rule_refs, bundle.rules)]:
        require(len(set(refs)) == len(refs) and set(refs) == {item.identity for item in items},
                "manifest_content_mismatch")
    entries = {item.entry_id: item for item in catalog.entries}
    documents = unique(bundle.documents, "identity")
    evidence = unique(bundle.evidence, "evidence_id")
    facts = unique(bundle.facts, "fact_id")
    rules = unique(bundle.rules, "identity")
    unique(bundle.rules, "rule_id")
    for doc in bundle.documents:
        require(doc.snapshot_ref in release.snapshot_refs, "document_snapshot_not_in_release")
    for item in evidence.values():
        doc = documents.get(item.normalized_document_ref)
        require(item.release_id == release.release_id and doc is not None, "evidence_release_or_document_mismatch")
        require(item.citation.accessed_at <= release.created_at, "evidence_access_after_release")
        require(item.snapshot_ref == doc.snapshot_ref and item.citation.source_id == doc.source_id,
                "evidence_source_chain_mismatch")
        require(doc.text[item.start_offset:item.end_offset] == item.original_excerpt, "evidence_span_mismatch")
        require(any(s.section_id == item.section_id and s.start_offset <= item.start_offset
                    and item.end_offset <= s.end_offset for s in doc.sections), "evidence_section_mismatch")
        require(item.effective_source_language in policy.source_languages, "evidence_language_outside_policy")
        require(all(c in entries and entries[c].kind == "concept" for c in item.canonical_concept_ids),
                "unknown_evidence_concept")
    for fact in facts.values():
        require(len(set(fact.evidence_ids)) == len(fact.evidence_ids) and set(fact.evidence_ids) <= evidence.keys(),
                "unknown_or_duplicate_fact_evidence")
        require(all(ref in rules for ref in fact.rule_refs), "unknown_fact_rule")
    for rule in rules.values():
        require(len(set(rule.fact_ids)) == len(rule.fact_ids) and set(rule.fact_ids) <= facts.keys(), "unknown_rule_fact")
        require(all(rule.identity in facts[f].rule_refs for f in rule.fact_ids), "rule_output_missing_provenance")
    profiles = {p.coverage_profile_id: p for p in catalog.coverage_profiles}
    plans = unique(graph.plans, "coverage_profile_id")
    require(plans.keys() == profiles.keys(), "coverage_plan_mismatch")
    schemas = {s.identity: s for s in catalog.context_schemas}
    evidence_refs = {e.identity for e in bundle.evidence}
    for schema in schemas.values():
        for condition in [*schema.conditional_requirements, *schema.consistency_rules]:
            require(set(condition.rule_refs) <= rules.keys()
                    and set(condition.evidence_refs) <= evidence_refs, "context_dependency_not_loaded")
    for identifier, plan in plans.items():
        profile = profiles[identifier]
        require(set(profile.rule_refs) <= rules.keys(), "profile_rule_not_loaded")
        schema = schemas[profile.context_schema_ref]
        unique(plan.portions, "portion_id")
        for portion in plan.portions:
            require(set(portion.concept_ids) <= set(profile.concept_ids), "portion_outside_profile")
            require(set(portion.fact_ids) <= facts.keys(), "unknown_portion_fact")
            require(set(portion.evidence_ids) <= evidence.keys(), "unknown_portion_evidence")
            for evidence_id in portion.evidence_ids:
                item = evidence[evidence_id]
                require(item.citation.source_id in profile.source_ids
                        and item.effective_source_language in profile.source_languages
                        and bool(set(item.canonical_concept_ids) & set(portion.concept_ids or profile.concept_ids)),
                        "excerpt_outside_profile")
            require(all(not facts[f].rule_refs for f in portion.fact_ids), "conditional_fact_in_unconditional_portion")
            require(all(ref in rules and ref in profile.rule_refs for ref in portion.rule_refs), "unknown_portion_rule")
            outputs = set(portion.fact_ids)
            for ref in portion.rule_refs:
                rule = rules[ref]
                outputs.update(rule.fact_ids)
                for condition in rule.when:
                    require(condition.field in {f.name for f in schema.fields}, "undeclared_rule_field")
                    for value in condition.values:
                        errors, _ = validate_context({condition.field: value}, schema)
                        require(not errors, "invalid_rule_value")
            for fact_id in outputs:
                require(set(facts[fact_id].rule_refs) <= set(portion.rule_refs), "fact_rule_outside_portion")
                for evidence_id in facts[fact_id].evidence_ids:
                    item = evidence[evidence_id]
                    require(item.citation.source_id in profile.source_ids, "fact_source_outside_profile")
                    require(item.effective_source_language in profile.source_languages, "fact_language_outside_profile")
                    require(bool(set(item.canonical_concept_ids) & set(portion.concept_ids or profile.concept_ids)),
                            "fact_evidence_outside_portion")
    for conflict in graph.conflicts:
        require(len(set(conflict.fact_ids)) == len(conflict.fact_ids) and set(conflict.fact_ids) <= facts.keys(),
                "unknown_or_duplicate_conflicting_fact")
    validate_retrieval(bundle, require)


def validate_retrieval(bundle, require):
    """Check the loaded retrieval graph, not just externally declared hashes."""
    config = bundle.retrieval_configuration
    if config is None:
        require(not (bundle.projections or bundle.terminology or bundle.equivalences
                     or bundle.retrieval_index or bundle.retrieval_providers
                     or bundle.release.index_refs or bundle.release.projection_refs
                     or bundle.release.terminology_refs), "incomplete_retrieval_assets")
        return  # Explicit BUILD-03 legacy baseline, never reported as hybrid.
    release = bundle.release
    index, providers = bundle.retrieval_index, bundle.retrieval_providers
    require(index is not None and providers is not None, "incomplete_retrieval_assets")
    require(config.identity == release.ranking_configuration_ref
            and providers.identity == release.provider_configuration_ref == config.provider_configuration_ref
            and release.index_refs == [index.identity] and config.index_ref == index.identity,
            "retrieval_manifest_mismatch")
    require(index.embedding_model == providers.embedding_model, "embedding_model_mismatch")
    require(set(bundle.language_policy.projection_languages) == {"en", "de", "fr", "it", "rm"},
            "hybrid_requires_five_projection_languages")
    for refs, items in [(release.projection_refs, bundle.projections),
                        (release.terminology_refs, bundle.terminology),
                        (config.equivalence_refs, bundle.equivalences)]:
        require(len(refs) == len(set(refs)) and set(refs) == {a.identity for a in items},
                "retrieval_manifest_mismatch")
    require(set(index.projection_refs) == set(release.projection_refs)
            and len(index.projection_refs) == len(set(index.projection_refs)), "index_projection_mismatch")
    evidence = {e.identity: e for e in bundle.evidence}
    facts = {f.fact_id: f for f in bundle.facts}
    concepts = {c.entry_id for c in bundle.catalog.entries if c.kind == "concept"}
    projection_keys = set()
    for projection in bundle.projections:
        require(projection.evidence_ref in evidence, "projection_evidence_not_loaded")
        require(projection.language in bundle.language_policy.projection_languages, "projection_language_outside_policy")
        key = (projection.evidence_ref, projection.language)
        require(key not in projection_keys, "duplicate_evidence_projection")
        projection_keys.add(key)
    vector_refs = set()
    for vector in index.vectors:
        require(vector.evidence_ref in evidence and vector.evidence_ref not in vector_refs,
                "unknown_or_duplicate_vector_evidence")
        require(len(vector.values) == index.dimensions and any(vector.values), "invalid_index_vector")
        vector_refs.add(vector.evidence_ref)
    require(vector_refs == evidence.keys(), "incomplete_evidence_vectors")
    for term in bundle.terminology:
        require(term.concept_id in concepts and term.term_language in bundle.language_policy.term_languages,
                "terminology_outside_policy_or_catalog")
    terminology = {t.identity: t for t in bundle.terminology}
    profiles = {p.coverage_profile_id: p for p in bundle.catalog.coverage_profiles}
    require(config.evaluation_refs.keys() == profiles.keys(), "unevaluated_retrieval_profile")
    for profile in profiles.values():
        require(set(profile.projection_languages_complete) == {"en", "de", "fr", "it", "rm"},
                "hybrid_requires_five_complete_projections")
        require(config.evaluation_refs[profile.coverage_profile_id] == profile.evaluation_ref,
                "retrieval_evaluation_mismatch")
        for route in profile.term_routes:
            require(all(ref in terminology and terminology[ref].term_language == route.term_language
                        and terminology[ref].concept_id in profile.concept_ids for ref in route.terminology_refs),
                    "route_terminology_not_loaded_or_outside_scope")
        for item in bundle.evidence:
            if item.citation.source_id in profile.source_ids and set(item.canonical_concept_ids) & set(profile.concept_ids):
                require(all((item.identity, language) in projection_keys
                            for language in profile.projection_languages_complete), "missing_required_projection")
    fallback_ids = [f.coverage_profile_id for f in config.fallbacks]
    require(len(fallback_ids) == len(set(fallback_ids)) and set(fallback_ids) <= profiles.keys(),
            "invalid_fallback_profiles")
    grouped = set()
    for group in bundle.equivalences:
        members = group.evidence_refs
        require(len(set(members)) == len(members) and set(members) <= evidence.keys(), "invalid_equivalence_members")
        require(not grouped.intersection(members), "overlapping_equivalence_groups")
        grouped.update(members)
        first = evidence[members[0]]
        require(all(evidence[r].jurisdiction == first.jurisdiction
                    and evidence[r].temporal_coverage == first.temporal_coverage
                    and set(evidence[r].canonical_concept_ids) == set(first.canonical_concept_ids)
                    and evidence[r].citation.authority == first.citation.authority for r in members),
                "incompatible_equivalence_scope")
        member_ids = {evidence[r].evidence_id for r in members}
        require(len(group.fact_ids) == len(set(group.fact_ids)) and set(group.fact_ids) <= facts.keys(),
                "unknown_equivalence_fact")
        require(len(group.fact_refs) == len(set(group.fact_refs))
                and set(group.fact_refs) == {facts[f].identity for f in group.fact_ids},
                "equivalence_fact_revision_mismatch")
        referenced = {f.fact_id for f in bundle.facts if set(f.evidence_ids) & member_ids}
        require(referenced == set(group.fact_ids), "equivalence_fact_support_mismatch")
        # Interchangeability is reviewed per exact fact, including conditions and
        # all-of evidence. Never collapse two distinct supporting spans of a fact.
        require(all(len(set(facts[f].evidence_ids) & member_ids) == 1 for f in group.fact_ids),
                "equivalence_collapses_joint_support")
        require(not any(len(set(c.fact_ids) & referenced) > 1 for c in bundle.graph.conflicts),
                "equivalence_hides_conflict")


class ReleaseStore:
    """Private immutable snapshots with explicit active selection and historical reads.

    Loading is not publication/approval. No ID may be replaced with new content.
    Copies at both boundaries prevent callers mutating a validated release.
    """

    def __init__(self, bundles: list[ReleaseBundle], *, active_release_id: str):
        self._bundles: dict[str, str] = {}
        for supplied in bundles:
            bundle = ReleaseBundle.model_validate_json(supplied.model_dump_json())
            validate_release(bundle)
            identifier = bundle.release.release_id
            if identifier in self._bundles:
                raise ValueError("duplicate_release_id")
            self._bundles[identifier] = bundle.model_dump_json()
        if active_release_id not in self._bundles:
            raise ValueError("active_release_unavailable")
        self._active_release_id = active_release_id

    @classmethod
    def from_files(cls, paths: list[Path], *, active_release_id: str) -> ReleaseStore:
        return cls([ReleaseBundle.model_validate_json(p.read_bytes()) for p in paths],
                   active_release_id=active_release_id)

    @property
    def active_release_id(self) -> str:
        return self._active_release_id

    def get(self, release_id: str) -> ReleaseBundle | None:
        content = self._bundles.get(release_id)
        return ReleaseBundle.model_validate_json(content) if content is not None else None
