"""Strict, versioned wire contracts; these models do not publish or serve knowledge.

Context schemas intentionally support scalar fields only. Their closed vocabulary
is typed fields, enums, numeric/string bounds, all-of conditional requirements,
and pairwise comparisons. They are not arbitrary executable JSON Schema.
"""

from __future__ import annotations

from datetime import date, datetime
import re
from typing import Annotated, Literal, Union

from pydantic import (
    AfterValidator, BaseModel, ConfigDict, Field, StrictBool, StrictFloat,
    StrictInt, StrictStr, StringConstraints, ValidationInfo, field_validator, model_validator,
)


StableId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", min_length=1, max_length=80)]
FieldName = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)]
ShortText = Annotated[str, StringConstraints(min_length=1, max_length=500)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
JsonScalar = Union[Annotated[StrictStr, Field(max_length=1000)], StrictInt, StrictFloat, StrictBool, None]
ScopeMode = Literal["exact", "descendants"]
Lifecycle = Literal["CURATED", "VERIFIED_AUTOMATIC", "CANDIDATE", "MERGED", "DEPRECATED", "REJECTED"]
ApprovalStatus = Literal["DRAFT", "APPROVED"]
GroundingStatus = Literal[
    "NEEDS_CONTEXT", "OUT_OF_COVERAGE", "INSUFFICIENT_VERIFIED_EVIDENCE",
    "PARTIALLY_SUPPORTED", "CONFLICTING_EVIDENCE", "STALE", "SUPPORTED",
]
ToolErrorCode = Literal["INVALID_ARGUMENT", "RELEASE_UNAVAILABLE", "UNSUPPORTED_LANGUAGE", "OPERATIONAL_ERROR"]


def canonical_language_tag(value: str) -> str:
    """Validate BCP 47 syntax and casing, without enabling unsupported languages.

    Supports the RFC 5646 regular grammar, private use and grandfathered tags.
    Registry membership and the closed TIP role catalog belong to validation.py.
    Deprecated tag aliases are not silently substituted.
    """
    grandfathered = {
        "art-lojban", "cel-gaulish", "en-gb-oed", "i-ami", "i-bnn", "i-default",
        "i-enochian", "i-hak", "i-klingon", "i-lux", "i-mingo", "i-navajo",
        "i-pwn", "i-tao", "i-tay", "i-tsu", "no-bok", "no-nyn", "sgn-be-fr",
        "sgn-be-nl", "sgn-ch-de", "zh-guoyu", "zh-hakka", "zh-min", "zh-min-nan", "zh-xiang",
    }
    if not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", value):
        raise ValueError("malformed_language_tag")
    parts = value.lower().split("-")
    if value.lower() in grandfathered:
        return "-".join(part.upper() if len(part) == 2 and i > 0 else part for i, part in enumerate(parts))
    if parts[0] == "x":
        if len(parts) < 2 or any(not 1 <= len(p) <= 8 for p in parts[1:]):
            raise ValueError("malformed_language_tag")
        return "-".join(parts)
    if not parts[0].isalpha() or not 2 <= len(parts[0]) <= 8:
        raise ValueError("malformed_language_tag")
    index = 1
    if len(parts[0]) <= 3:
        for _ in range(3):
            if index < len(parts) and len(parts[index]) == 3 and parts[index].isalpha():
                index += 1
            else:
                break
    if index < len(parts) and len(parts[index]) == 4 and parts[index].isalpha():
        parts[index] = parts[index].title()
        index += 1
    if index < len(parts) and ((len(parts[index]) == 2 and parts[index].isalpha()) or (len(parts[index]) == 3 and parts[index].isdigit())):
        parts[index] = parts[index].upper()
        index += 1
    variants: set[str] = set()
    while index < len(parts) and (5 <= len(parts[index]) <= 8 or (len(parts[index]) == 4 and parts[index][0].isdigit())):
        if parts[index] in variants:
            raise ValueError("duplicate_language_variant")
        variants.add(parts[index])
        index += 1
    extensions: set[str] = set()
    while index < len(parts) and len(parts[index]) == 1 and parts[index] != "x":
        singleton = parts[index]
        if singleton in extensions:
            raise ValueError("duplicate_language_extension")
        extensions.add(singleton)
        index += 1
        start = index
        while index < len(parts) and 2 <= len(parts[index]) <= 8:
            index += 1
        if index == start:
            raise ValueError("malformed_language_tag")
    if index < len(parts) and parts[index] == "x":
        index += 1
        start = index
        while index < len(parts) and 1 <= len(parts[index]) <= 8:
            index += 1
        if index == start:
            raise ValueError("malformed_language_tag")
    if index != len(parts):
        raise ValueError("malformed_language_tag")
    return "-".join(parts)


LanguageTag = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", min_length=2, max_length=128), AfterValidator(canonical_language_tag)]


def _canonical_date(value: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("expected_yyyy_mm_dd")
    date.fromisoformat(value)
    return value


DateString = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"), AfterValidator(_canonical_date)]


def _utc_timestamp(value: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value):
        raise ValueError("expected_utc_timestamp_seconds")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


UtcTimestamp = Annotated[str, AfterValidator(_utc_timestamp)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, validate_default=True, allow_inf_nan=False)


class ArtifactRef(StrictModel):
    """Immutable dependency identity with canonical-content or raw-byte SHA-256.

    The artifact kind defines the hashing convention; model artifacts use
    identity.py canonical JSON, while preserved source files use raw bytes.
    """

    model_config = ConfigDict(frozen=True)
    artifact_id: StableId
    version: Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$", max_length=80)]
    sha256: Sha256


class Jurisdiction(StrictModel):
    country_code: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
    canton_code: Literal[
        "CH-AG", "CH-AI", "CH-AR", "CH-BE", "CH-BL", "CH-BS", "CH-FR", "CH-GE",
        "CH-GL", "CH-GR", "CH-JU", "CH-LU", "CH-NE", "CH-NW", "CH-OW", "CH-SG",
        "CH-SH", "CH-SO", "CH-SZ", "CH-TG", "CH-TI", "CH-UR", "CH-VD", "CH-VS", "CH-ZG", "CH-ZH",
    ] | None = None
    municipality_id: Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]{0,3}$")] | None = None

    @model_validator(mode="after")
    def consistent(self) -> Jurisdiction:
        if self.canton_code is not None and self.country_code != "CH":
            raise ValueError("swiss_canton_requires_ch_country")
        if self.municipality_id is not None and self.canton_code is None:
            raise ValueError("municipality_requires_canton")
        return self


class DateRange(StrictModel):
    """Applicability window with open bounds by default.

    Knowledge carries no commencement or expiry date unless its cited source
    states one (a treaty applied from a fixed date, a law in force from a
    future date). A missing bound is unbounded. Snapshot age is a separate
    freshness concern recorded on each citation.
    """

    valid_from: DateString | None = None
    valid_through: DateString | None = None

    @model_validator(mode="after")
    def ordered(self) -> DateRange:
        if self.valid_from is not None and self.valid_through is not None and self.valid_through < self.valid_from:
            raise ValueError("inverted_date_range")
        return self

    def covers(self, day: str) -> bool:
        """Whether a canonical YYYY-MM-DD applicability date lies inside the window."""
        return ((self.valid_from is None or self.valid_from <= day)
                and (self.valid_through is None or day <= self.valid_through))


class ContextField(StrictModel):
    name: FieldName
    kind: Literal["string", "integer", "number", "boolean", "date", "identifier"]
    description: ShortText
    required: bool = False
    reason_code: FieldName
    enum: Annotated[list[JsonScalar], Field(min_length=1, max_length=100)] | None = None
    minimum: StrictInt | StrictFloat | None = None
    maximum: StrictInt | StrictFloat | None = None
    min_length: Annotated[int, Field(ge=0, le=1000)] | None = None
    max_length: Annotated[int, Field(ge=1, le=1000)] | None = None

    @model_validator(mode="after")
    def constraints(self) -> ContextField:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("inverted_numeric_bounds")
        if self.min_length is not None and self.max_length is not None and self.min_length > self.max_length:
            raise ValueError("inverted_length_bounds")
        if (self.minimum is not None or self.maximum is not None) and self.kind not in {"integer", "number"}:
            raise ValueError("numeric_bounds_require_numeric_kind")
        if (self.min_length is not None or self.max_length is not None) and self.kind not in {"string", "identifier"}:
            raise ValueError("length_bounds_require_text_kind")
        return self


class ContextCondition(StrictModel):
    field: FieldName
    operator: Literal["equals", "not_equals", "in", "not_in", "present", "absent"]
    values: Annotated[list[JsonScalar], Field(max_length=100)] = Field(default_factory=list)

    @model_validator(mode="after")
    def arity(self) -> ContextCondition:
        expected = 0 if self.operator in {"present", "absent"} else 1
        if self.operator in {"equals", "not_equals", "present", "absent"} and len(self.values) != expected:
            raise ValueError("invalid_condition_arity")
        if self.operator in {"in", "not_in"} and not self.values:
            raise ValueError("condition_requires_values")
        return self


class ConditionalRequirement(StrictModel):
    when: Annotated[list[ContextCondition], Field(min_length=1, max_length=20)]
    required_fields: Annotated[list[FieldName], Field(min_length=1, max_length=64)]
    reason_code: FieldName
    rule_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)
    evidence_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)


class ContextConsistencyRule(StrictModel):
    left_field: FieldName
    operator: Literal["equals", "not_equals", "lt", "lte", "gt", "gte"]
    right_field: FieldName
    reason_code: FieldName
    rule_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)
    evidence_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)


class ContextSchema(StrictModel):
    schema_version: Literal["context-schema/v1"] = "context-schema/v1"
    identity: ArtifactRef
    additional_properties: Literal[False] = False
    fields: Annotated[list[ContextField], Field(max_length=64)]
    conditional_requirements: Annotated[list[ConditionalRequirement], Field(max_length=100)] = Field(default_factory=list)
    consistency_rules: Annotated[list[ContextConsistencyRule], Field(max_length=100)] = Field(default_factory=list)

    @field_validator("additional_properties", mode="before")
    @classmethod
    def explicitly_false(cls, value: object) -> object:
        if type(value) is not bool or value:
            raise ValueError("context_schema_must_forbid_additional_properties")
        return value

    @model_validator(mode="after")
    def declared_fields(self) -> ContextSchema:
        names = {field.name for field in self.fields}
        if len(names) != len(self.fields):
            raise ValueError("duplicate_context_field")
        for condition in self.conditional_requirements:
            if not set(condition.required_fields).issubset(names) or any(c.field not in names for c in condition.when):
                raise ValueError("undeclared_conditional_field")
        for rule in self.consistency_rules:
            if rule.left_field not in names or rule.right_field not in names:
                raise ValueError("undeclared_consistency_field")
        return self


class LocalizedMetadata(StrictModel):
    label: ShortText
    aliases: Annotated[list[ShortText], Field(max_length=30)] = Field(default_factory=list)
    description: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    provenance: Annotated[list[ArtifactRef], Field(min_length=1, max_length=20)]


class CatalogEntry(StrictModel):
    schema_version: Literal["catalog-entry/v1"] = "catalog-entry/v1"
    entry_id: StableId
    kind: Literal["knowledge_space", "domain", "topic", "concept"]
    parent_ids: Annotated[list[StableId], Field(max_length=20)] = Field(default_factory=list)
    labels: Annotated[dict[LanguageTag, LocalizedMetadata], Field(min_length=1, max_length=20)]
    lifecycle: Lifecycle = "CANDIDATE"
    replacement_ids: Annotated[list[StableId], Field(max_length=20)] = Field(default_factory=list)

    @field_validator("labels", mode="before")
    @classmethod
    def distinct_canonical_keys(cls, value: object) -> object:
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            keys = [canonical_language_tag(key) for key in value]
            if len(set(keys)) != len(keys):
                raise ValueError("duplicate_canonical_label_language")
        return value


class TermProjectionRoute(StrictModel):
    term_language: LanguageTag
    projection_language: LanguageTag
    terminology_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)
    dialect_profile: StableId | None = None
    idiom_profile: StableId | None = None


class EvaluatedTermRoute(TermProjectionRoute):
    source_languages: Annotated[list[LanguageTag], Field(min_length=1, max_length=100)]
    evaluation_ref: ArtifactRef


class LanguagePolicy(StrictModel):
    schema_version: Literal["language-policy/v1"] = "language-policy/v1"
    identity: ArtifactRef
    platform_catalog: Literal["tip-language-catalog/v3", "tip-language-catalog/v4"] = "tip-language-catalog/v3"
    term_languages: Annotated[list[LanguageTag], Field(max_length=6)]
    source_languages: Annotated[list[LanguageTag], Field(max_length=100)]
    projection_languages: Annotated[list[LanguageTag], Field(max_length=5)]
    term_aliases: Annotated[dict[LanguageTag, LanguageTag], Field(max_length=8)] = Field(default_factory=dict)
    routes: Annotated[list[TermProjectionRoute], Field(max_length=20)]
    source_detector_mappings: Annotated[dict[ShortText, LanguageTag], Field(max_length=100)] = Field(default_factory=dict)
    source_declaration_aliases: Annotated[dict[LanguageTag, LanguageTag], Field(max_length=0)] = Field(default_factory=dict)
    evaluation_ref: ArtifactRef | None = None
    approval_status: ApprovalStatus = "DRAFT"

    @model_validator(mode="after")
    def approved_evaluation(self) -> LanguagePolicy:
        if self.approval_status == "APPROVED" and self.evaluation_ref is None:
            raise ValueError("approved_language_policy_requires_evaluation")
        return self


class FreshnessPolicy(StrictModel):
    max_age_days: Annotated[int, Field(ge=1, le=3650)]
    policy_ref: ArtifactRef


class CoverageProfile(StrictModel):
    schema_version: Literal["coverage-profile/v1"] = "coverage-profile/v1"
    coverage_profile_id: StableId
    release_id: StableId
    catalog_ref: ArtifactRef
    knowledge_space_id: StableId
    domain_id: StableId
    topic_id: StableId
    concept_ids: Annotated[list[StableId], Field(max_length=50)] = Field(default_factory=list)
    intent: StableId
    concept_selection_required: bool = False
    jurisdiction: Jurisdiction
    context_schema_ref: ArtifactRef
    scope_modes: Annotated[list[ScopeMode], Field(min_length=1, max_length=2)]
    max_descendant_depth: Annotated[int, Field(ge=0, le=20)] = 0
    max_concepts: Annotated[int, Field(ge=1, le=50)] = 20
    source_ids: Annotated[list[StableId], Field(min_length=1, max_length=100)]
    source_languages: Annotated[list[LanguageTag], Field(min_length=1, max_length=100)]
    temporal_coverage: DateRange
    term_routes: Annotated[list[EvaluatedTermRoute], Field(max_length=40)] = Field(default_factory=list)
    projection_languages_complete: Annotated[list[LanguageTag], Field(max_length=5)] = Field(default_factory=list)
    evaluation_ref: ArtifactRef | None = None
    rule_refs: Annotated[list[ArtifactRef], Field(max_length=100)] = Field(default_factory=list)
    exclusions: Annotated[list[ShortText], Field(max_length=30)] = Field(default_factory=list)
    freshness_policy: FreshnessPolicy
    approval_status: ApprovalStatus = "DRAFT"

    @model_validator(mode="after")
    def approved_evaluation(self) -> CoverageProfile:
        if self.approval_status == "APPROVED" and self.evaluation_ref is None:
            raise ValueError("approved_coverage_requires_evaluation")
        return self


class KnowledgeCatalog(StrictModel):
    schema_version: Literal["knowledge-catalog/v1"] = "knowledge-catalog/v1"
    identity: ArtifactRef
    release_id: StableId
    entries: Annotated[list[CatalogEntry], Field(min_length=1, max_length=10000)]
    context_schemas: Annotated[list[ContextSchema], Field(max_length=1000)] = Field(default_factory=list)
    coverage_profiles: Annotated[list[CoverageProfile], Field(max_length=10000)] = Field(default_factory=list)
    language_policy_ref: ArtifactRef
    max_evidence: Annotated[int, Field(ge=1, le=5)] = 5
    discovery_default_limit: Annotated[int, Field(ge=1, le=100)] = 20
    discovery_max_limit: Annotated[int, Field(ge=1, le=100)] = 100
    ordering: Literal["entry_id_ascending"] = "entry_id_ascending"

    @model_validator(mode="after")
    def discovery_limits(self) -> KnowledgeCatalog:
        if self.discovery_default_limit > self.discovery_max_limit:
            raise ValueError("discovery_default_exceeds_maximum")
        return self


class KnowledgeRelease(StrictModel):
    schema_version: Literal["knowledge-release/v1"] = "knowledge-release/v1"
    release_id: StableId
    identity: ArtifactRef
    created_at: UtcTimestamp
    catalog_ref: ArtifactRef
    context_schema_refs: Annotated[list[ArtifactRef], Field(max_length=1000)]
    language_policy_ref: ArtifactRef
    snapshot_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    normalized_document_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    evidence_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    concept_graph_ref: ArtifactRef
    terminology_refs: Annotated[list[ArtifactRef], Field(max_length=10000)]
    fact_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    rule_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    projection_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    index_refs: Annotated[list[ArtifactRef], Field(max_length=100)]
    contract_schema_refs: Annotated[list[ArtifactRef], Field(min_length=1, max_length=100)]
    provider_configuration_ref: ArtifactRef
    ranking_configuration_ref: ArtifactRef
    evaluation_ref: ArtifactRef


class RetrievalTerm(StrictModel):
    text: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    language: LanguageTag

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("empty_retrieval_term")
        return value


class ScopeSelection(StrictModel):
    knowledge_space_id: StableId
    domain_id: StableId
    topic_id: StableId
    concept_ids: Annotated[list[StableId], Field(max_length=50)] = Field(default_factory=list)
    intent: StableId
    jurisdiction: Jurisdiction
    as_of: DateString
    scope_mode: ScopeMode

    @field_validator("concept_ids")
    @classmethod
    def distinct_concepts(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate_concept_id")
        return value


class StructuredGroundingRequest(ScopeSelection):
    schema_version: Literal["structured-grounding/v1"]
    release_id: StableId
    context: Annotated[dict[FieldName, JsonScalar], Field(max_length=64)]
    retrieval_terms: Annotated[list[RetrievalTerm], Field(max_length=20)] = Field(default_factory=list)
    source_languages: Annotated[list[LanguageTag], Field(min_length=1, max_length=20)] | None = None
    max_evidence: Annotated[int, Field(ge=1, le=5)] = 5

    @field_validator("source_languages")
    @classmethod
    def distinct_source_languages(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else list(dict.fromkeys(value))


class Citation(StrictModel):
    source_id: StableId
    authority: ShortText
    url: Annotated[str, StringConstraints(pattern=r"^https?://[^\s]+$", max_length=2000)]
    title: ShortText
    accessed_at: UtcTimestamp


class EvidenceObject(StrictModel):
    schema_version: Literal["evidence-object/v1", "evidence-object/v2"] = "evidence-object/v1"
    identity: ArtifactRef
    evidence_id: StableId
    release_id: StableId
    snapshot_ref: ArtifactRef
    normalized_document_ref: ArtifactRef
    section_id: StableId
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(gt=0)]
    original_excerpt: Annotated[str, StringConstraints(min_length=1, max_length=20000)]
    citation: Citation
    declared_language: Annotated[list[LanguageTag], Field(max_length=20)]
    detected_language: LanguageTag | None
    effective_source_language: LanguageTag
    language_detection_method: StableId
    language_confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    reviewed_language_override_ref: ArtifactRef | None = None
    canonical_concept_ids: Annotated[list[StableId], Field(min_length=1, max_length=50)]
    jurisdiction: Jurisdiction
    temporal_coverage: DateRange
    provenance_refs: Annotated[list[ArtifactRef], Field(min_length=1, max_length=30)]

    @field_validator("effective_source_language")
    @classmethod
    def exact_source_role(cls, value: str, info: ValidationInfo) -> str:
        if info.data.get("schema_version", "evidence-object/v1") == "evidence-object/v1" and value not in {"en", "de", "fr", "it", "rm"}:
            raise ValueError("effective_language_requires_exact_v3_source_tag")
        if value.split("-")[0] in {"und", "mul", "zxx"}:
            raise ValueError("effective_source_language_must_identify_a_language")
        return value

    @model_validator(mode="after")
    def span_length(self) -> EvidenceObject:
        if self.end_offset - self.start_offset != len(self.original_excerpt):
            raise ValueError("excerpt_length_does_not_match_codepoint_span")
        return self


class ValidationIssue(StrictModel):
    path: ShortText
    reason_code: FieldName
    message: ShortText
    allowed_values: Annotated[list[JsonScalar], Field(max_length=100)] = Field(default_factory=list)


class MissingContextField(StrictModel):
    path: ShortText
    reason_code: FieldName
    schema_ref: ArtifactRef
    allowed_values: Annotated[list[JsonScalar], Field(max_length=100)] = Field(default_factory=list)
    rule_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)
    evidence_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)


class ToolError(StrictModel):
    schema_version: Literal["tool-error/v1"] = "tool-error/v1"
    code: ToolErrorCode
    issues: Annotated[list[ValidationIssue], Field(min_length=1, max_length=100)]
    release_id: StableId | None = None
    active_release_id: StableId | None = None


class GetCoverageRequest(StrictModel):
    schema_version: Literal["get-coverage/v1"] = "get-coverage/v1"
    release_id: StableId | None = None
    knowledge_space_id: StableId | None = None
    parent_id: StableId | None = None
    cursor: Annotated[str, StringConstraints(min_length=1, max_length=2000)] | None = None
    limit: Annotated[int, Field(ge=1, le=100)] = 20

    @model_validator(mode="after")
    def pinned_continuations(self) -> GetCoverageRequest:
        if (self.parent_id is not None or self.cursor is not None) and self.release_id is None:
            raise ValueError("child_and_continuation_requests_require_release")
        return self


class GetCoverageResult(StrictModel):
    schema_version: Literal["get-coverage-result/v1"] = "get-coverage-result/v1"
    release_id: StableId
    release_ref: ArtifactRef
    catalog_ref: ArtifactRef
    language_policy_ref: ArtifactRef
    knowledge_space_id: StableId | None = None
    parent: CatalogEntry | None = None
    entries: Annotated[list[CatalogEntry], Field(max_length=100)]
    coverage_profiles: Annotated[list[CoverageProfile], Field(max_length=1000)]
    context_schemas: Annotated[list[ContextSchema], Field(max_length=1000)]
    next_cursor: Annotated[str, StringConstraints(min_length=1, max_length=2000)] | None = None
    default_limit: Annotated[int, Field(ge=1, le=100)] = 20
    maximum_limit: Annotated[int, Field(ge=1, le=100)] = 100
    ordering: Literal["entry_id_ascending"] = "entry_id_ascending"


class GetEvidenceRequest(StrictModel):
    schema_version: Literal["get-evidence/v1"] = "get-evidence/v1"
    release_id: StableId
    evidence_ids: Annotated[list[StableId], Field(min_length=1, max_length=5)]

    @field_validator("evidence_ids")
    @classmethod
    def distinct_evidence(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("duplicate_evidence_id")
        return value


class GetEvidenceResult(StrictModel):
    schema_version: Literal["get-evidence-result/v1"] = "get-evidence-result/v1"
    release_id: StableId
    release_ref: ArtifactRef
    evidence: Annotated[list[EvidenceObject], Field(max_length=5)]

    @model_validator(mode="after")
    def pinned_evidence(self) -> GetEvidenceResult:
        if any(item.release_id != self.release_id for item in self.evidence):
            raise ValueError("evidence_release_mismatch")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate_evidence_id")
        return self


class PublishedFact(StrictModel):
    schema_version: Literal["published-fact/v1"] = "published-fact/v1"
    identity: ArtifactRef
    fact_id: StableId
    statement: Annotated[str, StringConstraints(min_length=1, max_length=2000)]
    language: LanguageTag
    evidence_ids: Annotated[list[StableId], Field(min_length=1, max_length=5)]
    rule_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)
    applicability_conditions: Annotated[list[ShortText], Field(max_length=30)] = Field(default_factory=list)


class PublishedRule(StrictModel):
    """All-of scalar predicates selecting pre-authored facts, never executable code."""

    schema_version: Literal["published-rule/v1"] = "published-rule/v1"
    identity: ArtifactRef
    rule_id: StableId
    when: Annotated[list[ContextCondition], Field(min_length=1, max_length=20)]
    fact_ids: Annotated[list[StableId], Field(min_length=1, max_length=50)]


class ResolutionPortion(StrictModel):
    """One required, reviewed portion of an operation's finite coverage."""

    portion_id: StableId
    concept_ids: Annotated[list[StableId], Field(max_length=50)]
    fact_ids: Annotated[list[StableId], Field(max_length=50)] = Field(default_factory=list)
    rule_refs: Annotated[list[ArtifactRef], Field(max_length=20)] = Field(default_factory=list)
    evidence_ids: Annotated[list[StableId], Field(max_length=50)] = Field(default_factory=list)


class ResolutionPlan(StrictModel):
    coverage_profile_id: StableId
    portions: Annotated[list[ResolutionPortion], Field(min_length=1, max_length=50)]


class FactConflict(StrictModel):
    fact_ids: Annotated[list[StableId], Field(min_length=2, max_length=50)]


class ResolutionGraph(StrictModel):
    """Runtime graph bound by KnowledgeRelease.concept_graph_ref."""

    schema_version: Literal["resolution-graph/v1"] = "resolution-graph/v1"
    identity: ArtifactRef
    release_id: StableId
    plans: Annotated[list[ResolutionPlan], Field(max_length=10000)]
    conflicts: Annotated[list[FactConflict], Field(max_length=10000)] = Field(default_factory=list)


class NormalizedSection(StrictModel):
    section_id: StableId
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(gt=0)]


class NormalizedEvidenceDocument(StrictModel):
    schema_version: Literal["normalized-evidence-document/v1"] = "normalized-evidence-document/v1"
    identity: ArtifactRef
    snapshot_ref: ArtifactRef
    source_id: StableId
    text: Annotated[str, StringConstraints(min_length=1, max_length=10000000)]
    sections: Annotated[list[NormalizedSection], Field(min_length=1, max_length=10000)]

    @model_validator(mode="after")
    def valid_sections(self) -> NormalizedEvidenceDocument:
        if len({s.section_id for s in self.sections}) != len(self.sections):
            raise ValueError("duplicate_normalized_section")
        if any(not 0 <= s.start_offset < s.end_offset <= len(self.text) for s in self.sections):
            raise ValueError("invalid_normalized_section_span")
        return self


class UnresolvedPortion(StrictModel):
    concept_ids: Annotated[list[StableId], Field(max_length=50)]
    reason_code: FieldName
    limitation: ShortText


class Freshness(StrictModel):
    status: Literal["FRESH", "STALE", "UNKNOWN"]
    checked_at: UtcTimestamp
    oldest_source_at: UtcTimestamp | None = None
    policy_ref: ArtifactRef


class TrustEnvelope(StrictModel):
    source_authorities: Annotated[list[ShortText], Field(max_length=20)]
    evaluation_ref: ArtifactRef
    fact_support: Literal["PUBLISHED_FACTS_OR_RULES", "EXCERPTS_ONLY", "NONE"]
    limitations: Annotated[list[ShortText], Field(max_length=30)]


class TermRoute(StrictModel):
    input_index: Annotated[int, Field(ge=0, lt=20)]
    original_text: Annotated[str, StringConstraints(min_length=1, max_length=120)]
    requested_language: LanguageTag
    effective_term_language: LanguageTag
    projection_language: LanguageTag
    source_languages: Annotated[list[LanguageTag], Field(min_length=1, max_length=100)]
    terminology_refs: Annotated[list[ArtifactRef], Field(max_length=20)]
    language_policy_ref: ArtifactRef
    evaluation_ref: ArtifactRef


class ProviderDegradation(StrictModel):
    reason_code: FieldName
    omitted_channels: Annotated[list[Literal["lexical", "concept", "vector", "semantic_ranking"]], Field(max_length=4)]
    evaluated_fallback_ref: ArtifactRef


class EvidenceSelection(StrictModel):
    mapping_ref: ArtifactRef
    representative_id: StableId
    alternate_ids: Annotated[list[StableId], Field(min_length=1, max_length=20)]
    fact_ids: Annotated[list[StableId], Field(max_length=50)]
    reason_code: Literal["german_equivalent_tie", "higher_ranked_equivalent", "only_eligible_equivalent", "stable_equivalent_tie", "fresher_equivalent"]


class RetrievalProjection(StrictModel):
    schema_version: Literal["retrieval-projection/v1"] = "retrieval-projection/v1"
    identity: ArtifactRef
    evidence_ref: ArtifactRef
    language: LanguageTag
    text: Annotated[str, StringConstraints(min_length=1, max_length=4000)]
    provenance_refs: Annotated[list[ArtifactRef], Field(min_length=1, max_length=20)]


class ReviewedTerminology(StrictModel):
    schema_version: Literal["reviewed-terminology/v1"] = "reviewed-terminology/v1"
    identity: ArtifactRef
    concept_id: StableId
    term_language: LanguageTag
    terms: Annotated[list[ShortText], Field(min_length=1, max_length=100)]
    review_ref: ArtifactRef


class EvidenceEquivalence(StrictModel):
    """Review attests interchangeable claim support for these exact revisions.

    Concept alignment alone cannot create this artifact. All members support
    each listed fact with the same conditions; omitted/partial translations
    belong outside the group.
    """
    schema_version: Literal["evidence-equivalence/v1"] = "evidence-equivalence/v1"
    identity: ArtifactRef
    evidence_refs: Annotated[list[ArtifactRef], Field(min_length=2, max_length=21)]
    fact_ids: Annotated[list[StableId], Field(max_length=50)]
    fact_refs: Annotated[list[ArtifactRef], Field(max_length=50)]
    review_ref: ArtifactRef


class EvidenceVector(StrictModel):
    evidence_ref: ArtifactRef
    values: Annotated[list[float], Field(min_length=1, max_length=4096)]


class RetrievalIndex(StrictModel):
    schema_version: Literal["retrieval-index/v1"] = "retrieval-index/v1"
    identity: ArtifactRef
    embedding_model: ShortText
    dimensions: Annotated[int, Field(ge=1, le=4096)]
    projection_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    vectors: Annotated[list[EvidenceVector], Field(max_length=100000)]


class RetrievalProviders(StrictModel):
    schema_version: Literal["retrieval-providers/v1"] = "retrieval-providers/v1"
    identity: ArtifactRef
    embedding_model: ShortText
    ranking_model: ShortText
    embedding_provider: ShortText
    ranking_provider: ShortText


class RetrievalFallback(StrictModel):
    coverage_profile_id: StableId
    evaluation_ref: ArtifactRef
    channels: Literal["lexical_concept"] = "lexical_concept"
    minimum_lexical_score: Annotated[float, Field(ge=0.0)] | None = None


class RetrievalConfiguration(StrictModel):
    schema_version: Literal["retrieval-configuration/v1"] = "retrieval-configuration/v1"
    identity: ArtifactRef
    provider_configuration_ref: ArtifactRef
    index_ref: ArtifactRef
    equivalence_refs: Annotated[list[ArtifactRef], Field(max_length=100000)]
    evaluation_refs: Annotated[dict[StableId, ArtifactRef], Field(min_length=1, max_length=10000)]
    fallbacks: Annotated[list[RetrievalFallback], Field(max_length=10000)] = Field(default_factory=list)
    candidate_limit: Annotated[int, Field(ge=20, le=100)] = 20
    channel_limit: Annotated[int, Field(ge=20, le=100)] = 20
    rrf_constant: Annotated[int, Field(ge=1, le=1000)] = 60
    minimum_semantic_score: float | None = None
    selection_policy: Literal["verified-equivalence-german-tie/v1"] = "verified-equivalence-german-tie/v1"


class RetrievalTrace(StrictModel):
    term_routes: Annotated[list[TermRoute], Field(max_length=20)]
    effective_source_languages: Annotated[list[LanguageTag], Field(min_length=1, max_length=100)] | None
    channels: Annotated[list[Literal["lexical", "concept", "vector", "semantic_ranking"]], Field(max_length=4)]
    index_refs: Annotated[list[ArtifactRef], Field(max_length=20)]
    provider_configuration_ref: ArtifactRef
    ranking_configuration_ref: ArtifactRef
    candidate_count: Annotated[int, Field(ge=0)]
    evidence_count: Annotated[int, Field(ge=0, le=5)]
    degradations: Annotated[list[ProviderDegradation], Field(max_length=10)] = Field(default_factory=list)
    language_policy_ref: ArtifactRef | None = None
    projection_refs: Annotated[list[ArtifactRef], Field(max_length=100)] = Field(default_factory=list)
    candidate_ids: Annotated[list[StableId], Field(max_length=100)] = Field(default_factory=list)
    selections: Annotated[list[EvidenceSelection], Field(max_length=5)] = Field(default_factory=list)
    selection_policy: Literal["verified-equivalence-german-tie/v1"] | None = None


class StructuredGroundingResult(StrictModel):
    schema_version: Literal["structured-grounding-result/v1"] = "structured-grounding-result/v1"
    release_id: StableId
    release_ref: ArtifactRef
    catalog_ref: ArtifactRef
    requested_scope: ScopeSelection
    executed_scope: ScopeSelection | None
    coverage_profile_ids: Annotated[list[StableId], Field(max_length=50)]
    status: GroundingStatus
    supported_portions: Annotated[list[PublishedFact], Field(max_length=50)]
    unresolved_portions: Annotated[list[UnresolvedPortion], Field(max_length=50)]
    evidence: Annotated[list[EvidenceObject], Field(max_length=5)]
    missing_context: Annotated[list[MissingContextField], Field(max_length=64)]
    freshness: Freshness
    trust: TrustEnvelope
    trace: RetrievalTrace | None

    @model_validator(mode="after")
    def result_invariants(self) -> StructuredGroundingResult:
        if any(item.release_id != self.release_id for item in self.evidence):
            raise ValueError("evidence_release_mismatch")
        evidence_ids = {item.evidence_id for item in self.evidence}
        if len(evidence_ids) != len(self.evidence):
            raise ValueError("duplicate_evidence_id")
        selections = self.trace.selections if self.trace else []
        if any(s.representative_id not in evidence_ids or s.representative_id in s.alternate_ids
               or len(set(s.alternate_ids)) != len(s.alternate_ids) for s in selections):
            raise ValueError("invalid_evidence_selection")
        for fact in self.supported_portions:
            represented = evidence_ids | {e for s in selections if fact.fact_id in s.fact_ids for e in s.alternate_ids}
            if not set(fact.evidence_ids).issubset(represented):
                raise ValueError("fact_references_missing_evidence")
        if self.status == "NEEDS_CONTEXT" and not self.missing_context:
            raise ValueError("needs_context_requires_missing_fields")
        if self.status == "SUPPORTED" and (self.missing_context or self.unresolved_portions or not self.supported_portions):
            raise ValueError("supported_requires_complete_published_support")
        if self.status == "PARTIALLY_SUPPORTED" and (not self.supported_portions or not self.unresolved_portions):
            raise ValueError("partial_requires_supported_and_unresolved_portions")
        if self.status in {"SUPPORTED", "PARTIALLY_SUPPORTED"} and self.executed_scope is None:
            raise ValueError("supported_requires_executed_scope")
        if self.supported_portions and self.trust.fact_support != "PUBLISHED_FACTS_OR_RULES":
            raise ValueError("facts_require_published_support_trust")
        if self.status == "SUPPORTED" and self.freshness.status != "FRESH":
            raise ValueError("supported_requires_fresh_evidence")
        if self.trace is not None and self.trace.evidence_count != len(self.evidence):
            raise ValueError("trace_evidence_count_mismatch")
        return self


CONTRACT_MODELS = (
    ArtifactRef, Jurisdiction, ContextSchema, CatalogEntry, CoverageProfile,
    KnowledgeCatalog, LanguagePolicy, KnowledgeRelease, EvidenceObject,
    StructuredGroundingRequest, StructuredGroundingResult, ToolError,
    GetCoverageRequest, GetCoverageResult, GetEvidenceRequest, GetEvidenceResult,
    PublishedFact, PublishedRule, ResolutionGraph, NormalizedEvidenceDocument,
    RetrievalProjection, ReviewedTerminology, EvidenceEquivalence, RetrievalIndex,
    RetrievalProviders, RetrievalConfiguration,
)
