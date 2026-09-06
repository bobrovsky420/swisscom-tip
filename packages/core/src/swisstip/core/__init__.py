"""Shared, versioned contracts for SwissTIP knowledge and structured grounding."""

from .contracts import (
    ArtifactRef, CatalogEntry, ContextSchema, CoverageProfile, EvidenceObject,
    GetCoverageRequest, GetCoverageResult, GetEvidenceRequest, GetEvidenceResult,
    Jurisdiction, KnowledgeCatalog, KnowledgeRelease, LanguagePolicy,
    StructuredGroundingRequest, StructuredGroundingResult, ToolError,
)

__all__ = [
    "ArtifactRef", "CatalogEntry", "ContextSchema", "CoverageProfile", "EvidenceObject",
    "GetCoverageRequest", "GetCoverageResult", "GetEvidenceRequest", "GetEvidenceResult",
    "Jurisdiction", "KnowledgeCatalog", "KnowledgeRelease", "LanguagePolicy",
    "StructuredGroundingRequest", "StructuredGroundingResult", "ToolError",
]
