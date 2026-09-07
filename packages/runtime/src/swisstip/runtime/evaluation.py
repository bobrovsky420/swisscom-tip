"""Reproducible retrieval gates for explicitly labelled, release-bound cases.

This evaluates supplied labels; it does not manufacture semantic ground truth or
approve a release. The demo labels/providers are synthetic integration fixtures.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Annotated

from pydantic import Field

from swisstip.core.contracts import ArtifactRef, StableId, StrictModel, StructuredGroundingRequest, ToolError
from swisstip.core.identity import json_content_hash


class RetrievalGoldCase(StrictModel):
    case_id: StableId
    release_ref: ArtifactRef
    request: StructuredGroundingRequest
    # Each group is one required original document or reviewed equivalent set.
    required_evidence_groups: Annotated[list[list[StableId]], Field(min_length=1, max_length=20)]
    required_fact_ids: Annotated[list[StableId], Field(min_length=1, max_length=50)]
    eligible_evidence_ids: Annotated[list[StableId], Field(min_length=1, max_length=100000)]
    relevant_evidence_ids: Annotated[list[StableId], Field(min_length=1, max_length=100000)]
    minimum_precision_at_5: Annotated[float, Field(ge=0.0, le=1.0)]


def evaluate(service, cases):
    """Require every declared gate; an empty suite or mismatched release fails."""
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("evaluation_requires_unique_nonempty_cases")
    outcomes = []
    for case in cases:
        groups = [set(g) for g in case.required_evidence_groups]
        eligible, relevant = set(case.eligible_evidence_ids), set(case.relevant_evidence_ids)
        if any(not g or not g <= relevant for g in groups) or not relevant <= eligible:
            raise ValueError("inconsistent_gold_labels")
        start = time.perf_counter()
        result = service.resolve(case.request)
        elapsed = (time.perf_counter() - start) * 1000
        if isinstance(result, ToolError):
            outcomes.append(dict(case_id=case.case_id, passed=False, error=result.code, latency_ms=round(elapsed, 3)))
            continue
        if result.release_ref != case.release_ref:
            raise ValueError("evaluation_release_mismatch")
        candidates = result.trace.candidate_ids[:20] if result.trace else []
        final = [e.evidence_id for e in result.evidence[:5]]
        recall = sum(bool(set(candidates) & g) for g in groups) / len(groups)
        fact_recall = len(set(case.required_fact_ids) & {f.fact_id for f in result.supported_portions}) / len(set(case.required_fact_ids))
        precision = len(set(final) & relevant) / len(final) if final else 0.0
        leakage = len((set(candidates) | set(final)) - eligible)
        fetched = service.get_evidence(dict(release_id=result.release_id, evidence_ids=final)) if final else None
        citations = fetched is not None and not isinstance(fetched, ToolError) and fetched.evidence == result.evidence
        required_in_final = all(set(final) & g for g in groups)
        passed = (recall == 1.0 and fact_recall == 1.0 and required_in_final and citations and leakage == 0
                  and precision >= case.minimum_precision_at_5 and result.status == "SUPPORTED")
        outcomes.append(dict(case_id=case.case_id, passed=passed, status=result.status,
                             recall_at_20=recall, fact_recall_at_5=fact_recall, precision_at_5=precision,
                             scope_leakage=leakage, original_citations=citations,
                             candidate_count=len(candidates), evidence_count=len(final),
                             channels=result.trace.channels if result.trace else [],
                             latency_ms=round(elapsed, 3), response_bytes=len(result.model_dump_json().encode("utf-8"))))
    return dict(schema_version="retrieval-evaluation/v1", cases_sha256=json_content_hash([c.model_dump(mode="json") for c in cases]),
                release_refs=[r.model_dump() for r in sorted({c.release_ref for c in cases}, key=lambda r: r.artifact_id)],
                passed=all(o["passed"] for o in outcomes), case_count=len(outcomes),
                passed_count=sum(o["passed"] for o in outcomes), outcomes=outcomes)


def synthetic_evaluation():
    from .hybrid_fixture import LANGUAGES, TERMS, SyntheticSemanticProvider, hybrid_fixture
    from .service import KnowledgeService
    from .release import ReleaseStore
    bundle, request = hybrid_fixture()
    store = ReleaseStore([bundle], active_release_id=request["release_id"])
    cases = []
    for term_language, term in TERMS.items():
        for source in LANGUAGES:
            target = "evidence-parent" if source == "en" else "evidence-" + source
            eligible = [e.evidence_id for e in bundle.evidence if e.effective_source_language == source
                        and "fixture-parent" in e.canonical_concept_ids and e.evidence_id != "evidence-work"]
            cases.append(RetrievalGoldCase(
                case_id=f"synthetic-{term_language}-{source}", release_ref=bundle.release.identity,
                request={**request, "retrieval_terms": [dict(text=term, language=term_language)], "source_languages": [source]},
                required_evidence_groups=[[target]], required_fact_ids=["fact-parent"],
                eligible_evidence_ids=eligible, relevant_evidence_ids=[target], minimum_precision_at_5=1.0))
    class Outage(SyntheticSemanticProvider):
        def rank(self, query, candidates, *, model):
            raise TimeoutError("Synthetic ranker outage")
    results = {}
    for name, embedding, ranking in [("hybrid", SyntheticSemanticProvider(), SyntheticSemanticProvider()),
                                      ("embedding_outage", None, SyntheticSemanticProvider()),
                                      ("ranking_outage", SyntheticSemanticProvider(), Outage())]:
        service = KnowledgeService(store, embedding_provider=embedding, ranking_provider=ranking,
                                   clock=lambda: datetime(2026, 9, 6, 12, tzinfo=timezone.utc))
        results[name] = evaluate(service, cases)
    return dict(synthetic=True, limitation="Fabricated data, labels, evaluations and semantic providers; no live model qualification.",
                passed=all(r["passed"] for r in results.values()), profiles=results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--release", type=Path)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--embedding-url")
    parser.add_argument("--ranking-url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.synthetic:
        if args.release or args.cases or args.embedding_url or args.ranking_url:
            parser.error("--synthetic cannot be combined with release, cases or provider endpoints")
        report = synthetic_evaluation()
    else:
        if not args.release or not args.cases:
            parser.error("Supply --release and --cases, or --synthetic")
        from .release import ReleaseBundle, ReleaseStore
        from .service import KnowledgeService
        from .providers import OllamaRetrievalProvider
        bundle = ReleaseBundle.model_validate_json(args.release.read_bytes())
        store = ReleaseStore([bundle], active_release_id=bundle.release.release_id)
        service = KnowledgeService(store,
                                   embedding_provider=OllamaRetrievalProvider(args.embedding_url) if args.embedding_url else None,
                                   ranking_provider=OllamaRetrievalProvider(args.ranking_url) if args.ranking_url else None)
        cases = [RetrievalGoldCase.model_validate(c) for c in json.loads(args.cases.read_text(encoding="utf-8"))]
        report = evaluate(service, cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    print("Retrieval gates: " + ("PASS" if report["passed"] else "FAIL"))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
