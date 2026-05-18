"""End-to-end test of the MCP server over stdio.

Marked as integration so it can be skipped with `pytest -m "not integration"`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


_ROOT = Path(__file__).resolve().parent.parent


def _send(proc: subprocess.Popen, payload: dict) -> None:
    if proc.stdin is None:
        raise RuntimeError("no stdin")
    line = json.dumps(payload) + "\n"
    proc.stdin.write(line)
    proc.stdin.flush()


def _recv(proc: subprocess.Popen, timeout: float = 10.0) -> dict:
    if proc.stdout is None:
        raise RuntimeError("no stdout")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.05)
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise TimeoutError(f"no response within {timeout}s")


def test_initialize_and_list_tools() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    proc = subprocess.Popen(
        [sys.executable, "server.py", "--transport", "stdio", "--log-level", "ERROR"],
        cwd=str(_ROOT),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        bufsize=1,
        env=env,
    )

    try:
        # 1. initialize
        _send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "e2e-test", "version": "0.0.0"},
                },
            },
        )
        init_resp = _recv(proc, timeout=15.0)
        assert init_resp.get("id") == 1
        assert "result" in init_resp

        # 2. initialized notification
        _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

        # 3. tools/list
        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools_resp = _recv(proc, timeout=15.0)
        assert tools_resp.get("id") == 2
        tools = tools_resp.get("result", {}).get("tools", [])
        tool_names = {t.get("name") for t in tools}
        # At least one of the core tools should be present.
        expected = {"search_cpp_docs", "manage_file"}
        assert expected & tool_names

        # 4. tools/call search_cpp_docs (if present)
        if "search_cpp_docs" in tool_names:
            _send(
                proc,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "search_cpp_docs",
                        "arguments": {"query": "vector", "source": "all", "max_results": 1},
                    },
                },
            )
            call_resp = _recv(proc, timeout=15.0)
            assert call_resp.get("id") == 3
            assert "result" in call_resp
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
