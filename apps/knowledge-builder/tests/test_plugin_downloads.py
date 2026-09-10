import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from swisstip.builder.download_cli import main
from swisstip.builder.plugin_downloads import MetadataFetcher, run_source_plugins
from swisstip.ingestion.acquisition import write_json
from swisstip.ingestion.source_plugins import PluginRegistry, SourceDocument, SourcePlugin
from swisstip.ingestion.source_snapshots import normalize_source_snapshot


class ExamplePlugin(SourcePlugin):
    plugin_id = "example"
    version = "1"
    metadata_hosts = ("example.gov",)
    document_hosts = ("example.gov",)

    def matches(self, url):
        return url == "https://example.gov/law"

    def resolve(self, request, fetch_json):
        metadata = fetch_json("https://example.gov/metadata")
        return [SourceDocument(metadata["url"], "text/html", "en", version_uri="2026-09-10")]


class PluginDownloadTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_json(self.root / "plan.json", {"created_at": "2026-09-10T00:00:00Z",
                   "catalogue_sha256": "abc", "targets": [{"url": "https://example.gov/law",
                   "references": [{"label": "Law"}]}]})

    def cache_metadata(self, body=b'{"url":"https://example.gov/law.html"}'):
        output = self.root / "example-documents"
        folder = output / "metadata"
        folder.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(b"https://example.gov/metadata").hexdigest()
        (folder / f"{key}.json").write_bytes(body)
        write_json(folder / f"{key}.request.json", {"sha256": hashlib.sha256(body).hexdigest()})
        return output, folder / f"{key}.json"

    def fake_snapshot(self, target, output, hosts, transport):
        path = output / "pages" / target["url_id"] / "attempt-001" / "response.html"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"<html><title>Law</title><p>A residence permit is required.</p></html>")
        result = {**target, "status": "saved", "snapshots": [{
            "relative_path": path.relative_to(output).as_posix(), "review_flags": [],
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes_downloaded": path.stat().st_size,
            "requested_url": target["url"], "final_url": target["url"],
            "retrieved_at": "2026-09-10T00:00:00Z", "content_type": "text/html"}]}
        write_json(path.parent / "manifest.json", result)
        write_json(path.parent.parent / "latest.json", result)
        return result

    def test_second_plugin_runs_resumes_and_normalizes_with_provenance(self):
        self.cache_metadata()
        registry = PluginRegistry([ExamplePlugin()])
        with patch("swisstip.builder.plugin_downloads.snapshot", side_effect=self.fake_snapshot) as save, \
                patch("swisstip.builder.plugin_downloads.time.sleep"), redirect_stdout(io.StringIO()):
            reports = run_source_plugins(self.root, registry)
            self.assertEqual(reports[0]["counts"], {"saved": 1})
            run_source_plugins(self.root, registry)
            save.assert_called_once()
        path = next(self.root.rglob("response.html"))
        page = normalize_source_snapshot(path, plugins=registry)
        self.assertEqual(page.provenance["source_url"], "https://example.gov/law")
        self.assertEqual(page.provenance["source_plugin"]["id"], "example")
        self.assertEqual(len(page.provenance["resolution_metadata"]), 1)

    def test_resolution_errors_are_persisted_and_explicit_retry_recovers(self):
        self.cache_metadata(b"{}")
        registry = PluginRegistry([ExamplePlugin()])
        report = run_source_plugins(self.root, registry)[0]
        self.assertEqual(len(report["resolution_errors"]), 1)
        self.cache_metadata()
        self.assertTrue(run_source_plugins(self.root, registry)[0]["resolution_errors"])
        with patch("swisstip.builder.plugin_downloads.snapshot", side_effect=self.fake_snapshot), \
                patch("swisstip.builder.plugin_downloads.time.sleep"), redirect_stdout(io.StringIO()):
            report = run_source_plugins(self.root, registry, retry_failed=True)[0]
        self.assertEqual(report["resolution_errors"], [])
        self.assertEqual(report["counts"], {"saved": 1})

    def test_metadata_rejects_unknown_hosts_tampered_cache_and_excess_calls(self):
        output, path = self.cache_metadata()
        fetch = MetadataFetcher(output, ExamplePlugin())
        with self.assertRaisesRegex(ValueError, "declared hosts"):
            fetch("https://other.gov/metadata")
        path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash"):
            fetch("https://example.gov/metadata")
        self.cache_metadata()
        fetch("https://example.gov/metadata")
        fetch("https://example.gov/metadata")
        with self.assertRaisesRegex(ValueError, "four metadata"):
            fetch("https://example.gov/metadata")

    def test_planning_identifies_fedlex_without_network_or_resolution(self):
        catalogue = self.root / "sources.md"
        catalogue.write_text("[Act](https://www.fedlex.admin.ch/eli/cc/2007/758/de)", encoding="utf-8")
        output = self.root / "planned"
        with patch("sys.argv", ["download", "--catalogue", str(catalogue), "--output", str(output)]), \
                patch("swisstip.builder.download_cli.snapshot") as download, \
                patch("swisstip.builder.plugin_downloads.run_source_plugins") as resolve, \
                redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)
            download.assert_not_called()
            resolve.assert_not_called()
        plan = json.loads((output / "plugin-plan.json").read_text())
        self.assertEqual(plan["sources"][0]["plugin_id"], "fedlex")
