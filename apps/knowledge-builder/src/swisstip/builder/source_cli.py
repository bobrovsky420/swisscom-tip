"""Plan offline by default; explicitly crawl selected sources for later extraction."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Sequence

from swisstip.ingestion import CrawlLimits, SafeCrawler
from swisstip.ingestion.crawler import CrawledPage

from .source_catalog import build_plan, load_source_catalog, source_definition


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def crawl_plan(plan: dict, output: Path) -> dict:
    """Save the exact HTML bytes already fetched by SafeCrawler, with provenance."""
    ready = [entry for entry in plan["sources"] if entry["scan_status"] == "ready"]
    if not ready:
        raise ValueError("No eligible sources; review the exclusions before crawling")
    # A new run directory prevents mixing snapshots or overwriting earlier experiments.
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "plan.json", plan)
    limits = CrawlLimits(**plan["limits_per_source"])
    results = []
    for index, entry in enumerate(ready):
        # Each SafeCrawler enforces its origin's robots delay internally. Preserve
        # that effective delay across separately configured seeds as well.
        if index:
            time.sleep(max(limits.delay_seconds, results[-1]["report"]["effective_delay_seconds"]))
        definition = source_definition(entry)
        print(f"Scanning {index + 1}/{len(ready)}: {definition.source_id}", file=sys.stderr, flush=True)
        source_dir = output / definition.source_id
        pages_dir = source_dir / "pages"
        pages_dir.mkdir(parents=True)
        snapshots: list[dict] = []

        def save_page(page: CrawledPage, body: bytes) -> None:
            name = hashlib.sha256(page.requested_url.encode("utf-8")).hexdigest() + ".html"
            destination = pages_dir / name
            with destination.open("xb") as stream:
                stream.write(body)
            snapshots.append({
                **asdict(page), "source_id": definition.source_id,
                "catalog_ref": plan["catalog_ref"],
                "relative_path": destination.relative_to(output).as_posix(),
                "source_language_hint": definition.language,
                "declared_language": None, "detected_language": None,
                "language_validation_status": "PENDING_NORMALIZATION",
            })

        report = SafeCrawler(definition, limits, on_page=save_page).crawl()
        result = {"source": entry, "snapshots": snapshots, "report": report.to_dict(),
                  "status": "captured" if snapshots and not report.failures else "incomplete"}
        _write_json(source_dir / "manifest.json", result)
        results.append(result)
    result = {"schema_version": "swisstip.source-scan/v1", "mode": "crawl",
              "knowledge_space_id": plan["knowledge_space_id"], "catalog_ref": plan["catalog_ref"],
              "excluded_sources": plan["excluded_sources"], "results": results,
              "saved_html_pages": sum(len(item["snapshots"]) for item in results),
              "extraction_status": "NOT_RUN"}
    _write_json(output / "scan.json", result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path("config/catalogs/hackathon.sources.json"))
    selectors = parser.add_mutually_exclusive_group()
    selectors.add_argument("--set", dest="scan_set", default="smoke", help="named scan set; default: smoke")
    selectors.add_argument("--source", action="append", help="explicit source ID; repeatable")
    parser.add_argument("--profile", default="smoke", help="crawl budget profile; default: smoke")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="offline validation and plan (the default)")
    modes.add_argument("--crawl", action="store_true", help="make bounded HTTP requests and save HTML")
    parser.add_argument("--output", type=Path, help="new directory required with --crawl")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args(argv)
    if args.crawl != (args.output is not None):
        parser.error("--crawl and --output must be supplied together")
    try:
        data = load_source_catalog(args.catalog)
        plan = build_plan(data, scan_set=args.scan_set, source_ids=args.source, profile=args.profile)
        result = crawl_plan(plan, args.output) if args.crawl else plan
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=None if args.compact else 2)
    sys.stdout.write("\n")
    return int(args.crawl and any(item["status"] != "captured" for item in result["results"]))


if __name__ == "__main__":
    raise SystemExit(main())
