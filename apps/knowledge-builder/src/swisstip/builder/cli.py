"""Command-line entry point for the bounded demonstration crawler."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Sequence

from swisstip.ingestion import CrawlLimits, SafeCrawler, SourceDefinition
from swisstip.ingestion.crawler import CrawlConfigurationError, DEFAULT_USER_AGENT


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than 0")
    return parsed


def _non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be at least 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swisstip-crawl",
        description=(
            "Safely scan an allowlisted site and emit snapshot metadata. "
            "robots.txt and redirects count against the request budget."
        ),
    )
    parser.add_argument("url", help="absolute HTTP(S) seed URL")
    parser.add_argument("--source-id", default="cli-demo")
    parser.add_argument("--authority", help="canonical source authority label")
    parser.add_argument("--jurisdiction", help="source jurisdiction code")
    parser.add_argument("--language", help="source language code")
    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        metavar="HOST",
        help="additional exact host to allow; repeatable (seed host is always allowed)",
    )
    parser.add_argument(
        "--allow-path-prefix",
        action="append",
        default=[],
        metavar="PATH",
        help="allowed path prefix; repeatable (default: /)",
    )
    parser.add_argument("--max-depth", type=_non_negative_int, default=1)
    parser.add_argument("--max-pages", type=_positive_int, default=20)
    parser.add_argument("--max-requests", type=_positive_int, default=30)
    parser.add_argument("--max-total-bytes", type=_positive_int, default=5_000_000)
    parser.add_argument("--max-response-bytes", type=_positive_int, default=1_000_000)
    parser.add_argument("--max-duration", type=_positive_float, default=60.0)
    parser.add_argument("--timeout", type=_positive_float, default=10.0)
    parser.add_argument("--delay", type=_non_negative_float, default=1.0)
    parser.add_argument("--max-redirects", type=_non_negative_int, default=3)
    parser.add_argument("--max-links-per-page", type=_positive_int, default=100)
    parser.add_argument("--max-queued-urls", type=_positive_int, default=200)
    parser.add_argument("--max-failures", type=_positive_int, default=5)
    parser.add_argument(
        "--allow-query-strings",
        action="store_true",
        help="opt in to query URLs; disabled by default to avoid crawler traps",
    )
    parser.add_argument(
        "--allow-private-networks",
        action="store_true",
        help="DEVELOPMENT ONLY: allow loopback/private targets (SSRF guard is on by default)",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the effective configuration without network access",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.user_agent.strip():
        parser.error("--user-agent cannot be empty")
    try:
        source = SourceDefinition(
            source_id=args.source_id,
            start_url=args.url,
            allowed_hosts=tuple(args.allow_host),
            allowed_path_prefixes=tuple(args.allow_path_prefix or ["/"]),
            canonical_authority=args.authority,
            jurisdiction=args.jurisdiction,
            language=args.language,
        )
        limits = CrawlLimits(
            max_depth=args.max_depth,
            max_pages=args.max_pages,
            max_requests=args.max_requests,
            max_total_bytes=args.max_total_bytes,
            max_response_bytes=args.max_response_bytes,
            max_duration_seconds=args.max_duration,
            request_timeout_seconds=args.timeout,
            delay_seconds=args.delay,
            max_redirects=args.max_redirects,
            max_links_per_page=args.max_links_per_page,
            max_queued_urls=args.max_queued_urls,
            max_failures=args.max_failures,
        )
    except CrawlConfigurationError as exc:
        parser.error(str(exc))

    if args.dry_run:
        output: dict[str, object] = {
            "mode": "dry-run",
            "source": asdict(source),
            "effective_allowed_hosts": sorted(source.effective_allowed_hosts),
            "limits": asdict(limits),
            "policies": {
                "robots_txt": "required; failures deny crawling",
                "redirects": "manually followed and allowlist-checked",
                "network": (
                    "private addresses explicitly allowed for development"
                    if args.allow_private_networks
                    else "public addresses only"
                ),
                "concurrency": 1,
                "query_strings": args.allow_query_strings,
            },
        }
        exit_code = 0
    else:
        report = SafeCrawler(
            source,
            limits,
            user_agent=args.user_agent,
            allow_query_strings=args.allow_query_strings,
            allow_private_networks=args.allow_private_networks,
        ).crawl()
        output = {
            "mode": "crawl",
            "source": asdict(source),
            "effective_allowed_hosts": sorted(source.effective_allowed_hosts),
            "limits": asdict(limits),
            "report": report.to_dict(),
        }
        exit_code = 0 if report.pages else 1

    json.dump(
        output,
        sys.stdout,
        ensure_ascii=False,
        indent=None if args.compact else 2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
