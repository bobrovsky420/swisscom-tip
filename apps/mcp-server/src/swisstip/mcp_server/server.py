"""Serve explicitly supplied local releases over MCP stdio."""

import argparse
import asyncio
import logging
from pathlib import Path
import sys

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

from .bundled import bundled_releases


TOOL_CONTRACTS = {
    "get_coverage": (GetCoverageRequest, GetCoverageResult,
                     "Discover the published catalog level by level. Call it first with no arguments to obtain "
                     "the active release_id and the knowledge space entry; then repeat with that release_id and "
                     "parent_id set to an entry_id to list its children (knowledge space > domain > topic > "
                     "concepts). Topic and concept levels also return coverage_profiles and context_schemas: a "
                     "profile states, for its concept_ids, the exact intent, jurisdiction (country_code, "
                     "canton_code, municipality_id), scope_modes, temporal_coverage and context schema that "
                     "resolve accepts. Identifiers cannot be guessed; use limit up to 100 and copy next_cursor "
                     "unchanged to continue a listing."),
    "resolve": (StructuredGroundingRequest, StructuredGroundingResult,
                "Return the published facts, original evidence excerpts and citations for the concepts of one "
                "coverage profile of a pinned release; no generated answer. Build the request from a profile "
                "returned by get_coverage: copy its knowledge_space_id, domain_id, topic_id and intent exactly; "
                "give the user's jurisdiction at the most specific level you know (country_code, plus canton_code "
                "and municipality_id when known): a profile serves every place inside its own jurisdiction, so a "
                "federal profile (country only) answers for any canton and executed_scope reports the level that "
                "answered; use concept_ids with that profile's concepts only (normally one concept per call; "
                "resolve related concepts, including federal ones, in separate calls), a scope_mode from its "
                "scope_modes, an as_of date inside its temporal_coverage (normally today; null valid_from and "
                "valid_through mean any date is covered), and context values for every required field of its "
                "context schema. Leave retrieval_terms empty unless the release publishes term routes; "
                "max_evidence is at most 5. NEEDS_CONTEXT lists the missing context fields. OUT_OF_COVERAGE names "
                "the mismatching dimension in unresolved_portions (jurisdiction_not_covered, "
                "more_specific_jurisdiction_required, date_outside_coverage, scope_mode_not_offered, "
                "concept_set_not_published) together with the published values to use instead. Cite the returned "
                "evidence URLs when using the facts."),
    "get_evidence": (GetEvidenceRequest, GetEvidenceResult,
                     "Read up to five original evidence excerpts and citations by release_id and the evidence_ids "
                     "exactly as returned in resolve's evidence array. Rule, fact, concept, profile or document "
                     "identifiers are not evidence IDs."),
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
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument("--release", type=Path, action="append",
                        help="Serving release JSON; repeat to retain historical releases. "
                             "Default: the hash-verified releases bundled with this package.")
    storage.add_argument('--database-dsn-env', help='Environment variable holding a PostgreSQL URL; uses pgvector scoring.')
    parser.add_argument("--active-release-id",
                        help="Release served by default. Required with --release or --database-dsn-env; "
                             "otherwise the bundled manifest's active release.")
    parser.add_argument("--releases-dir", type=Path,
                        help="Folder holding MANIFEST.json and the bundled releases. Default: SWISSTIP_RELEASES_DIR, "
                             "else the releases/ folder found by walking up from the package or the working directory.")
    parser.add_argument("--embedding-url", help="Opt-in Ollama embedding base URL; model is pinned by each release.")
    parser.add_argument("--ranking-url", help="Opt-in Ollama ranking base URL; model is pinned by each release.")
    parser.add_argument("--provider-timeout", type=float, help="Timeout for legacy Ollama URL flags; default 30 seconds.")
    parser.add_argument("--provider-config", type=Path, help="Retrieval provider TOML with endpoints and model allowlists.")
    args = parser.parse_args(argv)
    if args.provider_config and (args.embedding_url or args.ranking_url or args.provider_timeout is not None):
        parser.error("--provider-config cannot be combined with provider URL or timeout flags")
    if args.release is None and args.database_dsn_env is None:
        try:
            args.release, bundled_active = bundled_releases(args.releases_dir)
        except (OSError, ValueError) as exc:
            parser.error(f"No --release given and no bundled release is available: {exc}")
        args.active_release_id = args.active_release_id or bundled_active
        print(f"Serving bundled releases from {args.release[0].parent.parent} (active {args.active_release_id})",
              file=sys.stderr)
    if args.active_release_id is None:
        parser.error("--active-release-id is required with --release or --database-dsn-env")
    try:
        vector_store = None
        if args.database_dsn_env:
            import os
            from swisstip.runtime.postgres import PostgresReleaseStore
            dsn = os.environ.get(args.database_dsn_env, '').strip()
            if not dsn:
                raise ValueError('Database URL environment variable is missing')
            store = PostgresReleaseStore(dsn, active_release_id=args.active_release_id)
            vector_store = store
        else:
            store = ReleaseStore.from_files(args.release, active_release_id=args.active_release_id)
        if args.provider_config:
            embedding, ranking = load_provider_settings(args.provider_config).create_providers()
        else:
            timeout = args.provider_timeout if args.provider_timeout is not None else 30.0
            embedding = OllamaRetrievalProvider(args.embedding_url, timeout=timeout) if args.embedding_url else None
            ranking = OllamaRetrievalProvider(args.ranking_url, timeout=timeout) if args.ranking_url else None
    except Exception as exc:
        if args.database_dsn_env:
            parser.error(f'Cannot load database-backed service ({type(exc).__name__})')
        if not isinstance(exc, (OSError, ValueError)):
            raise
        parser.error(f"Cannot load serving releases: {exc}")
    asyncio.run(serve(KnowledgeService(store, embedding_provider=embedding, ranking_provider=ranking,
                                      vector_store=vector_store)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
