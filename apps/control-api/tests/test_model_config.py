"""Configuration/catalog integration without a database or model requests."""

from dataclasses import replace
import json
import re
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from swisstip.builder.model_profiles import load_model_profiles, ModelProfileConfigurationError
from swisstip.control import api
from swisstip.control.models import JobRequest
from swisstip.core.model_profiles import load_model_config
from swisstip.runtime.provider_config import load_provider_settings


ROOT = Path(__file__).resolve().parents[3]


class ModelConfigTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / "config").mkdir()
        for name in ("model-profiles.toml", "semantic-models.toml", "retrieval-models.toml"):
            (self.root / "config" / name).write_bytes((ROOT / "config" / name).read_bytes())
        root_patch = patch.object(api, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        self.catalog = self.root / "config/model-profiles.toml"
        self.semantic = self.root / "config/semantic-models.toml"
        self.retrieval = self.root / "config/retrieval-models.toml"

    def test_catalog_exposes_resolved_models_and_credential_presence_only(self):
        with patch.object(api, "catalog_data", return_value={"sources": []}), patch.dict(
            "os.environ", {"HF_TOKEN": "secret-sentinel", "DEEPSEEK_API_KEY": "deepseek-secret-sentinel"}, clear=True
        ):
            data = api.catalog()
        profiles = {p["name"]: p for p in data["profiles"]}
        self.assertEqual(profiles["ollama_local"]["adapter"], "ollama")
        self.assertEqual(profiles["apertus_70b"]["model"], "swiss-ai/Apertus-70B-Instruct-2509")
        self.assertFalse(profiles["apertus_70b"]["selected"])
        self.assertFalse(profiles["deepseek_v4_pro"]["selected"])
        self.assertTrue(profiles["deepseek_v4_1_flash"]["selected"])
        self.assertEqual(data["extraction_profile"], "concept_extraction_v3")
        self.assertTrue(profiles["deepseek_v4_pro"]["credential_ready"])
        self.assertTrue(profiles["apertus_70b"]["credential_ready"])
        self.assertNotIn("secret-sentinel", json.dumps(data))
        with self.assertRaises(HTTPException) as raised:
            api.config_text("unknown")
        self.assertEqual(raised.exception.status_code, 422)

    def test_deepseek_gui_profile_checks_its_own_key_and_freezes_json_mode(self):
        with patch.object(api, "catalog_data", return_value={"sources": []}), patch.dict(
            "os.environ", {"HF_TOKEN": "wrong-provider-token"}, clear=True
        ):
            profile = next(p for p in api.catalog()["profiles"] if p["name"] == "deepseek_v4_pro")
            self.assertFalse(profile["credential_ready"])
            with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "deepseek-secret-sentinel"}):
                profile = next(p for p in api.catalog()["profiles"] if p["name"] == "deepseek_v4_pro")
                self.assertTrue(profile["credential_ready"])
                snapshot = api.config_text("deepseek_v4_pro")
        self.assertEqual(profile["adapter"], "deepseek")
        self.assertNotIn("deepseek-secret-sentinel", snapshot)
        self.catalog.unlink()
        path = self.root / "job.toml"
        path.write_text(snapshot, encoding="utf-8")
        config = load_model_profiles(path)
        self.assertEqual(config.active_profile.model, "deepseek-v4-pro")
        self.assertEqual(config.active_profile.response_mode, "json_object")
        self.assertEqual(config.recovery.max_retries, 0)

    def test_job_creation_resolves_omitted_model_and_preserves_explicit_selection(self):
        for selected, expected in ((None, 'deepseek_v4_1_flash'), ('deepseek_v4_pro', 'deepseek_v4_pro')):
            with self.subTest(selected=selected):
                body = JobRequest(kind='plan', asset_ids=['fixture-asset'],
                                  **({} if selected is None else {'profile': selected}))
                with patch.object(api, 'rows', return_value=[{'asset_id': 'fixture-asset'}]), patch.object(
                    api, 'save_job', return_value={'job_id': 'fixture-job'}
                ) as save_job:
                    api.create_job(body)
                stored, snapshot = save_job.call_args.args
                self.assertEqual(stored.profile, expected)
                self.assertEqual(tomllib.loads(snapshot)['semantic_model']['active_profile'], expected)
                self.assertEqual(body.profile, selected)

    def test_flash_gui_selection_resolves_shared_model_into_job_snapshot(self):
        with patch.object(api, "catalog_data", return_value={"sources": []}), patch.dict(
            "os.environ", {"DEEPSEEK_API_KEY": "flash-secret-sentinel"}, clear=True
        ):
            profile = next(p for p in api.catalog()["profiles"] if p["name"] == "deepseek_v4_1_flash")
            self.assertTrue(profile["credential_ready"])
            self.assertTrue(profile["selected"])
            snapshot = api.config_text("deepseek_v4_1_flash")
        self.assertNotIn("flash-secret-sentinel", snapshot)
        self.catalog.unlink()
        path = self.root / "job.toml"
        path.write_text(snapshot, encoding="utf-8")
        config = load_model_profiles(path)
        self.assertEqual(config.active_profile.model, "deepseek-flash")
        self.assertEqual(config.active_profile.response_mode, "json_object")
        self.assertEqual(config.recovery.max_retries, 0)

    def test_gui_snapshots_are_portable_and_keep_original_prompt_directory(self):
        document = self.semantic.read_text(encoding="utf-8")
        document = document.replace("[extraction]", '[extraction]\nextraction_prompt_file = "prompts/extract.md"\nreview_prompt_file = "prompts/review.md"')
        self.semantic.write_text(document, encoding="utf-8")
        expected = load_model_profiles(self.semantic)
        expected = replace(expected, recovery=replace(expected.recovery, max_retries=0))
        with patch.dict("os.environ", {"HF_TOKEN": "secret-sentinel"}):
            snapshot = api.config_text(expected.active_profile.name)
        self.assertNotIn("secret-sentinel", snapshot)
        data = tomllib.loads(snapshot)
        self.assertNotIn("model_profiles_file", data)
        self.assertTrue(all("model_profile" not in p for p in data["profiles"].values()))
        self.catalog.unlink()
        job_config = self.root / "job/semantic-models.toml"
        job_config.parent.mkdir()
        job_config.write_text(snapshot, encoding="utf-8")
        self.assertEqual(load_model_profiles(job_config), expected)
        self.assertEqual(data["extraction"]["review_prompt_file"], str((self.root / "config/prompts/review.md").resolve()))

    def test_gui_snapshots_preserve_explicit_and_omitted_repair_input_limits(self):
        document = self.semantic.read_text(encoding="utf-8")
        for allowance in (None, 32768):
            with self.subTest(allowance=allowance):
                without_limit = re.sub(r'(?m)^max_repair_input_characters\s*=.*\n?', '', document)
                configured = without_limit if allowance is None else without_limit.replace(
                    "[extraction]", f"[extraction]\nmax_repair_input_characters = {allowance}")
                self.semantic.write_text(configured, encoding="utf-8")
                snapshot = api.config_text("deepseek_v4_pro")
                data = tomllib.loads(snapshot)
                if allowance is None:
                    self.assertNotIn("max_repair_input_characters", data["extraction"])
                else:
                    self.assertEqual(data["extraction"]["max_repair_input_characters"], allowance)
                path = self.root / "job.toml"
                path.write_text(snapshot, encoding="utf-8")
                config = load_model_profiles(path)
                self.assertEqual(config.extraction.max_repair_input_characters, allowance)
                self.assertEqual(config.extraction.max_review_input_characters, 64000)

    def test_shared_edit_updates_both_consumers_but_not_existing_job_snapshots(self):
        snapshot = api.config_text("ollama_local")
        self.semantic.write_text(re.sub(r'(?m)^active_profile\s*=.*$', 'active_profile = "ollama_local"',
                                        self.semantic.read_text(encoding="utf-8"), count=1), encoding="utf-8")
        old_model = "MichelRosselli/apertus:8b-instruct-2509-q4_k_m"
        self.catalog.write_text(self.catalog.read_text(encoding="utf-8").replace(old_model, "fixture:8b"), encoding="utf-8")
        semantic = load_model_profiles(self.semantic)
        retrieval = load_provider_settings(self.retrieval)
        self.assertEqual(semantic.active_profile.model, "fixture:8b")
        self.assertEqual(retrieval.ranking_profile.model, "fixture:8b")
        self.assertEqual((semantic.active_profile.timeout_seconds, retrieval.ranking_profile.timeout_seconds), (180, 60))
        self.assertEqual(retrieval.embedding_profile.model, "qwen3-embedding:0.6b")
        job_config = self.root / "job.toml"
        job_config.write_text(snapshot, encoding="utf-8")
        self.assertEqual(load_model_profiles(job_config).active_profile.model, old_model)

    def test_catalog_transport_errors_still_fail_in_role_loaders(self):
        self.catalog.write_text(self.catalog.read_text(encoding="utf-8").replace(
            "http://127.0.0.1:11434", "http://user:password@127.0.0.1:11434"), encoding="utf-8")
        with self.assertRaises(ModelProfileConfigurationError):
            load_model_profiles(self.semantic)
        with self.assertRaises(ValueError):
            load_provider_settings(self.retrieval)

    def test_legacy_retrieval_config_loads_without_catalog(self):
        import tomli_w
        expected = load_provider_settings(self.retrieval)
        self.retrieval.write_text(tomli_w.dumps(load_model_config(self.retrieval)), encoding="utf-8")
        self.catalog.unlink()
        self.assertEqual(load_provider_settings(self.retrieval), expected)


if __name__ == "__main__":
    unittest.main()
