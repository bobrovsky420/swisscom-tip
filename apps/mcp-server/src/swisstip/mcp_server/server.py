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


TOOL_CONTRACTS = {
    "get_coverage": (GetCoverageRequest, GetCoverageResult,
                     "Discover bounded catalog levels and inline context schemas. Pin the returned release on child and continuation requests."),
    "resolve": (StructuredGroundingRequest, StructuredGroundingResult,
                "Resolve explicit published scope and typed context against a pinned release. Retrieval terms only rank eligible evidence. Returns facts and citations; no generated answer."),
    "get_evidence": (GetEvidenceRequest, GetEvidenceResult,
                     "Read up to five original evidence excerpts and citations by their pinned release and evidence IDs."),
}


def create_server(service: KnowledgeService) -> Server:
    server = Server("swisstip", version="0.1.0")

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=name, description=description,
                           inputSchema=request.model_json_schema(),
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
    args = parser.parse_args(argv)
    try:
        store = ReleaseStore.from_files(args.release, active_release_id=args.active_release_id)
    except (OSError, ValueError) as exc:
        parser.error(f"Cannot load serving releases: {exc}")
    asyncio.run(serve(KnowledgeService(store)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
