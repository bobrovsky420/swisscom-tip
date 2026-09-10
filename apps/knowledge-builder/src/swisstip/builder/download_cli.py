"""Download a catalogue's explicit URLs and resolve enabled source plugins."""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

from swisstip.ingestion.acquisition import (
    PRINT_LOCK, catalogue_targets, now, saved_and_intact, snapshot, summary, write_json,
)
from swisstip.ingestion.source_plugins import load_source_plugins

ROOT = Path.cwd()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue", type=Path, default=ROOT / "config/catalogs/hackathon.sources.md")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download", action="store_true", help="make requests; otherwise only save the plan")
    parser.add_argument("--retry-failed", action="store_true", help="retry unsuccessful URLs in an existing run")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=4)
    parser.add_argument("--transport", choices=("urllib", "curl"), default="urllib")
    plugins = parser.add_mutually_exclusive_group()
    plugins.add_argument("--source-plugin", action="append", help="enabled source plugin; repeatable; default: fedlex")
    plugins.add_argument("--no-source-plugins", action="store_true", help="only snapshot listed URLs")
    args = parser.parse_args()
    registry = load_source_plugins([] if args.no_source_plugins else args.source_plugin)
    args.output.mkdir(parents=True, exist_ok=True)
    plan_path = args.output / "plan.json"
    digest = hashlib.sha256(args.catalogue.read_bytes()).hexdigest()
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        if plan["catalogue_sha256"] != digest:
            parser.error("Catalogue changed; use a new output directory to preserve the original plan")
    else:
        targets = catalogue_targets(args.catalogue)
        hosts = {urlsplit(t["url"]).hostname for t in targets}
        # Explicit www aliases allow ordinary official-site redirects. No link crawling.
        hosts |= {host[4:] if host.startswith("www.") else "www." + host for host in list(hosts)}
        registry_path = args.catalogue.with_suffix(".json")
        source_registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {"sources": []}
        by_url = defaultdict(list)
        for entry in source_registry["sources"]:
            by_url[entry["definition"]["start_url"]].append(entry)
        for target in targets:
            target["registry_entries"] = by_url[target["url"]]
        plan = {"schema_version": "swisstip.catalogue-download-plan/v1", "created_at": now(),
                "catalogue": str(args.catalogue.resolve()), "catalogue_sha256": digest,
                "targets": targets, "allowed_redirect_hosts": sorted(hosts),
                "scope": "Exact Markdown URL inventory, depth zero; no recursive crawling",
                "workers": args.workers, "robots_policy": "required; fail closed",
                "max_response_bytes": 25_000_000}
        write_json(plan_path, plan)
        (args.output / "catalogue.md").write_bytes(args.catalogue.read_bytes())
    plugin_plan = {"enabled": registry.describe(), "sources": [
        {"url": t["url"], "plugin_id": p.plugin_id}
        for t in plan["targets"] if (p := registry.select(t["url"])) is not None]}
    write_json(args.output / "plugin-plan.json", plugin_plan)
    print(f"Planned {len(plan['targets'])} distinct URLs in {args.output}", flush=True)
    if not args.download:
        summary(args.output, plan)
        return 0
    groups = defaultdict(list)
    for target in plan["targets"]:
        latest = args.output / "pages" / target["url_id"] / "latest.json"
        if latest.exists():
            prior = json.loads(latest.read_text(encoding="utf-8"))
            if saved_and_intact(prior, args.output):
                continue
            if prior["status"] != "saved" and not args.retry_failed:
                continue
        host = urlsplit(target["url"]).hostname.removeprefix("www.")
        groups[host].append(target)

    def download_group(targets: list[dict]) -> None:
        for index, target in enumerate(targets):
            if index:
                time.sleep(max(2, result.get("report", {}).get("effective_delay_seconds", 2)))
            result = snapshot(target, args.output, tuple(plan["allowed_redirect_hosts"]), args.transport)
            with PRINT_LOCK:
                print(f"{result['status']}: {target['url']}", flush=True)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_group, targets) for targets in groups.values()]
        for future in as_completed(futures):
            future.result()
            summary(args.output, plan)
    result = summary(args.output, plan)
    from .plugin_downloads import run_source_plugins
    plugin_reports = run_source_plugins(args.output, registry, transport=args.transport, retry_failed=args.retry_failed)
    result = summary(args.output, plan)
    print(json.dumps({key: result[key] for key in ("target_count", "counts", "saved_bytes")}), flush=True)
    return int(result["counts"].get("saved", 0) != result["target_count"] or any(
        r["counts"].get("saved", 0) != r["target_count"] or r.get("resolution_errors") for r in plugin_reports))


if __name__ == "__main__":
    raise SystemExit(main())
