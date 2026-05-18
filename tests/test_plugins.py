"""Tests for the plugin discovery & loading system."""

from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture()
def fastmcp() -> Any:
    pytest.importorskip("mcp.server.fastmcp")
    from mcp.server.fastmcp import FastMCP

    return FastMCP("plugins-test")


def test_load_all_discovers_builtins(fastmcp: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Builtins (cpp-analyzer + cmake-helper) should always load."""
    # Make sure no external plugin dirs interfere.
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.chdir(tmp_path)

    from plugins.loader import load_all

    summary = load_all(fastmcp)
    names = {p["name"] for p in summary["loaded"]}
    assert "cpp-analyzer" in names
    assert "cmake-helper" in names


def test_load_all_finds_sandbox_plugin(fastmcp: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A plugin under a /tmp/nexcpp-sandbox-*/plugins dir should load."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.chdir(tmp_path)

    # Temporarily redirect tempfile.gettempdir to our tmp_path.
    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    sandbox_dir = tmp_path / "nexcpp-sandbox-abc" / "plugins"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "my_plugin.py").write_text(
        textwrap.dedent(
            """\
            PLUGIN_META = {"name": "test-sandbox-plugin", "version": "0.1.0"}
            def register(ctx):
                @ctx.tool(description="test tool")
                def echo(msg: str) -> str:
                    return msg
            """
        ),
        encoding="utf-8",
    )

    from plugins.loader import load_all

    summary = load_all(fastmcp)
    names = {p["name"] for p in summary["loaded"]}
    assert "test-sandbox-plugin" in names


def test_local_scope_wins_over_sandbox(fastmcp: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A plugin defined in cwd/.nexcpp/plugins shadows one in sandbox dir."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.chdir(tmp_path)

    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    local_dir = tmp_path / ".nexcpp" / "plugins"
    local_dir.mkdir(parents=True, exist_ok=True)
    (local_dir / "shared.py").write_text(
        textwrap.dedent(
            """\
            PLUGIN_META = {"name": "shared", "version": "1.0.0"}
            def register(ctx):
                @ctx.tool(description="local version")
                def shared_tool() -> str:
                    return "local"
            """
        ),
        encoding="utf-8",
    )

    sandbox_dir = tmp_path / "nexcpp-sandbox-zzz" / "plugins"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "shared.py").write_text(
        textwrap.dedent(
            """\
            PLUGIN_META = {"name": "shared", "version": "1.0.0"}
            def register(ctx):
                @ctx.tool(description="sandbox version")
                def shared_tool() -> str:
                    return "sandbox"
            """
        ),
        encoding="utf-8",
    )

    from plugins.loader import load_all

    summary = load_all(fastmcp)
    loaded_by_name: dict[str, Any] = {p["name"]: p for p in summary["loaded"]}
    assert loaded_by_name.get("shared", {}).get("scope") == "local"
    # The sandbox copy should appear in errors as shadowed.
    shadowed = [e for e in summary["errors"] if e.get("name") == "shared" and e.get("shadowed")]
    assert shadowed


def test_broken_plugin_captured_in_errors(fastmcp: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A plugin that raises during register() must not crash the loader."""
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "home"))
    monkeypatch.chdir(tmp_path)

    import tempfile

    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))

    sandbox_dir = tmp_path / "nexcpp-sandbox-bad" / "plugins"
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    (sandbox_dir / "broken.py").write_text(
        textwrap.dedent(
            """\
            PLUGIN_META = {"name": "broken-plugin", "version": "0.0.0"}
            def register(ctx):
                raise RuntimeError("intentional failure")
            """
        ),
        encoding="utf-8",
    )

    from plugins.loader import load_all

    summary = load_all(fastmcp)
    broken_errors = [e for e in summary["errors"] if e.get("name") == "broken-plugin"]
    assert broken_errors
    assert "intentional failure" in broken_errors[0]["error"]
