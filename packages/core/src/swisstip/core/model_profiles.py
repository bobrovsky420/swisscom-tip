"""Resolve shared model definitions before role-specific configuration validation."""

from pathlib import Path
import re
import tomllib


CATALOG_SCHEMA_VERSION = "swisstip.model-profiles/v1"
_IDENTITY_FIELDS = {"adapter", "model", "base_url", "provider", "token_env", "bill_to"}
_ADAPTER_FIELDS = {
    "ollama": {"adapter", "model", "base_url"},
    "huggingface": _IDENTITY_FIELDS,
    "groq": {"adapter", "model", "base_url", "token_env"},
    "deepseek": {"adapter", "model", "base_url", "token_env"},
}


def _reject_secrets(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower().replace("-", "_") in {"api_key", "token"}:
                raise ValueError(f"literal credential field {key!r} is forbidden; use token_env")
            _reject_secrets(child)
    elif isinstance(value, list):
        for child in value:
            _reject_secrets(child)


def _read(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            document = tomllib.load(stream)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"invalid TOML in {path}: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"cannot read model profile file {path}: {exc}") from exc
    _reject_secrets(document)
    return document


def load_model_catalog(path: str | Path) -> dict[str, dict]:
    """Load connection identities only; role loaders validate transport and options."""
    document = _read(Path(path))
    if set(document) - {"schema_version", "profiles"}:
        raise ValueError("model catalog contains unknown fields")
    if document.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ValueError(f"model catalog.schema_version must be {CATALOG_SCHEMA_VERSION!r}")
    profiles = document.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("model catalog.profiles must be a non-empty table")
    for name, profile in profiles.items():
        label = f"model catalog.profiles.{name}"
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,199}", name):
            raise ValueError("model catalog profile names must be letters, digits, hyphens or underscores")
        if not isinstance(profile, dict):
            raise ValueError(f"{label} must be a table")
        adapter = profile.get("adapter")
        if not isinstance(adapter, str) or adapter not in _ADAPTER_FIELDS:
            raise ValueError(f"{label}.adapter must be ollama, huggingface, groq or deepseek")
        unknown = set(profile) - _ADAPTER_FIELDS[adapter]
        if unknown:
            raise ValueError(f"{label} contains unknown fields: {', '.join(sorted(unknown))}")
        required = {"adapter", "model", "base_url"}
        if adapter == "huggingface":
            required |= {"provider", "token_env"}
        if adapter == "deepseek":
            required.add("token_env")
        if required - set(profile):
            raise ValueError(f"{label} requires {', '.join(sorted(required - set(profile)))}")
        for key, value in profile.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label}.{key} must be a non-empty string")
        if "token_env" in profile and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", profile["token_env"]):
            raise ValueError(f"{label}.token_env must be an environment variable name")
    return profiles


def load_model_config(path: str | Path) -> dict:
    """Return an inline document, resolving references relative to the input file.

    Legacy self-contained documents remain supported. Model identities cannot be
    overridden by a referring profile; timeouts and other role options stay in
    that profile. No credentials are read and no provider calls are made here.
    """
    config_path = Path(path)
    document = _read(config_path)
    catalog = None
    if "model_profiles_file" in document:
        reference = document.pop("model_profiles_file")
        if not isinstance(reference, str) or not reference.strip():
            raise ValueError("model_profiles_file must be a non-empty path string")
        catalog = load_model_catalog(config_path.parent / reference)
    profiles = document.get("profiles")
    if isinstance(profiles, dict):
        for name, profile in profiles.items():
            if not isinstance(profile, dict) or "model_profile" not in profile:
                continue  # The role loader validates inline profiles and table types.
            reference = profile["model_profile"]
            if catalog is None:
                raise ValueError(f"profiles.{name}.model_profile requires model_profiles_file")
            if not isinstance(reference, str) or reference not in catalog:
                raise ValueError(f"profiles.{name}.model_profile refers to an unknown model profile")
            conflicts = set(profile) & _IDENTITY_FIELDS
            if conflicts:
                raise ValueError(f"profiles.{name} cannot override shared model fields: {', '.join(sorted(conflicts))}")
            options = {key: value for key, value in profile.items() if key != "model_profile"}
            profiles[name] = {**catalog[reference], **options}
    return document
