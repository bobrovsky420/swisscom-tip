"""Build the selected semantic-model adapter from one resolved profile."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from swisstip.ingestion.concepts import SemanticModelProvider
from swisstip.ingestion.ollama import OllamaOptions, OllamaSemanticModelProvider

from .huggingface_provider import HuggingFaceRouterProvider
from .deepseek_provider import DeepSeekSemanticModelProvider
from .groq_provider import GroqSemanticModelProvider
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
    to the token variable explicitly referenced by the selected hosted profile.
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

    if profile.adapter in {"huggingface", "deepseek", "groq"}:
        if profile.token_env is None or (profile.adapter == "huggingface" and profile.provider is None):
            raise ProviderFactoryConfigurationError(
                f"Hosted profile {profile.name!r} is incomplete"
            )
        environment = os.environ if environ is None else environ
        token = environment.get(profile.token_env)
        if token is None or not token.strip():
            raise ProviderFactoryConfigurationError(
                f"profile {profile.name!r} requires environment variable "
                f"{profile.token_env}"
            )
        if profile.adapter == "deepseek":
            return DeepSeekSemanticModelProvider(token=token, model=profile.model, base_url=profile.base_url,
                                                timeout=profile.timeout_seconds, max_tokens=config.generation.max_output_tokens,
                                                temperature=config.generation.temperature, **opener_arguments)
        if profile.adapter == "groq":
            return GroqSemanticModelProvider(token=token, model=profile.model, base_url=profile.base_url,
                                            timeout_seconds=profile.timeout_seconds, max_tokens=config.generation.max_output_tokens,
                                            temperature=config.generation.temperature, response_mode=profile.response_mode,
                                            **opener_arguments)
        return HuggingFaceRouterProvider(
            token=token,
            model=profile.model,
            provider=profile.provider,
            base_url=profile.base_url,
            bill_to=profile.bill_to,
            timeout_seconds=profile.timeout_seconds,
            max_tokens=config.generation.max_output_tokens,
            temperature=config.generation.temperature,
            response_mode=profile.response_mode,
            **opener_arguments,
        )

    raise ProviderFactoryConfigurationError(
        f"unsupported adapter {profile.adapter!r} in profile {profile.name!r}"
    )
