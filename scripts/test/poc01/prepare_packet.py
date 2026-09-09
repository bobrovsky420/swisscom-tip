"""Preserve POC-01 inputs and prepare source-only review without model calls."""
from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
import hashlib
import html
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import uuid

from swisstip.ingestion.concepts import normalize_downloaded_page

ROOT = Path(__file__).resolve().parents[3]
SUPPORT = Path(__file__).resolve().parent
MANIFEST = "preservation-manifest.json"


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative_file(root: Path, relative: str) -> Path:
    """Reject absolute/traversing paths rather than trusting imported manifests."""
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("Manifest paths must be portable relative paths")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or not parts.parts or any(p in ("..", ".") for p in parts.parts):
        raise ValueError("Manifest path escapes its root")
    result = root.joinpath(*parts.parts)
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError("Manifest path escapes its root")
    return result


def files_below(root: Path) -> list[Path]:
    paths = []
    for path in root.rglob("*"):
        # Do not preserve a link by following it into unrelated private data.
        junction = getattr(path, "is_junction", lambda: False)()
        if path.is_symlink() or junction:
            raise ValueError(f"Links are unsupported in experiment inputs: {path}")
        if path.is_file():
            paths.append(path)
    return sorted(paths)


def check_download_manifest(source: Path) -> list[dict]:
    manifest = load_json(source / "download-manifest.json")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("Download manifest must contain source pages")
    if manifest.get("page_count") != len(pages):
        raise ValueError("Download manifest page count differs")
    seen = set()
    total = 0
    for page in pages:
        relative = page["relative_path"]
        if relative in seen:
            raise ValueError("Duplicate source path in download manifest")
        seen.add(relative)
        path = relative_file(source / "pages", relative)
        if not path.is_file() or digest(path) != page["sha256"]:
            raise ValueError(f"Source SHA-256 mismatch: {relative}")
        if path.stat().st_size != page["bytes"]:
            raise ValueError(f"Source byte count mismatch: {relative}")
        if not isinstance(page.get("url"), str) or not page["url"]:
            raise ValueError("Each source requires its original URL")
        total += path.stat().st_size
    if manifest.get("total_bytes") != total:
        raise ValueError("Download manifest total byte count differs")
    return pages


def inert_html(title: str, text: str) -> str:
    return ('<!doctype html>\n<html><head><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<style>body{font:16px/1.6 system-ui,sans-serif;max-width:76rem;margin:2rem auto;padding:0 1rem}'
            'pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}h1{line-height:1.25}</style>'
            f'<title>{html.escape(title)}</title></head><body>'
            f'<h1>{html.escape(title)}</h1><pre>{html.escape(text)}</pre></body></html>\n')


def git_output(repo: Path, *arguments: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *arguments],
                            capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else "UNAVAILABLE"


def freeze_metadata(destination: Path, repo: Path) -> dict:
    selected = {SUPPORT / name for name in (
        "prepare_packet.py", "review-schema.json", "evaluation-suite.json", "REVIEW.md", "README.md")}
    selected.add(repo / "config/semantic-models.toml")
    selected.add(repo / "config/model-profiles.toml")
    for base in (repo / "packages/ingestion/src", repo / "apps/knowledge-builder/src", repo / "packages/core/src"):
        selected.update(base.rglob("*.py"))
    selected.update((repo / "packages/core/schemas").rglob("*.json"))
    selected.update(repo / p for p in (
        "packages/ingestion/pyproject.toml", "packages/core/pyproject.toml",
        "apps/knowledge-builder/pyproject.toml", "TODO.md",
        "docs/product/product-functional-specification.md",
        "docs/architecture/technical-specification.md",
        "docs/experiments/2026-09-06-poc-01-semantic-ground-truth.md",
        "apps/knowledge-builder/tests/test_poc01_packet.py"))
    records = []
    for original in sorted(selected):
        if not original.is_file():
            continue
        relative = (original.relative_to(repo).as_posix() if original.is_relative_to(repo)
                    else f"scripts/test/poc01/{original.name}")
        copied = relative_file(destination / "metadata/frozen", relative)
        copied.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, copied)
        records.append({"path": relative, "sha256": digest(copied)})
    identity = {"created_at": timestamp(), "code_revision": git_output(repo, "rev-parse", "HEAD"),
                "working_tree_status": git_output(repo, "status", "--porcelain"),
                "python_version": sys.version, "files": records,
                "configuration_note": "Current configuration snapshot; no inference executed. Historical manifests remain unchanged in archive.",
                "normalization": {"function": "swisstip.ingestion.concepts.normalize_downloaded_page",
                                  "preserve_structure": True, "fidelity": "UNVALIDATED"}}
    write_json(destination / "metadata/build-identity.json", identity)
    return identity


def make_reviewer(destination: Path, pages: list[dict], reviewer: str) -> list[dict]:
    schema = load_json(SUPPORT / "review-schema.json")
    review = destination / "reviewer"
    review.mkdir()
    rows, mappings, links = [], [], []
    for ordinal, source in enumerate(pages, 1):
        page_id = f"source-{ordinal:02d}"
        relative = f"pages/{source['relative_path']}"
        raw = relative_file(destination / "archive", relative)
        normalized = normalize_downloaded_page(raw, preserve_structure=True)
        page_dir = review / "sources" / page_id
        page_dir.mkdir(parents=True)
        sections = [{**section.content_dict(), "evidence_text": section.evidence_text}
                    for section in normalized.sections]
        value = {"page_id": page_id, "document_id": normalized.document_id,
                 "source_url": source["url"], "source_sha256": source["sha256"],
                 "normalized_sha256": normalized.content_hash, "title": normalized.title,
                 "language_hint": normalized.language, "source_language_validated": False,
                 "preserve_structure": True, "sections": sections}
        write_json(page_dir / "normalized.json", value)
        normalized_text = "\n\n".join(
            f"[{section['section_id']}]\n{section['evidence_text']}" for section in sections)
        (page_dir / "normalized.html").write_text(
            inert_html(f"{page_id}: normalized source (fidelity unvalidated)", normalized_text), encoding="utf-8")
        (page_dir / "raw-source.html").write_text(
            inert_html(f"{page_id}: full escaped original HTML", raw.read_bytes().decode("utf-8-sig")), encoding="utf-8")
        links.append(f'<li>{page_id}: {html.escape(source["url"])} - '
                     f'<a href="sources/{page_id}/normalized.html">normalized sections</a> - '
                     f'<a href="sources/{page_id}/raw-source.html">full inert source</a></li>')
        mappings.append({"page_id": page_id, "original_relative_path": source["relative_path"],
                         "archived_relative_path": f"archive/{relative}",
                         "reviewer_relative_path": f"reviewer/sources/{page_id}/normalized.json",
                         "source_url": source["url"], "source_sha256": source["sha256"]})
        for number in range(1, 11):
            row = dict.fromkeys(schema["columns"], "")
            row.update(gold_id=f"{page_id}-gold-{number:02d}", page_id=page_id,
                       source_url=source["url"], source_sha256=source["sha256"],
                       split="development", primary_reviewer=reviewer,
                       same_person_rereviewer=reviewer)
            rows.append(row)
    with (review / "gold.csv").open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=schema["columns"])
        writer.writeheader()
        writer.writerows(rows)
    index = ('<!doctype html><html><head><meta charset="utf-8">'
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
             'base-uri \'none\'; form-action \'none\'">'
             '<title>POC-01 source-only review</title></head><body><h1>POC-01 source-only review</h1>'
             '<p>Read <a href="REVIEW.md">the review instructions</a> before editing '
             '<a href="gold.csv">the worksheet (gold.csv)</a>. No model proposals are included. '
             'Compare normalized sections with the full inert source; normalization is unvalidated.</p><ul>'
             + "".join(links) + '</ul></body></html>\n')
    (review / "index.html").write_text(index, encoding="utf-8")
    shutil.copy2(SUPPORT / "REVIEW.md", review / "REVIEW.md")
    shutil.copy2(SUPPORT / "review-schema.json", review / "review-schema.json")
    return mappings


def prepare_packet(source: Path, destination: Path, *, repo: Path = ROOT, reviewer: str = "user") -> dict:
    source, destination, repo = source.resolve(), destination.resolve(), repo.resolve()
    if not destination.is_relative_to(repo / ".local"):
        raise ValueError("Review packets must stay under the repository's ignored .local directory")
    if source == destination or source.is_relative_to(destination) or destination.is_relative_to(source):
        raise ValueError("Source and destination must not overlap")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Destination is nonempty; use verify or a new destination. Annotations are never overwritten.")
    originals = files_below(source)
    pages = check_download_manifest(source)
    original_records = [{"path": p.relative_to(source).as_posix(), "bytes": p.stat().st_size,
                         "sha256": digest(p)} for p in originals]
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination / "archive")
    copied_paths = [p.relative_to(destination / "archive").as_posix()
                    for p in files_below(destination / "archive")]
    if copied_paths != [record["path"] for record in original_records]:
        raise ValueError("Artifact inventory changed during preservation; use a new destination")
    for record in original_records:
        copied = relative_file(destination / "archive", record["path"])
        if digest(copied) != record["sha256"] or copied.stat().st_size != record["bytes"]:
            raise ValueError("Artifact changed during preservation; use a new destination")
    check_download_manifest(destination / "archive")
    identity = freeze_metadata(destination, repo)
    mappings = make_reviewer(destination, pages, reviewer)
    write_json(destination / "metadata/source-map.json", {
        "original_root": str(source), "original_manifest_path": str(source / "download-manifest.json"),
        "archived_manifest_path": "archive/download-manifest.json", "sources": mappings})
    files = [{"path": p.relative_to(destination).as_posix(), "bytes": p.stat().st_size,
              "sha256": digest(p)} for p in files_below(destination)
             if p != destination / "reviewer/gold.csv"]
    manifest = {"schema_version": "swisstip.poc01-preservation/v1", "created_at": timestamp(),
                "status": "PREPARED_NOT_EVALUATED", "original_root": str(source),
                "original_files": original_records, "files": files,
                "mutable_paths": ["reviewer/gold.csv"],
                "initial_gold_sha256": digest(destination / "reviewer/gold.csv"),
                "source_count": len(pages), "corpus_role": "development",
                "primary_reviewer": reviewer, "second_pass": "same-person re-review",
                "independent_adjudication": "PENDING", "code_revision": identity["code_revision"]}
    write_json(destination / MANIFEST, manifest)
    (destination / f"{MANIFEST}.sha256").write_text(digest(destination / MANIFEST) + "\n", encoding="ascii")
    return verify_packet(destination)


def verify_packet(destination: Path) -> dict:
    destination = destination.resolve()
    manifest_path = destination / MANIFEST
    if digest(manifest_path) != (destination / f"{MANIFEST}.sha256").read_text(encoding="ascii").strip():
        raise ValueError("Preservation manifest checksum differs")
    manifest = load_json(manifest_path)
    expected = set()
    for record in manifest["files"]:
        path = relative_file(destination, record["path"])
        expected.add(record["path"])
        if not path.is_file() or path.stat().st_size != record["bytes"] or digest(path) != record["sha256"]:
            raise ValueError(f"Preserved file differs: {record['path']}")
    actual = {p.relative_to(destination).as_posix() for p in files_below(destination)
              if not p.is_relative_to(destination / "review-freezes")}
    allowed = expected | set(manifest["mutable_paths"]) | {MANIFEST, f"{MANIFEST}.sha256"}
    if actual != allowed:
        raise ValueError("Packet file inventory differs (unexpected or missing files)")
    check_download_manifest(destination / "archive")
    freezes = destination / "review-freezes"
    if freezes.exists():
        for freeze in freezes.iterdir():
            freeze_manifest = freeze / "freeze-manifest.json"
            if not freeze.is_dir() or {p.name for p in freeze.iterdir()} != {
                    "gold.csv", "validated-gold.json", "freeze-manifest.json", "freeze-manifest.json.sha256"}:
                raise ValueError("Review freeze inventory differs")
            if digest(freeze_manifest) != (freeze / "freeze-manifest.json.sha256").read_text(encoding="ascii").strip():
                raise ValueError("Review freeze manifest checksum differs")
            frozen = load_json(freeze_manifest)
            if digest(freeze / "gold.csv") != frozen["gold_sha256"]:
                raise ValueError("Frozen gold worksheet checksum differs")
            if digest(freeze / "validated-gold.json") != frozen["validated_gold_sha256"]:
                raise ValueError("Validated gold checksum differs")
            if frozen["preservation_manifest_sha256"] != digest(manifest_path):
                raise ValueError("Review freeze belongs to a different preservation manifest")
    return {"status": "VERIFIED_PRESERVATION_ONLY", "source_count": manifest["source_count"],
            "artifact_count": len(manifest["original_files"]),
            "manifest_sha256": digest(manifest_path), "destination": str(destination)}


def validate_gold(destination: Path, stage: str) -> list[dict]:
    schema = load_json(destination / "reviewer/review-schema.json")
    mapping = load_json(destination / "metadata/source-map.json")["sources"]
    pages = {item["page_id"]: item for item in mapping}
    manifest = load_json(destination / MANIFEST)
    with (destination / "reviewer/gold.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != schema["columns"]:
            raise ValueError("Gold worksheet columns differ from frozen review schema")
        rows = list(reader)
    selected, identifiers = [], set()
    counts = dict.fromkeys(pages, 0)
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Gold worksheet has malformed CSV rows")
        if row["gold_id"] in identifiers:
            raise ValueError("Duplicate gold identifier")
        identifiers.add(row["gold_id"])
        if row["page_id"] not in pages:
            raise ValueError("Unknown source page in gold worksheet")
        page = pages[row["page_id"]]
        if any(row[field] != page[field] for field in ("source_url", "source_sha256")) or row["split"] != "development":
            raise ValueError("Historical corpus identity/split cannot be changed in gold worksheet")
        if row["primary_reviewer"] != manifest["primary_reviewer"] or row["same_person_rereviewer"] != manifest["primary_reviewer"]:
            raise ValueError("Reviewer identity differs from declared same-person review protocol")
        if row["independent_adjudicator"] or row["independent_adjudication"]:
            raise ValueError("Independent adjudication needs a separately documented protocol; same-person review cannot claim it")
        if not row["label"].strip():
            continue
        if any(not row[field].strip() for field in schema["required_for_labeled_row"]):
            raise ValueError(f"Incomplete labeled row: {row['gold_id']}")
        try:
            minutes = float(row["review_minutes"])
        except ValueError as exc:
            raise ValueError("Review minutes must be a finite nonnegative number") from exc
        if not math.isfinite(minutes) or minutes < 0:
            raise ValueError("Review minutes must be a finite nonnegative number")
        normalized = load_json(relative_file(destination, page["reviewer_relative_path"]))
        sections = {section["section_id"]: section["evidence_text"] for section in normalized["sections"]}
        refs = json.loads(row["evidence_refs_json"])
        if not isinstance(refs, list) or not refs:
            raise ValueError("A labeled concept needs exact source evidence")
        validated_refs = []
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) not in (
                    {"section_id", "quote"}, {"section_id", "start", "end", "quote"}):
                raise ValueError("Malformed evidence reference")
            if not isinstance(ref["section_id"], str) or not isinstance(ref["quote"], str) or not ref["quote"]:
                raise ValueError("Evidence references need a section identifier and nonempty exact quote")
            text = sections.get(ref["section_id"])
            if text is None:
                raise ValueError(f"Unknown evidence section: {ref['section_id']}")
            if "start" not in ref:
                start = text.find(ref["quote"])
                if start < 0:
                    raise ValueError(f"Evidence span mismatch: {row['gold_id']} (quote is absent from the section)")
                if text.find(ref["quote"], start + 1) >= 0:
                    raise ValueError(f"Ambiguous evidence quote: {row['gold_id']}; include more unique text or explicit start/end offsets")
                end = start + len(ref["quote"])
            else:
                start, end = ref["start"], ref["end"]
            if (text is None or type(start) is not int or type(end) is not int or
                    not 0 <= start < end <= len(text) or text[start:end] != ref["quote"]):
                raise ValueError(f"Evidence span mismatch: {row['gold_id']}")
            validated_refs.append({**ref, "start": start, "end": end})
        counts[row["page_id"]] += 1
        if stage == "full-gold" or row["first_batch"].strip().lower() == "yes":
            if stage == "initial-batch" and not row["risk_reason"].strip():
                raise ValueError("First-batch concepts require the reviewer's risk reason")
            selected.append({**row, "validated_evidence_refs": validated_refs})
    if stage == "initial-batch" and not 10 <= len(selected) <= 15:
        raise ValueError("Initial batch requires 10-15 reviewer-selected, labeled concepts")
    if stage == "full-gold" and any(not 5 <= count <= 10 for count in counts.values()):
        raise ValueError("Full gold requires 5-10 labeled concepts per source page")
    return selected


def freeze_review(destination: Path, *, stage: str = "initial-batch") -> dict:
    if stage not in ("initial-batch", "full-gold"):
        raise ValueError("Unknown review freeze stage")
    verify_packet(destination)
    before = digest(destination / "reviewer/gold.csv")
    rows = validate_gold(destination, stage)
    freeze = destination / "review-freezes" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8])
    freeze.mkdir(parents=True)
    shutil.copy2(destination / "reviewer/gold.csv", freeze / "gold.csv")
    if digest(freeze / "gold.csv") != before or digest(destination / "reviewer/gold.csv") != before:
        raise ValueError("Review worksheet changed during freeze; retry without editing")
    write_json(freeze / "validated-gold.json", {
        "schema_version": "swisstip.poc01-validated-gold/v1", "stage": stage, "rows": rows})
    result = {"schema_version": "swisstip.poc01-review-freeze/v1", "created_at": timestamp(),
              "stage": stage, "status": "GOLD_SNAPSHOT_NOT_EVALUATION_PASS", "selected_count": len(rows),
              "selected_gold_ids": [row["gold_id"] for row in rows],
              "gold_sha256": before, "preservation_manifest_sha256": digest(destination / MANIFEST),
              "validated_gold_sha256": digest(freeze / "validated-gold.json"),
              "corpus_role": "development", "second_pass": "same-person re-review",
              "independent_adjudication": "PENDING", "holdout": "PENDING", "live_comparison": "PENDING"}
    write_json(freeze / "freeze-manifest.json", result)
    (freeze / "freeze-manifest.json.sha256").write_text(digest(freeze / "freeze-manifest.json") + "\n", encoding="ascii")
    return {"status": result["status"], "selected_count": len(rows), "freeze": str(freeze)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "verify", "freeze-review"))
    parser.add_argument("--source", type=Path, default=Path(tempfile.gettempdir()) / "swisstip-zhch-poc")
    parser.add_argument("--destination", type=Path, default=ROOT / ".local/experiments/poc-01")
    parser.add_argument("--reviewer", default="user")
    parser.add_argument("--stage", choices=("initial-batch", "full-gold"), default="initial-batch")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare_packet(args.source, args.destination, reviewer=args.reviewer)
        elif args.command == "verify":
            result = verify_packet(args.destination)
        else:
            result = freeze_review(args.destination, stage=args.stage)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, f"POC-01: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
