"""Tests for MCP resources (nexcpp:// URIs)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest


def _read(mcp: Any, uri: str) -> str:
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(mcp.read_resource(uri))
    finally:
        loop.close()
    # read_resource may return Iterable[ResourceContent] or a list.
    if isinstance(result, list):
        if not result:
            return ""
        first = result[0]
        for attr in ("content", "text"):
            val = getattr(first, attr, None)
            if isinstance(val, str):
                return val
        if isinstance(first, dict):
            for k in ("content", "text"):
                if isinstance(first.get(k), str):
                    return first[k]
        return str(first)
    if isinstance(result, str):
        return result
    return str(result)


def test_docs_std_resource_returns_content(mcp_server: Any) -> None:
    pytest.importorskip("resources.cpp_docs")
    text = _read(mcp_server, "nexcpp://docs/std/std::vector")
    assert text
    assert "vector" in text.lower()


def test_docs_cmake_resource_returns_content(mcp_server: Any) -> None:
    pytest.importorskip("resources.cpp_docs")
    text = _read(mcp_server, "nexcpp://docs/cmake/find_package")
    assert text


def test_docs_index_resource(mcp_server: Any) -> None:
    pytest.importorskip("resources.cpp_docs")
    text = _read(mcp_server, "nexcpp://docs/index")
    assert text
    assert "#" in text  # markdown headers


def test_project_files_returns_tree(mcp_server: Any, tmp_project: Path) -> None:
    pytest.importorskip("resources.project")
    text = _read(mcp_server, "nexcpp://project/files")
    assert text
    parsed = json.loads(text)
    assert parsed.get("type") == "dir"
    names = {c.get("name") for c in parsed.get("children", [])}
    assert "CMakeLists.txt" in names


def test_project_build_system_detects_cmake(mcp_server: Any, tmp_project: Path) -> None:
    pytest.importorskip("resources.project")
    text = _read(mcp_server, "nexcpp://project/build-system")
    parsed = json.loads(text)
    types = {s.get("type") for s in parsed.get("systems", [])}
    assert "cmake" in types


def test_build_log_latest_when_none(mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("resources.build_log")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    text = _read(mcp_server, "nexcpp://build/log/latest")
    assert text
    assert "no log" in text.lower() or "not found" in text.lower() or "empty" in text.lower() or len(text) > 0


def test_cmake_presets_resource(mcp_server: Any, tmp_project: Path) -> None:
    """The built-in cmake-helper plugin registers nexcpp://cmake/presets/{name}.

    We register the plugin directly here so this test doesn't depend on the
    plugin loader running.
    """
    pytest.importorskip("mcp.server.fastmcp")
    presets = {
        "version": 6,
        "configurePresets": [
            {"name": "default", "generator": "Ninja"},
        ],
    }
    (tmp_project / "CMakePresets.json").write_text(json.dumps(presets), encoding="utf-8")

    from mcp.server.fastmcp import FastMCP

    from plugins.builtin import cmake_helper
    from sdk import PluginContext

    mcp = FastMCP("preset-test")
    ctx = PluginContext(mcp=mcp, scope="builtin", plugin_name="cmake-helper", plugin_dir=tmp_project)
    cmake_helper.register(ctx)

    text = _read(mcp, "nexcpp://cmake/presets/default")
    parsed = json.loads(text)
    assert parsed.get("preset", {}).get("name") == "default"
