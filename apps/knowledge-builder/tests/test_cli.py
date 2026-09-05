from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

APP_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = APP_ROOT.parents[1]
sys.path.insert(0, str(APP_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "packages" / "ingestion" / "src"))

from swisstip.builder.cli import main  # noqa: E402


class CrawlerCliTests(unittest.TestCase):
    def test_dry_run_reports_effective_scope_limits_and_policies(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "https://official.example/allowed/start",
                    "--source-id",
                    "official-test",
                    "--authority",
                    "Official Test Authority",
                    "--jurisdiction",
                    "CH",
                    "--language",
                    "en",
                    "--allow-path-prefix",
                    "/allowed/",
                    "--max-depth",
                    "0",
                    "--max-pages",
                    "1",
                    "--max-requests",
                    "2",
                    "--max-total-bytes",
                    "1000",
                    "--max-response-bytes",
                    "500",
                    "--dry-run",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["mode"], "dry-run")
        self.assertEqual(payload["source"]["source_id"], "official-test")
        self.assertEqual(payload["source"]["jurisdiction"], "CH")
        self.assertEqual(payload["effective_allowed_hosts"], ["official.example"])
        self.assertEqual(payload["limits"]["max_depth"], 0)
        self.assertEqual(payload["limits"]["max_requests"], 2)
        self.assertEqual(payload["policies"]["concurrency"], 1)
        self.assertEqual(payload["policies"]["robots_txt"], "required; failures deny crawling")


if __name__ == "__main__":
    unittest.main()
