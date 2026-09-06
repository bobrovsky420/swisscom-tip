"""Bounded discovery and deterministic identifier/lexical fixture resolution."""

from __future__ import annotations

import base64
from datetime import datetime, timezone, timedelta
import hmac
import json
import re
import secrets
from collections.abc import Callable

from pydantic import ValidationError

from swisstip.core.contracts import (
    Freshness, GetCoverageRequest, GetCoverageResult, GetEvidenceRequest,
    GetEvidenceResult, MissingContextField, RetrievalTrace, ScopeSelection,
    StructuredGroundingRequest, StructuredGroundingResult, TermRoute, ToolError,
    TrustEnvelope, UnresolvedPortion, ValidationIssue,
)
from swisstip.core.validation import matches_condition, validate_request

from .release import ReleaseStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeService:
    def __init__(self, store: ReleaseStore, *, cursor_key: bytes | None = None,
                 clock: Callable[[], datetime] = _now):
        self.store = store
        self._cursor_key = cursor_key if cursor_key is not None else secrets.token_bytes(32)
        if len(self._cursor_key) < 32:
            raise ValueError("cursor_key_requires_32_bytes")
        self._clock = clock

    def _error(self, code, path, reason, message, release_id=None):
        return ToolError(code=code, release_id=release_id,
                         active_release_id=self.store.active_release_id,
                         issues=[ValidationIssue(path=path, reason_code=reason, message=message)])

    def _parse(self, model, payload):
        try:
            return model.model_validate(payload.model_dump(exclude_unset=True)
                                        if isinstance(payload, model) else payload)
        except (ValidationError, ValueError, TypeError) as exc:
            if isinstance(exc, ValidationError):
                issues = [ValidationIssue(
                    path=(".".join(map(str, e["loc"])) or "request")[:500], reason_code=e["type"],
                    message=e["msg"][:500],
                ) for e in exc.errors(include_input=False)[:100]]
                return ToolError(code="INVALID_ARGUMENT", issues=issues)
            return self._error("INVALID_ARGUMENT", "request", "invalid_request", "Expected a structured object.")

    def _load(self, identifier):
        return self.store.get(identifier) or self._error(
            "RELEASE_UNAVAILABLE", "release_id", "release_unavailable",
            "The pinned release is unavailable. Discover the active release explicitly.", identifier)

    def _cursor(self, binding, after):
        payload = json.dumps([binding, after], sort_keys=True, separators=(",", ":")).encode()
        signed = hmac.digest(self._cursor_key, payload, "sha256") + payload
        return base64.urlsafe_b64encode(signed).decode().rstrip("=")

    def _after(self, cursor, binding):
        raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        signature, payload = raw[:32], raw[32:]
        if not hmac.compare_digest(signature, hmac.digest(self._cursor_key, payload, "sha256")):
            raise ValueError("invalid_cursor_signature")
        previous, after = json.loads(payload)
        if previous != binding or not isinstance(after, str):
            raise ValueError("cursor_selector_mismatch")
        return after

    def get_coverage(self, payload) -> GetCoverageResult | ToolError:
        request = self._parse(GetCoverageRequest, payload)
        if isinstance(request, ToolError):
            return request
        bundle = self._load(request.release_id or self.store.active_release_id)
        if isinstance(bundle, ToolError):
            return bundle
        catalog = bundle.catalog
        entries = {e.entry_id: e for e in catalog.entries}
        limit = request.limit if "limit" in request.model_fields_set else catalog.discovery_default_limit
        if limit > catalog.discovery_max_limit:
            return self._error("INVALID_ARGUMENT", "limit", "discovery_limit", "Limit exceeds this catalog's maximum.", catalog.release_id)

        def ancestors(identifier):
            found, pending = set(), list(entries[identifier].parent_ids)
            while pending:
                current = pending.pop()
                if current not in found:
                    found.add(current)
                    pending.extend(entries[current].parent_ids)
            return found

        space = entries.get(request.knowledge_space_id)
        if request.knowledge_space_id and (space is None or space.kind != "knowledge_space"):
            return self._error("INVALID_ARGUMENT", "knowledge_space_id", "unknown_id", "Unknown Knowledge Space.", catalog.release_id)
        parent = entries.get(request.parent_id)
        if request.parent_id and parent is None:
            return self._error("INVALID_ARGUMENT", "parent_id", "unknown_id", "Unknown catalog parent.", catalog.release_id)
        if parent and space and space.entry_id not in {parent.entry_id, *ancestors(parent.entry_id)}:
            return self._error("INVALID_ARGUMENT", "parent_id", "inconsistent_selectors", "Parent is outside the selected space.", catalog.release_id)
        root = request.parent_id or request.knowledge_space_id
        children = sorted((e for e in entries.values() if
                           (root in e.parent_ids if root else e.kind == "knowledge_space")),
                          key=lambda e: e.entry_id)
        binding = [catalog.release_id, catalog.identity.sha256,
                   request.knowledge_space_id, request.parent_id, limit]
        if request.cursor:
            try:
                after = self._after(request.cursor, binding)
                if after not in {e.entry_id for e in children}:
                    raise ValueError("unknown_cursor_position")
            except (ValueError, TypeError, UnicodeError):
                return self._error("INVALID_ARGUMENT", "cursor", "invalid_cursor", "Cursor is invalid or belongs to different release selectors.", catalog.release_id)
            children = [e for e in children if e.entry_id > after]
        page = children[:limit]
        visible = {e.entry_id for e in page}
        if parent:
            visible.add(parent.entry_id)
        # Detail metadata accompanies topic/concept entries only. Root discovery
        # never dumps every operation in the release.
        profiles = sorted((p for p in catalog.coverage_profiles if
                           p.topic_id in visible or bool(set(p.concept_ids) & visible)),
                          key=lambda p: p.coverage_profile_id)
        if len(profiles) > 1000:
            return self._error("OPERATIONAL_ERROR", "coverage_profiles", "discovery_metadata_limit", "Profile metadata exceeds the bounded response contract.", catalog.release_id)
        schema_refs = {p.context_schema_ref for p in profiles}
        return GetCoverageResult(
            release_id=catalog.release_id, release_ref=bundle.release.identity,
            catalog_ref=catalog.identity, language_policy_ref=bundle.language_policy.identity,
            knowledge_space_id=request.knowledge_space_id, parent=parent, entries=page,
            coverage_profiles=profiles,
            context_schemas=sorted((s for s in catalog.context_schemas if s.identity in schema_refs),
                                   key=lambda s: s.identity.artifact_id),
            next_cursor=self._cursor(binding, page[-1].entry_id) if len(children) > limit else None,
            default_limit=catalog.discovery_default_limit, maximum_limit=catalog.discovery_max_limit)

    def get_evidence(self, payload) -> GetEvidenceResult | ToolError:
        request = self._parse(GetEvidenceRequest, payload)
        if isinstance(request, ToolError):
            return request
        bundle = self._load(request.release_id)
        if isinstance(bundle, ToolError):
            return bundle
        evidence = {e.evidence_id: e for e in bundle.evidence}
        if any(identifier not in evidence for identifier in request.evidence_ids):
            return self._error("INVALID_ARGUMENT", "evidence_ids", "unknown_evidence_id", "Evidence reference does not belong to this release.", request.release_id)
        if len(request.evidence_ids) > bundle.catalog.max_evidence:
            return self._error("INVALID_ARGUMENT", "evidence_ids", "evidence_limit", "Evidence count exceeds the catalog limit.", request.release_id)
        return GetEvidenceResult(release_id=request.release_id, release_ref=bundle.release.identity,
                                 evidence=[evidence[i] for i in request.evidence_ids])

    def resolve(self, payload) -> StructuredGroundingResult | ToolError:
        request = self._parse(StructuredGroundingRequest, payload)
        if isinstance(request, ToolError):
            return request
        bundle = self._load(request.release_id)
        if isinstance(bundle, ToolError):
            return bundle
        catalog, release = bundle.catalog, bundle.release
        assessment = validate_request(request, catalog, bundle.language_policy,
                                      active_release_id=self.store.active_release_id)
        if assessment.status in {"INVALID_ARGUMENT", "UNSUPPORTED_LANGUAGE", "RELEASE_UNAVAILABLE"}:
            return ToolError(code=assessment.status, release_id=request.release_id,
                             active_release_id=self.store.active_release_id,
                             issues=[ValidationIssue(path=i.field or "request", reason_code=i.reason,
                                                     message=i.message, allowed_values=list(i.supported_values)[:100])
                                     for i in assessment.issues[:100]])
        request = assessment.request
        now = self._clock().astimezone(timezone.utc)
        checked_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        scope = ScopeSelection.model_validate({k: getattr(request, k) for k in ScopeSelection.model_fields})
        profile = next((p for p in catalog.coverage_profiles
                        if p.coverage_profile_id in assessment.coverage_profile_ids), None)
        missing = [MissingContextField(path=m.field, reason_code=m.reason_code,
                                       schema_ref=m.schema_ref, allowed_values=list(m.allowed_values),
                                       rule_refs=list(m.rule_refs), evidence_refs=list(m.evidence_refs))
                   for m in assessment.missing_context]
        result = dict(
            release_id=request.release_id, release_ref=release.identity, catalog_ref=catalog.identity,
            requested_scope=scope, executed_scope=None, coverage_profile_ids=list(assessment.coverage_profile_ids),
            status=assessment.status if assessment.status != "READY" else "INSUFFICIENT_VERIFIED_EVIDENCE",
            supported_portions=[], unresolved_portions=[], evidence=[], missing_context=missing,
            freshness=Freshness(status="UNKNOWN", checked_at=checked_at,
                                policy_ref=profile.freshness_policy.policy_ref if profile else release.evaluation_ref),
            trust=TrustEnvelope(source_authorities=[], evaluation_ref=profile.evaluation_ref if profile else release.evaluation_ref,
                                fact_support="NONE", limitations=[]), trace=None)
        if assessment.status != "READY":
            result["unresolved_portions"] = [UnresolvedPortion(concept_ids=request.concept_ids,
                                                              reason_code=i.reason, limitation=i.message)
                                             for i in assessment.issues[:50]]
            return StructuredGroundingResult(**result)

        selected = set(assessment.executed_concept_ids)
        # An exact topic operation covers only direct concepts; descendant depth
        # remains the validator's responsibility and is never widened by terms.
        if not request.concept_ids and request.scope_mode == "exact":
            selected = {e.entry_id for e in catalog.entries if e.kind == "concept"
                        and request.topic_id in e.parent_ids and e.entry_id in profile.concept_ids}
        if len(selected) > profile.max_concepts:
            return self._error("INVALID_ARGUMENT", "scope_mode", "traversal_limit", "Topic scope exceeds the published concept limit.", request.release_id)
        result["executed_scope"] = scope.model_copy(update={"concept_ids": sorted(selected)})
        plan = next(p for p in bundle.graph.plans if p.coverage_profile_id == profile.coverage_profile_id)
        portions = [p for p in plan.portions if
                    (bool(set(p.concept_ids) & selected) if p.concept_ids else not request.concept_ids)]
        facts = {f.fact_id: f for f in bundle.facts}
        rules = {r.identity: r for r in bundle.rules}
        schema = next(s for s in catalog.context_schemas if s.identity == profile.context_schema_ref)
        required: dict[str, set[str]] = {}
        active_rules = set()
        for portion in portions:
            required[portion.portion_id] = set(portion.fact_ids)
            for ref in portion.rule_refs:
                rule = rules[ref]
                absent = {c.field for c in rule.when if c.field not in request.context
                          and c.operator not in {"present", "absent"}}
                for name in sorted(absent):
                    spec = next(f for f in schema.fields if f.name == name)
                    missing.append(MissingContextField(path="context." + name, reason_code=spec.reason_code,
                                                       schema_ref=schema.identity, allowed_values=spec.enum or [],
                                                       rule_refs=[ref]))
                if not absent and all(matches_condition(c, request.context) for c in rule.when):
                    active_rules.add(ref)
                    required[portion.portion_id].update(rule.fact_ids)
        if missing:
            merged = {}
            for field in missing:
                if field.path in merged:
                    merged[field.path].rule_refs = list(dict.fromkeys(merged[field.path].rule_refs + field.rule_refs))
                else:
                    merged[field.path] = field
            result.update(status="NEEDS_CONTEXT", missing_context=list(merged.values()), executed_scope=None)
            return StructuredGroundingResult(**result)

        sources = set(assessment.effective_source_languages or profile.source_languages) & set(profile.source_languages)
        wanted = set().union(*required.values()) if required else set()

        def eligible(item, *, federal_rule=False):
            place = item.jurisdiction == request.jurisdiction
            if federal_rule:
                place |= (item.jurisdiction.country_code == request.jurisdiction.country_code
                          and item.jurisdiction.canton_code is None)
            return (place and item.citation.source_id in profile.source_ids
                    and item.effective_source_language in sources
                    and bool(set(item.canonical_concept_ids) & selected)
                    and item.temporal_coverage.valid_from <= request.as_of
                    and (item.temporal_coverage.valid_through is None
                         or request.as_of <= item.temporal_coverage.valid_through))

        evidence = {e.evidence_id: e for e in bundle.evidence}
        eligible_facts = {identifier for identifier in wanted
                          if set(facts[identifier].rule_refs) <= active_rules
                          and all(eligible(evidence[e], federal_rule=bool(facts[identifier].rule_refs))
                                  for e in facts[identifier].evidence_ids)}
        excerpt_ids = {e for portion in portions for e in portion.evidence_ids}
        candidates = {e: evidence[e] for e in excerpt_ids if eligible(evidence[e])}
        for identifier in eligible_facts:
            for e in facts[identifier].evidence_ids:
                candidates[e] = evidence[e]
        terms = {token for term in request.retrieval_terms for token in re.findall(r"\w+", term.text.casefold())}

        def score(item):
            return len(terms & set(re.findall(r"\w+", item.original_excerpt.casefold())))

        cap = min(request.max_evidence, catalog.max_evidence)
        chosen, supported = {}, []
        ordered = sorted(eligible_facts, key=lambda f: (-sum(score(evidence[e]) for e in facts[f].evidence_ids), f))
        for identifier in ordered:
            fact = facts[identifier]
            if len(set(chosen) | set(fact.evidence_ids)) <= cap and len(supported) < 50:
                chosen.update((e, evidence[e]) for e in fact.evidence_ids)
                supported.append(fact)
        for item in sorted(candidates.values(), key=lambda e: (-score(e), e.evidence_id)):
            if len(chosen) < cap:
                chosen[item.evidence_id] = item
        supported_ids = {f.fact_id for f in supported}
        unresolved = []
        covered_concepts = set().union(*(set(p.concept_ids) for p in portions)) if portions else set()
        if not portions or selected - covered_concepts and not any(not p.concept_ids for p in portions):
            unresolved.append(UnresolvedPortion(concept_ids=sorted(selected - covered_concepts),
                                               reason_code="missing_published_portion",
                                               limitation="No published operation portion covers the selected scope."))
        for portion in portions:
            expected = required[portion.portion_id]
            if not expected or not expected <= supported_ids:
                unresolved.append(UnresolvedPortion(concept_ids=sorted(set(portion.concept_ids) & selected),
                                                   reason_code="insufficient_verified_evidence",
                                                   limitation="Published support is absent, inapplicable or exceeds the evidence budget."))
        conflict = any(len(set(c.fact_ids) & eligible_facts) > 1 for c in bundle.graph.conflicts)
        if conflict:
            unresolved = [UnresolvedPortion(concept_ids=sorted(selected), reason_code="published_conflict",
                                            limitation="The release records conflicting applicable facts.")] + unresolved
        oldest = min((e.citation.accessed_at for e in chosen.values()), default=None)
        stale = oldest is not None and now > datetime.fromisoformat(oldest.replace("Z", "+00:00")) + timedelta(days=profile.freshness_policy.max_age_days)
        status = ("CONFLICTING_EVIDENCE" if conflict else "STALE" if stale else
                  "PARTIALLY_SUPPORTED" if supported and unresolved else "SUPPORTED" if supported else
                  "INSUFFICIENT_VERIFIED_EVIDENCE")
        trace_routes = []
        for route in assessment.term_routes:
            published = next(r for r in profile.term_routes if r.term_language == route.effective_term_language)
            trace_routes.append(TermRoute(
                input_index=route.input_index, original_text=route.original_text,
                requested_language=route.requested_language, effective_term_language=route.effective_term_language,
                projection_language=route.projection_language, source_languages=list(route.source_languages),
                terminology_refs=published.terminology_refs, language_policy_ref=bundle.language_policy.identity,
                evaluation_ref=published.evaluation_ref))
        result.update(
            status=status, supported_portions=supported, unresolved_portions=unresolved[:50], evidence=list(chosen.values()),
            freshness=Freshness(status="STALE" if stale else "FRESH" if oldest else "UNKNOWN",
                                checked_at=checked_at, oldest_source_at=oldest, policy_ref=profile.freshness_policy.policy_ref),
            trust=TrustEnvelope(source_authorities=sorted({e.citation.authority for e in chosen.values()}),
                                evaluation_ref=profile.evaluation_ref,
                                fact_support="PUBLISHED_FACTS_OR_RULES" if supported else "EXCERPTS_ONLY" if chosen else "NONE",
                                limitations=["Identifier/lexical baseline; multilingual hybrid retrieval is not implemented.",
                                             *profile.exclusions][:30]),
            trace=RetrievalTrace(term_routes=trace_routes, effective_source_languages=sorted(sources),
                                 channels=["concept", "lexical"] if terms else ["concept"],
                                 index_refs=release.index_refs[:20], provider_configuration_ref=release.provider_configuration_ref,
                                 ranking_configuration_ref=release.ranking_configuration_ref,
                                 candidate_count=len(candidates), evidence_count=len(chosen)))
        return StructuredGroundingResult(**result)
