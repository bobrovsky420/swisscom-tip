"""Repeat a saved GUI extraction with current code and fresh model requests.

Run with the repository .venv. The original job is read only; each invocation
writes a new directory containing inputs, configuration, report and progress.
"""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

import tomli_w

from swisstip.builder.concept_cli import main as extract_main
from swisstip.builder.provider_factory import create_semantic_model_provider
from swisstip.core.model_profiles import load_model_config
from swisstip.ingestion.concepts import SUPPORTED_PAGE_SUFFIXES


ROOT = Path(__file__).resolve().parents[2]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_credential(name, env_file):
    """Read only the selected profile's credential, without evaluating shell code."""
    if not name:
        return {}, "not_required"
    if os.environ.get(name):
        return {name: os.environ[name]}, "process"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip().removeprefix("export ").strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() != name:
                continue
            value = value.strip()
            if value.startswith(('"', "'")):
                end = value.find(value[0], 1)
                if end < 0 or (value[end + 1:].strip() and not value[end + 1:].strip().startswith("#")):
                    raise ValueError(f"Invalid quoted value for {name}")
                value = value[1:end]
            else:
                value = value.split(" #", 1)[0].strip()
            if value:
                return {name: value}, env_file.name
    return {}, "missing"


def redact(value, credentials):
    secrets = {form for secret in credentials.values() if secret
               for form in (secret, json.dumps(secret)[1:-1], json.dumps(secret, ensure_ascii=False)[1:-1])}
    for secret in sorted(secrets, key=len, reverse=True):
        value = value.replace(secret, "[REDACTED]")
    return value


class Progress(io.StringIO):
    def __init__(self, console, credentials):
        super().__init__()
        self.console, self.credentials = console, credentials
        self.pending = ""

    def write(self, text):
        self.pending += text
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            self.console.write(redact(line + "\n", self.credentials))
        self.console.flush()
        return super().write(text)

    def finish(self):
        self.console.write(redact(self.pending, self.credentials))
        self.console.flush()
        self.pending = ""


def summarize(result, code, elapsed, dry_run):
    pages = result.get("reports", [])
    quality = result.get("quality_summary", {})
    histories = [entry for page in pages for review in page.get("semantic_reviews", [])
                 for entry in review.get("history", [])]
    count = quality.get("candidate_count", 0)
    ready = bool(pages) and all(page.get("candidates") for page in pages)
    # Match the worker: human-review warnings legitimately keep drafts in attention.
    attention = not count or any(p.get("warnings") or p.get("rejected_candidates") for p in pages)
    return {
        "builder_exit_code": code,
        "script_exit_code": code if code else 0 if dry_run or ready else 2,
        "extraction_status": "failed" if code else "planned" if dry_run else "draft_ready" if ready else "no_usable_draft_for_some_pages",
        "gui_equivalent_status": "failed" if code else "completed" if dry_run or not attention else "needs_attention",
        "elapsed_seconds": round(elapsed, 3),
        "planned_request_ceiling": result.get("planned_request_ceiling"),
        "quality_summary": quality,
        "execution": result.get("execution"),
        "candidate_labels": [c["preferred_label"] for p in pages for c in p.get("candidates", [])],
        "review_normalizations": [n for h in histories for n in h.get("review_normalizations", [])],
        "history_failures": [h["error"] for h in histories if h.get("error")],
        "warnings": [w for p in pages for w in p.get("warnings", [])],
        "assessment": "Candidates remain drafts requiring human source review and explicit promotion.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", type=Path, required=True, help="Saved GUI job containing page snapshots and semantic-models.toml")
    parser.add_argument("--output", type=Path, help="New artifact directory; must not already exist")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.dev")
    parser.add_argument("--dry-run", action="store_true", help="Plan without constructing a model provider")
    args = parser.parse_args(argv)
    try:
        original = args.job_dir.resolve(strict=True)
        config_path = original / "semantic-models.toml"
        document = load_model_config(config_path)
        sources = sorted(p for p in original.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_PAGE_SUFFIXES)
        # Prompt overrides may live beside the saved input; they are not pages.
        prompt_files = {key: (original / document["extraction"][key]).resolve()
                        for key in ("extraction_prompt_file", "review_prompt_file") if document["extraction"].get(key)}
        sources = [p for p in sources if p.resolve() not in prompt_files.values()]
        if not sources:
            raise ValueError("Saved job contains no supported page snapshots")
        profile = document["semantic_model"]["active_profile"]
        token_name = document["profiles"][profile].get("token_env")
        credentials, credential_source = load_credential(token_name, args.env_file)
        if not args.dry_run and credential_source == "missing":
            raise ValueError(f"Missing {token_name}; no model calls started")
        source_bytes = {p.name: p.read_bytes() for p in sources}
        prompt_bytes = {key: path.read_bytes() for key, path in prompt_files.items()}
        folder = (args.output or ROOT / ".local/admin/cli-extractions" /
                  (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])).resolve()
        folder.mkdir(parents=True, exist_ok=False)
    except (ValueError, OSError, KeyError) as exc:
        parser.error(str(exc))

    inputs = folder / "inputs"
    inputs.mkdir()
    for name, raw in source_bytes.items():
        (inputs / name).write_bytes(raw)
    document.setdefault("recovery", {})["max_retries"] = 0
    for key, raw in prompt_bytes.items():
        path = folder / f"{key}.md"
        path.write_bytes(raw)
        document["extraction"][key] = str(path)
    config = folder / "semantic-models.toml"
    config.write_text(tomli_w.dumps(document), encoding="utf-8")
    arguments = [*[str(inputs / name) for name in source_bytes], "--config", str(config),
                 "--structured", "--verbose", "--fresh-inference", "--checkpoint-dir", str(folder / "checkpoints")]
    if args.dry_run:
        arguments.append("--dry-run")
    manifest = {"schema_version": "swisstip.saved-extraction-run/v1", "original_job": str(original),
                "started_at": datetime.now(UTC).isoformat(), "dry_run": args.dry_run, "profile": profile,
                "credential_source": credential_source, "arguments": arguments,
                "source_sha256": {name: digest(raw) for name, raw in source_bytes.items()},
                "original_config_sha256": digest(config_path.read_bytes()),
                "script_sha256": digest(Path(__file__).read_bytes())}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Extraction artifacts: {folder}", flush=True)
    output, progress = io.StringIO(), Progress(sys.stderr, credentials)
    started = time.monotonic()
    try:
        with redirect_stdout(output), redirect_stderr(progress):
            code = extract_main(arguments, provider_factory=lambda config: create_semantic_model_provider(config, environ=credentials))
    finally:
        progress.finish()
        (folder / "result.json").write_text(redact(output.getvalue(), credentials), encoding="utf-8")
        (folder / "progress.log").write_text(redact(progress.getvalue(), credentials), encoding="utf-8")
    try:
        result = json.loads(output.getvalue())
    except ValueError:
        result, code = {}, code or 1
    summary = summarize(result, code, time.monotonic() - started, args.dry_run)
    (folder / "summary.json").write_text(redact(json.dumps(summary, indent=2), credentials) + "\n", encoding="utf-8")
    print(redact(json.dumps(summary, indent=2), credentials), flush=True)
    return summary["script_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
