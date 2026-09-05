"""Command-line entry point for evidence-backed concept proposals."""

from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from swisstip.ingestion.concepts import (
    CandidateConceptExtractor,
    ConceptExtractionError,
    SemanticModelError,
    SUPPORTED_PAGE_SUFFIXES,
    normalize_downloaded_page,
)

from .model_profiles import load_model_profiles
from .provider_factory import create_semantic_model_provider


BATCH_SCHEMA_VERSION = "swisstip.concept-proposal-batch/v1"
DEFAULT_CONFIG_PATH = Path("config/semantic-models.toml")
DEFAULT_MAX_DISCOVERY_ENTRIES = 100_000


class PageInputDiscoveryError(ValueError):
    """Raised when file, directory, or wildcard inputs cannot resolve safely."""


@dataclass(slots=True)
class _DiscoveryBudget:
    limit: int
    visited: int = 0

    def consume(self, path: Path) -> None:
        self.visited += 1
        if self.visited > self.limit:
            raise PageInputDiscoveryError(
                f"input discovery exceeded the limit of {self.limit} filesystem "
                f"entries while visiting {path}"
            )


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _page_input(value: str) -> Path:
    if not value.strip():
        raise argparse.ArgumentTypeError("input path or wildcard must not be empty")
    return Path(value)


def _path_sort_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def _deduplication_key(path: Path) -> str:
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError):
        resolved = path.absolute()
    return os.path.normcase(os.fspath(resolved))


def _is_directory_link(path: Path) -> bool:
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if is_junction is not None and is_junction():
            return True
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        return bool(
            os.name == "nt"
            and reparse_flag
            and getattr(path.lstat(), "st_file_attributes", 0) & reparse_flag
        )
    except OSError as exc:
        raise PageInputDiscoveryError(f"cannot inspect directory {path}: {exc}") from exc


def _walk_files(
    root: Path,
    *,
    budget: _DiscoveryBudget,
    max_depth: int | None = None,
) -> Iterable[Path]:
    """Yield a deterministic recursive file walk without following directories."""

    def walk(directory: Path, depth: int) -> Iterable[Path]:
        try:
            entries: list[tuple[str, Path, bool, bool]] = []
            with os.scandir(directory) as scanner:
                for entry in scanner:
                    path = Path(entry.path)
                    budget.consume(path)
                    is_directory = entry.is_dir(follow_symlinks=False)
                    if is_directory and _is_directory_link(path):
                        is_directory = False
                    entries.append(
                        (
                            entry.name,
                            path,
                            is_directory,
                            entry.is_file(follow_symlinks=False),
                        )
                    )
        except OSError as exc:
            raise PageInputDiscoveryError(
                f"cannot scan directory tree {root}: {exc}"
            ) from exc

        entries.sort(key=lambda value: (os.path.normcase(value[0]), value[0]))
        for _, path, is_directory, is_file in entries:
            if is_file:
                yield path
            elif is_directory and (
                max_depth is None or depth + 1 < max_depth
            ):
                yield from walk(path, depth + 1)

    budget.consume(root)
    yield from walk(root, 0)


def _supported_files_in_directory(
    root: Path,
    *,
    budget: _DiscoveryBudget,
) -> Iterable[Path]:
    found = False
    for path in _walk_files(root, budget=budget):
        if path.suffix.lower() in SUPPORTED_PAGE_SUFFIXES:
            found = True
            yield path
    if not found:
        raise PageInputDiscoveryError(
            f"directory tree contains no supported page files: {root}"
        )


def _glob_root_and_pattern(pattern: str) -> tuple[Path, tuple[str, ...]]:
    parts = Path(pattern).parts
    magic_index = next(
        (index for index, part in enumerate(parts) if glob.has_magic(part)),
        None,
    )
    if magic_index is None:
        raise PageInputDiscoveryError(f"input is not a wildcard pattern: {pattern}")
    root = Path(*parts[:magic_index]) if magic_index else Path(".")
    return root, tuple(parts[magic_index:])


def _matches_glob_parts(
    path_parts: tuple[str, ...],
    pattern_parts: tuple[str, ...],
) -> bool:
    if not pattern_parts:
        return not path_parts
    pattern_head = pattern_parts[0]
    if pattern_head == "**":
        if _matches_glob_parts(path_parts, pattern_parts[1:]):
            return True
        return (
            bool(path_parts)
            and not path_parts[0].startswith(".")
            and _matches_glob_parts(path_parts[1:], pattern_parts)
        )
    if not path_parts:
        return False
    if path_parts[0].startswith(".") and not pattern_head.startswith("."):
        return False
    return fnmatch.fnmatch(path_parts[0], pattern_head) and _matches_glob_parts(
        path_parts[1:], pattern_parts[1:]
    )


def _supported_files_for_glob(
    pattern: str,
    *,
    budget: _DiscoveryBudget,
) -> Iterable[Path]:
    root, pattern_parts = _glob_root_and_pattern(pattern)
    if not root.is_dir():
        raise PageInputDiscoveryError(
            f"wildcard matched no supported page files: {pattern}"
        )

    maximum_depth = None if "**" in pattern_parts else len(pattern_parts)
    found = False
    for candidate in _walk_files(
        root,
        budget=budget,
        max_depth=maximum_depth,
    ):
        relative_parts = candidate.relative_to(root).parts
        if (
            candidate.suffix.lower() in SUPPORTED_PAGE_SUFFIXES
            and _matches_glob_parts(relative_parts, pattern_parts)
        ):
            found = True
            yield candidate
    if not found:
        raise PageInputDiscoveryError(
            f"wildcard matched no supported page files: {pattern}"
        )


def resolve_page_inputs(
    inputs: Sequence[Path],
    *,
    max_pages: int,
    max_discovery_entries: int = DEFAULT_MAX_DISCOVERY_ENTRIES,
) -> list[Path]:
    """Resolve explicit files, recursive directories, and native wildcard inputs."""

    if max_pages < 1:
        raise PageInputDiscoveryError("max_pages must be positive")
    if max_discovery_entries < 1:
        raise PageInputDiscoveryError("max_discovery_entries must be positive")
    if not inputs:
        raise PageInputDiscoveryError("at least one page input is required")
    budget = _DiscoveryBudget(max_discovery_entries)
    resolved: dict[str, Path] = {}
    for input_path in inputs:
        rendered_input = os.fspath(input_path)
        if glob.has_magic(rendered_input):
            candidates = _supported_files_for_glob(rendered_input, budget=budget)
        elif input_path.exists():
            candidates = (
                _supported_files_in_directory(input_path, budget=budget)
                if input_path.is_dir()
                else _explicit_file(input_path, budget)
            )
        else:
            candidates = _explicit_file(input_path, budget)

        for candidate in candidates:
            key = _deduplication_key(candidate)
            existing = resolved.get(key)
            if existing is not None:
                if _path_sort_key(candidate) < _path_sort_key(existing):
                    resolved[key] = candidate
                continue
            resolved[key] = candidate
            if len(resolved) > max_pages:
                raise ConceptExtractionError(
                    f"resolved inputs exceed the configured page limit of {max_pages}"
                )
    return sorted(resolved.values(), key=_path_sort_key)


def _explicit_file(path: Path, budget: _DiscoveryBudget) -> tuple[Path]:
    budget.consume(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_PAGE_SUFFIXES:
        raise PageInputDiscoveryError(
            f"unsupported page extension {suffix or '<none>'}: {path}"
        )
    return (path,)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swisstip-concepts",
        description=(
            "Propose evidence-backed candidate concepts from explicit local "
            "HTML, text, or Markdown pages."
        ),
    )
    parser.add_argument(
        "pages",
        nargs="+",
        type=_page_input,
        metavar="INPUT",
        help="downloaded page file, recursive directory, or quoted wildcard",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="semantic-model TOML file (default: config/semantic-models.toml)",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=_positive_int,
        default=2_000_000,
        help="maximum size of each local input file (default: 2000000)",
    )
    parser.add_argument(
        "--max-discovery-entries",
        type=_positive_int,
        default=DEFAULT_MAX_DISCOVERY_ENTRIES,
        help="maximum filesystem entries inspected during discovery (default: 100000)",
    )
    parser.add_argument("--compact", action="store_true", help="emit compact JSON")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="write live extraction progress to standard error",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started_at = time.monotonic()

    def progress(message: str) -> None:
        if not args.verbose:
            return
        elapsed = time.monotonic() - started_at
        sys.stderr.write(f"swisstip-concepts: progress: +{elapsed:.1f}s {message}\n")
        sys.stderr.flush()

    try:
        progress(f"Loading semantic-model configuration from {args.config}")
        config = load_model_profiles(args.config)
        extraction = config.extraction
        profile = config.active_profile
        progress(
            f"Selected profile={profile.name}, adapter={profile.adapter}, "
            f"provider={profile.provider or 'automatic'}, model={profile.model}, "
            f"base_url={profile.base_url}, timeout_seconds={profile.timeout_seconds:g}"
        )
        progress(f"Resolving {len(args.pages)} input specification(s)")
        page_paths = resolve_page_inputs(
            args.pages,
            max_pages=extraction.max_pages_per_run,
            max_discovery_entries=args.max_discovery_entries,
        )
        progress(f"Discovered {len(page_paths)} supported page(s)")
        pages = []
        for index, path in enumerate(page_paths, start=1):
            progress(f"Normalizing page {index}/{len(page_paths)}: {path}")
            page = normalize_downloaded_page(
                path,
                max_file_bytes=args.max_file_bytes,
            )
            page_characters = sum(
                len(section.evidence_text) for section in page.sections
            )
            progress(
                f"Normalized page {index}/{len(page_paths)}: "
                f"sections={len(page.sections)}, characters={page_characters}, "
                f"title={page.title!r}"
            )
            pages.append(page)
        total_input_characters = sum(
            len(section.evidence_text)
            for page in pages
            for section in page.sections
        )
        if total_input_characters > extraction.max_total_input_characters:
            raise ConceptExtractionError(
                f"run has {total_input_characters} normalized input characters, "
                f"exceeding the configured limit of "
                f"{extraction.max_total_input_characters}"
            )
        progress(
            f"Validated normalized input: pages={len(pages)}, "
            f"characters={total_input_characters}"
        )
        progress("Creating semantic-model provider")
        provider = create_semantic_model_provider(config)
        progress("Semantic-model provider is ready")
        extractor = CandidateConceptExtractor(
            provider,
            active_profile=config.active_profile.name,
            prompt_profile=extraction.prompt_profile,
            chunk_content_characters=extraction.chunk_content_characters,
            chunk_overlap_characters=extraction.chunk_overlap_characters,
            max_concepts_per_chunk=extraction.max_concepts_per_chunk,
            max_model_requests_per_page=extraction.max_model_requests_per_page,
            progress=progress,
        )
        requests_per_page = [
            extractor.planned_request_count(page) for page in pages
        ]
        planned_requests = sum(requests_per_page)
        for index, (page, request_count) in enumerate(
            zip(pages, requests_per_page, strict=True),
            start=1,
        ):
            progress(
                f"Planned page {index}/{len(pages)}: "
                f"model_requests={request_count}, source={page.source}"
            )
        progress(f"Planned {planned_requests} model request(s) for this run")
        if planned_requests > extraction.max_model_requests_per_run:
            raise ConceptExtractionError(
                f"run requires {planned_requests} model requests, exceeding the "
                f"configured limit of {extraction.max_model_requests_per_run}"
            )
        reports = []
        for index, page in enumerate(pages, start=1):
            progress(f"Extracting page {index}/{len(pages)}: {page.source}")
            report = extractor.extract(page)
            reports.append(report.to_dict())
            progress(
                f"Finished page {index}/{len(pages)}: "
                f"requests={report.request_count}, candidates={len(report.candidates)}, "
                f"warnings={len(report.warnings)}"
            )
    except (ValueError, SemanticModelError) as exc:
        sys.stderr.write(f"swisstip-concepts: error: {exc}\n")
        return 2

    output: dict[str, object] = {
        "schema_version": BATCH_SCHEMA_VERSION,
        "model_config_schema_version": config.schema_version,
        "active_profile": config.active_profile.name,
        "report_count": len(reports),
        "reports": reports,
    }
    progress(f"Writing {len(reports)} report(s) as JSON")
    json.dump(
        output,
        sys.stdout,
        ensure_ascii=False,
        indent=None if args.compact else 2,
        sort_keys=True,
    )
    sys.stdout.write("\n")
    sys.stdout.flush()
    progress("Concept extraction completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
