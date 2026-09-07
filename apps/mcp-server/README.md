# Structured knowledge MCP server

The stdio application exposes exactly `get_coverage`, `resolve` and `get_evidence`
through the [runtime service](../../packages/runtime/README.md). It uses the
[official MCP Python SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)
with an explicit `<2` dependency boundary; the tested SDK version is 1.29.1.
Request schemas are the core contracts, with flat structured arguments and strict
unknown-field handling. Results include structured JSON plus equivalent text JSON.
Typed tool errors set MCP `isError`; factual statuses such as `NEEDS_CONTEXT` and
`OUT_OF_COVERAGE` are normal structured results.

Advertised tool input schemas inline local definitions, including the nested
`jurisdiction` object and retrieval-term items. This accommodates clients such as
Ollama's [Qwen tool parser](https://github.com/ollama/ollama/blob/main/model/parsers/qwen3coder.go),
which reads a parameter's inline type and otherwise defaults to a string. The
canonical core schema exports retain their shared definitions. Runtime validation
stays strict: stringified JSON objects are rejected. Restart connected MCP clients
after updating the server so they reload the advertised schemas.

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

Hybrid BUILD-05 bundles use the same three tools. To connect an evaluated bundle
to local Qwen embeddings and Groq evidence ranking, add
`--provider-config config/retrieval-models.toml` (use an absolute path in an MCP
client config). Set `GROQ_API_KEY` in the parent process environment and start
Ollama with `qwen3-embedding:0.6b` installed. The selected ranking model is
`openai/gpt-oss-20b`. Select alternatives by changing `[embedding].active_profile`
and `[ranking].active_profile` to names defined under `[profiles.<name>]` in the
TOML file. The default pair requires the release to pin adapter `groq-ranking/v1`, embedding
adapter `ollama-retrieval/v1`, these exact model names and a matching vector index.
The config performs no startup model calls and cannot rewrite sealed releases.
Allow at least 120 seconds per MCP call for the configured 30-second embedding
and 60-second ranking stages. OpenCode's caller model remains independent.

Alternatively, for an evaluated bundle
whose provider IDs are `ollama-retrieval/v1`, add `--embedding-url` and
`--ranking-url` with the corresponding Ollama base URLs, plus optional
`--provider-timeout` (30 seconds by default). The bundle pins both model names;
CLI flags cannot change them. The legacy URL/timeout flags cannot be combined
with `--provider-config`. No provider calls occur until a valid `resolve`.
Missing or failed providers use only the bundle's evaluated fallback for that
coverage profile, or return `OPERATIONAL_ERROR`. See the runtime README for
asset validation, equivalent-evidence traces and the synthetic hybrid fixture.

```shell
./.venv/Scripts/python.exe -m unittest discover -s packages/runtime/tests -v
./.venv/Scripts/python.exe -m unittest discover -s apps/mcp-server/tests -v
./.venv/Scripts/python.exe -m swisstip.core.schemas --output packages/core/schemas --check
```

The MCP test launches the actual stdio application with the SDK client and checks
tool schemas, paginated discovery, Python/MCP result parity, original evidence
round-trips, missing context and typed failures. No remote sources or models are
used. A hybrid stdio case also checks declared degradation, source filters,
representatives and alternate-evidence lookup. This is one SDK client qualification fixture; independent clients,
Swisscom harness compatibility, HTTP deployment and production release promotion
remain separate gates.
