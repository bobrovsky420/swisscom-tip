from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from swisstip.ingestion.concepts import PageNormalizationError
from swisstip.ingestion.source_plugins import (
    PluginRegistry, SourceDocument, SourcePlugin, SourceRequest,
    load_source_plugins, validate_documents,
)
from swisstip.ingestion.source_snapshots import normalize_source_snapshot
from swisstip.ingestion.sources.fedlex import FedlexPlugin


class ExamplePlugin(SourcePlugin):
    plugin_id = "example"
    version = "1"
    document_hosts = ("example.gov",)

    def matches(self, url):
        return url.startswith("https://example.gov/")


def bindings(language="fr", version="20260612"):
    work = "https://fedlex.data.admin.ch/eli/cc/2007/758"
    base = f"https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/2007/758/{version}/{language}"
    return {"results": {"bindings": [
        {"version": {"value": f"{work}/{version}"}, "file": {"value": f"{base}/html/law.html"}},
        {"version": {"value": f"{work}/{version}"}, "file": {"value": f"{base}/pdf-a/law.pdf"}},
    ]}}


class SourcePluginTests(unittest.TestCase):
    def test_external_plugins_are_explicitly_enabled(self):
        entry = Mock(name="entry")
        entry.name = "example"
        entry.load.return_value = ExamplePlugin
        with patch("swisstip.ingestion.source_plugins.entry_points", return_value=[entry]) as discover:
            self.assertEqual(load_source_plugins().describe()[0]["id"], "fedlex")
            discover.assert_not_called()
            registry = load_source_plugins(["example"])
            self.assertIsInstance(registry.select("https://example.gov/law"), ExamplePlugin)
            entry.load.assert_called_once()
            with self.assertRaisesRegex(ValueError, "Expected one installed"):
                load_source_plugins(["missing"])

    def test_duplicate_ambiguous_and_incompatible_plugins_fail(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            PluginRegistry([ExamplePlugin(), ExamplePlugin()])
        other = ExamplePlugin()
        other.plugin_id = "other"
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            PluginRegistry([ExamplePlugin(), other]).select("https://example.gov/law")
        other.api_version = 999
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            PluginRegistry([other])

    def test_documents_must_be_bounded_unique_and_on_declared_hosts(self):
        plugin = ExamplePlugin()
        for url in ("http://example.gov/law", "https://evil.gov/law", "https://user@example.gov/law",
                    "https://example.gov:444/law"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_documents(plugin, [SourceDocument(url, "text/html", "de")])
        valid = SourceDocument("https://example.gov/law", "text/html", "de")
        validate_documents(plugin, [valid])
        for documents in ([], [valid, valid], [valid] * 101):
            with self.assertRaises(ValueError):
                validate_documents(plugin, documents)

    def test_fedlex_selects_requested_language_and_records_version(self):
        fetch = Mock(return_value=bindings())
        plugin = FedlexPlugin()
        documents = plugin.resolve(SourceRequest("https://www.fedlex.admin.ch/eli/cc/2007/758/fr",
                                                 date(2026, 9, 10)), fetch)
        validate_documents(plugin, documents)
        query = parse_qs(urlsplit(fetch.call_args.args[0]).query)["query"][0]
        self.assertIn('"/fr"', query)
        self.assertIn("/20260910", query)
        self.assertIn("j:isExemplifiedBy", query)
        self.assertEqual([d.preferred_for_extraction for d in documents], [True, False])
        self.assertTrue(all(d.language == "fr" and d.version_uri.endswith("/20260612") for d in documents))

    def test_fedlex_rejects_wrong_language_future_version_or_missing_html(self):
        request = SourceRequest("https://www.fedlex.admin.ch/eli/cc/2007/758/fr", date(2026, 9, 10))
        pdf_only = bindings()
        pdf_only["results"]["bindings"].pop(0)
        for result in (bindings("de"), bindings(version="20270101"), pdf_only):
            with self.subTest(result=result), self.assertRaises(ValueError):
                FedlexPlugin().resolve(request, lambda _: result)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "pages" / "law" / "attempt-001" / "response.html"
        self.path.parent.mkdir(parents=True)
        self.path.write_text('<html lang="fr"><title>Residence</title><body><h1>Residence</h1>'
                             '<p>A residence permit is required.</p></body></html>', encoding="utf-8")
        self.manifest = {
            "source_page_url": "https://www.fedlex.admin.ch/eli/cc/2007/758/fr",
            "version_uri": "https://fedlex.data.admin.ch/eli/cc/2007/758/20260612",
            "source_plugin": {"id": "fedlex", "version": "1.0.0", "api_version": 1},
            "snapshots": [{"relative_path": self.path.relative_to(self.root).as_posix(),
                           "sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
                           "requested_url": "https://fedlex.data.admin.ch/law.html",
                           "final_url": "https://fedlex.data.admin.ch/law.html",
                           "retrieved_at": "2026-09-10T00:00:00Z", "content_type": "text/html",
                           "review_flags": []}],
        }
        self.save_manifest()

    def save_manifest(self):
        (self.path.parent / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_manifest_binds_verified_provenance(self):
        page = normalize_source_snapshot(self.path)
        self.assertEqual(page.provenance["source_url"], self.manifest["source_page_url"])
        self.assertEqual(page.provenance["version_uri"], self.manifest["version_uri"])
        self.assertEqual(page.source_sha256, self.manifest["snapshots"][0]["sha256"])
        self.assertTrue(page.sections)

    def test_tampering_review_flags_and_plugin_mismatch_prevent_extraction(self):
        self.path.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(PageNormalizationError, "hash"):
            normalize_source_snapshot(self.path)
        self.manifest["snapshots"][0]["sha256"] = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.manifest["snapshots"][0]["review_flags"] = ["javascript_application_shell"]
        self.save_manifest()
        with self.assertRaisesRegex(PageNormalizationError, "review"):
            normalize_source_snapshot(self.path)
        self.manifest["snapshots"][0]["review_flags"] = []
        self.save_manifest()
        with self.assertRaisesRegex(PageNormalizationError, "plugin"):
            normalize_source_snapshot(self.path, plugins=PluginRegistry([]))

    def test_plain_html_still_uses_generic_normalization(self):
        (self.path.parent / "manifest.json").unlink()
        page = normalize_source_snapshot(self.path)
        self.assertEqual(page.provenance, {})
        self.assertTrue(page.sections)
