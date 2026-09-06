"""Canonical content identities for contracts that carry their own hash.

Raw source snapshots are hashed as bytes elsewhere. Contract documents are
hashed after validated model serialization (including defaults) as sorted compact
UTF-8 JSON. Only the root self hash and a catalog's embedded self-reference hashes
are omitted. All other dependency hashes and all versions remain part of the
content. This avoids a circular hash without ignoring dependency changes.
"""

from __future__ import annotations

import hashlib
import json
from typing import TypeVar

from .contracts import StrictModel


Artifact = TypeVar("Artifact", bound=StrictModel)


def _document(artifact: StrictModel) -> dict:
    document = artifact.model_dump(mode="json")
    identity = document.get("identity")
    if not isinstance(identity, dict) or not {"artifact_id", "version", "sha256"} <= identity.keys():
        raise ValueError("Contract does not carry an artifact identity")
    return document


def _self_references(document: dict) -> list[dict]:
    identity = document["identity"]
    references = [identity]
    if document.get("schema_version") == "knowledge-catalog/v1":
        for profile in document["coverage_profiles"]:
            reference = profile["catalog_ref"]
            if (reference["artifact_id"], reference["version"]) == (identity["artifact_id"], identity["version"]):
                references.append(reference)
    return references


def json_content_hash(document: object) -> str:
    """Hash JSON metadata independently of file indentation and line endings."""
    canonical = json.dumps(document, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def artifact_hash(artifact: StrictModel) -> str:
    """Compute an artifact's canonical content hash, independent of its self hash."""
    document = _document(artifact)
    for reference in _self_references(document):
        del reference["sha256"]
    return json_content_hash(document)


def seal_artifact(artifact: Artifact) -> Artifact:
    """Return a validated copy with current self hashes; this is not approval.

    Seal dependencies first. This function never changes a dependency ID/version
    or repairs mismatched references; catalog integrity validation handles those.
    """
    document = _document(artifact)
    content_hash = artifact_hash(artifact)
    for reference in _self_references(document):
        reference["sha256"] = content_hash
    return type(artifact).model_validate(document)


def verify_artifact(artifact: StrictModel) -> bool:
    """Check content plus embedded self references against the declared identity."""
    document = _document(artifact)
    content_hash = artifact_hash(artifact)
    return all(reference["sha256"] == content_hash for reference in _self_references(document))
