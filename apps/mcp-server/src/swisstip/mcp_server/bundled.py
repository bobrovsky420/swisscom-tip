"""Releases shipped with the repository, so a clean checkout serves real knowledge.

The releases live in a top-level `releases/` folder next to the code. Its
`MANIFEST.json` lists every release with the SHA-256 of its release file and
names the one served by default. The folder is located in this order:

1. an explicit path (the server's `--releases-dir`),
2. the `SWISSTIP_RELEASES_DIR` environment variable,
3. walking up from this package file to a directory containing
   `releases/MANIFEST.json` (an editable install or a copied checkout),
4. walking up from the current working directory.

Hashes are verified before a path is handed to the release store; a mismatch
is an error, never a silent fallback.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

MANIFEST_NAME = "MANIFEST.json"
MANIFEST_SCHEMA = "bundled-releases/v1"
ENVIRONMENT_VARIABLE = "SWISSTIP_RELEASES_DIR"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _walk_up(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        if (candidate / "releases" / MANIFEST_NAME).is_file():
            return candidate / "releases"
    return None


def locate_releases_dir(explicit: Path | str | None = None) -> Path:
    """Return the releases folder, or raise FileNotFoundError naming what was tried."""
    tried = []
    if explicit:
        path = Path(explicit).resolve()
        if (path / MANIFEST_NAME).is_file():
            return path
        raise FileNotFoundError(f"No {MANIFEST_NAME} in the given releases directory {path}")
    configured = os.environ.get(ENVIRONMENT_VARIABLE, "").strip()
    if configured:
        path = Path(configured).resolve()
        if (path / MANIFEST_NAME).is_file():
            return path
        tried.append(f"{ENVIRONMENT_VARIABLE}={path}")
    for start in (Path(__file__).resolve().parent, Path.cwd().resolve()):
        found = _walk_up(start)
        if found is not None:
            return found
        tried.append(f"walk up from {start}")
    raise FileNotFoundError("No releases/" + MANIFEST_NAME + " found; tried " + "; ".join(tried))


def read_manifest(directory: Path | str | None = None) -> tuple[Path, dict]:
    """The located releases folder and its parsed manifest."""
    releases = locate_releases_dir(directory)
    data = json.loads((releases / MANIFEST_NAME).read_text(encoding="utf-8"))
    if data.get("schema_version") != MANIFEST_SCHEMA:
        raise ValueError("unsupported_bundled_manifest_schema")
    if not data.get("releases"):
        raise ValueError("bundled_manifest_lists_no_releases")
    return releases, data


def bundled_releases(directory: Path | str | None = None) -> tuple[list[Path], str]:
    """Verified paths of every bundled release file, and the active release ID."""
    releases, data = read_manifest(directory)
    paths = []
    identifiers = set()
    for entry in data["releases"]:
        path = releases / entry["path"]
        if not path.is_file():
            raise FileNotFoundError(f"Bundled release file missing: {path}")
        if sha256(path) != entry["sha256"]:
            raise ValueError(f"bundled_release_hash_mismatch: {entry['release_id']}")
        paths.append(path)
        identifiers.add(entry["release_id"])
    active = data.get("active_release_id")
    if active not in identifiers:
        raise ValueError("bundled_active_release_not_listed")
    return paths, active
