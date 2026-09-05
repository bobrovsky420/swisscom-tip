"""Conservative consolidation and review metrics for concept proposal batches."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict

from swisstip.ingestion.concepts import ConceptProposalReport


def _key(value: str) -> str:
    return unicodedata.normalize("NFC", " ".join(value.split())).lower()


_LABEL_STOP_WORDS = {"der", "die", "das", "den", "des", "dem", "ein", "eine",
                     "einer", "eines", "und", "oder", "für", "durch", "von", "im",
                     "in", "mit", "zum", "zur", "the", "of", "for", "and", "a"}


def _review_pairs(groups: list[dict[str, object]]) -> tuple[list[dict[str, object]], int]:
    """Surface wording variants for human review; never merge them automatically."""
    labels = [
        {_key(label) for member in group["members"] for label in
         [member["candidate"]["preferred_label"], *member["candidate"]["alternative_labels"]]}
        for group in groups
    ]
    tokens = [set(re.findall(r"\w+", _key(g["preferred_label"]))) - _LABEL_STOP_WORDS for g in groups]
    pairs = []
    total = 0
    for right, second in enumerate(groups):
        for left in range(right):
            first = groups[left]
            if first["language"] != second["language"]:
                continue
            overlap = tokens[left] & tokens[right]
            union = tokens[left] | tokens[right]
            similarity = len(overlap) / len(union) if union else 0
            alias_match = bool(labels[left] & labels[right])
            if not alias_match and not (len(overlap) >= 2 and similarity >= 0.6):
                continue
            total += 1
            if len(pairs) < 200:
                pairs.append({
                    "group_ids": [first["group_id"], second["group_id"]],
                    "labels": [first["preferred_label"], second["preferred_label"]],
                    "reason": "shared_label_or_alias" if alias_match else "similar_label_tokens",
                    "label_similarity": round(similarity, 3),
                    "same_scope": _key(first["scope"]) == _key(second["scope"]),
                    "different_fields": [field for field in ("scope", "description", "concept_type", "granularity")
                                         if _key(first[field]) != _key(second[field])],
                    "action": "review_equivalence_and_applicability_before_merging",
                })
    return pairs, total


def summarize_reports(reports: list[ConceptProposalReport]) -> dict[str, object]:
    """Group matching claims, preserving every source and conflicting proposal."""
    groups: dict[tuple[str, ...], dict[str, object]] = {}
    possible_duplicates: dict[str, list[str]] = defaultdict(list)
    for report in reports:
        for candidate in report.candidates:
            identity = tuple(_key(value) for value in (
                report.language or "", candidate.preferred_label, candidate.scope,
                candidate.concept_type, candidate.granularity, candidate.description,
            ))
            if identity not in groups:
                digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()[:16]
                groups[identity] = {
                    "group_id": f"proposal-group-{digest}",
                    "preferred_label": candidate.preferred_label,
                    "scope": candidate.scope,
                    "description": candidate.description,
                    "concept_type": candidate.concept_type,
                    "granularity": candidate.granularity,
                    "language": report.language,
                    "validation_state": "CANDIDATE",
                    "members": [],
                }
                possible_duplicates[_key(candidate.preferred_label)].append(f"proposal-group-{digest}")
            groups[identity]["members"].append({
                "source": report.source,
                "document_id": report.document_id,
                "input_hash": report.input_hash,
                # Preserve evidence, questions, confidence and relations from each source.
                "candidate": candidate.to_dict(),
            })

    candidates = [c for report in reports for c in report.candidates]
    rejected_count = sum(int(r.quality_metrics["rejected_proposals"]) for r in reports)
    accepted_count = sum(int(r.quality_metrics["accepted_proposals"]) for r in reports)
    raw_count = rejected_count + accepted_count
    review_pairs, review_pair_count = _review_pairs(list(groups.values()))

    def token_total(field: str) -> int | None:
        values = [getattr(r, field) for r in reports]
        return None if any(v is None for v in values) else sum(values)

    return {
        "consolidation_policy": "exact_normalized_label_scope_type_granularity_description_language",
        "consolidated_concepts": list(groups.values()),
        "duplicate_review_pairs": review_pairs,
        "duplicate_review_pair_count": review_pair_count,
        "duplicate_review_pairs_truncated": review_pair_count > len(review_pairs),
        "duplicate_review_groups": [
            {"normalized_label": label, "group_ids": ids,
             "reason": "Matching label with different claims or scope; review before merging"}
            for label, ids in possible_duplicates.items() if len(ids) > 1
        ],
        "quality_summary": {
            "report_count": len(reports),
            "request_count": sum(r.request_count for r in reports),
            "prompt_tokens": token_total("prompt_tokens"),
            "output_tokens": token_total("output_tokens"),
            "proposed_count": raw_count,
            "rejected_count": rejected_count,
            "rejection_rate": rejected_count / raw_count if raw_count else None,
            "candidate_count": len(candidates),
            "consolidated_count": len(groups),
            "empty_page_count": sum(not r.candidates for r in reports),
            "empty_question_count": sum(not c.user_questions for c in candidates),
            "excluded_section_count": sum(len(r.excluded_sections) for r in reports),
            "skipped_chunk_count": sum(len(r.skipped_chunks) for r in reports),
            "review_request_count": sum(int(r.quality_metrics.get("review_request_count", 0)) for r in reports),
            "semantic_review_issue_counts": dict(Counter(
                verdict["issue"] for report in reports for verdict in report.semantic_reviews
                if verdict["decision"] != "supported"
            )),
            "semantic_quality": "requires_human_review; counts_do_not_measure_accuracy_or_recall",
        },
    }
