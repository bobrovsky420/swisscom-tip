from __future__ import annotations

import json
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

APP_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = APP_ROOT.parents[1]
sys.path.insert(0, str(APP_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT / "packages" / "ingestion" / "src"))

from swisstip.builder.huggingface_provider import (  # noqa: E402
    HuggingFaceRouterProvider,
)
from swisstip.builder.model_profiles import load_model_profiles  # noqa: E402
from swisstip.builder.provider_factory import (  # noqa: E402
    ProviderFactoryConfigurationError,
    create_semantic_model_provider,
)
from swisstip.ingestion.ollama import (  # noqa: E402
    OllamaSemanticModelProvider,
)


class FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self.headers: dict[str, str] = {}
        self.closed = False

    def getcode(self) -> int:
        return 200

    def read(self, amount: int) -> bytes:
        return self._body[:amount]

    def close(self) -> None:
        self.closed = True


class RecordingOpener:
    def __init__(self) -> None:
        self.requests: list[urllib.request.Request] = []

    def open(self, request: urllib.request.Request, *, timeout: float) -> FakeResponse:
        self.requests.append(request)
        requested_model = json.loads(request.data.decode("utf-8"))["model"]
        return FakeResponse(
            {
                "id": "request-1",
                "model": requested_model,
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": '{"concepts": []}'},
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2},
            }
        )


class ProviderFactoryTests(unittest.TestCase):
    def test_builds_configured_local_ollama_profile(self) -> None:
        config = self._load_profile("ollama_local")

        provider = create_semantic_model_provider(
            config,
            environ={},
            opener=RecordingOpener(),
        )

        self.assertIsInstance(provider, OllamaSemanticModelProvider)
        self.assertEqual(
            provider.options.model,
            "MichelRosselli/apertus:8b-instruct-2509-q4_k_m",
        )
        self.assertEqual(provider.options.base_url, "http://127.0.0.1:11434")
        self.assertEqual(provider.options.num_ctx, 8192)
        self.assertEqual(provider.options.num_predict, 2048)
        self.assertEqual(provider.options.temperature, 0.0)
        self.assertEqual(provider.options.keep_alive, "5m")

    def test_builds_both_hugging_face_profiles_with_the_same_token_mechanism(self) -> None:
        for profile, expected_model in {
            "hf_free": "swiss-ai/Apertus-8B-Instruct-2509:publicai",
            "hf_paid": "swiss-ai/Apertus-70B-Instruct-2509:publicai",
        }.items():
            with self.subTest(profile=profile):
                config = self._load_profile(profile)
                opener = RecordingOpener()
                provider = create_semantic_model_provider(
                    config,
                    environ={"HF_TOKEN": "hf_test_token"},
                    opener=opener,
                )

                self.assertIsInstance(provider, HuggingFaceRouterProvider)
                provider.generate_structured(
                    system_prompt="Extract concepts.",
                    user_prompt="Page text.",
                    response_schema={"type": "object"},
                )

                request = opener.requests[0]
                payload = json.loads(request.data.decode("utf-8"))
                self.assertEqual(payload["model"], expected_model)
                self.assertEqual(
                    request.get_header("Authorization"),
                    "Bearer hf_test_token",
                )
                self.assertEqual(
                    request.full_url,
                    "https://router.huggingface.co/v1/chat/completions",
                )

    def test_hugging_face_profile_fails_closed_without_token(self) -> None:
        config = self._load_profile("hf_free")

        with self.assertRaisesRegex(
            ProviderFactoryConfigurationError,
            "requires environment variable HF_TOKEN",
        ):
            create_semantic_model_provider(config, environ={})

    def _load_profile(self, profile: str):
        source_path = REPOSITORY_ROOT / "config" / "semantic-models.toml"
        document = source_path.read_text(encoding="utf-8")
        document = document.replace(
            'active_profile = "ollama_local"',
            f'active_profile = "{profile}"',
        )
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "semantic-models.toml"
            config_path.write_text(document, encoding="utf-8")
            return load_model_profiles(config_path)


if __name__ == "__main__":
    unittest.main()
