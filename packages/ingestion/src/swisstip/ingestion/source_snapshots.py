"""Bind downloaded snapshot provenance and source adapters to standard normalization."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

from .concepts import PageNormalizationError, SUPPORTED_PAGE_SUFFIXES, normalize_downloaded_page
from .source_plugins import PluginRegistry, load_source_plugins


def normalize_source_snapshot(path: Path, *, plugins: PluginRegistry | None = None, **options):
    path = Path(path)
    metadata = None
    for candidate in (path.parent / "manifest.json", path.parent.parent / "manifest.json"):
        if candidate.is_file():
            try:
                value = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise PageNormalizationError(f"Cannot read snapshot manifest: {candidate}") from exc
            if "snapshots" in value:
                metadata = value
                break
    if metadata is None:
        return normalize_downloaded_page(path, **options)
    matches = []
    for snapshot in metadata["snapshots"]:
        relative = Path(snapshot["relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise PageNormalizationError("Snapshot manifest contains an unsafe relative path")
        if any((parent / relative).resolve() == path.resolve() for parent in path.resolve().parents):
            matches.append(snapshot)
    if len(matches) != 1:
        raise PageNormalizationError("Snapshot manifest must identify this input file exactly once")
    snapshot = matches[0]
    if snapshot.get("review_flags"):
        raise PageNormalizationError(f"Snapshot requires acquisition review: {snapshot['review_flags']}")
    if path.suffix.lower() not in SUPPORTED_PAGE_SUFFIXES:
        raise PageNormalizationError("No text normalizer for this snapshot format; select its HTML representation")
    limit = options.get("max_file_bytes", 2_000_000)
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise PageNormalizationError(f"Cannot read snapshot: {path}") from exc
    if len(raw) > limit:
        raise PageNormalizationError(f"Snapshot exceeds the {limit}-byte input limit")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != snapshot.get("sha256"):
        raise PageNormalizationError("Snapshot bytes do not match the acquisition manifest hash")
    source_url = metadata.get("source_page_url", snapshot["requested_url"])
    registry = load_source_plugins() if plugins is None else plugins
    plugin = registry.select(source_url)
    declared_plugin = metadata.get("source_plugin")
    if declared_plugin and (plugin is None or declared_plugin != {
            "id": plugin.plugin_id, "version": plugin.version, "api_version": plugin.api_version}):
        raise PageNormalizationError("Snapshot source plugin is missing or its version differs")
    provenance = {
        "source_url": source_url, "requested_url": snapshot["requested_url"],
        "final_url": snapshot["final_url"], "retrieved_at": snapshot["retrieved_at"],
        "content_type": snapshot["content_type"], "sha256": digest,
        "version_uri": metadata.get("version_uri"), "source_plugin": declared_plugin,
        "normalization_plugin": {"id": plugin.plugin_id, "version": plugin.version} if plugin else None,
        "document_metadata": metadata.get("document_metadata", {}),
        "registry_entries": metadata.get("registry_entries", []),
        "resolution_metadata": metadata.get("resolution_metadata", []),
        "local_snapshot": str(path),
    }
    page = (plugin.normalize(path, provenance, **options) if plugin else normalize_downloaded_page(path, **options))
    return replace(page, source_sha256=digest, provenance=provenance)
