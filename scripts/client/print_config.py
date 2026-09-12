"""Print an MCP client configuration for this checkout, with absolute paths.

Nothing is written; paste the output into the client's configuration or
redirect it to a file. The server runs on stdio with the bundled release.
"""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def server_command() -> list[str]:
    venv = ROOT / ".venv"
    executable = venv / ("Scripts/swisstip-mcp.exe" if os.name == "nt" else "bin/swisstip-mcp")
    if executable.is_file():
        return [str(executable)]
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return [str(python if python.is_file() else Path(sys.executable)), "-m", "swisstip.mcp_server.server"]


def opencode_config(command: list[str]) -> dict:
    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {"swisstip": {"type": "local", "command": command, "enabled": True, "timeout": 120000,
                             "environment": {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}}},
        # Topic-level discovery currently returns about 140 KB; OpenCode's default
        # cap of 51,200 bytes would truncate it. Remove once discovery is compact.
        "tool_output": {"max_bytes": 400000, "max_lines": 20000},
    }


def generic_config(command: list[str]) -> dict:
    return {"mcpServers": {"swisstip": {"command": command[0], "args": command[1:],
                                        "env": {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}}}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=["opencode", "generic"], default="opencode",
                        help="opencode: opencode.json; generic: the mcpServers shape used by Claude Desktop and similar clients")
    args = parser.parse_args(argv)
    command = server_command()
    config = opencode_config(command) if args.client == "opencode" else generic_config(command)
    print(json.dumps(config, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
