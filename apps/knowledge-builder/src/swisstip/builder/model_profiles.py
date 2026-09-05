"""Typed loading and validation for semantic-model profiles."""

from __future__ import annotations

import math
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias, cast
from urllib.parse import urlsplit


AdapterName: TypeAlias = Literal["ollama", "huggingface"]
CONFIG_SCHEMA_VERSION = "swisstip.semantic-model-profiles/v1"

_FORBIDDEN_SECRET_FIELDS = frozenset({"api_key", "token"})
_TOP_LEVEL_FIELDS = frozenset(
    {"schema_version", "semantic_model", "generation", "extraction", "profiles"}
)
_COMMON_PROFILE_FIELDS = frozenset(
    {"adapter", "model", "base_url", "timeout_seconds"}
)
_OLLAMA_PROFILE_FIELDS = _COMMON_PROFILE_FIELDS | {
    "keep_alive",
    "num_ctx",
}
_HUGGINGFACE_PROFILE_FIELDS = _COMMON_PROFILE_FIELDS | {
    "provider",
    "token_env",
    "bill_to",
}


class ModelProfileConfigurationError(ValueError):
    """Raised when the semantic-model profile file is incomplete or unsafe."""


@dataclass(frozen=True, slots=True)
class GenerationConfig:
    """Generation values shared by every semantic-model adapter."""

    temperature: float
    max_output_tokens: int


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    """Concept-extraction limits shared across model profiles."""

    prompt_profile: str
    chunk_content_characters: int
    chunk_overlap_characters: int
    max_concepts_per_chunk: int
    max_pages_per_run: int
    max_total_input_characters: int
    max_model_requests_per_page: int
    max_model_requests_per_run: int


@dataclass(frozen=True, slots=True)
class ActiveModelProfile:
    """One fully resolved provider profile for a model factory."""

    name: str
    adapter: AdapterName
    model: str
    base_url: str
    timeout_seconds: float
    provider: str | None = None
    token_env: str | None = None
    bill_to: str | None = None
    num_ctx: int | None = None
    keep_alive: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticModelConfig:
    """Resolved semantic-model, generation, and extraction configuration."""

    schema_version: str
    active_profile: ActiveModelProfile
    generation: GenerationConfig
    extraction: ExtractionConfig


def load_model_profiles(path: str | Path) -> SemanticModelConfig:
    """Load a TOML file and resolve its single active semantic-model profile."""

    config_path = Path(path)
    try:
        with config_path.open("rb") as config_file:
            document = tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ModelProfileConfigurationError(
            f"invalid TOML in {config_path}: {exc}"
        ) from exc
    except OSError as exc:
        raise ModelProfileConfigurationError(
            f"cannot read model profile file {config_path}: {exc}"
        ) from exc

    _reject_secret_fields(document)
    _reject_unknown_fields(document, _TOP_LEVEL_FIELDS, "configuration")
    schema_version = _required_non_empty_string(
        document, "schema_version", "configuration"
    )
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ModelProfileConfigurationError(
            f"configuration.schema_version must be {CONFIG_SCHEMA_VERSION!r}"
        )

    semantic_model = _required_table(document, "semantic_model", "configuration")
    _reject_unknown_fields(semantic_model, {"active_profile"}, "semantic_model")
    active_name = _required_non_empty_string(
        semantic_model, "active_profile", "semantic_model"
    )

    generation = _load_generation(
        _required_table(document, "generation", "configuration")
    )
    extraction = _load_extraction(
        _required_table(document, "extraction", "configuration")
    )
    profile_tables = _required_table(document, "profiles", "configuration")
    if not profile_tables:
        raise ModelProfileConfigurationError("profiles must define at least one profile")

    profiles: dict[str, ActiveModelProfile] = {}
    for name, value in profile_tables.items():
        if not name.strip():
            raise ModelProfileConfigurationError("profile names must not be empty")
        if not isinstance(value, Mapping):
            raise ModelProfileConfigurationError(f"profiles.{name} must be a table")
        profiles[name] = _load_profile(name, cast(Mapping[str, object], value))

    try:
        active_profile = profiles[active_name]
    except KeyError as exc:
        available = ", ".join(sorted(profiles))
        raise ModelProfileConfigurationError(
            f"semantic_model.active_profile refers to unknown profile "
            f"{active_name!r}; available profiles: {available}"
        ) from exc

    return SemanticModelConfig(
        schema_version=schema_version,
        active_profile=active_profile,
        generation=generation,
        extraction=extraction,
    )


def _load_generation(table: Mapping[str, object]) -> GenerationConfig:
    path = "generation"
    _reject_unknown_fields(table, {"temperature", "max_output_tokens"}, path)
    temperature = _required_number(table, "temperature", path)
    if not 0.0 <= temperature <= 2.0:
        raise ModelProfileConfigurationError(
            "generation.temperature must be between 0 and 2 inclusive"
        )
    return GenerationConfig(
        temperature=temperature,
        max_output_tokens=_required_positive_integer(
            table, "max_output_tokens", path
        ),
    )


def _load_extraction(table: Mapping[str, object]) -> ExtractionConfig:
    path = "extraction"
    _reject_unknown_fields(
        table,
        {
            "prompt_profile",
            "chunk_content_characters",
            "chunk_overlap_characters",
            "max_concepts_per_chunk",
            "max_pages_per_run",
            "max_total_input_characters",
            "max_model_requests_per_page",
            "max_model_requests_per_run",
        },
        path,
    )
    chunk_content_characters = _required_positive_integer(
        table, "chunk_content_characters", path
    )
    if chunk_content_characters < 500:
        raise ModelProfileConfigurationError(
            "extraction.chunk_content_characters must be at least 500"
        )
    chunk_overlap_characters = _required_non_negative_integer(
        table, "chunk_overlap_characters", path
    )
    if chunk_overlap_characters > chunk_content_characters // 2:
        raise ModelProfileConfigurationError(
            "extraction.chunk_overlap_characters must not exceed half of "
            "extraction.chunk_content_characters"
        )
    max_concepts_per_chunk = _required_positive_integer(
        table, "max_concepts_per_chunk", path
    )
    if max_concepts_per_chunk > 100:
        raise ModelProfileConfigurationError(
            "extraction.max_concepts_per_chunk must not exceed 100"
        )
    max_model_requests_per_page = _required_positive_integer(
        table, "max_model_requests_per_page", path
    )
    max_model_requests_per_run = _required_positive_integer(
        table, "max_model_requests_per_run", path
    )
    if max_model_requests_per_page > max_model_requests_per_run:
        raise ModelProfileConfigurationError(
            "extraction.max_model_requests_per_page must not exceed "
            "extraction.max_model_requests_per_run"
        )
    return ExtractionConfig(
        prompt_profile=_required_non_empty_string(table, "prompt_profile", path),
        chunk_content_characters=chunk_content_characters,
        chunk_overlap_characters=chunk_overlap_characters,
        max_concepts_per_chunk=max_concepts_per_chunk,
        max_pages_per_run=_required_positive_integer(
            table, "max_pages_per_run", path
        ),
        max_total_input_characters=_required_positive_integer(
            table, "max_total_input_characters", path
        ),
        max_model_requests_per_page=max_model_requests_per_page,
        max_model_requests_per_run=max_model_requests_per_run,
    )


def _load_profile(name: str, table: Mapping[str, object]) -> ActiveModelProfile:
    path = f"profiles.{name}"
    adapter_value = _required_non_empty_string(table, "adapter", path)
    if adapter_value not in {"ollama", "huggingface"}:
        raise ModelProfileConfigurationError(
            f"{path}.adapter must be 'ollama' or 'huggingface'"
        )
    adapter = cast(AdapterName, adapter_value)

    if adapter == "ollama":
        _reject_unknown_fields(table, _OLLAMA_PROFILE_FIELDS, path)
    else:
        _reject_unknown_fields(table, _HUGGINGFACE_PROFILE_FIELDS, path)

    model = _required_non_empty_string(table, "model", path)
    if any(character.isspace() for character in model):
        raise ModelProfileConfigurationError(f"{path}.model must not contain whitespace")
    if adapter == "huggingface" and ":" in model:
        raise ModelProfileConfigurationError(
            f"{path}.model must not include the provider suffix"
        )
    base_url = _required_http_url(table, "base_url", path)
    parsed_base_url = urlsplit(base_url)
    if adapter == "ollama" and parsed_base_url.path not in {"", "/"}:
        raise ModelProfileConfigurationError(
            f"{path}.base_url must not contain a path for the Ollama adapter"
        )
    if adapter == "huggingface" and parsed_base_url.scheme.lower() != "https":
        raise ModelProfileConfigurationError(
            f"{path}.base_url must use HTTPS for the Hugging Face adapter"
        )
    timeout_seconds = _required_number(table, "timeout_seconds", path)
    if timeout_seconds <= 0:
        raise ModelProfileConfigurationError(
            f"{path}.timeout_seconds must be greater than zero"
        )

    if adapter == "ollama":
        return ActiveModelProfile(
            name=name,
            adapter=adapter,
            model=model,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            num_ctx=_required_positive_integer(table, "num_ctx", path),
            keep_alive=_required_non_empty_string(table, "keep_alive", path),
        )

    token_env = _required_non_empty_string(table, "token_env", path)
    if token_env != "HF_TOKEN":
        raise ModelProfileConfigurationError(f"{path}.token_env must be 'HF_TOKEN'")
    provider = _required_non_empty_string(table, "provider", path)
    if ":" in provider or any(character.isspace() for character in provider):
        raise ModelProfileConfigurationError(
            f"{path}.provider must be a single provider identifier"
        )
    return ActiveModelProfile(
        name=name,
        adapter=adapter,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        provider=provider,
        token_env=token_env,
        bill_to=_optional_non_empty_string(table, "bill_to", path),
    )


def _required_table(
    table: Mapping[str, object], key: str, path: str
) -> Mapping[str, object]:
    value = _required_value(table, key, path)
    if not isinstance(value, Mapping):
        raise ModelProfileConfigurationError(f"{path}.{key} must be a table")
    return cast(Mapping[str, object], value)


def _required_non_empty_string(
    table: Mapping[str, object], key: str, path: str
) -> str:
    value = _required_value(table, key, path)
    if not isinstance(value, str):
        raise ModelProfileConfigurationError(f"{path}.{key} must be a string")
    if not value.strip():
        raise ModelProfileConfigurationError(f"{path}.{key} must not be empty")
    if value != value.strip() or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise ModelProfileConfigurationError(
            f"{path}.{key} contains invalid whitespace or control characters"
        )
    return value


def _optional_non_empty_string(
    table: Mapping[str, object], key: str, path: str
) -> str | None:
    if key not in table:
        return None
    return _required_non_empty_string(table, key, path)


def _required_number(table: Mapping[str, object], key: str, path: str) -> float:
    value = _required_value(table, key, path)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ModelProfileConfigurationError(f"{path}.{key} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ModelProfileConfigurationError(f"{path}.{key} must be finite")
    return number


def _required_positive_integer(
    table: Mapping[str, object], key: str, path: str
) -> int:
    value = _required_integer(table, key, path)
    if value <= 0:
        raise ModelProfileConfigurationError(
            f"{path}.{key} must be greater than zero"
        )
    return value


def _required_non_negative_integer(
    table: Mapping[str, object], key: str, path: str
) -> int:
    value = _required_integer(table, key, path)
    if value < 0:
        raise ModelProfileConfigurationError(f"{path}.{key} must not be negative")
    return value


def _required_integer(table: Mapping[str, object], key: str, path: str) -> int:
    value = _required_value(table, key, path)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ModelProfileConfigurationError(f"{path}.{key} must be an integer")
    return value


def _required_http_url(table: Mapping[str, object], key: str, path: str) -> str:
    value = _required_non_empty_string(table, key, path)
    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ModelProfileConfigurationError(
            f"{path}.{key} must be an absolute HTTP(S) URL"
        )
    try:
        parsed.port
    except ValueError as exc:
        raise ModelProfileConfigurationError(
            f"{path}.{key} must contain a valid network port"
        ) from exc
    if any(character.isspace() for character in value):
        raise ModelProfileConfigurationError(
            f"{path}.{key} must not contain whitespace"
        )
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ModelProfileConfigurationError(
            f"{path}.{key} must not contain credentials, a query, or a fragment"
        )
    return value.rstrip("/")


def _required_value(table: Mapping[str, object], key: str, path: str) -> object:
    try:
        return table[key]
    except KeyError as exc:
        raise ModelProfileConfigurationError(
            f"missing required field {path}.{key}"
        ) from exc


def _reject_unknown_fields(
    table: Mapping[str, object], allowed: set[str] | frozenset[str], path: str
) -> None:
    unknown = sorted(set(table) - set(allowed))
    if unknown:
        rendered = ", ".join(unknown)
        raise ModelProfileConfigurationError(
            f"unknown field(s) in {path}: {rendered}"
        )


def _reject_secret_fields(value: object, path: str = "configuration") -> None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = key.strip().lower().replace("-", "_")
            nested_path = f"{path}.{key}"
            if normalized_key in _FORBIDDEN_SECRET_FIELDS:
                raise ModelProfileConfigurationError(
                    f"{nested_path} is forbidden; credentials must not be stored in config"
                )
            _reject_secret_fields(nested_value, nested_path)
    elif isinstance(value, list):
        for index, nested_value in enumerate(value):
            _reject_secret_fields(nested_value, f"{path}[{index}]")
