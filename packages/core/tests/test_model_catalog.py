"""Shared references resolve independently of role settings and working directory."""

from contextlib import chdir
from pathlib import Path
import tempfile
import tomllib
import unittest

from swisstip.core.model_profiles import load_model_catalog, load_model_config


CATALOG = '''schema_version = "swisstip.model-profiles/v1"
[profiles.local]
adapter = "ollama"
model = "fixture:8b"
base_url = "http://127.0.0.1:11434"
'''
CONFIG = '''model_profiles_file = "../shared/catalog.toml"
[profiles.extract]
model_profile = "local"
timeout_seconds = 180.0
num_ctx = 8192
[profiles.rank]
model_profile = "local"
timeout_seconds = 60.0
role = "ranking"
'''


class ModelCatalogTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "shared").mkdir()
        (self.root / "consumer").mkdir()
        self.catalog = self.root / "shared/catalog.toml"
        self.config = self.root / "consumer/settings.toml"
        self.catalog.write_text(CATALOG, encoding="utf-8")
        self.config.write_text(CONFIG, encoding="utf-8")

    def test_one_identity_resolves_multiple_profiles_with_independent_options(self):
        with chdir(self.root / "shared"):
            resolved = load_model_config(self.config)
        self.assertNotIn("model_profiles_file", resolved)
        extract, rank = (resolved["profiles"][key] for key in ("extract", "rank"))
        self.assertEqual(extract["model"], rank["model"])
        self.assertEqual((extract["timeout_seconds"], rank["timeout_seconds"]), (180, 60))
        self.assertNotIn("num_ctx", rank)
        self.assertNotIn("model_profile", extract)
        self.assertEqual(self.config.read_text(encoding="utf-8"), CONFIG)
        extract["model"] = "changed"
        self.assertEqual(rank["model"], "fixture:8b")
        self.assertEqual(load_model_catalog(self.catalog)["local"]["model"], "fixture:8b")

    def test_legacy_inline_document_is_preserved(self):
        standalone = '[profiles.local]\nadapter = "ollama"\nmodel = "fixture:8b"\n'
        self.config.write_text(standalone, encoding="utf-8")
        self.catalog.unlink()
        self.assertEqual(load_model_config(self.config), tomllib.loads(standalone))

    def test_missing_file_invalid_reference_and_missing_reference_file_fail(self):
        for document, message in (
            (CONFIG.replace("catalog.toml", "missing.toml"), "cannot read"),
            (CONFIG.replace('model_profile = "local"', 'model_profile = "missing"', 1), "unknown model profile"),
            (CONFIG.replace('model_profile = "local"', 'model_profile = []'), "unknown model profile"),
            (CONFIG.replace('"../shared/catalog.toml"', 'false'), "path string"),
            (CONFIG.replace('"../shared/catalog.toml"', '""'), "path string"),
            (CONFIG.split("\n", 1)[1], "requires model_profiles_file"),
        ):
            with self.subTest(message=message, document=document):
                self.config.write_text(document, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    load_model_config(self.config)

    def test_identity_overrides_are_rejected_even_for_unselected_profiles(self):
        for key in ("adapter", "model", "base_url", "provider", "token_env", "bill_to"):
            with self.subTest(key=key):
                self.config.write_text(CONFIG + f'{key} = "override"\n', encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "cannot override shared model fields"):
                    load_model_config(self.config)

    def test_all_catalog_entries_are_checked_and_catalogs_cannot_include_catalogs(self):
        for document in (
            CATALOG.replace("swisstip.model-profiles/v1", "future/v2"),
            CATALOG + '\n[profiles.unused]\nadapter = "unsupported"\n',
            CATALOG + '\n[profiles.unused]\nadapter = "ollama"\n',
            CATALOG + 'timeout_seconds = 30\n',
            CATALOG + 'model_profile = "local"\n',
            'model_profiles_file = "catalog.toml"\n' + CATALOG,
            CATALOG.replace('model = "fixture:8b"', 'model = 42'),
            CATALOG.replace('adapter = "ollama"', 'adapter = "huggingface"'),
        ):
            with self.subTest(document=document):
                self.catalog.write_text(document, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_model_config(self.config)

    def test_literal_secrets_are_rejected_without_echoing_values(self):
        for target, original in ((self.catalog, CATALOG), (self.config, CONFIG)):
            for field in ("token", "api_key", "api-key"):
                with self.subTest(target=target.name, field=field):
                    target.write_text(original + f'\n[unused]\n{field} = "secret-sentinel"\n', encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "forbidden") as raised:
                        load_model_config(self.config)
                    self.assertNotIn("secret-sentinel", str(raised.exception))
                    target.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
