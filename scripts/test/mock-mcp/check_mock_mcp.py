"""Standalone stdio round trip against the mock residence MCP server (no LLM)."""

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "mock_residence_mcp.py"
CONCEPT_ID = "eu-efta-municipal-registration-after-arrival"


async def run():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)],
                                   env={"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    failures = []

    def check(label, condition):
        print(("ok   " if condition else "FAIL ") + label)
        if not condition:
            failures.append(label)

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            check(f"initialize: server {init.serverInfo.name} {init.serverInfo.version}", init.serverInfo.name == "swisstip-mock")
            tools = (await session.list_tools()).tools
            check("tools advertised: " + ", ".join(t.name for t in tools),
                  [t.name for t in tools] == ["get_coverage", "resolve", "get_evidence"])

            coverage = await session.call_tool("get_coverage", {})
            body = coverage.structuredContent
            check("get_coverage returns the concept", not coverage.isError
                  and body["topics"][0]["concepts"][0]["concept_id"] == CONCEPT_ID)

            incomplete = await session.call_tool("resolve", {"concept_id": CONCEPT_ID})
            check("resolve without context -> NEEDS_CONTEXT listing nationality_group and purpose",
                  not incomplete.isError and incomplete.structuredContent["status"] == "NEEDS_CONTEXT"
                  and [m["field"] for m in incomplete.structuredContent["missing_context"]] == ["nationality_group", "purpose"])

            resolved = await session.call_tool("resolve", {
                "concept_id": CONCEPT_ID, "nationality_group": "EU_EFTA", "purpose": "EMPLOYMENT",
                "employment_duration": "MORE_THAN_3_MONTHS", "canton_code": "CH-ZH"})
            result = resolved.structuredContent
            check("resolve EU/EFTA employment Zurich -> SUPPORTED", not resolved.isError and result["status"] == "SUPPORTED")
            statements = " ".join(f["statement"] for f in result.get("facts", []))
            check("facts state 14 days AND before taking up work",
                  "within 14 days" in statements and "before taking up work" in statements)
            check("required user facts include arrival_date and first_working_day",
                  {"arrival_date", "first_working_day"} <= {f["name"] for f in result.get("required_user_facts", [])})
            check("Zurich city appointment fact included for CH-ZH",
                  any(f["fact_id"] == "f-zh-city-appointment" for f in result.get("facts", [])))
            check("text content equals structured content",
                  json.loads(resolved.content[0].text) == result)

            federal = await session.call_tool("resolve", {
                "concept_id": CONCEPT_ID, "nationality_group": "EU_EFTA", "purpose": "EMPLOYMENT"})
            check("resolve without canton omits Zurich facts",
                  not any(f["fact_id"].startswith("f-zh") for f in federal.structuredContent["facts"]))

            third = await session.call_tool("resolve", {
                "concept_id": CONCEPT_ID, "nationality_group": "THIRD_COUNTRY", "purpose": "EMPLOYMENT"})
            check("third-country -> OUT_OF_COVERAGE", third.structuredContent["status"] == "OUT_OF_COVERAGE")

            short = await session.call_tool("resolve", {
                "concept_id": CONCEPT_ID, "nationality_group": "EU_EFTA", "purpose": "EMPLOYMENT",
                "employment_duration": "UP_TO_3_MONTHS"})
            check("up to three months -> short-term notification fact",
                  short.structuredContent["facts"][0]["fact_id"] == "f-short-term-notification")

            ids = [c["evidence_id"] for c in result["citations"]][:5]
            evidence = await session.call_tool("get_evidence", {"evidence_ids": ids})
            check(f"get_evidence returns {len(ids)} excerpts with URLs",
                  not evidence.isError and [e["evidence_id"] for e in evidence.structuredContent["evidence"]] == ids
                  and all(e["citation"]["url"].startswith("https://") for e in evidence.structuredContent["evidence"]))

            bad = await session.call_tool("get_evidence", {"evidence_ids": ["nope"]})
            check("unknown evidence ID -> isError", bad.isError)
            unknown_tool = await session.call_tool("resolve", {"concept_id": "other"})
            check("unknown concept -> isError", unknown_tool.isError)

    print(f"\n{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
