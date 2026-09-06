"""Offline v4 review packets and revision-bound decision import; never publication."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

FIELDS = ["item_id", "report_sha256", "kind", "target_id", "decision", "notes"]
DECISIONS = {"pending", "accept", "correction", "reject", "defer"}


def read_report(path):
    raw = Path(path).read_bytes()
    report = json.loads(raw.decode("utf-8-sig"))
    reports = report.get("reports", [report])
    if not reports or any(r.get("prompt_profile") != "concept_extraction_v4" or
                          r.get("schema_version") != "swisstip.concept-proposal-report/v2" for r in reports):
        raise ValueError("review packets require nonempty v4 extraction reports")
    return raw, reports, hashlib.sha256(raw).hexdigest()


def review_items(reports, digest):
    items = []
    for report_index, report in enumerate(reports):
        candidates = {c["candidate_id"]: c for c in report["candidates"]}
        blocks = {b["section_id"]: b for b in report["source_inventory"]}
        for queue_index, entry in enumerate(report["human_review_queue"]):
            kind = "candidate" if "candidate_id" in entry else "source_block"
            target = entry.get("candidate_id", entry.get("section_id"))
            key = hashlib.sha256(f"{digest}:{report_index}:{queue_index}:{target}".encode()).hexdigest()
            detail = candidates[target] if kind == "candidate" else blocks[target]
            items.append({"item_id": key, "report_sha256": digest, "kind": kind,
                          "target_id": target, "decision": "pending", "notes": "",
                          "detail": detail, "queue_entry": entry, "source": report["source"],
                          "input_hash": report["input_hash"], "output_hash": report["output_hash"]})
    return items


def export_packet(report_path, output_dir):
    raw, reports, digest = read_report(report_path)
    items = review_items(reports, digest)
    directory = Path(output_dir)
    # A fresh directory prevents accidental replacement of previous decisions.
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "report.json").write_bytes(raw)
    with (directory / "decisions.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(items)
    parts = ["<!doctype html><html lang='en'><meta charset='utf-8'><title>Extraction review</title>",
             "<style>body{max-width:1100px;margin:2em auto;font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere}section{border-top:1px solid #aaa;padding:1em 0}</style>",
             "<h1>Extraction review</h1><p>Review the proposed output against the source evidence. "
             "Edit only decision and notes in decisions.csv. Decisions: pending, accept, correction, reject, defer. "
             "Correction, reject and defer require notes. Accept means suitable for authoring review, never publication. "
             "For source blocks, accept acknowledges the recorded disposition; it does not certify complete extraction. "
             "Corrections are recorded for a new revision, not silently applied.</p>"]
    for item in items:
        title = item["detail"].get("preferred_label", item["target_id"])
        parts.append(f"<section><h2>{html.escape(item['kind'] + ': ' + title)}</h2>"
                     f"<p>Item: {item['item_id']}</p><pre>{html.escape(json.dumps(item, ensure_ascii=False, indent=2))}</pre></section>")
    parts.append("<h2>Full source inventory and revision history</h2><p>Inspect omitted blocks, rejected proposals and all model assessments here.</p>")
    parts.append("<pre>" + html.escape(json.dumps(reports, ensure_ascii=False, indent=2)) + "</pre></html>")
    (directory / "index.html").write_text("\n".join(parts), encoding="utf-8")
    return {"item_count": len(items), "report_sha256": digest, "directory": str(directory)}


def import_decisions(report_path, decisions_path, reviewer):
    if not reviewer or not reviewer.strip():
        raise ValueError("a human reviewer identity is required")
    _, reports, digest = read_report(report_path)
    expected = {item["item_id"]: item for item in review_items(reports, digest)}
    text = Path(decisions_path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if reader.fieldnames != FIELDS:
        raise ValueError("decision columns differ from the exported template")
    seen, decisions = set(), []
    for row in reader:
        item_id = row["item_id"]
        if item_id not in expected or item_id in seen:
            raise ValueError("unknown or duplicate review item")
        if set(row) != set(FIELDS) or any(row[field] != expected[item_id][field]
                                         for field in FIELDS[:4]):
            raise ValueError("decision is stale or does not match the original report revision")
        if row["decision"] not in DECISIONS:
            raise ValueError("unknown decision")
        if row["notes"] is None or (row["decision"] in {"correction", "reject", "defer"} and not row["notes"].strip()):
            raise ValueError("correction, reject and defer require notes")
        seen.add(item_id)
        decisions.append({**row, "input_hash": expected[item_id]["input_hash"],
                          "output_hash": expected[item_id]["output_hash"], "publication_eligible": False})
    if seen != set(expected):
        raise ValueError("decision file must retain every review item, including pending ones")
    return {"schema_version": "swisstip.extraction-human-decisions/v1", "report_sha256": digest,
            "reviewer": reviewer.strip(), "recorded_at": datetime.now(UTC).isoformat(),
            "decisions": decisions, "pending_count": sum(d["decision"] == "pending" for d in decisions),
            "publication_eligible": False, "verified_coverage": False,
            "scope": "authoring annotations; promotion and corrected revisions require separate validation"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export")
    export.add_argument("report", type=Path)
    export.add_argument("--output-dir", type=Path, required=True)
    record = commands.add_parser("import")
    record.add_argument("report", type=Path)
    record.add_argument("--decisions", type=Path, required=True)
    record.add_argument("--reviewer", required=True)
    args = parser.parse_args(argv)
    try:
        result = export_packet(args.report, args.output_dir) if args.command == "export" else import_decisions(args.report, args.decisions, args.reviewer)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"extraction-review: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
