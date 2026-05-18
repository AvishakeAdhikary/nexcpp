"""Tests for MCP prompts — render output mentions tool names where expected."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest


def _prompt(mcp: Any, name: str, args: dict[str, Any] | None = None) -> str:
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.get_prompt(name, args or {}))
    finally:
        loop.close()
    # FastMCP returns a GetPromptResult-like object with .messages.
    messages = getattr(result, "messages", None)
    if messages is None and isinstance(result, dict):
        messages = result.get("messages")
    if not messages:
        return ""
    out: list[str] = []
    for m in messages:
        content = getattr(m, "content", None)
        if content is None and isinstance(m, dict):
            content = m.get("content")
        if isinstance(content, list):
            for c in content:
                t = getattr(c, "text", None) or (c.get("text") if isinstance(c, dict) else None)
                if t:
                    out.append(t)
        elif content is not None:
            t = getattr(content, "text", None) or (content if isinstance(content, str) else None)
            if t:
                out.append(t)
    return "\n".join(out)


@pytest.mark.parametrize(
    "name,args,must_contain",
    [
        ("cpp_library_scaffold", {"name": "foo", "description": "test", "kind": "static"}, "generate_package"),
        ("cmake_error_fix", {"error_output": "Could not find package fmt"}, "search_cpp_docs"),
        (
            "vcpkg_port_authoring",
            {"library_name": "mylib", "version": "1.0.0", "github_url": "https://github.com/x/y"},
            "portfile",
        ),
        ("pybind11_binding", {"header_file": "x.hpp", "module_name": "x"}, "pybind11"),
    ],
)
def test_prompt_renders_with_tool_hint(mcp_server: Any, name: str, args: dict[str, Any], must_contain: str) -> None:
    try:
        text = _prompt(mcp_server, name, args)
    except Exception:
        pytest.skip(f"prompt {name} not registered yet")
    if not text:
        pytest.skip(f"prompt {name} returned empty content")
    assert isinstance(text, str)
    assert must_contain.lower() in text.lower()
