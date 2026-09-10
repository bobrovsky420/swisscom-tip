"""Compatibility entry point; Fedlex is implemented by the shared plugin runner."""
import argparse
from pathlib import Path

from swisstip.builder.plugin_downloads import run_source_plugins
from swisstip.ingestion.source_plugins import load_source_plugins


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    args = parser.parse_args()
    reports = run_source_plugins(args.corpus, load_source_plugins(["fedlex"]), retry_failed=True)
    return int(any(r["counts"].get("saved", 0) != r["target_count"] or r.get("resolution_errors") for r in reports))


if __name__ == "__main__":
    raise SystemExit(main())
