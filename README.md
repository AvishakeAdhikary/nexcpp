# nexcpp

**nexcpp** is a Model Context Protocol (MCP) server that gives any
MCP-compatible AI agent — Claude, Codex, Cursor, Windsurf — deep,
structured knowledge of C++ development: language and library docs,
CMake, vcpkg/Conan, sandboxed builds, static analysis, code generation,
and GitHub automation. It runs as a local subprocess and speaks
JSON-RPC over stdio (or SSE for team deployments).

> nexcpp is **not** a CLI tool. Agents call it; humans configure it.

---

## Install

Requires Python 3.11+.

```bash
git clone https://github.com/AvishakeAdhikary/nexcpp.git
cd nexcpp
uv sync             # or: pip install -e ".[dev]"
nexcpp-fetch all    # populate the offline docs index
```

## Run

```bash
# stdio (default — how agents launch it)
uv run server.py

# SSE (team / remote deployments)
uv run server.py --transport sse --port 7777
```

Useful flags: `--config <path>`, `--log-level DEBUG`.

## Configure your agent

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json` (Windows) /
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "nexcpp": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/nexcpp", "run", "server.py"]
    }
  }
}
```

### Claude Code

`.claude/settings.json` (project) or `~/.claude/settings.json` (global):

```json
{
  "mcpServers": {
    "nexcpp": {
      "command": "uv",
      "args": ["--directory", "/path/to/nexcpp", "run", "server.py"],
      "type": "stdio"
    }
  }
}
```

Or: `claude mcp add nexcpp -- uv --directory /path/to/nexcpp run server.py`.

### Codex CLI

`~/.codex/config.yaml`:

```yaml
mcp_servers:
  nexcpp:
    command: uv
    args:
      - --directory
      - /absolute/path/to/nexcpp
      - run
      - server.py
```

### Cursor / Windsurf / VS Code

`.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) — same
shape as Claude Desktop. Windsurf reads
`~/.codeium/windsurf/mcp_config.json`; VS Code reads `.vscode/mcp.json`.

### Remote SSE

```json
{
  "mcpServers": {
    "nexcpp": { "url": "http://localhost:7777/sse", "type": "sse" }
  }
}
```

## What it exposes

* **Tools** — `search_cpp_docs`, `manage_file`, `build_project`,
  `run_snippet`, `analyze_code`, `generate_package`, `generate_bridge`,
  `github_op`.
* **Resources** — `nexcpp://docs/std/{symbol}`,
  `nexcpp://docs/cmake/{topic}`, `nexcpp://docs/vcpkg/{package}`,
  `nexcpp://docs/index`, `nexcpp://project/files`,
  `nexcpp://project/config`, `nexcpp://project/build-system`,
  `nexcpp://project/dependencies`, `nexcpp://build/log/latest`.
* **Prompts** — `cpp_library_scaffold`, `cmake_error_fix`,
  `vcpkg_port_authoring`, `pybind11_binding`, `sanitizer_debug`,
  `github_release`.

## Project config

Drop a `.nexcpp/config.toml` next to your project for per-repo settings
(docs mirror path, vcpkg root, file allowlist, plugin list). Global
defaults live at `~/.nexcpp/config.toml`.

## License

MIT.
