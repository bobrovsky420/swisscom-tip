"""Named deployment profiles selected independently for embedding and ranking."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from swisstip.core.contracts import ShortText, StrictModel
from swisstip.core.model_profiles import load_model_config
from .providers import GroqAnswerRelevanceProvider, GroqRankingProvider, OllamaRetrievalProvider


class OllamaProfile(StrictModel):
    adapter: Literal["ollama"]
    role: Literal["embedding", "ranking"]
    model: ShortText
    base_url: ShortText
    timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 30.0

    def create_provider(self):
        return OllamaRetrievalProvider(self.base_url, timeout=self.timeout_seconds, expected_model=self.model)


class GroqProfile(StrictModel):
    adapter: Literal["groq"]
    role: Literal["ranking"]
    model: Literal["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    base_url: ShortText
    token_env: Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")] = "GROQ_API_KEY"
    timeout_seconds: Annotated[float, Field(gt=0, le=300)] = 60.0
    scoring_contract: Literal["relevance_v1", "answer_relevance_v2"] = "relevance_v1"

    def create_provider(self):
        provider = GroqAnswerRelevanceProvider if self.scoring_contract == "answer_relevance_v2" else GroqRankingProvider
        return provider(self.base_url, timeout=self.timeout_seconds,
                        expected_model=self.model, token_env=self.token_env)


RetrievalProfile = Annotated[OllamaProfile | GroqProfile, Field(discriminator="adapter")]
ProfileName = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$", max_length=200)]


class ProfileSelection(StrictModel):
    active_profile: ProfileName


class ProviderSettings(StrictModel):
    schema_version: Literal["swisstip.retrieval-model-profiles/v1"]
    embedding: ProfileSelection
    ranking: ProfileSelection
    profiles: Annotated[dict[ProfileName, RetrievalProfile], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_profiles(self):
        for role in ("embedding", "ranking"):
            name = getattr(self, role).active_profile
            if name not in self.profiles:
                raise ValueError(f"{role}.active_profile refers to unknown profile {name!r}; "
                                 f"available profiles: {', '.join(sorted(self.profiles))}")
            if self.profiles[name].role != role:
                raise ValueError(f"{role}.active_profile requires a {role} profile: {name!r}")
        # Validate endpoints/transport limits for inactive profiles too. Creating
        # an adapter does not read credentials, load models or make network calls.
        for profile in self.profiles.values():
            profile.create_provider()
        return self

    @property
    def embedding_profile(self):
        return self.profiles[self.embedding.active_profile]

    @property
    def ranking_profile(self):
        return self.profiles[self.ranking.active_profile]

    def create_providers(self):
        # The configured model is an allowlist, never a replacement for the
        # release's model or vector index. Mismatches fail before network I/O.
        return self.embedding_profile.create_provider(), self.ranking_profile.create_provider()


def load_provider_settings(path: Path) -> ProviderSettings:
    return ProviderSettings.model_validate(load_model_config(path))
