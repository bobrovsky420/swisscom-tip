"""Packaged prompts and immutable, auditable per-run overrides."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


_EXTRACTION_FILES = {
    "concept_extraction_v1": ("concept_extraction_v1.md",),
    "concept_extraction_v2": ("concept_extraction_v2.md",),
    "concept_extraction_v3": ("concept_extraction_v2.md", "concept_extraction_v3_extension.md"),
    "concept_extraction_v4": ("structured_claim_extraction_v4.md", "structured_claim_example_v4.md"),
}
_REVIEW_FILES = {
    "concept_extraction_v3": ("concept_review_v3.md",),
    "concept_extraction_v4": ("structured_claim_review_v4.md",),
}


def load_bundled_prompt(name: str) -> str:
    """Read package data, including when installed from a wheel."""
    return files("swisstip.ingestion").joinpath("prompts", name).read_text(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class Prompt:
    text: str
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {"text": self.text, "sha256": hashlib.sha256(self.text.encode("utf-8")).hexdigest(),
                "sources": list(self.sources)}


@dataclass(frozen=True, slots=True)
class PromptSet:
    profile: str
    extraction: Prompt
    review: Prompt | None

    def to_dict(self) -> dict[str, object]:
        return {"extraction": self.extraction.to_dict(),
                **({"review": self.review.to_dict()} if self.review is not None else {})}


def _load(names: tuple[str, ...], override: str | Path | None) -> Prompt:
    if override is None:
        return Prompt("".join(load_bundled_prompt(name) for name in names),
                      tuple(f"package:swisstip.ingestion/prompts/{name}" for name in names))
    path = Path(override).resolve()
    try:
        # Accept Markdown saved by Windows editors with a UTF-8 BOM; normalize CRLF.
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"cannot read UTF-8 prompt file {path}: {exc}") from exc
    if not text.strip():
        raise ValueError(f"prompt file must not be empty: {path}")
    return Prompt(text, (str(path),))


def load_prompts(profile: str, *, extraction_prompt_file: str | Path | None = None,
                 review_prompt_file: str | Path | None = None) -> PromptSet:
    """Snapshot defaults/overrides once; never interpolate source data into templates.

    Overrides replace the complete system prompt for their role. Schemas, request
    data and validation remain in the caller's code.
    """
    if profile not in _EXTRACTION_FILES:
        raise ValueError(f"unsupported prompt profile: {profile}")
    review_names = _REVIEW_FILES.get(profile)
    if review_prompt_file is not None and review_names is None:
        raise ValueError(f"review_prompt_file is not supported by {profile}; use v3 or v4")
    return PromptSet(profile, _load(_EXTRACTION_FILES[profile], extraction_prompt_file),
                     _load(review_names, review_prompt_file) if review_names else None)
