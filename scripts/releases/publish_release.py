"""Copy a validated release into the repository's top-level releases/ folder.

This is the only sanctioned way to change what a clean checkout serves. The
release file is re-validated, its hash must match the builder's validation
report, the manifest entry is rewritten, and COVERAGE.md is regenerated.
Raw source snapshots are deliberately not copied; they are hash-referenced
provenance and stay under the Git-ignored corpus directories.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from swisstip.mcp_server.bundled import ENVIRONMENT_VARIABLE, MANIFEST_NAME, MANIFEST_SCHEMA, sha256
from swisstip.runtime.release import ReleaseBundle, validate_release

ROOT = Path(__file__).resolve().parents[2]
RELEASES_DIR = ROOT / "releases"
MANIFEST_PATH = RELEASES_DIR / MANIFEST_NAME
FILES = ["release.json", "validation.json", "provenance.json", "mcp-requests.json", "external-artifacts.json",
         "contacts.json", "source-disposition.json", "unavailable.json", "README.md"]
DIRECTORIES = ["controls"]


def publish(source: Path, *, activate: bool) -> dict:
    validation = json.loads((source / "validation.json").read_text(encoding="utf-8"))
    release_path = source / "release.json"
    digest = sha256(release_path)
    if digest != validation.get("release_sha256"):
        raise ValueError("release_hash_mismatch: release.json differs from validation.json")
    bundle = ReleaseBundle.model_validate_json(release_path.read_bytes())
    validate_release(bundle)
    release_id = bundle.release.release_id
    if release_id != validation.get("release_id"):
        raise ValueError("release_id_mismatch: release.json differs from validation.json")
    target = RELEASES_DIR / release_id
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    if ENVIRONMENT_VARIABLE in os.environ:
        print(f"note: {ENVIRONMENT_VARIABLE} is set; this script always publishes into {RELEASES_DIR}", file=sys.stderr)
    for name in FILES:
        if (source / name).is_file():
            shutil.copyfile(source / name, target / name)
    for name in DIRECTORIES:
        if (source / name).is_dir():
            shutil.copytree(source / name, target / name)
    manifest = (json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.is_file()
                else {"schema_version": MANIFEST_SCHEMA, "active_release_id": None, "releases": []})
    profiles = bundle.catalog.coverage_profiles
    entry = dict(
        release_id=release_id, path=f"{release_id}/release.json", sha256=digest,
        created_at=bundle.release.created_at,
        snapshot_dates=validation.get("source_snapshot_dates"),
        documents=len(bundle.documents), concepts=sum(1 for e in bundle.catalog.entries if e.kind == "concept"),
        facts=len(bundle.facts), evidence=len(bundle.evidence), rules=len(bundle.rules), coverage_profiles=len(profiles),
        freshness_days=sorted({p.freshness_policy.max_age_days for p in profiles}),
        temporal_coverage=validation.get("temporal_coverage"),
        published_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source=str(source.relative_to(ROOT)).replace("\\", "/") if source.is_relative_to(ROOT) else str(source),
        excluded=["sources/ (raw snapshots, hash-referenced provenance)", "semantic-extraction.json (derived export)",
                  "mcp-client.json (machine-specific paths)"])
    manifest["releases"] = [e for e in manifest["releases"] if e["release_id"] != release_id] + [entry]
    if activate or not manifest.get("active_release_id"):
        manifest["active_release_id"] = release_id
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return entry


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Release directory written by a builder, with validation.json")
    parser.add_argument("--activate", action="store_true", help="Serve this release by default")
    parser.add_argument("--no-coverage", action="store_true", help="Skip regenerating COVERAGE.md")
    args = parser.parse_args(argv)
    entry = publish(args.source.resolve(), activate=args.activate)
    print(json.dumps(entry, indent=2))
    if not args.no_coverage:
        subprocess.run([sys.executable, str(ROOT / "scripts/releases/coverage_report.py"), "--output", str(ROOT / "COVERAGE.md")], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
