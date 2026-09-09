"""Repeat the real v4 pipeline with frozen inputs and redacted wire diagnostics.

Run using the repository .venv. No shell evaluation of credential files, implicit
retries, cache reuse, model fallback, or edits to active repository selections.
"""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4

import tomli_w

from swisstip.builder.concept_cli import main as extract_main
from swisstip.builder.provider_factory import create_semantic_model_provider
from swisstip.core.model_profiles import load_model_config


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / ".local/admin/jobs/8d0e464828e74e2bbc024ec4f8d0702d/57fdf9ad48164dcab573e7f404bf1327.html"
PROFILES = ("apertus_70b", "groq_gpt_oss_120b", "deepseek_v4_pro")
KEY_NAMES = ("HF_TOKEN", "GROQ_API_KEY", "DEEPSEEK_API_KEY")


def stamp():
    return datetime.now(UTC).isoformat()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_keys(env_file, environ):
    """Process values take precedence; read only the three named API keys."""
    result = {name: environ[name] for name in KEY_NAMES if environ.get(name)}
    sources = {name: "process" for name in result}
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip().removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name, value = name.strip(), value.strip()
            if name not in KEY_NAMES or name in result:
                continue
            if value.startswith(('"', "'")):
                quote = value[0]
                end = value.find(quote, 1)
                if end < 0 or (value[end + 1:].strip() and not value[end + 1:].strip().startswith("#")):
                    raise ValueError(f"Invalid quoted value for {name} in credential file")
                value = value[1:end]
            else:
                value = value.split(" #", 1)[0].strip()
            if value:
                result[name], sources[name] = value, env_file.name
    return result, sources


def redact(text, keys):
    for value in sorted(keys.values(), key=len, reverse=True):
        if value:
            text = text.replace(value, "[REDACTED]")
    return text


def write_json(path, value, keys=None):
    path.write_text(redact(json.dumps(value, ensure_ascii=False, indent=2), keys or {}) + "\n", encoding="utf-8")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class RequestPacer:
    """Space Groq calls for the current account's token-per-minute allowance."""
    def __init__(self, interval, console, *, now=time.monotonic, sleep=time.sleep):
        self.interval, self.console, self.now, self.sleep = interval, console, now, sleep
        self.last_start = None

    def wait(self):
        started = self.now()
        if self.last_start is not None:
            delay = max(0.0, self.interval - (started - self.last_start))
            if delay:
                print(f"Groq pacing: waiting {delay:.1f}s before the next request (not a retry)", file=self.console, flush=True)
            while delay > 0:
                self.sleep(min(delay, 10.0))
                delay = max(0.0, self.interval - (self.now() - self.last_start))
        self.last_start = self.now()
        return round(self.last_start - started, 3)


class TracedResponse:
    def __init__(self, response, record, save):
        self.response, self.record, self.save = response, record, save
        self.headers = response.headers
        self.body = bytearray()

    def getcode(self):
        return self.response.getcode()

    def read(self, amount):
        raw = self.response.read(amount)
        self.body.extend(raw[:max(0, 1_000_001 - len(self.body))])
        return raw

    def close(self):
        try:
            self.response.close()
        finally:
            self.record["response_text"] = self.body.decode("utf-8", errors="replace")
            self.save()


class TraceOpener:
    """Record bounded request/response bodies, never authorization headers."""
    def __init__(self, folder, keys, pacer=None):
        self.folder, self.keys, self.calls = folder, keys, []
        self.pacer = pacer
        folder.mkdir()
        self.opener = urllib.request.build_opener(NoRedirect())

    def open(self, request, *, timeout):
        number = len(self.calls) + 1
        pacing_seconds = self.pacer.wait() if self.pacer is not None else 0.0
        started = time.monotonic()
        record = {"call": number, "started_at": stamp(), "url": request.full_url,
                  "timeout_seconds": timeout, "pacing_seconds": pacing_seconds, "request": json.loads(request.data),
                  "user_agent": request.get_header("User-agent")}
        self.calls.append(record)

        def save():
            record["elapsed_seconds"] = round(time.monotonic() - started, 3)
            write_json(self.folder / f"call-{number:02d}.json", record, self.keys)

        write_json(self.folder / f"call-{number:02d}.json", record, self.keys)
        try:
            response = self.opener.open(request, timeout=timeout)
            record["status"] = response.getcode()
            return TracedResponse(response, record, save)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read(65536)
                record.update(status=exc.code, response_text=body.decode("utf-8", errors="replace"))
                # The adapter receives and closes the original HTTP error.
            finally:
                save()
            raise
        except Exception as exc:
            record["transport_error"] = str(exc)
            save()
            raise


def summarize(report, calls, exit_code, elapsed):
    pages = report.get("reports", [])
    histories = [entry for page in pages for review in page.get("semantic_reviews", []) for entry in review.get("history", [])]
    usage, missing_usage, models = {"prompt_tokens": 0, "completion_tokens": 0}, 0, []
    for call in calls:
        try:
            data = json.loads(call.get("response_text", ""))
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if data.get("model"):
            models.append(data["model"])
        tokens = data.get("usage", {})
        if not isinstance(tokens, dict) or not all(type(tokens.get(key)) is int for key in usage):
            missing_usage += 1
        else:
            for key in usage:
                usage[key] += tokens[key]
    return {"exit_code": exit_code, "elapsed_seconds": round(elapsed, 3), "http_attempts": len(calls),
            "api_seconds": round(sum(call.get("elapsed_seconds", 0) for call in calls), 3),
            "pacing_seconds": round(sum(call.get("pacing_seconds", 0) for call in calls), 3),
            "observed_models": sorted(set(models)), "reported_usage": usage, "calls_without_usage": missing_usage,
            "retained_candidates": sum(len(p.get("candidates", [])) for p in pages),
            "rejected_candidates": sum(len(p.get("rejected_candidates", [])) for p in pages),
            "history_failures": [h.get("error") for h in histories if h.get("error")],
            "warnings": [warning for page in pages for warning in page.get("warnings", [])],
            "execution": report.get("execution"),
            "quality_metrics": [page.get("quality_metrics") for page in pages],
            "quality_note": "Retained candidates and self-review are not independently verified accuracy or recall."}


def write_summary(folder, manifest, keys=None):
    lines = ["# Extraction comparison", "", f"Source SHA-256: `{manifest['source_sha256']}`", "",
             "| Profile | Run | Retained | API calls | API seconds | Pacing seconds | Wall seconds | Input tokens | Output tokens |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for run in manifest["runs"]:
        usage = run["reported_usage"]
        lines.append(f"| {run['profile']} | {run['repeat']} | {run['retained_candidates']} | "
                     f"{run['http_attempts']} | {run['api_seconds']:.1f} | {run['pacing_seconds']:.1f} | "
                     f"{run['elapsed_seconds']:.1f} | {usage['prompt_tokens']} | {usage['completion_tokens']} |")
    lines += ["", "Retained candidates measure pipeline completion, not verified accuracy. "
              "Inspect source, raw responses, review history and rejected proposals before judging quality. "
              "Usage includes reported tokens from rejected responses; billing for failures without usage is unknown.", ""]
    for run in manifest["runs"]:
        lines += [f"## {run['profile']}, run {run['repeat']}", "",
                  f"[Full result]({run['directory']}/result.json) | [Progress]({run['directory']}/progress.log)", "",
                  "Observed models: " + (", ".join(run["observed_models"]) or "none") + ".", ""]
        lines += [f"- {warning}" for warning in dict.fromkeys(run["history_failures"] + run["warnings"])]
        lines.append("")
    (folder / "summary.md").write_text(redact("\n".join(lines), keys or {}), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--config", type=Path, default=ROOT / "config/semantic-models.toml")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.dev")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--profiles", nargs="+", default=list(PROFILES), choices=PROFILES)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--groq-interval-seconds", type=float, default=60.0,
                        help="Minimum interval between Groq calls; default 60 for the current 8000 TPM account")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.repeats <= 5 or len(set(args.profiles)) != len(args.profiles):
        parser.error("Use 1-5 repeats and distinct profiles")
    if not 0 <= args.groq_interval_seconds <= 300:
        parser.error("Groq request interval must be between 0 and 300 seconds")
    keys, key_sources = load_keys(args.env_file, os.environ)
    document = load_model_config(args.config)
    for name in args.profiles:
        token_env = document["profiles"][name]["token_env"]
        if not args.dry_run and not keys.get(token_env):
            parser.error(f"Missing {token_env}; no model calls started")
    source = args.input.read_bytes()
    folder = (args.output or ROOT / ".local/experiments/model-comparison" /
              (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8])).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    copied_source = folder / ("source" + args.input.suffix)
    copied_source.write_bytes(source)
    document["recovery"]["max_retries"] = 0
    document["extraction"]["prompt_profile"] = "concept_extraction_v4"
    for key in ("extraction_prompt_file", "review_prompt_file"):
        if value := document["extraction"].get(key):
            prompt = args.config.parent / value
            copy = folder / f"{key}.md"
            copy.write_bytes(prompt.read_bytes())
            document["extraction"][key] = str(copy)
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    code_files = [p for base in ("packages/ingestion/src", "apps/knowledge-builder/src", "packages/core/src")
                  for p in (ROOT / base).rglob("*") if p.suffix in {".py", ".md"}]
    code_files += [Path(__file__).resolve(), Path(__file__).with_name("README.md").resolve()]
    for original in code_files:
        target = folder / "code_snapshot" / original.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(original.read_bytes())
    manifest = {"schema_version": "swisstip.model-comparison/v1", "started_at": stamp(), "dry_run": args.dry_run,
                "source_path": str(args.input.resolve()), "source_sha256": digest(source), "git_revision": revision,
                "code_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in code_files},
                "script_sha256": digest(Path(__file__).read_bytes()), "credential_sources": key_sources,
                "profiles": args.profiles, "repeats": args.repeats, "runs": [],
                "groq_interval_seconds": args.groq_interval_seconds,
                "design": "One frozen page, current v4 prompts/limits, local checkpoints bypassed, zero retries; rotated model order."}
    write_json(folder / "manifest.json", manifest)
    print(f"Comparison artifacts: {folder}", flush=True)
    groq_pacer = RequestPacer(args.groq_interval_seconds, sys.stdout)
    try:
        for repeat in range(args.repeats):
            order = args.profiles[repeat % len(args.profiles):] + args.profiles[:repeat % len(args.profiles)]
            for name in order:
                run_folder = folder / f"{name}-run-{repeat + 1}"
                run_folder.mkdir()
                document["semantic_model"]["active_profile"] = name
                config = run_folder / "semantic-models.toml"
                config.write_text(tomli_w.dumps(document), encoding="utf-8")
                trace = TraceOpener(run_folder / "calls", keys, groq_pacer if document["profiles"][name]["adapter"] == "groq" else None)
                output, log = io.StringIO(), io.StringIO()
                started = time.monotonic()
                print(f"Starting {name}, run {repeat + 1}/{args.repeats}", flush=True)
                arguments = [str(copied_source), "--config", str(config), "--structured", "--verbose",
                             "--fresh-inference", "--checkpoint-dir", str(run_folder / "checkpoints")]
                if args.dry_run:
                    arguments.append("--dry-run")
                with redirect_stdout(output), redirect_stderr(log):
                    code = extract_main(arguments, provider_factory=lambda config: create_semantic_model_provider(
                        config, environ=keys, opener=trace))
                raw = redact(output.getvalue(), keys)
                (run_folder / "result.json").write_text(raw, encoding="utf-8")
                (run_folder / "progress.log").write_text(redact(log.getvalue(), keys), encoding="utf-8")
                try:
                    result = json.loads(raw)
                except ValueError:
                    result = {}
                summary = {"profile": name, "repeat": repeat + 1, "directory": run_folder.name,
                           **summarize(result, trace.calls, code, time.monotonic() - started)}
                if args.dry_run:
                    summary["planned_request_ceiling"] = result.get("planned_request_ceiling")
                write_json(run_folder / "summary.json", summary, keys)
                manifest["runs"].append(summary)
                write_json(folder / "manifest.json", manifest, keys)
                write_summary(folder, manifest, keys)
                print(f"Finished {name}: exit={code}, requests={len(trace.calls)}, retained={summary['retained_candidates']}, seconds={summary['elapsed_seconds']}", flush=True)
    finally:
        manifest["finished_at"] = stamp()
        write_json(folder / "manifest.json", manifest, keys)
    print(f"Completed {len(manifest['runs'])} runs. Review source, calls and result.json before drawing quality conclusions.", flush=True)
    return 0 if all(run["exit_code"] == 0 for run in manifest["runs"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
