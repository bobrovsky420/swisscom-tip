"""Generate a synthetic BUILD-03 serving fixture, with no real-world coverage.

These fabricated review/evaluation records exercise contracts only. They never
promote the residence seed or candidates into approved production knowledge.
"""

import argparse
import hashlib
from pathlib import Path

from swisstip.core.contracts import (
    ArtifactRef, ContextSchema, EvidenceObject, KnowledgeCatalog, KnowledgeRelease,
    LanguagePolicy, NormalizedEvidenceDocument, PublishedFact, PublishedRule,
    ResolutionGraph, StrictModel,
)
from swisstip.core.identity import seal_artifact

from .release import ReleaseBundle


def ref(name):
    return ArtifactRef(artifact_id=name, version="1", sha256="a" * 64)


def fixture(release_id="fixture-release-a"):
    review = ref("fixture-review")
    documents, evidence, facts = [], [], []
    for name in ["parent", "child", "sibling", "work"]:
        concept = "fixture-parent" if name == "work" else "fixture-" + name
        text = f"Synthetic {name} requirement for fixture group A."
        snapshot = ArtifactRef(artifact_id=f"snapshot-{name}", version="1",
                               sha256=hashlib.sha256(text.encode()).hexdigest())
        doc = seal_artifact(NormalizedEvidenceDocument(
            identity=ref(f"document-{name}"), snapshot_ref=snapshot,
            source_id="fixture-source", text=text,
            sections=[dict(section_id=f"section-{name}", start_offset=0, end_offset=len(text))]))
        item = seal_artifact(EvidenceObject(
            identity=ref(f"evidence-{name}"), evidence_id=f"evidence-{name}", release_id=release_id,
            snapshot_ref=snapshot, normalized_document_ref=doc.identity,
            section_id=f"section-{name}", start_offset=0, end_offset=len(text), original_excerpt=text,
            citation=dict(source_id="fixture-source", authority="Synthetic fixture authority",
                          url=f"https://example.invalid/{name}", title="Synthetic fixture",
                          accessed_at="2026-09-06T00:00:00Z"), declared_language=["en"],
            detected_language="en", effective_source_language="en", language_detection_method="fixture",
            language_confidence=1.0, canonical_concept_ids=[concept], jurisdiction=dict(country_code="CH", canton_code="CH-ZH"),
            temporal_coverage=dict(valid_from="2026-01-01", valid_through="2026-12-31"), provenance_refs=[review]))
        documents.append(doc)
        evidence.append(item)
        facts.append(seal_artifact(PublishedFact(identity=ref(f"fact-{name}"), fact_id=f"fact-{name}",
                                                statement=text, language="en", evidence_ids=[item.evidence_id])))
    rule = seal_artifact(PublishedRule(identity=ref("fixture-work-rule"), rule_id="fixture-work-rule",
                                      when=[dict(field="purpose", operator="equals", values=["work"])],
                                      fact_ids=["fact-work"]))
    facts[-1] = seal_artifact(facts[-1].model_copy(update={"rule_refs": [rule.identity]}))
    schema = seal_artifact(ContextSchema(
        identity=ref("fixture-context"), fields=[
            dict(name="population", kind="string", description="Synthetic group.", required=True,
                 enum=["group-a"], reason_code="population_required"),
            dict(name="purpose", kind="string", description="Synthetic purpose.", required=True,
                 enum=["study", "work"], reason_code="purpose_required"),
            dict(name="work_days", kind="integer", description="Synthetic duration.", minimum=1,
                 maximum=365, reason_code="duration_required")],
        conditional_requirements=[dict(when=[dict(field="purpose", operator="equals", values=["work"])],
                                       required_fields=["work_days"], reason_code="duration_required",
                                       rule_refs=[rule.identity], evidence_refs=[evidence[-1].identity])]))
    policy = seal_artifact(LanguagePolicy(
        identity=ref("fixture-policy"), term_languages=["en", "de"], source_languages=["en", "de"],
        projection_languages=["en", "de"], routes=[dict(term_language=t, projection_language=t) for t in ["en", "de"]],
        approval_status="APPROVED", evaluation_ref=ref("fixture-language-evaluation")))
    entries = []
    for name, kind, parent in [("space", "knowledge_space", None), ("domain", "domain", "space"),
                                ("topic", "topic", "domain"), ("parent", "concept", "topic"),
                                ("child", "concept", "parent"), ("sibling", "concept", "topic")]:
        entries.append(dict(entry_id="fixture-" + name, kind=kind,
                            parent_ids=["fixture-" + parent] if parent else [], lifecycle="CURATED",
                            labels={"en": dict(label="Synthetic " + name,
                                               description="Fabricated BUILD-03 fixture; no real-world coverage.",
                                               provenance=[review])}))
    profile = dict(
        coverage_profile_id="fixture-profile", release_id=release_id, catalog_ref=ref("fixture-catalog"),
        knowledge_space_id="fixture-space", domain_id="fixture-domain", topic_id="fixture-topic",
        concept_ids=["fixture-parent", "fixture-child", "fixture-sibling"], intent="requirements",
        jurisdiction=dict(country_code="CH", canton_code="CH-ZH"), context_schema_ref=schema.identity,
        scope_modes=["exact", "descendants"], max_descendant_depth=1, max_concepts=5,
        source_ids=["fixture-source"], source_languages=["en"],
        temporal_coverage=dict(valid_from="2026-01-01", valid_through="2026-12-31"),
        term_routes=[dict(term_language=t, projection_language=t, source_languages=["en"],
                          evaluation_ref=ref("fixture-route-evaluation")) for t in ["en", "de"]],
        projection_languages_complete=["en", "de"], evaluation_ref=ref("fixture-evaluation"),
        rule_refs=[rule.identity], exclusions=["Synthetic fixture only; no Swiss legal coverage."],
        freshness_policy=dict(max_age_days=30, policy_ref=ref("fixture-freshness")), approval_status="APPROVED")
    catalog = seal_artifact(KnowledgeCatalog(identity=ref("fixture-catalog"), release_id=release_id,
                                             entries=entries, context_schemas=[schema], coverage_profiles=[profile],
                                             language_policy_ref=policy.identity))
    graph = seal_artifact(ResolutionGraph(
        identity=ref("fixture-graph"), release_id=release_id,
        plans=[dict(coverage_profile_id="fixture-profile", portions=[
            dict(portion_id="portion-" + name, concept_ids=["fixture-" + name], fact_ids=["fact-" + name],
                 evidence_ids=["evidence-" + name],
                 rule_refs=[rule.identity] if name == "parent" else []) for name in ["parent", "child", "sibling"]])]))
    release = seal_artifact(KnowledgeRelease(
        release_id=release_id, identity=ref("fixture-release"), created_at="2026-09-06T00:00:00Z",
        catalog_ref=catalog.identity, context_schema_refs=[schema.identity], language_policy_ref=policy.identity,
        snapshot_refs=[d.snapshot_ref for d in documents], normalized_document_refs=[d.identity for d in documents],
        evidence_refs=[e.identity for e in evidence], concept_graph_ref=graph.identity,
        terminology_refs=[], fact_refs=[f.identity for f in facts], rule_refs=[rule.identity],
        projection_refs=[], index_refs=[], contract_schema_refs=[ref("fixture-contract")],
        provider_configuration_ref=ref("fixture-no-provider"), ranking_configuration_ref=ref("fixture-lexical-ranking"),
        evaluation_ref=ref("fixture-evaluation")))
    bundle = ReleaseBundle(release=release, catalog=catalog, language_policy=policy, graph=graph,
                           documents=documents, evidence=evidence, facts=facts, rules=[rule])
    supplied = {a.identity.artifact_id for a in [release, catalog, policy, schema, graph, *documents, *evidence, *facts, rule]}
    external = {}

    def collect(value):
        if isinstance(value, ArtifactRef):
            if value.artifact_id not in supplied:
                external[value.artifact_id] = value
        elif isinstance(value, StrictModel):
            for field in type(value).model_fields:
                collect(getattr(value, field))
        elif isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(bundle)
    bundle.external_refs = sorted(external.values(), key=lambda r: r.artifact_id)
    request = dict(schema_version="structured-grounding/v1", release_id=release_id,
                   knowledge_space_id="fixture-space", domain_id="fixture-domain", topic_id="fixture-topic",
                   concept_ids=["fixture-parent"], intent="requirements", jurisdiction=dict(country_code="CH", canton_code="CH-ZH"),
                   context=dict(population="group-a", purpose="study"), as_of="2026-09-06", scope_mode="exact")
    return bundle, request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    bundle, _ = fixture()
    from .release import validate_release
    validate_release(bundle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(bundle.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote synthetic fixture (not production knowledge): {args.output}")


if __name__ == "__main__":
    main()
