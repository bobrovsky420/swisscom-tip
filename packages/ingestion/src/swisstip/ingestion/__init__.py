"""Ingestion components for SwissTIP."""

from .concepts import (
    CandidateConcept,
    CandidateConceptExtractor,
    CONCEPT_EXTRACTION_OPERATION,
    ConceptExtractionError,
    ConceptProposalReport,
    EvidenceSpan,
    ModelCompletion,
    NormalizedPage,
    NormalizedSection,
    PageNormalizationError,
    SemanticModelError,
    SemanticModelProvider,
    normalize_downloaded_page,
)
from .crawler import CrawlLimits, CrawlReport, SafeCrawler, SourceDefinition

__all__ = [
    "CandidateConcept",
    "CandidateConceptExtractor",
    "CONCEPT_EXTRACTION_OPERATION",
    "ConceptExtractionError",
    "ConceptProposalReport",
    "CrawlLimits",
    "CrawlReport",
    "EvidenceSpan",
    "ModelCompletion",
    "NormalizedPage",
    "NormalizedSection",
    "PageNormalizationError",
    "SafeCrawler",
    "SemanticModelError",
    "SemanticModelProvider",
    "SourceDefinition",
    "normalize_downloaded_page",
]
