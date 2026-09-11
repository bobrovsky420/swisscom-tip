# Mock residence MCP server and OpenCode caller test

A stdio MCP server with one hardcoded knowledge fact, plus a harness that runs
OpenCode against it. The purpose is to test the calling LLM, not the knowledge
base: does it call the MCP tools for this question, does it collect the arrival
date instead of assuming it, and does it pick the binding deadline?

The fact: EU/EFTA nationals taking up employment in Switzerland must register
with their municipality within 14 days of arrival **and** before starting work.
The server's `resolve` result lists the user facts still needed (arrival date,
first working day) and a decision rule. The decision is left to the LLM.

Files:

- `mock_residence_mcp.py` - the server. Tools `get_coverage`, `resolve`,
  `get_evidence`, same names as the real SwissTIP server, flat schemas, constants
  only. It never reads the repository corpus or releases.
- `check_mock_mcp.py` - standalone MCP client round trip, no LLM.
- `run_opencode_test.py` - OpenCode harness (CLI), see below.

## Server self-check

```shell
./.venv/Scripts/python.exe scripts/test/mock-mcp/check_mock_mcp.py
```

## OpenCode CLI test

Default model: `opencode/ling-3.0-flash-fin-free`, the last model used
successfully with OpenCode in this repository. Override with `--model`.

```shell
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --check-connection
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --live
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --live --scenario work-first --no-followup
```

`--server real` runs the same test against the real SwissTIP MCP server
(`swisstip.mcp_server.server`) on the assistant-curated pilot release, by default
`.local/mvp/residence-semantic-2026-09-11-v2/` (override with `--release-file`
and `--release-id`). Build it first with `scripts/corpora/build_residence_mvp.py`.
The real-server config raises OpenCode's tool-output cap because topic-level
discovery returns about 140 KB. Results are in the
[real-server note](../../../docs/experiments/2026-09-11-opencode-real-mcp-caller-test.md).

```shell
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --check-connection
./.venv/Scripts/python.exe scripts/test/mock-mcp/run_opencode_test.py --server real --live
```

Each live run creates `.local/mock-mcp/runs/run-<timestamp>/` with the generated
`opencode.json`, one JSONL transcript per turn and `summary.json`. The
configuration is passed to the child process only (`OPENCODE_CONFIG` and
`OPENCODE_CONFIG_CONTENT`); the user's own OpenCode configuration is unchanged.
OpenCode runs in a temporary workspace so the repository's `AGENTS.md` is not
injected as instructions.

Turn 1 sends exactly:

> I'm a Czech citizen and starting my work in Zurich next week. By when latest
> should I register my stay on the municipal authority?

Turn 2 answers with the scenario's dates in the same session:

| Scenario | Arrival | First working day | Expected answer |
| --- | --- | --- | --- |
| `work-first` | Sun 13 Sep 2026 | Wed 16 Sep 2026 | Register before 16 Sep (by 15 Sep); the 14-day limit (27 Sep) does not bind |
| `fourteen-days-first` | Tue 1 Sep 2026 | Fri 18 Sep 2026 | Register by 15 Sep (14 days after arrival), earlier than the first working day |

The assessment printed at the end is heuristic (string checks on the final
answer): MCP called, `resolve` used, arrival date asked for, both limits stated,
no date computed before the arrival date was known, expected deadline named in
turn 2. Read the transcript before drawing conclusions.

The generated agent `residence-assistant` has every built-in OpenCode tool
disabled, so only the MCP tools remain, and a short system prompt that mentions
the SwissTIP tools exist without saying when to call them. Replace the prompt
with `--prompt-file` to test other instructions, for example an empty one.

## OpenCode TUI

The harness also writes a stable copy to `.local/mock-mcp/opencode.json`. In
PowerShell:

```powershell
$env:OPENCODE_CONFIG = "C:\Users\bobro\OneDrive\Developer\Hackathon2026\.local\mock-mcp\opencode.json"
Set-Location $env:TEMP\swisstip-mock-mcp-workspace
opencode
```

Select the `residence-assistant` agent (Tab) and paste the question. Setting
`OPENCODE_CONFIG` replaces the user configuration for that process only.
