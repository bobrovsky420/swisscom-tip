"""Offline validation and crawl planning for an operator-authored source registry."""

from __future__ import annotations

from dataclasses import asdict, fields
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import posixpath
import re
from urllib.parse import unquote, urlsplit

from swisstip.ingestion import CrawlLimits, SourceDefinition


SOURCE_SCHEMA = "swisstip.source-catalog/v1"
SCAN_STATUSES = {"ready", "needs_access_review", "manual_adapter_required"}
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
CANTONS = frozenset("AG AI AR BE BL BS FR GE GL GR JU LU NE NW OW SG SH SO SZ TG TI UR VD VS ZG ZH".split())


def content_hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _identifier(value: object) -> bool:
    return isinstance(value, str) and ID_PATTERN.fullmatch(value) is not None


def _https_url(value: str) -> None:
    parsed = urlsplit(value)
    _require(parsed.scheme == "https" and bool(parsed.hostname), "Source URLs must use absolute HTTPS")
    _require(not (parsed.username or parsed.password or parsed.query or parsed.fragment),
             "Source URLs cannot contain credentials, queries or fragments")
    _require(parsed.port in {None, 443}, "Source URLs must use the standard HTTPS port")


def _in_paths(path: str, prefixes: list[str]) -> bool:
    path = posixpath.normpath(unquote(path))
    return any(prefix == "/" or path == prefix.rstrip("/") or path.startswith(prefix.rstrip("/") + "/")
               for prefix in prefixes)


def source_definition(entry: dict) -> SourceDefinition:
    values = dict(entry["definition"])
    values["allowed_hosts"] = tuple(values["allowed_hosts"])
    values["allowed_path_prefixes"] = tuple(values["allowed_path_prefixes"])
    return SourceDefinition(**values)


def load_source_catalog(path: Path) -> dict:
    """Reject malformed scopes and dangling selectors without DNS, HTTP or inference."""
    data = json.loads(path.read_text(encoding="utf-8"))
    _require(data["schema_version"] == SOURCE_SCHEMA, "Unsupported source catalog schema")
    _require(data["status"] == "SOURCES_ONLY", "Expected a source-only catalog")
    _require(_identifier(data["knowledge_space_id"]) and _identifier(data["artifact_id"]), "Invalid catalog ID")
    topics = [item["topic_id"] for item in data["planning_topics"]]
    _require(all(_identifier(topic) for topic in topics) and len(set(topics)) == len(topics),
             "Planning topic IDs must be valid and unique")
    _require(data["scope"]["country_code"] == "CH", "Expected Swiss jurisdiction")
    cantons = data["scope"]["canton_codes"]
    _require(len(cantons) == len(set(cantons)) and set(cantons) <= {f"CH-{code}" for code in CANTONS},
             "Invalid or duplicate cantonal scope")
    for values in data["crawl_profiles"].values():
        _require(set(values) == {field.name for field in fields(CrawlLimits)}, "Specify every crawl limit explicitly")
        for key, value in values.items():
            _require(type(value) in {int, float} and math.isfinite(value), f"Invalid numeric limit: {key}")
            if not key.endswith("seconds"):
                _require(type(value) is int, f"Expected integer limit: {key}")
        CrawlLimits(**values)
    ids: set[str] = set()
    urls: set[str] = set()
    _require(bool(data["sources"]), "Source list cannot be empty")
    for entry in data["sources"]:
        source = source_definition(entry)
        _require(_identifier(source.source_id) and source.source_id not in ids, "Invalid or duplicate source ID")
        _https_url(source.start_url)
        _require(source.start_url not in urls, "Duplicate seed URL")
        _require(bool(source.canonical_authority), "Missing canonical authority")
        _require(source.jurisdiction in {"CH", *cantons}, "Source jurisdiction outside catalog scope")
        _require(source.language in {"en", "de", "fr", "it", "rm"}, "Invalid seed language hint")
        _require(entry["authority_level"] in {"federal", "cantonal", "municipal"}, "Invalid authority level")
        _require((entry["authority_level"] == "federal") == (source.jurisdiction == "CH"), "Authority/jurisdiction mismatch")
        if entry["authority_level"] == "municipal":
            _require(bool(entry["municipality"]["name"]) and re.fullmatch(r"[0-9]{4}", entry["municipality"]["bfs_code"]) is not None,
                     "Municipal sources require an explicit municipality and BFS code")
        _require(entry["priority"] in {"P0", "P1", "P2"}, "Invalid source priority")
        _require(entry["scan_status"] in SCAN_STATUSES, "Invalid scan status")
        _require(bool(entry["title"]) and bool(entry["notes"]), "Missing source title or scan notes")
        _require(bool(entry["topic_hints"]) and set(entry["topic_hints"]) <= set(topics), "Unknown planning topic")
        _require(bool(source.allowed_hosts) and urlsplit(source.start_url).hostname in source.allowed_hosts,
                 "Seed host must be explicitly allowlisted")
        for prefix in source.allowed_path_prefixes:
            _require((unquote(prefix) == prefix and posixpath.normpath(prefix) == prefix.rstrip("/")) or prefix == "/",
                     "Path prefixes must be canonical and decoded")
            _require("?" not in prefix and "#" not in prefix and "\\" not in prefix,
                     "Path prefixes cannot contain queries, fragments or backslashes")
        _require(_in_paths(urlsplit(source.start_url).path or "/", list(source.allowed_path_prefixes)),
                 "Seed path must be inside its allowlist")
        _https_url(entry["discovery"]["reference_url"])
        date.fromisoformat(entry["discovery"]["located_on"])
        _require(entry["discovery"]["method"] in {"official_search_result", "official_page_link", "official_directory_link"},
                 "Unknown discovery method")
        ids.add(source.source_id)
        urls.add(source.start_url)
    for name, members in data["scan_sets"].items():
        _require(_identifier(name) and bool(members) and len(set(members)) == len(members) and set(members) <= ids,
                 "Scan sets require unique, known source IDs")
    return data


def build_plan(data: dict, *, scan_set: str = "smoke", source_ids: list[str] | None = None,
               profile: str = "smoke") -> dict:
    if profile not in data["crawl_profiles"]:
        raise ValueError(f"Unknown crawl profile: {profile}")
    if source_ids is None and scan_set not in data["scan_sets"]:
        raise ValueError(f"Unknown scan set: {scan_set}")
    selected = set(source_ids if source_ids is not None else data["scan_sets"][scan_set])
    known = {entry["definition"]["source_id"] for entry in data["sources"]}
    _require(bool(selected) and selected <= known, "Select at least one known source ID")
    entries = sorted((entry for entry in data["sources"] if entry["definition"]["source_id"] in selected),
                     key=lambda entry: entry["definition"]["source_id"])
    ready = [entry for entry in entries if entry["scan_status"] == "ready"]
    limits = asdict(CrawlLimits(**data["crawl_profiles"][profile]))
    return {
        "schema_version": "swisstip.source-plan/v1", "mode": "dry-run",
        "knowledge_space_id": data["knowledge_space_id"],
        "catalog_ref": {"artifact_id": data["artifact_id"], "version": data["version"], "sha256": content_hash(data)},
        "profile": profile, "limits_per_source": limits,
        "aggregate_ceilings": {key: limits[key] * len(ready) for key in
                               ("max_pages", "max_requests", "max_total_bytes", "max_duration_seconds")},
        "policies": {"robots_txt": "required; failures deny crawling", "concurrency": 1,
                     "query_strings": False, "private_networks": False, "redirects": "allowlist-checked per hop",
                     "duration_scope": "Sum of per-source crawler budgets; inter-source delays and local I/O are additional."},
        "sources": entries,
        "ready_source_count": len(ready),
        "excluded_sources": [{"source_id": entry["definition"]["source_id"],
                              "reason": entry["scan_status"], "notes": entry["notes"]}
                             for entry in entries if entry["scan_status"] != "ready"],
    }
