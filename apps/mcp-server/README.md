# Structured knowledge MCP server

The stdio application exposes exactly `get_coverage`, `resolve` and `get_evidence`
through the [runtime service](../../packages/runtime/README.md). It uses the
[official MCP Python SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)
with an explicit `<2` dependency boundary; the tested SDK version is 1.29.1.
Request schemas are the core contracts, with flat structured arguments and strict
unknown-field handling. Results include structured JSON plus equivalent text JSON.
Typed tool errors set MCP `isError`; factual statuses such as `NEEDS_CONTEXT` and
`OUT_OF_COVERAGE` are normal structured results.

From the repository root:

```shell
./.venv/Scripts/python.exe -m pip install -e packages/core -e packages/runtime -e apps/mcp-server
./.venv/Scripts/python.exe -m swisstip.runtime.fixture --output .local/build03/fixture.json
./.venv/Scripts/python.exe -m swisstip.mcp_server.server --release .local/build03/fixture.json --active-release-id fixture-release-a
```

The last command waits for MCP messages on stdin. Diagnostics go to stderr;
stdout is reserved for the protocol. `swisstip-mcp` is the installed entry point.
On Unix substitute `./.venv/bin/python`.

An MCP client's stdio configuration can use absolute paths without shell
activation or reliance on its working directory:

```json
{
  "mcpServers": {
    "swisstip": {
      "command": "C:/path/to/Hackathon2026/.venv/Scripts/python.exe",
      "args": [
        "-m", "swisstip.mcp_server.server",
        "--release", "C:/path/to/Hackathon2026/.local/build03/fixture.json",
        "--active-release-id", "fixture-release-a"
      ]
    }
  }
}
```

Replace the example root with the checkout's absolute location. Start with
`get_coverage({})`, retain its release ID, then inspect parents with that ID.
Selected topic/concept details include the operation's full context schema.
Copy `next_cursor` unchanged and preserve all selectors and the page limit for
continuations. The default cursor key changes when the server restarts; restart
discovery if a cursor becomes invalid. Submit the structured `resolve` payload
shown in the runtime README. User questions, answer language and conversational
history are not tool arguments.

Repeat `--release` for historical serving bundles and choose the active release
explicitly. Missing pinned releases are never replaced by active data. Invalid
bundles fail startup. The application does not crawl or publish releases and does
not load the experimental candidate-bundle format.

```shell
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -v
./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests -v
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas --check
```

The MCP test launches the actual stdio application with the SDK client and checks
tool schemas, paginated discovery, Python/MCP result parity, original evidence
round-trips, missing context and typed failures. No remote sources or models are
used. This is one SDK client qualification fixture; independent clients,
Swisscom harness compatibility, HTTP deployment and production release promotion
remain separate gates.
