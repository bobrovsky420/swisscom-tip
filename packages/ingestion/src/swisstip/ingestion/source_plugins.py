"""Versioned source adapters; network and storage remain with the shared runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from importlib.metadata import entry_points
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit
import re

from .concepts import NormalizedPage, normalize_downloaded_page


PLUGIN_API_VERSION = 1
ENTRY_POINT_GROUP = "swisstip.source_plugins"


@dataclass(frozen=True)
class SourceRequest:
    url: str
    as_of: date


@dataclass(frozen=True)
class SourceDocument:
    url: str
    media_type: str
    language: str
    version_uri: str | None = None
    preferred_for_extraction: bool = True
    metadata: dict = field(default_factory=dict)


class SourcePlugin:
    """Subclass and register through the entry-point group or an explicit registry.

    resolve() receives a bounded, cached JSON fetch callback. Plugins must not do
    their own networking. normalize() is local and must never call a model.
    """

    api_version = PLUGIN_API_VERSION
    plugin_id: str
    version: str
    metadata_hosts: tuple[str, ...] = ()
    document_hosts: tuple[str, ...] = ()
    max_documents = 8

    def matches(self, url: str) -> bool:
        raise NotImplementedError

    def resolve(self, request: SourceRequest, fetch_json: Callable[[str], dict]) -> list[SourceDocument]:
        raise NotImplementedError

    def normalize(self, path: Path, provenance: dict, **options) -> NormalizedPage:
        return normalize_downloaded_page(path, **options)


class PluginRegistry:
    def __init__(self, plugins: list[SourcePlugin]) -> None:
        self.plugins = tuple(plugins)
        ids = []
        for plugin in plugins:
            if not isinstance(plugin, SourcePlugin) or plugin.api_version != PLUGIN_API_VERSION:
                raise ValueError("Unsupported source plugin API")
            if not re.fullmatch(r"[a-z][a-z0-9-]*", plugin.plugin_id) or not plugin.version:
                raise ValueError("Source plugins require a stable ID and version")
            if not 1 <= plugin.max_documents <= 100:
                raise ValueError("Source plugin max_documents must be between 1 and 100")
            for host in (*plugin.metadata_hosts, *plugin.document_hosts):
                if not re.fullmatch(r"[a-z0-9.-]+", host):
                    raise ValueError("Source plugins must declare exact host names")
            ids.append(plugin.plugin_id)
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate source plugin ID")

    def select(self, url: str) -> SourcePlugin | None:
        matches = [plugin for plugin in self.plugins if plugin.matches(url)]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous source plugins for {url}: {[p.plugin_id for p in matches]}")
        return matches[0] if matches else None

    def describe(self) -> list[dict]:
        return [{"id": p.plugin_id, "version": p.version, "api_version": p.api_version}
                for p in self.plugins]


def load_source_plugins(names: list[str] | None = None) -> PluginRegistry:
    """Only load explicitly enabled external plugins; Fedlex is bundled by default."""
    from .sources.fedlex import FedlexPlugin

    names = ["fedlex"] if names is None else names
    installed = entry_points(group=ENTRY_POINT_GROUP) if any(n != "fedlex" for n in names) else ()
    plugins = []
    for name in names:
        if name == "fedlex":
            plugin = FedlexPlugin()
        else:
            matches = [entry for entry in installed if entry.name == name]
            if len(matches) != 1:
                raise ValueError(f"Expected one installed source plugin named {name!r}")
            plugin = matches[0].load()()
        if plugin.plugin_id != name:
            raise ValueError(f"Source plugin ID does not match entry-point name {name!r}")
        plugins.append(plugin)
    return PluginRegistry(plugins)


def validate_documents(plugin: SourcePlugin, documents: list[SourceDocument]) -> None:
    if not documents or len(documents) > plugin.max_documents:
        raise ValueError(f"{plugin.plugin_id} returned an empty or oversized document list")
    seen = set()
    for document in documents:
        url = urlsplit(document.url)
        if (url.scheme != "https" or url.hostname not in plugin.document_hosts or
                url.username or url.password or url.port not in (None, 443)):
            raise ValueError(f"{plugin.plugin_id} returned a document outside its declared hosts")
        if document.url in seen:
            raise ValueError(f"{plugin.plugin_id} returned duplicate document URLs")
        if not document.media_type or not document.language:
            raise ValueError("Plugin documents require a media type and language")
        seen.add(document.url)
