"""Exercise the actual PowerShell workflow against a loopback fake model."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
POWERSHELL = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"


@unittest.skipUnless(os.name == "nt" and POWERSHELL.is_file(), "Windows PowerShell required")
class ZhChWorkflowTests(unittest.TestCase):
    def test_cached_fixture_repeated_runs_failure_and_empty_results(self):
        state = {"fail": False, "empty": False, "invalid_review": False, "calls": 0, "fail_at": 4}

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                state["calls"] += 1
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if state["fail"] or state["calls"] == state["fail_at"]:
                    self.send_error(504)
                    return
                payload = json.loads(request["messages"][1]["content"])
                page = payload.get("untrusted_page", {})
                span = next((s for s in page.get("evidence_spans", []) if "Apply online." in s["text"]), {})
                candidate = {
                    "preferred_label": "Permit application", "alternative_labels": [],
                    "concept_type": "PROCESS", "granularity": "ANSWERABLE",
                    "description": "Apply online.", "scope": "Residents",
                    "user_questions": ["How do I apply?"], "confidence": 0.8,
                    "evidence": [{"evidence_id": span.get("evidence_id")}], "relations": [],
                    "primary_section_id": span.get("section_id"),
                }
                result = {"concepts": [] if state["empty"] else [candidate]}
                if "untrusted_review" in payload:
                    result = {"verdicts": [
                        {"review_id": p["review_id"], "decision": "supported",
                         "issue": "none", "reason": "Supported test proposal."}
                        for p in payload["untrusted_review"]["proposals"]
                    ]}
                    if state["invalid_review"]:
                        result = {"verdicts": []}
                body = json.dumps({
                    "model": request["model"], "done": True, "done_reason": "stop",
                    "message": {"content": json.dumps(result)},
                    "prompt_eval_count": 10, "eval_count": 5,
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        with tempfile.TemporaryDirectory(prefix="swisstip-workflow-test-") as directory:
            fixture = Path(directory) / "fixture"
            pages = fixture / "pages" / "nested"
            pages.mkdir(parents=True)
            entries = []
            for index in range(6):
                path = pages / f"{index}.html"
                body = b"<html lang='en'><h1>Permit</h1><p>Apply online.</p><h2>Kontakt</h2><p>Telephone</p></html>"
                path.write_bytes(body)
                entries.append({"relative_path": f"nested/{path.name}", "bytes": len(body),
                                "sha256": hashlib.sha256(body).hexdigest()})
            manifest = fixture / "download-manifest.json"
            manifest.write_text(json.dumps({
                "schema_version": "swisstip.zhch-test-fixture/v1", "page_count": 6,
                "total_bytes": sum(e["bytes"] for e in entries), "pages": entries,
            }), encoding="utf-8")
            original_manifest = manifest.read_bytes()
            (fixture / "crawl-preflight.json").write_text("{}", encoding="utf-8")
            envfile = Path(directory) / ".env.dev"
            envfile.write_text("HF_TOKEN=hf_offline_test_only\n", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                config = (ROOT / "config/semantic-models.toml").read_text(encoding="utf-8")
                config = re.sub(r'(?m)^active_profile = "[^"]+"$', 'active_profile = "ollama_local"', config)
                # The loopback model returns the historical v3 proposal/review contract.
                config = re.sub(r'(?m)^prompt_profile\s*=.*$', 'prompt_profile = "concept_extraction_v3"', config)
                self.assertIn('active_profile = "ollama_local"', config)
                config = config.replace("http://127.0.0.1:11434", f"http://127.0.0.1:{server.server_port}")
                config_path = Path(directory) / "test.toml"
                config_path.write_text(config, encoding="utf-8")

                def run(name, *, fresh=False):
                    return subprocess.run([
                        str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "scripts/test/zhch/Invoke-ZhChConceptPoc.ps1"),
                        "-OutputRoot", str(fixture), "-ConfigPath", str(config_path),
                        "-EnvFilePath", str(envfile), "-RunName", name, "-Verbose",
                        *(["-FreshInference"] if fresh else []),
                    ], cwd=ROOT, capture_output=True, timeout=45)

                self.assertNotEqual(run("interrupted").returncode, 0)
                self.assertEqual(state["calls"], 4)
                self.assertEqual(len(list((fixture / "checkpoints").glob("*.json"))), 3)
                state["fail_at"] = None
                for name in ("first", "second"):
                    result = run(name)
                    self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                    run_dir = fixture / "runs" / name
                    output = json.loads((run_dir / "concept-proposals.json").read_text(encoding="utf-8"))
                    self.assertEqual(output["quality_summary"]["candidate_count"], 6)
                    self.assertEqual(output["quality_summary"]["consolidated_count"], 1)
                    self.assertEqual(output["quality_summary"]["review_request_count"], 6)
                    self.assertEqual(output["execution"]["checkpoint_hits"], 3 if name == "first" else 12)
                    self.assertEqual(output["execution"]["network_attempts"], 9 if name == "first" else 0)
                    with (run_dir / "review.csv").open(encoding="utf-8-sig", newline="") as stream:
                        self.assertEqual(len(list(csv.DictReader(stream))), 6)
                    log = (run_dir / "run.log").read_text(encoding="utf-8-sig")
                    self.assertIn("Model request 1/1 started", log)
                    self.assertNotIn("hf_offline_test_only", log)
                calls = state["calls"]
                self.assertNotEqual(run("first").returncode, 0)
                self.assertEqual(state["calls"], calls)

                state["fail"] = True
                self.assertNotEqual(run("failed", fresh=True).returncode, 0)
                failed_dir = fixture / "runs/failed"
                self.assertFalse((failed_dir / "concept-proposals.json").exists())
                self.assertIn("HTTP 504", (failed_dir / "run.log").read_text(encoding="utf-8-sig"))
                state.update(fail=False, invalid_review=True)
                self.assertNotEqual(run("invalid-review", fresh=True).returncode, 0)
                invalid_dir = fixture / "runs/invalid-review"
                self.assertFalse((invalid_dir / "concept-proposals.json").exists())
                self.assertIn("semantic review must cover every proposal",
                              (invalid_dir / "run.log").read_text(encoding="utf-8-sig"))
                state["invalid_review"] = False
                self.assertEqual(run("review-resumed").returncode, 0)
                resumed = json.loads((fixture / "runs/review-resumed/concept-proposals.json").read_text(encoding="utf-8"))
                # A malformed fresh review no longer overwrites the valid old cache.
                self.assertEqual(resumed["execution"]["checkpoint_hits"], 12)
                self.assertEqual(resumed["execution"]["network_attempts"], 0)
                state.update(fail=False, empty=True)
                self.assertEqual(run("empty", fresh=True).returncode, 0)
                empty = json.loads((fixture / "runs/empty/concept-proposals.json").read_text(encoding="utf-8"))
                self.assertEqual(empty["quality_summary"]["empty_page_count"], 6)
                self.assertTrue((fixture / "runs/empty/review.csv").is_file())
                self.assertEqual(manifest.read_bytes(), original_manifest)
                self.assertTrue((fixture / "runs/first/concept-proposals.json").is_file())
                # Zero-call link-only reports must coexist with cached model reports.
                for name, indexes in (("mixed-links", range(1)), ("only-links", range(6))):
                    for index in indexes:
                        body = b"<html lang='en'><h1>Links</h1><a href='/banks'>Bank list</a></html>"
                        (pages / f"{index}.html").write_bytes(body)
                        entries[index].update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
                    manifest.write_text(json.dumps({
                        "schema_version": "swisstip.zhch-test-fixture/v1", "page_count": 6,
                        "total_bytes": sum(e["bytes"] for e in entries), "pages": entries,
                    }), encoding="utf-8")
                    calls = state["calls"]
                    result = run(name)
                    self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                    self.assertEqual(state["calls"], calls)
                    output = json.loads((fixture / "runs" / name / "concept-proposals.json").read_text(encoding="utf-8"))
                    self.assertEqual(output["quality_summary"]["skipped_chunk_count"], len(indexes))
            finally:
                server.shutdown()
                server.server_close()
                worker.join()


if __name__ == "__main__":
    unittest.main()
