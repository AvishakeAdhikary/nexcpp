"""Tests for the plugin SDK (PluginContext)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest


def test_plugin_context_namespaces_tool_name(tmp_path: Path) -> None:
    pytest.importorskip("mcp.server.fastmcp")
    from mcp.server.fastmcp import FastMCP

    from sdk import PluginContext

    mcp = FastMCP("sdk-test")
    ctx = PluginContext(mcp=mcp, scope="builtin", plugin_name="myplug", plugin_dir=tmp_path)

    @ctx.tool(description="adds two ints")
    def add(a: int, b: int) -> int:
        return a + b

    async def check() -> None:
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert "myplug__add" in names
        result = await mcp.call_tool("myplug__add", {"a": 1, "b": 2})
        # call_tool returns (content_list, structured)
        if isinstance(result, tuple):
            content, structured = result
            assert structured.get("result") == 3 or any(
                getattr(c, "text", "") == "3" for c in content
            )

    asyncio.run(check())


def test_plugin_context_dir_and_log(tmp_path: Path) -> None:
    pytest.importorskip("mcp.server.fastmcp")
    from mcp.server.fastmcp import FastMCP

    from sdk import PluginContext, get_logger

    mcp = FastMCP("sdk-test-2")
    plugin_dir = tmp_path / "myplug"
    plugin_dir.mkdir()
    ctx = PluginContext(mcp=mcp, scope="local", plugin_name="myplug", plugin_dir=plugin_dir)
    assert ctx.dir == plugin_dir
    assert ctx.scope == "local"
    assert ctx.plugin_name == "myplug"
    # The logger we get from get_logger should match the ctx.log.
    assert get_logger("myplug") is ctx.log


def test_plugin_context_prompt_namespaced(tmp_path: Path) -> None:
    pytest.importorskip("mcp.server.fastmcp")
    from mcp.server.fastmcp import FastMCP

    from sdk import PluginContext

    mcp = FastMCP("sdk-test-3")
    ctx = PluginContext(mcp=mcp, scope="builtin", plugin_name="myp", plugin_dir=tmp_path)

    @ctx.prompt(description="greet the user")
    def hello(name: str) -> str:
        return f"hello {name}"

    async def check() -> None:
        prompts = await mcp.list_prompts()
        names = {p.name for p in prompts}
        assert "myp__hello" in names

    asyncio.run(check())
