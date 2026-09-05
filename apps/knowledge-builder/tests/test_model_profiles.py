from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

APP_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = APP_ROOT.parents[1]
sys.path.insert(0, str(APP_ROOT / "src"))

from swisstip.builder.model_profiles import (  # noqa: E402
    ModelProfileConfigurationError,
    load_model_profiles,
)


VALID_CONFIG = """
schema_version = "swisstip.semantic-model-profiles/v1"

[semantic_model]
active_profile = "ollama_local"

[generation]
temperature = 0.0
max_output_tokens = 2048

[extraction]
prompt_profile = "concept_extraction_v1"
chunk_content_characters = 12000
chunk_overlap_characters = 600
max_concepts_per_chunk = 24
max_pages_per_run = 10
max_total_input_characters = 120000
max_model_requests_per_page = 12
max_model_requests_per_run = 20

[profiles.ollama_local]
adapter = "ollama"
model = "MichelRosselli/apertus:8b-instruct-2509-q4_k_m"
base_url = "http://127.0.0.1:11434"
timeout_seconds = 180.0
num_ctx = 8192
keep_alive = "5m"

[profiles.hf_free]
adapter = "huggingface"
model = "swiss-ai/Apertus-8B-Instruct-2509"
base_url = "https://router.huggingface.co/v1"
timeout_seconds = 120.0
provider = "publicai"
token_env = "HF_TOKEN"

[profiles.hf_paid]
adapter = "huggingface"
model = "swiss-ai/Apertus-70B-Instruct-2509"
base_url = "https://router.huggingface.co/v1"
timeout_seconds = 180.0
provider = "publicai"
token_env = "HF_TOKEN"
""".strip()


class ModelProfileTests(unittest.TestCase):
    def test_repository_config_resolves_local_q4_profile(self) -> None:
        config = load_model_profiles(REPOSITORY_ROOT / "config" / "semantic-models.toml")

        self.assertEqual(config.active_profile.name, "ollama_local")
        self.assertEqual(
            config.schema_version,
            "swisstip.semantic-model-profiles/v1",
        )
        self.assertEqual(config.active_profile.adapter, "ollama")
        self.assertEqual(
            config.active_profile.model,
            "MichelRosselli/apertus:8b-instruct-2509-q4_k_m",
        )
        self.assertEqual(config.active_profile.num_ctx, 8192)
        self.assertEqual(config.active_profile.keep_alive, "5m")
        self.assertIsNone(config.active_profile.provider)
        self.assertEqual(config.generation.temperature, 0.0)
        self.assertGreater(config.generation.max_output_tokens, 0)
        self.assertGreater(config.extraction.chunk_content_characters, 0)
        self.assertLess(
            config.extraction.chunk_overlap_characters,
            config.extraction.chunk_content_characters,
        )
        self.assertEqual(config.extraction.max_pages_per_run, 10)
        self.assertEqual(config.extraction.max_concepts_per_chunk, 12)
        self.assertEqual(config.extraction.max_total_input_characters, 120000)
        self.assertEqual(config.extraction.max_model_requests_per_page, 12)
        self.assertEqual(config.extraction.max_model_requests_per_run, 20)

    def test_file_selector_is_not_overridden_by_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"SWISSTIP_SEMANTIC_PROFILE": "hf_paid"},
            clear=False,
        ):
            config = self._load(VALID_CONFIG)

        self.assertEqual(config.active_profile.name, "ollama_local")

    def test_huggingface_profiles_are_resolved_with_safe_token_reference(self) -> None:
        for name, expected_model in {
            "hf_free": "swiss-ai/Apertus-8B-Instruct-2509",
            "hf_paid": "swiss-ai/Apertus-70B-Instruct-2509",
        }.items():
            with self.subTest(name=name):
                config = self._load(
                    VALID_CONFIG.replace(
                        'active_profile = "ollama_local"',
                        f'active_profile = "{name}"',
                    )
                )
                self.assertEqual(config.active_profile.adapter, "huggingface")
                self.assertEqual(config.active_profile.model, expected_model)
                self.assertEqual(config.active_profile.provider, "publicai")
                self.assertEqual(config.active_profile.token_env, "HF_TOKEN")
                self.assertIsNone(config.active_profile.bill_to)

    def test_unknown_active_profile_is_rejected(self) -> None:
        self._assert_invalid(
            VALID_CONFIG.replace(
                'active_profile = "ollama_local"',
                'active_profile = "missing"',
            ),
            "unknown profile",
        )

    def test_unknown_schema_version_is_rejected(self) -> None:
        self._assert_invalid(
            VALID_CONFIG.replace(
                'schema_version = "swisstip.semantic-model-profiles/v1"',
                'schema_version = "future/v2"',
            ),
            "schema_version",
        )

    def test_missing_tables_and_wrong_field_types_are_rejected(self) -> None:
        cases = {
            "missing generation": VALID_CONFIG.replace("[generation]", "[not_generation]"),
            "selector type": VALID_CONFIG.replace(
                'active_profile = "ollama_local"', "active_profile = 7"
            ),
            "integer type": VALID_CONFIG.replace(
                "max_output_tokens = 2048", 'max_output_tokens = "2048"'
            ),
            "profile table type": VALID_CONFIG.replace(
                "[profiles.hf_paid]", 'profiles.hf_paid = "not-a-table"'
            ),
        }
        for name, document in cases.items():
            with self.subTest(name=name):
                self._assert_invalid(document)

    def test_unknown_adapters_and_adapter_specific_fields_are_rejected(self) -> None:
        cases = {
            "unknown adapter": VALID_CONFIG.replace(
                'adapter = "ollama"', 'adapter = "other"', 1
            ),
            "ollama missing context": VALID_CONFIG.replace("num_ctx = 8192\n", ""),
            "ollama missing keep alive": VALID_CONFIG.replace(
                'keep_alive = "5m"\n', ""
            ),
            "hf missing provider": VALID_CONFIG.replace('provider = "publicai"\n', "", 1),
            "hf missing token env": VALID_CONFIG.replace('token_env = "HF_TOKEN"\n', "", 1),
            "ollama with hf field": VALID_CONFIG.replace(
                "num_ctx = 8192",
                'num_ctx = 8192\nprovider = "publicai"',
            ),
        }
        for name, document in cases.items():
            with self.subTest(name=name):
                self._assert_invalid(document)

    def test_urls_must_be_absolute_http_or_https_without_credentials(self) -> None:
        for invalid_url in (
            "localhost:11434",
            "ftp://localhost/model",
            "http://user:secret@localhost:11434",
            "http://localhost:11434?token=secret",
            "http://localhost:70000",
            "http://local host:11434",
        ):
            with self.subTest(url=invalid_url):
                self._assert_invalid(
                    VALID_CONFIG.replace(
                        "http://127.0.0.1:11434",
                        invalid_url,
                    ),
                    "base_url",
                )

    def test_generation_and_extraction_ranges_are_validated(self) -> None:
        replacements = {
            "temperature below range": ("temperature = 0.0", "temperature = -0.1"),
            "temperature above range": ("temperature = 0.0", "temperature = 2.1"),
            "output tokens": ("max_output_tokens = 2048", "max_output_tokens = 0"),
            "chunk characters": (
                "chunk_content_characters = 12000",
                "chunk_content_characters = 0",
            ),
            "negative overlap": (
                "chunk_overlap_characters = 600",
                "chunk_overlap_characters = -1",
            ),
            "overlap too large": (
                "chunk_overlap_characters = 600",
                "chunk_overlap_characters = 6001",
            ),
            "concept limit": (
                "max_concepts_per_chunk = 24",
                "max_concepts_per_chunk = 0",
            ),
            "page limit": ("max_pages_per_run = 10", "max_pages_per_run = 0"),
            "total input": (
                "max_total_input_characters = 120000",
                "max_total_input_characters = 0",
            ),
            "per-page request limit": (
                "max_model_requests_per_page = 12",
                "max_model_requests_per_page = 0",
            ),
            "run request limit": (
                "max_model_requests_per_run = 20",
                "max_model_requests_per_run = 0",
            ),
            "timeout": ("timeout_seconds = 180.0", "timeout_seconds = 0",),
            "ollama context": ("num_ctx = 8192", "num_ctx = 0"),
        }
        for name, (old, new) in replacements.items():
            with self.subTest(name=name):
                self._assert_invalid(VALID_CONFIG.replace(old, new, 1))

        self._assert_invalid(
            VALID_CONFIG.replace(
                "max_model_requests_per_run = 20",
                "max_model_requests_per_run = 10",
            ),
            "must not exceed",
        )

    def test_adapter_specific_urls_are_rejected_during_profile_loading(self) -> None:
        self._assert_invalid(
            VALID_CONFIG.replace(
                "http://127.0.0.1:11434",
                "http://127.0.0.1:11434/api",
            ),
            "Ollama adapter",
        )
        self._assert_invalid(
            VALID_CONFIG.replace(
                "https://router.huggingface.co/v1",
                "http://router.huggingface.co/v1",
                1,
            ),
            "HTTPS",
        )

    def test_unknown_fields_are_rejected_in_every_profile(self) -> None:
        self._assert_invalid(
            VALID_CONFIG.replace(
                'token_env = "HF_TOKEN"\n\n[profiles.hf_paid]',
                'token_env = "HF_TOKEN"\nunexpected = true\n\n[profiles.hf_paid]',
            ),
            "unknown field",
        )

    def test_literal_credentials_are_forbidden_at_any_depth(self) -> None:
        for field in ("token", "api_key", "api-key"):
            with self.subTest(field=field):
                self._assert_invalid(
                    f'{VALID_CONFIG}\n{field} = "must-not-be-here"\n',
                    "forbidden",
                )

    def _load(self, document: str):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "models.toml"
            path.write_text(document, encoding="utf-8")
            return load_model_profiles(path)

    def _assert_invalid(self, document: str, message: str | None = None) -> None:
        with self.assertRaises(ModelProfileConfigurationError) as raised:
            self._load(document)
        if message is not None:
            self.assertIn(message, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
