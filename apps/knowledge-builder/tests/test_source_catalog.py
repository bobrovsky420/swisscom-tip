from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/knowledge-builder/src"))
sys.path.insert(0, str(ROOT / "packages/ingestion/src"))
sys.path.insert(0, str(ROOT / "packages/ingestion/tests"))

from swisstip.builder.source_catalog import CANTONS, build_plan, load_source_catalog  # noqa: E402
from swisstip.builder.source_cli import crawl_plan, main  # noqa: E402
from swisstip.ingestion import SafeCrawler  # noqa: E402
from test_crawler import FakeOpener, FakeResponse, public_resolver  # noqa: E402


CATALOG = ROOT / "config/catalogs/hackathon.sources.json"


class SourceCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_source_catalog(CATALOG)

    def test_registry_covers_official_federal_sources_and_all_cantons(self) -> None:
        entries = self.catalog["sources"]
        self.assertEqual({entry["definition"]["jurisdiction"] for entry in entries},
                         {"CH", *(f"CH-{code}" for code in CANTONS)})
        self.assertTrue(any("admin.ch/" in entry["definition"]["start_url"] for entry in entries))
        official_domains = {"admin.ch", "ch.ch", "stadt-zuerich.ch", "baselland.ch", "jura.ch", *(code.lower() + ".ch" for code in CANTONS)}
        for entry in entries:
            for host in entry["definition"]["allowed_hosts"]:
                self.assertTrue(any(host == domain or host.endswith("." + domain) for domain in official_domains), host)

    def test_all_plan_exposes_ineligible_sources_and_aggregate_budgets(self) -> None:
        plan = build_plan(self.catalog, scan_set="all")
        excluded = {entry["source_id"] for entry in plan["excluded_sources"]}
        self.assertEqual(excluded, {"ai-residence", "nw-residence", "tg-residence", "ch-fedlex-aig", "ch-fedlex-vzae", "ch-fedlex-fza"})
        self.assertEqual(plan["aggregate_ceilings"]["max_pages"], plan["ready_source_count"])
        self.assertEqual(plan["aggregate_ceilings"]["max_requests"], 5 * plan["ready_source_count"])

    def test_default_cli_never_constructs_crawler_or_writes_files(self) -> None:
        stdout = io.StringIO()
        with patch("swisstip.builder.source_cli.SafeCrawler") as crawler, patch("pathlib.Path.mkdir") as mkdir, redirect_stdout(stdout):
            self.assertEqual(main(["--catalog", str(CATALOG)]), 0)
        crawler.assert_not_called()
        mkdir.assert_not_called()
        plan = json.loads(stdout.getvalue())
        self.assertEqual(plan["mode"], "dry-run")
        self.assertEqual(plan["ready_source_count"], 5)
        self.assertEqual({entry["definition"]["language"] for entry in plan["sources"]}, {"en", "de", "fr", "it"})

    def test_bad_selectors_fail_before_execution(self) -> None:
        for values in ({"scan_set": "missing"}, {"source_ids": ["missing"]}, {"profile": "missing"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                build_plan(self.catalog, **values)

    def test_malformed_catalogs_reject_scope_escape_and_dangling_references(self) -> None:
        mutations = [
            lambda data: data["sources"].append(deepcopy(data["sources"][0])),
            lambda data: data["sources"][0]["definition"].update(source_id="../escape"),
            lambda data: data["sources"][0]["definition"].update(allowed_path_prefixes=["/unrelated/"]),
            lambda data: data["sources"][0]["definition"].update(allowed_hosts=["*.ch"]),
            lambda data: data["scan_sets"]["smoke"].append("missing"),
            lambda data: data["sources"][0].update(topic_hints=["missing"]),
            lambda data: data["crawl_profiles"]["smoke"].update(max_pages=100),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            for mutate in mutations:
                data = deepcopy(self.catalog)
                mutate(data)
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                    load_source_catalog(path)

    def test_snapshot_capture_reuses_crawler_bytes_and_binds_provenance(self) -> None:
        plan = build_plan(self.catalog, source_ids=["zh-overview"])
        entry = plan["sources"][0]
        url = entry["definition"]["start_url"]
        body = b'<html lang="de"><title>Fixture</title><p>Offline fixture.</p></html>'
        opener = FakeOpener({
            "https://www.zh.ch/robots.txt": FakeResponse(200, b"User-agent: *\nAllow: /\n", content_type="text/plain"),
            url: FakeResponse(200, body),
        })

        def crawler(source, limits, **kwargs):
            return SafeCrawler(source, replace(limits, delay_seconds=0), opener=opener,
                               resolver=public_resolver, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new-run"
            with patch("swisstip.builder.source_cli.SafeCrawler", side_effect=crawler):
                result = crawl_plan(plan, output)
            self.assertEqual(opener.requested, ["https://www.zh.ch/robots.txt", url])
            self.assertEqual(result["saved_html_pages"], 1)
            self.assertEqual(result["extraction_status"], "NOT_RUN")
            snapshot = result["results"][0]["snapshots"][0]
            self.assertEqual((output / snapshot["relative_path"]).read_bytes(), body)
            self.assertEqual(snapshot["sha256"], hashlib.sha256(body).hexdigest())
            self.assertEqual(snapshot["catalog_ref"], plan["catalog_ref"])
            self.assertEqual(snapshot["final_url"], url)
            self.assertIsNone(snapshot["detected_language"])
            with self.assertRaises(FileExistsError):
                crawl_plan(plan, output)

    def test_robots_denial_saves_no_html_and_reports_incomplete(self) -> None:
        plan = build_plan(self.catalog, source_ids=["zh-overview"])
        opener = FakeOpener({"https://www.zh.ch/robots.txt": FakeResponse(
            200, b"User-agent: *\nDisallow: /\n", content_type="text/plain")})

        def crawler(source, limits, **kwargs):
            return SafeCrawler(source, replace(limits, delay_seconds=0), opener=opener,
                               resolver=public_resolver, **kwargs)

        with tempfile.TemporaryDirectory() as directory, patch("swisstip.builder.source_cli.SafeCrawler", side_effect=crawler):
            result = crawl_plan(plan, Path(directory) / "denied-run")
        self.assertEqual(result["saved_html_pages"], 0)
        self.assertEqual(result["results"][0]["status"], "incomplete")
        self.assertEqual(opener.requested, ["https://www.zh.ch/robots.txt"])

    def test_manual_sources_never_reach_crawler(self) -> None:
        plan = build_plan(self.catalog, source_ids=["ch-fedlex-aig"])
        with tempfile.TemporaryDirectory() as directory, patch("swisstip.builder.source_cli.SafeCrawler") as crawler:
            output = Path(directory) / "manual"
            with self.assertRaises(ValueError):
                crawl_plan(plan, output)
            self.assertFalse(output.exists())
            crawler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
