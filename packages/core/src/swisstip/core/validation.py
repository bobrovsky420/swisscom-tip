"""Validate catalog integrity and structured inputs without resolving knowledge.

``READY`` means that an input can proceed to retrieval/rule execution. It never
asserts that evidence exists or that the requested operation is supported.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import ValidationError

from .contracts import (
    ArtifactRef, CatalogEntry, ContextCondition, ContextSchema, CoverageProfile,
    KnowledgeCatalog, LanguagePolicy, StructuredGroundingRequest,
)
from .identity import verify_artifact


SELECTABLE_STATES = {"CURATED", "VERIFIED_AUTOMATIC"}
SOURCE_LANGUAGES = {"en", "de-CH", "fr-CH", "it-CH", "rm-CH"}
TERM_PROJECTIONS = {
    "en": "en", "de": "de-CH", "de-DE": "de-CH", "de-CH": "de-CH",
    "fr-CH": "fr-CH", "it-CH": "it-CH", "rm-CH": "rm-CH",
    "gsw": "de-CH", "gsw-CH": "de-CH",
}
TERM_ALIASES = {"de": "de-CH", "de-DE": "de-CH", "gsw": "gsw-CH"}


@dataclass(frozen=True)
class ValidationIssue:
    field: str
    reason: str
    message: str
    supported_values: tuple[Any, ...] = ()


@dataclass(frozen=True)
class MissingContext:
    field: str
    reason_code: str
    allowed_values: tuple[Any, ...]
    schema_ref: ArtifactRef
    rule_refs: tuple[ArtifactRef, ...] = ()
    evidence_refs: tuple[ArtifactRef, ...] = ()


@dataclass(frozen=True)
class ValidatedTermRoute:
    input_index: int
    original_text: str
    requested_language: str
    effective_term_language: str
    projection_language: str
    source_languages: tuple[str, ...]


@dataclass(frozen=True)
class ValidationAssessment:
    status: str
    request: StructuredGroundingRequest | None = None
    issues: tuple[ValidationIssue, ...] = ()
    missing_context: tuple[MissingContext, ...] = ()
    coverage_profile_ids: tuple[str, ...] = ()
    executed_concept_ids: tuple[str, ...] = ()
    effective_source_languages: tuple[str, ...] | None = None
    term_routes: tuple[ValidatedTermRoute, ...] = ()
    active_release_id: str | None = None


class CatalogIntegrityError(ValueError):
    """A catalog must be repaired before accepting requests against it."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        self.issues = issues
        super().__init__("; ".join(f"{issue.field}: {issue.message}" for issue in issues))


def _ancestors(entry_id: str, entries: Mapping[str, CatalogEntry]) -> set[str]:
    seen: set[str] = set()
    pending = list(entries[entry_id].parent_ids)
    while pending:
        parent = pending.pop()
        if parent in seen or parent not in entries:
            continue
        seen.add(parent)
        pending.extend(entries[parent].parent_ids)
    return seen


def validate_catalog(
    catalog: KnowledgeCatalog,
    language_policy: LanguagePolicy,
    *,
    artifacts: Mapping[str, ArtifactRef] | None = None,
) -> tuple[ValidationIssue, ...]:
    """Check cross-record integrity; an optional registry checks external refs.

    The registry maps artifact IDs to exact ArtifactRef values. Omitting it
    leaves external rule/evidence/provenance existence for the release builder;
    inline catalog, context-schema and language-policy references are always
    checked. Draft catalogs may contain candidate concepts and draft profiles.
    """
    issues: list[ValidationIssue] = []

    def issue(path: str, reason: str, message: str) -> None:
        issues.append(ValidationIssue(path, reason, message))

    def unique(items: Any, attribute: str, path: str) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for index, item in enumerate(items):
            key = getattr(item, attribute)
            if key in result:
                issue(f"{path}.{index}", "duplicate_id", f"Duplicate identifier {key}.")
            result[key] = item
        return result

    entries = unique(catalog.entries, "entry_id", "entries")
    profiles = unique(catalog.coverage_profiles, "coverage_profile_id", "coverage_profiles")
    schemas: dict[str, Any] = {}
    for path, artifact in [("identity", catalog), ("language_policy.identity", language_policy)]:
        if not verify_artifact(artifact):
            issue(path, "content_hash_mismatch", "Declared identity does not match canonical artifact content.")
    for index, schema in enumerate(catalog.context_schemas):
        key = schema.identity.artifact_id
        if key in schemas:
            issue(f"context_schemas.{index}", "duplicate_id", f"Duplicate schema {key}.")
        schemas[key] = schema
        if not verify_artifact(schema):
            issue(f"context_schemas.{index}.identity", "content_hash_mismatch", "Declared schema identity does not match its content.")
        fields = {item.name: item for item in schema.fields}
        for spec in schema.fields:
            for value in spec.enum or ():
                errors, _ = _validate_context({spec.name: value}, schema)
                if errors:
                    issue(f"context_schemas.{index}.fields.{spec.name}.enum", "invalid_context_schema", "Enum value does not satisfy its declared field type and bounds.")
        for requirement in schema.conditional_requirements:
            for condition in requirement.when:
                for value in condition.values:
                    errors, _ = _validate_context({condition.field: value}, schema)
                    if errors:
                        issue(f"context_schemas.{index}.conditional_requirements", "invalid_context_schema", "Condition value does not satisfy its declared field type and allowed values.")
        for rule in schema.consistency_rules:
            left_kind, right_kind = fields[rule.left_field].kind, fields[rule.right_field].kind
            if left_kind != right_kind and {left_kind, right_kind} != {"integer", "number"}:
                issue(f"context_schemas.{index}.consistency_rules", "invalid_context_schema", "Compared fields require compatible types.")
    if catalog.language_policy_ref != language_policy.identity:
        issue("language_policy_ref", "artifact_mismatch", "Language policy identity does not match.")
    allowed_parents = {
        "knowledge_space": set(), "domain": {"knowledge_space"},
        "topic": {"domain", "topic"}, "concept": {"topic", "concept"},
    }
    for entry_id, entry in entries.items():
        path = f"entries.{entry_id}.parent_ids"
        if len(set(entry.parent_ids)) != len(entry.parent_ids):
            issue(path, "duplicate_parent", "Parent identifiers must be unique.")
        if entry.kind == "knowledge_space" and entry.parent_ids:
            issue(path, "invalid_hierarchy", "Knowledge spaces are roots.")
        if entry.kind != "knowledge_space" and not entry.parent_ids:
            issue(path, "invalid_hierarchy", "Non-root entries require a parent.")
        for replacement in entry.replacement_ids:
            if replacement not in entries or replacement == entry_id:
                issue(f"entries.{entry_id}.replacement_ids", "unknown_id", "Replacement must reference another catalog entry.")
        for parent in entry.parent_ids:
            if parent not in entries:
                issue(path, "unknown_id", f"Unknown parent {parent}.")
            elif entries[parent].kind not in allowed_parents[entry.kind]:
                issue(path, "invalid_hierarchy", "Parent type is inconsistent with child type.")
        ancestors = _ancestors(entry_id, entries)
        if entry_id in ancestors:
            issue(path, "parent_cycle", "Parent hierarchy must be acyclic.")
        for kind in ("knowledge_space", "domain"):
            if entry.kind != kind and len([item for item in ancestors if entries[item].kind == kind]) > 1:
                issue(path, "invalid_hierarchy", f"Entry crosses {kind} boundaries.")
    for profile_id, profile in profiles.items():
        path = f"coverage_profiles.{profile_id}"
        if profile.release_id != catalog.release_id or profile.catalog_ref != catalog.identity:
            issue(path, "artifact_mismatch", "Profile must reference this exact catalog and release.")
        for name in ("concept_ids", "source_ids", "source_languages", "scope_modes", "projection_languages_complete"):
            if len(set(getattr(profile, name))) != len(getattr(profile, name)):
                issue(path + "." + name, "duplicate_value", "Profile declarations must be unique.")
        if profile.approval_status == "APPROVED" and profile.evaluation_ref is None:
            issue(path + ".evaluation_ref", "missing_evaluation", "Approved coverage requires an evaluation reference.")
        if not set(profile.projection_languages_complete) <= set(language_policy.projection_languages):
            issue(path + ".projection_languages_complete", "language_policy", "Completed projections must belong to enabled policy languages.")
        scope = [(profile.knowledge_space_id, "knowledge_space"), (profile.domain_id, "domain"), (profile.topic_id, "topic")]
        for entry_id, kind in scope:
            if entry_id not in entries or entries[entry_id].kind != kind:
                issue(path, "unknown_id", f"Unknown {kind} identifier {entry_id}.")
        if all(entry_id in entries for entry_id, _ in scope):
            if profile.knowledge_space_id not in _ancestors(profile.domain_id, entries) or profile.domain_id not in _ancestors(profile.topic_id, entries):
                issue(path, "invalid_hierarchy", "Profile selectors do not share their declared hierarchy.")
        for concept_id in profile.concept_ids:
            if concept_id not in entries or entries[concept_id].kind != "concept":
                issue(path, "unknown_id", f"Unknown concept {concept_id}.")
            elif profile.topic_id not in _ancestors(concept_id, entries):
                issue(path, "invalid_hierarchy", "Profile concept is outside its topic.")
            elif profile.approval_status == "APPROVED" and entries[concept_id].lifecycle not in SELECTABLE_STATES:
                issue(path, "unreviewed_coverage", "Only curated or verified concepts may support approved coverage.")
        schema = schemas.get(profile.context_schema_ref.artifact_id)
        if schema is None or schema.identity != profile.context_schema_ref:
            issue(path + ".context_schema_ref", "artifact_mismatch", "Profile must reference an inline context schema exactly.")
        if not set(profile.source_languages) <= set(language_policy.source_languages):
            issue(path + ".source_languages", "language_policy", "Profile sources must be enabled by the policy.")
        if profile.approval_status == "APPROVED" and language_policy.approval_status != "APPROVED":
            issue(path, "unreviewed_policy", "Approved coverage requires an approved language policy.")
        policy_routes = {(route.term_language, route.projection_language) for route in language_policy.routes}
        evaluated_routes: set[tuple[str, str]] = set()
        for route in profile.term_routes:
            route_key = (route.term_language, route.projection_language)
            if route_key in evaluated_routes:
                issue(path + ".term_routes", "duplicate_route", "Evaluated routes must be unambiguous within a profile.")
            evaluated_routes.add(route_key)
            if (route.term_language, route.projection_language) not in policy_routes:
                issue(path + ".term_routes", "language_policy", "Evaluated route must match an enabled policy route.")
            policy_route = next((item for item in language_policy.routes if item.term_language == route.term_language), None)
            if policy_route is not None and (route.dialect_profile, route.idiom_profile) != (policy_route.dialect_profile, policy_route.idiom_profile):
                issue(path + ".term_routes", "language_policy", "Evaluated dialect and idiom forms must match their policy route.")
            if profile.approval_status == "APPROVED" and route.projection_language not in profile.projection_languages_complete:
                issue(path + ".term_routes", "incomplete_projection", "An evaluated route requires its declared projection to be complete.")
            if not set(route.source_languages) <= set(profile.source_languages):
                issue(path + ".term_routes", "language_policy", "Evaluated route sources must belong to the profile.")
    for role, enabled, allowed in (
        ("term_languages", language_policy.term_languages, set(TERM_PROJECTIONS)),
        ("source_languages", language_policy.source_languages, SOURCE_LANGUAGES),
        ("projection_languages", language_policy.projection_languages, SOURCE_LANGUAGES),
    ):
        if not set(enabled) <= allowed:
            issue("language_policy." + role, "language_policy", "Enabled languages exceed the closed v2 role.")
        if len(set(enabled)) != len(enabled):
            issue("language_policy." + role, "duplicate_value", "Enabled language declarations must be unique.")
    if language_policy.approval_status == "APPROVED" and language_policy.evaluation_ref is None:
        issue("language_policy.evaluation_ref", "missing_evaluation", "Approved policy requires an evaluation reference.")
    if language_policy.source_declaration_aliases:
        issue("language_policy.source_declaration_aliases", "language_policy", "V2 has no source-declaration aliases.")
    for alias, target in language_policy.term_aliases.items():
        if TERM_ALIASES.get(alias) != target or target not in language_policy.term_languages:
            issue("language_policy.term_aliases", "language_policy", "Alias must be approved by v2 and target an enabled profile.")
    for target in language_policy.source_detector_mappings.values():
        if target not in language_policy.source_languages:
            issue("language_policy.source_detector_mappings", "language_policy", "Detector mapping targets a disabled source language.")
    routed: set[str] = set()
    for route in language_policy.routes:
        if route.term_language in routed:
            issue("language_policy.routes", "duplicate_route", "Each term profile has exactly one projection route.")
        routed.add(route.term_language)
        if route.term_language not in language_policy.term_languages or route.projection_language not in language_policy.projection_languages or TERM_PROJECTIONS.get(route.term_language) != route.projection_language:
            issue("language_policy.routes", "language_policy", "Route must connect enabled roles through the v2 projection.")
        if route.term_language in {"gsw", "gsw-CH"} and not route.dialect_profile:
            issue("language_policy.routes", "missing_language_profile", "Swiss German routes require a declared dialect profile.")
        if route.term_language == "rm-CH" and not route.idiom_profile:
            issue("language_policy.routes", "missing_language_profile", "Romansh routes require a declared idiom profile.")
    if set(language_policy.term_languages) != routed:
        issue("language_policy.routes", "language_policy", "Every enabled term profile requires a route.")
    if artifacts is not None:
        registry = dict(artifacts)
        for value in [catalog.identity, language_policy.identity, *(schema.identity for schema in schemas.values())]:
            if value.artifact_id in registry and registry[value.artifact_id] != value:
                issue("artifacts." + value.artifact_id, "artifact_mismatch", "Inline identity conflicts with the artifact registry.")
            registry[value.artifact_id] = value

        def check_refs(value: Any, path: str) -> None:
            if hasattr(value, "artifact_id") and hasattr(value, "sha256"):
                if registry.get(value.artifact_id) != value:
                    issue(path, "artifact_mismatch", f"Unregistered or mismatched artifact {value.artifact_id}.")
            elif hasattr(type(value), "model_fields"):
                for name in type(value).model_fields:
                    check_refs(getattr(value, name), f"{path}.{name}")
            elif isinstance(value, Mapping):
                for key, child in value.items():
                    check_refs(child, f"{path}.{key}")
            elif isinstance(value, (list, tuple)):
                for index, child in enumerate(value):
                    check_refs(child, f"{path}.{index}")

        check_refs(catalog, "catalog")
        check_refs(language_policy, "language_policy")
    return tuple(issues)


def _scalar_equal(left: Any, right: Any) -> bool:
    # JSON numbers compare by value; booleans remain a separate scalar type.
    numeric = (int, float)
    return left == right and (
        type(left) is type(right) or (type(left) in numeric and type(right) in numeric)
    )


def _matches_condition(condition: ContextCondition, context: Mapping[str, Any]) -> bool:
    present = condition.field in context
    if condition.operator == "present":
        return present
    if condition.operator == "absent":
        return not present
    if not present:
        return False
    value = context[condition.field]
    matches = any(_scalar_equal(value, item) for item in condition.values)
    return not matches if condition.operator in {"not_equals", "not_in"} else matches


def _validate_context(
    context: Mapping[str, Any], schema: ContextSchema,
) -> tuple[list[ValidationIssue], list[MissingContext]]:
    issues: list[ValidationIssue] = []
    missing: list[MissingContext] = []
    fields = {item.name: item for item in schema.fields}
    for name, value in context.items():
        path = "context." + name
        spec = fields.get(name)
        if spec is None:
            issues.append(ValidationIssue(path, "unknown_field", "Context field is not declared by this schema."))
            continue
        valid = {
            "string": type(value) is str, "identifier": type(value) is str,
            "integer": type(value) is int, "number": type(value) in (int, float),
            "boolean": type(value) is bool, "date": type(value) is str,
        }[spec.kind]
        if valid and spec.kind == "date":
            try:
                valid = date.fromisoformat(value).isoformat() == value
            except ValueError:
                valid = False
        if valid and spec.kind == "identifier":
            valid = re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", value) is not None and len(value) <= 80
        if not valid:
            issues.append(ValidationIssue(path, "invalid_type", f"Expected {spec.kind}."))
            continue
        if spec.enum and not any(_scalar_equal(value, item) for item in spec.enum):
            issues.append(ValidationIssue(path, "invalid_value", "Value is outside the declared enum.", tuple(spec.enum)))
        if type(value) in (int, float) and ((spec.minimum is not None and value < spec.minimum) or (spec.maximum is not None and value > spec.maximum)):
            issues.append(ValidationIssue(path, "invalid_value", "Value is outside the declared numeric bounds."))
        if type(value) is str and ((spec.min_length is not None and len(value) < spec.min_length) or (spec.max_length is not None and len(value) > spec.max_length)):
            issues.append(ValidationIssue(path, "invalid_value", "Value is outside the declared text bounds."))
    if issues:
        return issues, missing
    for rule in schema.consistency_rules:
        if rule.left_field not in context or rule.right_field not in context:
            continue
        left, right = context[rule.left_field], context[rule.right_field]
        try:
            valid = {
                "equals": lambda: left == right, "not_equals": lambda: left != right,
                "lt": lambda: left < right, "lte": lambda: left <= right,
                "gt": lambda: left > right, "gte": lambda: left >= right,
            }[rule.operator]()
        except TypeError:
            valid = False
        if not valid:
            issues.append(ValidationIssue("context." + rule.left_field, rule.reason_code, "Context fails a declared consistency rule."))
    for spec in schema.fields:
        if spec.required and spec.name not in context:
            missing.append(MissingContext("context." + spec.name, spec.reason_code, tuple(spec.enum or ()), schema.identity))
    for requirement in schema.conditional_requirements:
        if all(_matches_condition(condition, context) for condition in requirement.when):
            for name in requirement.required_fields:
                if name not in context:
                    missing.append(MissingContext("context." + name, requirement.reason_code, tuple(fields[name].enum or ()), schema.identity, tuple(requirement.rule_refs), tuple(requirement.evidence_refs)))
    unique_missing: dict[str, MissingContext] = {}
    for item in missing:
        previous = unique_missing.get(item.field)
        if previous is None:
            unique_missing[item.field] = item
        else:
            unique_missing[item.field] = MissingContext(item.field, previous.reason_code, previous.allowed_values, previous.schema_ref, tuple(dict.fromkeys((*previous.rule_refs, *item.rule_refs))), tuple(dict.fromkeys((*previous.evidence_refs, *item.evidence_refs))))
    return issues, list(unique_missing.values())


def validate_request(
    payload: Mapping[str, Any] | StructuredGroundingRequest,
    catalog: KnowledgeCatalog,
    language_policy: LanguagePolicy,
    *,
    active_release_id: str | None = None,
) -> ValidationAssessment:
    """Assess an input against one exact release's reviewed catalog and policy.

    A single evaluated profile must cover the entire requested combination;
    independent profiles are never combined to manufacture coverage. The input
    and returned concept/source boundaries are retained for later execution.
    """
    try:
        request = StructuredGroundingRequest.model_validate(
            payload.model_dump(exclude_unset=True)
            if isinstance(payload, StructuredGroundingRequest) else payload
        )
    except (ValidationError, TypeError, ValueError) as exc:
        if isinstance(exc, ValidationError):
            issues = tuple(ValidationIssue(".".join(str(part) for part in item["loc"]), item["type"], item["msg"]) for item in exc.errors(include_input=False))
        else:
            issues = (ValidationIssue("", "invalid_json", "Request must contain valid JSON values."),)
        return ValidationAssessment("INVALID_ARGUMENT", issues=issues)
    if request.release_id != catalog.release_id:
        return ValidationAssessment("RELEASE_UNAVAILABLE", request=request, active_release_id=active_release_id, issues=(ValidationIssue("release_id", "release_unavailable", "The requested release is not loaded; discover an available release."),))
    integrity = validate_catalog(catalog, language_policy)
    if integrity:
        raise CatalogIntegrityError(integrity)
    entries = {entry.entry_id: entry for entry in catalog.entries}

    def result(status: str, path: str, reason: str, message: str, values: Any = (), **kwargs: Any) -> ValidationAssessment:
        return ValidationAssessment(status, request=request, issues=(ValidationIssue(path, reason, message, tuple(values)),), **kwargs)

    for entry_id, kind in [(request.knowledge_space_id, "knowledge_space"), (request.domain_id, "domain"), (request.topic_id, "topic"), *((item, "concept") for item in request.concept_ids or [])]:
        entry = entries.get(entry_id)
        if entry is None or entry.kind != kind or (kind == "concept" and entry.lifecycle not in SELECTABLE_STATES):
            return result("INVALID_ARGUMENT", "concept_ids" if kind == "concept" else kind + "_id", "unknown_id", "Identifier is not a current selectable entry of the required kind.")
    if request.knowledge_space_id not in _ancestors(request.domain_id, entries) or request.domain_id not in _ancestors(request.topic_id, entries) or any(request.topic_id not in _ancestors(item, entries) for item in request.concept_ids or []):
        return result("INVALID_ARGUMENT", "topic_id", "inconsistent_selectors", "Selectors must belong to the declared space, domain and topic.")
    published = [profile for profile in catalog.coverage_profiles if profile.approval_status == "APPROVED"]
    intents = sorted({profile.intent for profile in published})
    if request.intent not in intents:
        return result("INVALID_ARGUMENT", "intent", "unknown_intent", "Intent is not a published operation.", intents)
    scoped = [profile for profile in published if (profile.knowledge_space_id, profile.domain_id, profile.topic_id, profile.intent) == (request.knowledge_space_id, request.domain_id, request.topic_id, request.intent)]
    applicable = [profile for profile in scoped if profile.jurisdiction == request.jurisdiction and request.scope_mode in profile.scope_modes and profile.temporal_coverage.valid_from <= request.as_of and (profile.temporal_coverage.valid_through is None or request.as_of <= profile.temporal_coverage.valid_through)]
    if applicable and not request.concept_ids and all(profile.concept_selection_required for profile in applicable):
        return result("INVALID_ARGUMENT", "concept_ids", "missing_concept_selector", "This operation requires a concept selector.")
    if request.max_evidence is not None and request.max_evidence > catalog.max_evidence:
        if "max_evidence" in request.model_fields_set:
            return result("INVALID_ARGUMENT", "max_evidence", "evidence_limit", "Requested evidence exceeds the catalog limit.", [catalog.max_evidence])
        request = request.model_copy(update={"max_evidence": catalog.max_evidence})
    compatible = [profile for profile in applicable if (not profile.concept_selection_required or request.concept_ids) and set(request.concept_ids or ()) <= set(profile.concept_ids)]
    schemas = {schema.identity.artifact_id: schema for schema in catalog.context_schemas}
    context_checks = [(profile, *_validate_context(request.context, schemas[profile.context_schema_ref.artifact_id])) for profile in compatible]
    valid_context = [item for item in context_checks if not item[1]]
    if context_checks and not valid_context:
        return ValidationAssessment("INVALID_ARGUMENT", request=request, issues=tuple(context_checks[0][1]))
    matches = valid_context
    if not matches:
        return result("OUT_OF_COVERAGE", "scope", "unsupported_combination", "No evaluated profile covers this combination and date.")
    accepted_terms = set(language_policy.term_languages) | set(language_policy.term_aliases)
    for index, term in enumerate(request.retrieval_terms or []):
        if term.language not in accepted_terms:
            return result("UNSUPPORTED_LANGUAGE", f"retrieval_terms.{index}.language", "unsupported_term_language", "Term language is not enabled by this release.", sorted(accepted_terms))
    source_filter = tuple(dict.fromkeys(request.source_languages)) if request.source_languages is not None else None
    for index, language in enumerate(source_filter or ()):
        if language not in language_policy.source_languages:
            return result("UNSUPPORTED_LANGUAGE", f"source_languages.{index}", "unsupported_source_language", "Source filters require enabled exact source tags.", language_policy.source_languages, effective_source_languages=source_filter)
    matched_sources = [(profile, context_issues, missing, tuple(language for language in profile.source_languages if source_filter is None or language in source_filter)) for profile, context_issues, missing in matches]
    matched_sources = [item for item in matched_sources if item[3]]
    if not matched_sources:
        return result("OUT_OF_COVERAGE", "source_languages", "no_coverage_in_requested_source_languages", "No covered sources match the requested filter.", effective_source_languages=source_filter)
    eligible: list[tuple[CoverageProfile, list[MissingContext], list[ValidatedTermRoute]]] = []
    for profile, _, missing, sources in matched_sources:
        routes: list[ValidatedTermRoute] = []
        for index, term in enumerate(request.retrieval_terms or []):
            effective = language_policy.term_aliases.get(term.language, term.language)
            route = next((route for route in profile.term_routes if route.term_language == effective and set(sources) <= set(route.source_languages)), None)
            if route is None:
                break
            routes.append(ValidatedTermRoute(index, term.text, term.language, effective, route.projection_language, sources))
        else:
            eligible.append((profile, missing, routes))
    if not eligible:
        return result("OUT_OF_COVERAGE", "retrieval_terms", "unevaluated_language_combination", "Term/source/projection combination has not passed this profile's evaluation.", effective_source_languages=source_filter)
    if len(eligible) > 1:
        return result("OUT_OF_COVERAGE", "scope", "ambiguous_coverage_profiles", "Multiple evaluated profiles match; catalog configuration must disambiguate them.", sorted(item[0].coverage_profile_id for item in eligible), effective_source_languages=source_filter)
    profile, missing, routes = eligible[0]
    selected = set(request.concept_ids or ())
    if request.scope_mode == "descendants":
        frontier = selected or {request.topic_id}
        visited = set(frontier)
        for _ in range(profile.max_descendant_depth):
            children = {
                entry.entry_id for entry in entries.values()
                if entry.kind in {"topic", "concept"}
                and entry.lifecycle in SELECTABLE_STATES
                and set(entry.parent_ids) & frontier
                and request.topic_id in _ancestors(entry.entry_id, entries)
                and (entry.kind == "topic" or entry.entry_id in profile.concept_ids)
            }
            frontier = children - visited
            visited.update(children)
            selected.update(child for child in children if entries[child].kind == "concept")
    if len(selected) > profile.max_concepts:
        return result("INVALID_ARGUMENT", "scope_mode", "traversal_limit", "Selected or descendant scope exceeds the published concept limit.", [profile.max_concepts])
    if missing:
        return ValidationAssessment("NEEDS_CONTEXT", request=request, missing_context=tuple(missing), coverage_profile_ids=(profile.coverage_profile_id,), effective_source_languages=source_filter, term_routes=tuple(routes))
    return ValidationAssessment("READY", request=request, coverage_profile_ids=(profile.coverage_profile_id,), executed_concept_ids=tuple(sorted(selected)), effective_source_languages=source_filter, term_routes=tuple(routes))
