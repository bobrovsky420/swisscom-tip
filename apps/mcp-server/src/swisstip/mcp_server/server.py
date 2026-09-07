"""Serve explicitly supplied local releases over MCP stdio."""

import argparse
import asyncio
import logging
from pathlib import Path

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from pydantic import TypeAdapter

from swisstip.core.contracts import (
    GetCoverageRequest, GetCoverageResult, GetEvidenceRequest, GetEvidenceResult,
    StructuredGroundingRequest, StructuredGroundingResult, ToolError, ValidationIssue,
)
from swisstip.runtime import KnowledgeService, ReleaseStore
from swisstip.runtime.providers import OllamaRetrievalProvider
from swisstip.runtime.provider_config import load_provider_settings


TOOL_CONTRACTS = {
    "get_coverage": (GetCoverageRequest, GetCoverageResult,
                     "Discover bounded catalog levels and inline context schemas. Pin the returned release on child and continuation requests."),
    "resolve": (StructuredGroundingRequest, StructuredGroundingResult,
                "Resolve explicit published scope and typed context against a pinned release. Retrieval terms only rank eligible evidence. Returns facts and citations; no generated answer."),
    "get_evidence": (GetEvidenceRequest, GetEvidenceResult,
                     "Read up to five original evidence excerpts and citations by their pinned release and evidence IDs."),
}


def tool_input_schema(model):
    """Inline local definitions for clients that inspect parameter types directly.

    In particular, Ollama's Qwen XML tool parser selects argument types from
    property.type/anyOf rather than resolving JSON Schema references. A bare
    $ref can therefore turn a correctly generated object into a string.
    Keep the canonical core schemas and strict runtime validation unchanged.
    """
    schema = model.model_json_schema()
    definitions = schema.pop("$defs", {})

    def expand(value, active=()):
        if isinstance(value, list):
            return [expand(item, active) for item in value]
        if not isinstance(value, dict):
            return value
        reference = value.get("$ref")
        if reference is None:
            return {key: expand(item, active) for key, item in value.items()}
        if not reference.startswith("#/$defs/") or reference in active:
            raise ValueError("Tool input schemas require acyclic local definitions")
        name = reference.removeprefix("#/$defs/").replace("~1", "/").replace("~0", "~")
        resolved = expand(definitions[name], (*active, reference))
        siblings = expand({key: item for key, item in value.items() if key != "$ref"}, active)
        # A reference's sibling constraints are conjunctive. Preserve both sets
        # if their keywords overlap, rather than overwrite a referenced bound.
        if resolved.keys() & siblings.keys():
            return {**resolved, "allOf": [*resolved.get("allOf", []), siblings]}
        return {**resolved, **siblings}

    return expand(schema)


def create_server(service: KnowledgeService) -> Server:
    server = Server("swisstip", version="0.1.0")

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=name, description=description,
                           inputSchema=tool_input_schema(request),
                           outputSchema={"type": "object", **TypeAdapter(response | ToolError).json_schema()},
                           annotations=types.ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                                            openWorldHint=False))
                for name, (request, response, description) in TOOL_CONTRACTS.items()]

    # Runtime validation preserves the shared typed errors, including strict
    # scalar types and unknown fields, for both Python and MCP callers.
    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        if name not in TOOL_CONTRACTS:
            result = ToolError(code="INVALID_ARGUMENT", issues=[ValidationIssue(
                path="name", reason_code="unknown_tool", message="Unknown tool name.")])
        else:
            try:
                result = getattr(service, name)(arguments)
            except Exception:
                logging.getLogger(__name__).exception("Knowledge service operation failed: %s", name)
                result = ToolError(code="OPERATIONAL_ERROR", issues=[ValidationIssue(
                    path="release", reason_code="execution_failed",
                    message="The loaded release could not complete this operation.")])
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=result.model_dump_json())],
            structuredContent=result.model_dump(mode="json"), isError=isinstance(result, ToolError))

    return server


async def serve(service: KnowledgeService):
    server = create_server(service)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, action="append", required=True,
                        help="Serving release JSON; repeat to retain historical releases.")
    parser.add_argument("--active-release-id", required=True)
    parser.add_argument("--embedding-url", help="Opt-in Ollama embedding base URL; model is pinned by each release.")
    parser.add_argument("--ranking-url", help="Opt-in Ollama ranking base URL; model is pinned by each release.")
    parser.add_argument("--provider-timeout", type=float, help="Timeout for legacy Ollama URL flags; default 30 seconds.")
    parser.add_argument("--provider-config", type=Path, help="Retrieval provider TOML with endpoints and model allowlists.")
    args = parser.parse_args(argv)
    if args.provider_config and (args.embedding_url or args.ranking_url or args.provider_timeout is not None):
        parser.error("--provider-config cannot be combined with provider URL or timeout flags")
    try:
        store = ReleaseStore.from_files(args.release, active_release_id=args.active_release_id)
        if args.provider_config:
            embedding, ranking = load_provider_settings(args.provider_config).create_providers()
        else:
            timeout = args.provider_timeout if args.provider_timeout is not None else 30.0
            embedding = OllamaRetrievalProvider(args.embedding_url, timeout=timeout) if args.embedding_url else None
            ranking = OllamaRetrievalProvider(args.ranking_url, timeout=timeout) if args.ranking_url else None
    except (OSError, ValueError) as exc:
        parser.error(f"Cannot load serving releases: {exc}")
    asyncio.run(serve(KnowledgeService(store, embedding_provider=embedding, ranking_provider=ranking)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
