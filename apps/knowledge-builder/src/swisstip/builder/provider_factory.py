"""Build the selected semantic-model adapter from one resolved profile."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from swisstip.ingestion.concepts import SemanticModelProvider
from swisstip.ingestion.ollama import OllamaOptions, OllamaSemanticModelProvider

from .huggingface_provider import HuggingFaceRouterProvider
from .model_profiles import SemanticModelConfig


class ProviderFactoryConfigurationError(ValueError):
    """Raised when runtime inputs cannot complete the selected profile."""


def create_semantic_model_provider(
    config: SemanticModelConfig,
    *,
    environ: Mapping[str, str] | None = None,
    opener: Any | None = None,
) -> SemanticModelProvider:
    """Create exactly the adapter named by ``config.active_profile``.

    The factory never falls back to another profile. Environment access is limited
    to the token variable explicitly referenced by a Hugging Face profile.
    """

    profile = config.active_profile
    opener_arguments = {} if opener is None else {"opener": opener}

    if profile.adapter == "ollama":
        if profile.num_ctx is None or profile.keep_alive is None:
            raise ProviderFactoryConfigurationError(
                f"Ollama profile {profile.name!r} is missing runtime options"
            )
        return OllamaSemanticModelProvider(
            OllamaOptions(
                model=profile.model,
                base_url=profile.base_url,
                timeout_seconds=profile.timeout_seconds,
                num_ctx=profile.num_ctx,
                num_predict=config.generation.max_output_tokens,
                temperature=config.generation.temperature,
                keep_alive=profile.keep_alive,
            ),
            **opener_arguments,
        )

    if profile.adapter == "huggingface":
        if profile.provider is None or profile.token_env is None:
            raise ProviderFactoryConfigurationError(
                f"Hugging Face profile {profile.name!r} is incomplete"
            )
        environment = os.environ if environ is None else environ
        token = environment.get(profile.token_env)
        if token is None or not token.strip():
            raise ProviderFactoryConfigurationError(
                f"profile {profile.name!r} requires environment variable "
                f"{profile.token_env}"
            )
        return HuggingFaceRouterProvider(
            token=token,
            model=profile.model,
            provider=profile.provider,
            base_url=profile.base_url,
            bill_to=profile.bill_to,
            timeout_seconds=profile.timeout_seconds,
            max_tokens=config.generation.max_output_tokens,
            temperature=config.generation.temperature,
            **opener_arguments,
        )

    raise ProviderFactoryConfigurationError(
        f"unsupported adapter {profile.adapter!r} in profile {profile.name!r}"
    )
