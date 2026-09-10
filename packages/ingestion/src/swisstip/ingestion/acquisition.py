"""Snapshot the exact public URLs in the MVP source catalogue, without link traversal."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from email.parser import BytesParser
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
from urllib.parse import urldefrag

from .crawler import CrawlLimits, SafeCrawler, SourceDefinition



DOCUMENT_TYPES = ("application/pdf", "application/octet-stream", "text/plain", "application/xml", "text/xml")
PRINT_LOCK = threading.Lock()


class CurlResponse(io.BytesIO):
    def __init__(self, body: bytes, headers: bytes) -> None:
        super().__init__(body)
        # Native curl may expose an initial proxy CONNECT header block.
        block = headers.strip().split(b"\r\n\r\n")[-1]
        status_line, _, fields = block.partition(b"\r\n")
        self.status = int(status_line.split()[1])
        self.headers = BytesParser().parsebytes(fields)

    def getcode(self) -> int:
        return self.status


class CurlOpener:
    """Use native certificate validation; SafeCrawler still controls every redirect."""

    def open(self, request, timeout=None):
        with tempfile.TemporaryDirectory() as directory:
            headers = Path(directory) / "headers"
            body = Path(directory) / "body"
            command = ["curl.exe" if os.name == "nt" else "curl", "--disable", "--silent", "--show-error",
                       "--proto", "=http,https", "--max-time", str(timeout or 20),
                       "--max-filesize", "25000000", "--dump-header", str(headers), "--output", str(body)]
            for key, value in request.header_items():
                command.extend(["--header", f"{key}: {value}"])
            command.append(request.full_url)
            completed = subprocess.run(command, capture_output=True, timeout=(timeout or 20) + 5,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            if completed.returncode:
                raise OSError(completed.stderr.decode(errors="replace").strip())
            return CurlResponse(body.read_bytes(), headers.read_bytes())


def now() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def saved_and_intact(result: dict, output: Path) -> bool:
    if result["status"] != "saved" or not result["snapshots"]:
        return False
    for item in result["snapshots"]:
        path = output / item["relative_path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            return False
    return True


def catalogue_targets(path: Path) -> list[dict]:
    content = path.read_text(encoding="utf-8")
    targets: dict[str, dict] = {}
    for match in re.finditer(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", content):
        url = urldefrag(match.group(2))[0]
        entry = targets.setdefault(url, {
            "url": url, "url_id": hashlib.sha256(url.encode()).hexdigest(), "references": [],
        })
        entry["references"].append({
            "label": " ".join(match.group(1).split()),
            "catalogue_line": content.count("\n", 0, match.start()) + 1,
        })
    return list(targets.values())


def snapshot(target: dict, output: Path, allowed_hosts: tuple[str, ...], transport: str = "urllib") -> dict:
    folder = output / "pages" / target["url_id"]
    folder.mkdir(parents=True, exist_ok=True)
    attempt_number = 1
    while (folder / f"attempt-{attempt_number:03d}").exists():
        attempt_number += 1
    attempt = folder / f"attempt-{attempt_number:03d}"
    attempt.mkdir()
    captured = []

    def save(page, body: bytes) -> None:
        suffix = ".pdf" if body.startswith(b"%PDF-") else {
            "text/html": ".html", "application/xhtml+xml": ".html",
            "text/plain": ".txt", "application/xml": ".xml", "text/xml": ".xml",
        }.get(page.content_type, ".bin")
        destination = attempt / ("response" + suffix)
        destination.write_bytes(body)
        flags = []
        if suffix == ".html":
            text = body.decode("utf-8", errors="replace").lower()
            if "<app-root" in text or "<fedlex" in text:
                flags.append("javascript_application_shell")
            if any(term in text for term in ("just a moment...", "checking your browser", "access denied")):
                flags.append("possible_access_challenge")
        captured.append({**asdict(page), "relative_path": destination.relative_to(output).as_posix(),
                         "review_flags": flags, "processing_status": "NOT_PROCESSED"})
        expected = target.get("expected_media_type")
        if expected and page.content_type != expected:
            flags.append("unexpected_media_type")

    limits = CrawlLimits(max_depth=0, max_pages=1, max_requests=16,
                         max_total_bytes=30_000_000, max_response_bytes=25_000_000,
                         max_duration_seconds=120, request_timeout_seconds=20,
                         delay_seconds=2, max_redirects=6, max_links_per_page=100,
                         max_queued_urls=1, max_failures=2)
    source = SourceDefinition(source_id=target["url_id"], start_url=target["url"],
                              allowed_hosts=allowed_hosts, allowed_path_prefixes=("/",))
    started = now()
    try:
        report = SafeCrawler(source, limits, allow_query_strings=True,
                             opener=CurlOpener() if transport == "curl" else None,
                             document_content_types=DOCUMENT_TYPES,
                             on_page=save, on_document=save).crawl().to_dict()
        result = {**target, "started_at": started, "finished_at": now(),
                  "status": "saved" if captured else "not_saved", "snapshots": captured,
                  "report": report, "transport": transport}
    except Exception as exc:
        result = {**target, "started_at": started, "finished_at": now(),
                  "status": "error", "snapshots": captured,
                  "error": f"{type(exc).__name__}: {exc}"}
    write_json(attempt / "manifest.json", result)
    write_json(folder / "latest.json", result)
    return result


def summary(output: Path, plan: dict) -> dict:
    results = []
    for target in plan["targets"]:
        path = output / "pages" / target["url_id"] / "latest.json"
        results.append(json.loads(path.read_text(encoding="utf-8")) if path.exists()
                       else {**target, "status": "pending", "snapshots": []})
    value = {"schema_version": "swisstip.catalogue-download/v1", "updated_at": now(),
             "catalogue_sha256": plan["catalogue_sha256"], "target_count": len(results),
             "counts": dict(Counter(item["status"] for item in results)),
             "saved_bytes": sum(s["bytes_downloaded"] for item in results for s in item["snapshots"]),
             "processing_status": "NOT_RUN", "results": results}
    value["resolution_errors"] = plan.get("resolution_errors", [])
    supplements = []
    for path in sorted(output.glob("*-documents/summary.json")):
        supplement = json.loads(path.read_text(encoding="utf-8"))
        supplements.append({"relative_path": path.relative_to(output).as_posix(),
                            "counts": supplement["counts"], "saved_bytes": supplement["saved_bytes"]})
    value["supplements"] = supplements
    write_json(output / "summary.json", value)
    lines = ["# Hackathon MVP source download", "", f"Updated: {value['updated_at']}", "",
             f"Targets: {len(results)}. Status counts: {value['counts']}.",
             f"Saved response bytes: {value['saved_bytes']}. No extraction or publication run.", "",
             "Only listed URLs were requested; links, assets and attachments were not recursively followed.",
             "Saved HTML can be a navigation page or JavaScript shell. See review flags and raw files.", "",
             ]
    for supplement in supplements:
        folder = Path(supplement["relative_path"]).parent.as_posix()
        lines.extend([f"[Source documents: {folder}]({folder}/README.md)", ""])
    for error in value["resolution_errors"]:
        lines.extend([f"Resolution failed: {error['source_url']}: {error['error']}", ""])
    lines.extend(["| Source | Status | Local response / reason |", "| --- | --- | --- |"])
    for item in results:
        if item["snapshots"]:
            detail = "; ".join(f"[response]({s['relative_path']}) " + ", ".join(s["review_flags"])
                               for s in item["snapshots"])
        else:
            report = item.get("report", {})
            detail = item.get("error") or "; ".join(
                [report.get("stop_reason", "pending")] +
                [s["reason"] for s in report.get("skipped", [])] +
                [f"HTTP {p['status']}: {p['outcome']}" for p in report.get("pages", [])])
        lines.append(f"| [{item['references'][0]['label']}]({item['url']}) | {item['status']} | {detail.replace('|', '/')} |")
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return value
