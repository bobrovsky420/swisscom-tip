"""Source-first extraction, bounded repair, coverage audit and human-review queue."""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import asdict
from datetime import UTC

from . import claim_contracts as contracts
from .concepts import (CandidateConcept, ConceptExtractionError, ConceptProposalReport,
                       EvidenceSpan, ModelCompletion, SemanticModelError, STRUCTURED_PROMPT_PROFILE)
from .source_structure import VERSION as NORMALIZATION_VERSION


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _repair_feedback(record):
    """Keep all diagnostics, with each proposal once and no raw review text."""
    result = {key: value for key, value in record.items() if key not in {"raw_completion", "error"}}
    result["structural_rejections"] = [
        {key: value for key, value in item.items() if key != "proposal"}
        for item in record.get("structural_rejections", [])]
    if "error" in record:
        result["validation_error"] = record["error"]
    return result


class StructuredExtraction:
    def __init__(self, engine):
        self.engine = engine

    def plan(self, page):
        if page.normalization_version != NORMALIZATION_VERSION:
            raise ConceptExtractionError("v4 requires normalize_downloaded_page(logical_blocks=True)")
        groups = OrderedDict()
        inventory = []
        for block in page.sections:
            status = "excluded_policy" if block.block_kind in {"navigation", "heading"} else "pending"
            inventory.append({"section_id": block.section_id, "scope_id": block.scope_id,
                              "kind": block.block_kind, "heading_path": block.heading_path,
                              "text": block.text, "status": status,
                              "evidence_text": block.evidence_text,
                              "evidence_id": f"{block.section_id}:0:{len(block.evidence_text)}",
                              "reason": block.block_kind if status == "excluded_policy" else "awaiting_extraction",
                              "structure_issues": list(block.structure_issues),
                              "candidate_ids": [], "assessment_origin": "deterministic_inventory"})
            if status == "pending":
                groups.setdefault(block.scope_id, []).append(block)
        eligible = []
        records = {r["section_id"]: r for r in inventory}
        for blocks in groups.values():
            problem = None
            if any(b.structure_issues for b in blocks):
                problem = ("unresolved_structure", "source structure requires human review")
            elif sum(len(b.evidence_text) for b in blocks) > self.engine._chunk_content_characters:
                problem = ("not_processed_size", "logical group exceeds input limit; no partial condition list is extracted")
            if problem:
                for block in blocks:
                    records[block.section_id].update(status=problem[0], reason=problem[1])
            else:
                eligible.append(blocks)
        # Pack whole ownership groups together to reduce calls without permitting
        # evidence borrowing between the distinct groups in a packet.
        packets = []
        for group in eligible:
            if not packets or sum(len(b.evidence_text) for b in [*packets[-1], *group]) > self.engine._chunk_content_characters:
                packets.append([])
            packets[-1].extend(group)
        jobs = packets[:self.engine._max_model_requests_per_page // 2]
        for blocks in packets[len(jobs):]:
            for block in blocks:
                records[block.section_id].update(status="not_processed_budget",
                    reason="insufficient budget for extraction and coverage audit")
        return jobs, inventory

    def planned_request_count(self, page):
        jobs, _ = self.plan(page)
        return min(self.engine._max_model_requests_per_page // 2 * 2,
                   len(jobs) * 2 * (1 + self.engine._max_repair_attempts))

    def extract(self, page):
        engine = self.engine
        jobs, inventory = self.plan(page)
        # The preview is an upper bound even for odd configured page budgets.
        request_ceiling = min(engine._max_model_requests_per_page // 2 * 2,
                              len(jobs) * 2 * (1 + engine._max_repair_attempts))
        by_block = {row["section_id"]: row for row in inventory}
        candidates, rejected, reviews, queue, completions, warnings = [], [], [], [], [], []
        attempt_counts = {"generation": 0, "review": 0, "repair": 0}
        provider_failed = False
        for job_index, blocks in enumerate(jobs, 1):
            if provider_failed:
                for block in blocks:
                    by_block[block.section_id].update(status="not_processed_provider_failure", reason="earlier provider failure")
                continue
            evidence = {f"{block.section_id}:0:{len(block.evidence_text)}":
                        {"section_id": block.section_id, "scope_id": block.scope_id, "start": 0, "end": len(block.evidence_text),
                         "text": block.evidence_text} for block in blocks}
            block_ids = [b.section_id for b in blocks]
            schema = contracts.extraction_schema(list(evidence), engine._max_concepts_per_chunk)
            source = {"normalization_version": page.normalization_version, "input_hash": page.content_hash,
                      "source_sha256": page.source_sha256, "language_hint": page.language,
                      "language_validated": False, "content_policy": contracts.POLICY,
                      "scope_ids": sorted({b.scope_id for b in blocks}), "evidence": evidence}
            history, feedback = [], None
            final_concepts, final_review, saturated = [], None, False
            for revision in range(engine._max_repair_attempts + 1):
                # Reserve initial extraction/audit calls for every planned packet
                # before spending remaining slots on a repair.
                if revision and request_ceiling - sum(attempt_counts.values()) < 2 * (len(jobs) - job_index) + 2:
                    break
                engine._progress(f"Structured group {job_index}/{len(jobs)}, revision {revision}: extraction and coverage review")
                revision_completion = None
                proposed, invalid, saturated = [], [], False
                stage = "extraction_input"
                try:
                    extraction_input = {"untrusted_source": source, "repair": feedback}
                    extraction_text = json.dumps(extraction_input, ensure_ascii=False)
                    extraction_limit = engine._chunk_content_characters * 4
                    if len(extraction_text) > extraction_limit:
                        original_characters = len(extraction_text)
                        extraction_text = json.dumps(extraction_input, ensure_ascii=False, separators=(",", ":"))
                        if len(extraction_text) > extraction_limit:
                            raise ValueError(
                                "extraction input exceeds bounded source/feedback allowance: "
                                f"{len(extraction_text)} characters after JSON whitespace compaction "
                                f"(from {original_characters}) > {extraction_limit}")
                        engine._progress(
                            f"Structured group {job_index}, revision {revision}: compacted extraction JSON "
                            f"whitespace from {original_characters} to {len(extraction_text)} characters "
                            f"(limit={extraction_limit}); source and feedback unchanged")
                    attempt_counts["repair" if revision else "generation"] += 1
                    stage = "extraction"
                    completion = engine._provider.generate_structured(system_prompt=engine.prompts.extraction.text,
                        user_prompt=extraction_text,
                        response_schema=schema)
                    completions.append(completion)
                    revision_completion = completion
                    stage = "extraction_validation"
                    raw = contracts.decode(completion.content, schema)
                    proposed = raw["concepts"]
                    saturated = raw["saturated"] or len(proposed) == engine._max_concepts_per_chunk
                    valid, invalid, identities = [], [], set()
                    for index, concept in enumerate(proposed):
                        errors = []
                        try:
                            contracts.validate_concept(concept, evidence, {b.section_id: b.scope_id for b in blocks})
                        except ValueError as exc:
                            errors = getattr(exc, "errors", [{"path": "concept", "reason": str(exc)}])
                        identity = _hash(concept)
                        if identity in identities:
                            errors.append({"path": "concept", "reason": "duplicate proposal"})
                        identities.add(identity)
                        if errors:
                            invalid.append({"proposal_index": index, "reason": errors[0]["reason"],
                                            "errors": errors, "proposal": concept})
                            for error in errors:
                                engine._progress(f"Structured proposal {index} rejected at {error['path']}: {error['reason']}")
                        else:
                            valid.append(concept)
                    repair_available = (revision < engine._max_repair_attempts and
                        request_ceiling - sum(attempt_counts.values()) >= 2 * (len(jobs) - job_index) + 2)
                    if invalid and (repair_available or not valid):
                        # Repair a malformed packet before paying to review it.
                        # A genuinely empty extraction has no rejections and still
                        # needs a source coverage audit. With no repair left, a
                        # mixed packet may still audit its valid proposals below.
                        reason = "repairing structural errors" if repair_available else "no structurally valid proposals"
                        record = {"revision": revision, "failure_stage": "structural_validation",
                                  "error": f"{len(invalid)} proposal(s) failed structural validation",
                                  "proposals": proposed, "structural_rejections": invalid,
                                  "saturated": saturated, "review_skipped": reason}
                        history.append(record)
                        final_concepts, final_review = [], None
                        feedback = _repair_feedback(record)
                        message = f"Structured group {job_index}, revision {revision}: semantic review skipped; {reason}"
                        engine._progress(message)
                        warnings.append(message)
                        if repair_available:
                            continue
                        break
                    stage = "review_input"
                    review_input = {"untrusted_source": source,
                                    "concepts": [dict(c, rendered_description=contracts.describe(c)) for c in valid]}
                    if feedback and feedback.get("failure_stage") == "review_validation":
                        # The extractor also receives repair feedback, but cannot
                        # fix the reviewer's JSON. Give the next reviewer its own
                        # bounded diagnostic; do not reuse an identical review request.
                        error = feedback["validation_error"]
                        review_input["review_validation_feedback"] = {
                            "previous_revision": feedback["revision"],
                            "validation_error": error[:2000],
                            "validation_error_truncated": len(error) > 2000,
                        }
                    # Bound the complete review payload independently of source packing.
                    # This includes proposals, rendered descriptions and validation feedback.
                    review_text = json.dumps(review_input, ensure_ascii=False)
                    if len(review_text) > engine._max_review_input_characters:
                        raise ValueError(
                            "review input exceeds bounded source/proposal allowance: "
                            f"{len(review_text)} characters > "
                            f"max_review_input_characters={engine._max_review_input_characters}")
                    attempt_counts["review"] += 1
                    stage = "review"
                    review_completion = engine._provider.generate_structured(system_prompt=engine.prompts.review.text,
                        user_prompt=review_text, response_schema=contracts.review_schema(valid, block_ids))
                    completions.append(review_completion)
                    revision_completion = review_completion
                    stage = "review_validation"
                    normalizations = []
                    audit = contracts.parse_review(review_completion.content, valid, block_ids,
                                                   normalizations=normalizations)
                    for coverage in audit["block_coverage"]:
                        if coverage["decision"] in {"covered", "partial"}:
                            for index in coverage["concept_indices"]:
                                if not any(evidence[ref]["section_id"] == coverage["section_id"]
                                           for ref in contracts.evidence_references(valid[index])):
                                    raise ValueError("coverage reference is not supported by a citation to that block")
                    record = {"revision": revision, "proposals": proposed,
                              "structural_rejections": invalid, "review": audit, "saturated": saturated}
                    if normalizations:
                        record.update(review_normalizations=normalizations, raw_completion=review_completion.content)
                        engine._progress(f"Structured group {job_index}, revision {revision}: normalized "
                                         f"{len(normalizations)} misplaced scope_fields object(s); "
                                         "all review assessments retained and validated")
                    history.append(record)
                    final_concepts, final_review = valid, audit
                    repair_needed = invalid or saturated or any(not contracts.review_passes(r) for r in audit["concept_reviews"]) or any(
                        r["decision"] in {"missing", "partial", "uncertain"} for r in audit["block_coverage"])
                    if not repair_needed:
                        break
                    feedback = _repair_feedback(history[-1])
                except ValueError as exc:
                    discard = getattr(engine._provider, "discard_last_checkpoint", None)
                    if (discard is not None and revision_completion is not None
                            and stage in {"extraction_validation", "review_validation"}):
                        discard()
                    # A malformed or truncated response remains a visible failed revision.
                    history.append({"revision": revision, "error": str(exc),
                                    "failure_stage": stage, "proposals": proposed,
                                    "structural_rejections": invalid, "saturated": saturated,
                                    "raw_completion": revision_completion.content if revision_completion else None})
                    final_concepts, final_review = [], None
                    # A review failure must not mask errors in the proposals it
                    # could not review. Include each proposal once; raw review
                    # text stays in history, outside the bounded repair payload.
                    feedback = _repair_feedback(history[-1])
                    if stage == "extraction_validation" and revision_completion is not None and not proposed:
                        # A schema-invalid response never became a proposal, but
                        # the repair still needs to see what it must correct.
                        feedback["invalid_completion"] = revision_completion.content[:6000]
                        feedback["invalid_completion_truncated"] = len(revision_completion.content) > 6000
                    message = f"Structured group {job_index}, revision {revision}: {stage} failed: {exc}"
                    warnings.append(message)
                    engine._progress(message)
                except SemanticModelError as exc:
                    history.append({"revision": revision, "provider_error": str(exc),
                                    "failure_stage": stage, "proposals": proposed,
                                    "structural_rejections": invalid, "saturated": saturated})
                    message = f"Structured group {job_index}, revision {revision}: {stage} provider failed: {exc}"
                    warnings.append(message)
                    engine._progress(message)
                    final_concepts, final_review = [], None
                    provider_failed = True
                    break
            reviews.append({"scope_ids": source["scope_ids"], "section_ids": block_ids, "history": history,
                            "review_contract_version": contracts.REVIEW_VERSION,
                            "decision": "recorded_for_human_review", "issue": "human_promotion_required"})
            if history:
                rejected.extend(dict(item, stage="structural_validation")
                                for item in history[-1].get("structural_rejections", []))
            accepted_indices = {}
            if final_review is not None:
                for review in final_review["concept_reviews"]:
                    index = review["concept_index"]
                    concept = final_concepts[index]
                    if contracts.review_passes(review):
                        refs = sorted(set(contracts.evidence_references(concept)))
                        identity = _hash({"version": contracts.VERSION, "input_hash": page.content_hash, "concept": concept})
                        candidate = CandidateConcept(
                            candidate_id=f"candidate-{identity[:24]}", preferred_label=concept["label"],
                            alternative_labels=(), concept_type=concept["concept_type"], granularity="ANSWERABLE",
                            description=contracts.describe(concept),
                            scope=json.dumps([c["scope"] for c in concept["claims"]], ensure_ascii=False, sort_keys=True),
                            user_questions=tuple(concept["questions"]), confidence=0.0,
                            evidence=tuple(EvidenceSpan(evidence[r]["section_id"], evidence[r]["text"], evidence[r]["start"], evidence[r]["end"]) for r in refs),
                            relations=(), primary_section_id=concept["primary_section_id"],
                            structured_claims=tuple(concept["claims"]), limitations=tuple(concept["limitations"]))
                        candidates.append(candidate)
                        accepted_indices[index] = candidate.candidate_id
                        queue.append({"candidate_id": candidate.candidate_id, "scope_id": by_block[concept["primary_section_id"]]["scope_id"],
                                      "reason": "new_or_changed_claim_requires_human_approval", "review": review,
                                      "revision_hash": identity, "publication_eligible": False})
                    else:
                        rejected.append({"stage": "structured_review", "reason": "one or more review dimensions failed",
                                         "proposal": concept, "review": review,
                                         "scope_id": by_block[concept["primary_section_id"]]["scope_id"]})
                for coverage in final_review["block_coverage"]:
                    retained = [accepted_indices[i] for i in coverage["concept_indices"] if i in accepted_indices]
                    status = coverage["decision"]
                    if coverage["concept_indices"] and len(retained) != len(coverage["concept_indices"]):
                        status = "rejected_or_partial"
                    if saturated:
                        status = "saturated_requires_review"
                    by_block[coverage["section_id"]].update(status=status, reason=coverage["reason"],
                        candidate_ids=retained, assessment_origin="model_assessment_not_verified_coverage")
            else:
                for block in blocks:
                    by_block[block.section_id].update(status="provider_failure" if provider_failed else "invalid_response",
                                                    reason="no valid final extraction and coverage audit")
        for row in inventory:
            if row["status"] not in {"excluded_policy", "covered"}:
                queue.append({"section_id": row["section_id"], "scope_id": row["scope_id"],
                              "reason": row["status"], "publication_eligible": False})
        if queue:
            warnings.append("Human review required; coverage assessments and model approvals do not publish knowledge.")
        first = completions[0] if completions else ModelCompletion("", "not_called", "not_called")
        if any((c.provider, c.model) != (first.provider, first.model) for c in completions):
            raise ConceptExtractionError("provider reported inconsistent identity across extraction/review")
        metrics = {"accepted_proposals": len(candidates), "rejected_proposals": len(rejected),
                   "retained_candidates": len(candidates), "review_request_count": attempt_counts["review"],
                   "generation_request_count": attempt_counts["generation"], "repair_request_count": attempt_counts["repair"],
                   "request_attempt_count": sum(attempt_counts.values()), "source_block_count": len(inventory),
                   "unresolved_block_count": sum(r["status"] not in {"covered", "excluded_policy"} for r in inventory),
                   "coverage_complete": False, "publication_eligible": False,
                   "confidence_interpretation": "not_scored; candidate_confidence_zero_is_not_a_probability",
                   "semantic_quality": "requires_human_review; model_coverage_is_not_verified_recall"}
        result_hash = _hash({"input_hash": page.content_hash, "candidates": [asdict(c) for c in candidates], "inventory": inventory,
                             "reviews": reviews, "policy": contracts.POLICY})
        return ConceptProposalReport(
            schema_version="swisstip.concept-proposal-report/v2", document_id=page.document_id,
            source=page.source, title=page.title, language=page.language, input_hash=page.content_hash,
            output_hash=result_hash, active_profile=engine._active_profile, provider=first.provider, model=first.model,
            operation="candidate_concept_extraction", prompt_profile=STRUCTURED_PROMPT_PROFILE,
            effective_prompts=engine.prompts.to_dict(),
            generated_at=engine._clock().astimezone(UTC).isoformat(), request_count=len(completions),
            prompt_tokens=engine._sum_optional(c.prompt_tokens for c in completions) if completions else 0,
            output_tokens=engine._sum_optional(c.output_tokens for c in completions) if completions else 0,
            request_ids=tuple(c.request_id for c in completions if c.request_id), candidates=tuple(candidates),
            warnings=tuple(warnings), rejected_candidates=tuple(rejected), quality_metrics=metrics,
            semantic_reviews=tuple(reviews), source_inventory=tuple(inventory), content_policy=contracts.POLICY,
            human_review_queue=tuple(queue), model_identities=tuple({k: getattr(c, k) for k in
                ("provider", "model", "requested_model", "observed_model", "request_id")} for c in completions),
            normalization_version=page.normalization_version, source_sha256=page.source_sha256,
            claim_contract_version=contracts.VERSION)
