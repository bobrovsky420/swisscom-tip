"""Actual SDK client/server stdio round trips, with no remote services."""

import asyncio
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from swisstip.core.contracts import StructuredGroundingResult, ToolError
from swisstip.runtime import KnowledgeService, ReleaseStore
from swisstip.runtime.fixture import fixture


class MCPTests(unittest.TestCase):
    def test_stdio_discovery_resolution_errors_and_evidence_parity(self):
        async def scenario(directory):
            bundle, request = fixture()
            path = Path(directory) / "fixture.json"
            path.write_text(bundle.model_dump_json(), encoding="utf-8")
            params = StdioServerParameters(command=sys.executable, args=[
                "-m", "swisstip.mcp_server.server", "--release", str(path),
                "--active-release-id", bundle.release.release_id])
            service = KnowledgeService(ReleaseStore([bundle], active_release_id=bundle.release.release_id))
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    tools = {t.name: t for t in listed.tools}
                    self.assertEqual(set(tools), {"get_coverage", "resolve", "get_evidence"})
                    for tool in tools.values():
                        Draft202012Validator.check_schema(tool.inputSchema)
                        Draft202012Validator.check_schema(tool.outputSchema)
                        self.assertFalse(tool.inputSchema["additionalProperties"])
                    self.assertIn("release_id", tools["resolve"].inputSchema["required"])
                    self.assertNotIn("question", tools["resolve"].inputSchema["properties"])

                    async def call(name, payload):
                        response = await session.call_tool(name, payload)
                        data = response.structuredContent
                        self.assertIsNotNone(data, response)
                        self.assertEqual(json.loads(response.content[0].text), data)
                        Draft202012Validator(tools[name].outputSchema).validate(data)
                        return response, data

                    response, root = await call("get_coverage", {})
                    self.assertFalse(response.isError)
                    self.assertEqual(root, service.get_coverage({}).model_dump(mode="json"))
                    _, child = await call("get_coverage", dict(release_id=root["release_id"], parent_id="fixture-topic", limit=1))
                    self.assertTrue(child["context_schemas"])
                    self.assertTrue(child["next_cursor"])
                    _, continuation = await call("get_coverage", dict(release_id=root["release_id"], parent_id="fixture-topic", limit=1, cursor=child["next_cursor"]))
                    self.assertIsNone(continuation["next_cursor"])
                    response, resolved = await call("resolve", request)
                    self.assertFalse(response.isError)
                    StructuredGroundingResult.model_validate(resolved)
                    expected = service.resolve(request).model_dump(mode="json")
                    expected["freshness"]["checked_at"] = resolved["freshness"]["checked_at"]
                    self.assertEqual(resolved, expected)
                    _, fetched = await call("get_evidence", dict(release_id=root["release_id"],
                                                               evidence_ids=[e["evidence_id"] for e in resolved["evidence"]]))
                    self.assertEqual(fetched["evidence"], resolved["evidence"])
                    for name, payload, expected_code in [
                        ("resolve", {**request, "question": "invent context"}, "INVALID_ARGUMENT"),
                        ("resolve", {**request, "release_id": "missing"}, "RELEASE_UNAVAILABLE"),
                        ("get_evidence", dict(release_id=root["release_id"], evidence_ids=["missing"]), "INVALID_ARGUMENT"),
                        ("get_coverage", dict(parent_id="fixture-topic"), "INVALID_ARGUMENT"),
                    ]:
                        response, data = await call(name, payload)
                        self.assertTrue(response.isError)
                        self.assertEqual(ToolError.model_validate(data).code, expected_code)
                    response, data = await call("resolve", {**request, "context": {}})
                    self.assertFalse(response.isError)
                    self.assertEqual(data["status"], "NEEDS_CONTEXT")
                    self.assertTrue(data["missing_context"])

        with TemporaryDirectory() as directory:
            asyncio.run(asyncio.wait_for(scenario(directory), timeout=45))


if __name__ == "__main__":
    unittest.main()
