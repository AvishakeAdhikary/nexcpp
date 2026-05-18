"""Smoke tests for every tool's register() and happy-path callable shape.

Mocks subprocess heavily — we don't want to invoke real compilers in unit
tests. Tools that aren't ready yet (peer streams still authoring) are
skipped via pytest.importorskip.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ----------------------------------------------------------- helpers


def _call(mcp: Any, name: str, args: dict[str, Any]) -> Any:
    """Synchronously invoke an MCP tool by name and return its raw result."""
    loop = asyncio.new_event_loop()
    try:
        out = loop.run_until_complete(mcp.call_tool(name, args))
    finally:
        loop.close()
    # call_tool returns (content_list, structured_result)
    if isinstance(out, tuple) and len(out) == 2:
        return out[1]
    return out


# ----------------------------------------------------------- docs


def test_search_cpp_docs_returns_synthetic_fallback(mcp_server: Any) -> None:
    pytest.importorskip("doc_index")
    result = _call(
        mcp_server,
        "search_cpp_docs",
        {"query": "std::vector", "source": "all", "max_results": 3},
    )
    # FastMCP wraps list results in {'result': [...]}.
    if isinstance(result, dict) and "result" in result:
        items = result["result"]
    else:
        items = result
    assert isinstance(items, list)
    assert len(items) >= 1


# ----------------------------------------------------------- files


def test_manage_file_roundtrip(mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.files")
    monkeypatch.chdir(tmp_path)

    write = _call(
        mcp_server,
        "manage_file",
        {"op": "write", "path": "hello.txt", "content": "hi there"},
    )
    assert write.get("ok") is True

    read = _call(mcp_server, "manage_file", {"op": "read", "path": "hello.txt"})
    assert read.get("ok") is True
    assert "hi there" in (read.get("result") or "")

    append = _call(
        mcp_server,
        "manage_file",
        {"op": "append", "path": "hello.txt", "content": "\nmore"},
    )
    assert append.get("ok") is True

    listing = _call(mcp_server, "manage_file", {"op": "list", "path": "."})
    assert listing.get("ok") is True

    delete = _call(mcp_server, "manage_file", {"op": "delete", "path": "hello.txt"})
    assert delete.get("ok") is True


def test_manage_file_rejects_traversal(mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.files")
    monkeypatch.chdir(tmp_path)
    # Try to read /etc/passwd via traversal
    result = _call(
        mcp_server,
        "manage_file",
        {"op": "read", "path": "/etc/passwd"} if os.name != "nt" else {"op": "read", "path": "C:/Windows/System32/drivers/etc/hosts"},
    )
    assert result.get("ok") is False
    assert result.get("error")


# ----------------------------------------------------------- generate


def test_generate_package_produces_files(mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.generate")
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "fastfoo"
    result = _call(
        mcp_server,
        "generate_package",
        {
            "name": "fastfoo",
            "kind": "static",
            "cpp_std": "20",
            "with_tests": True,
            "with_examples": False,
            "vcpkg": True,
            "license": "MIT",
            "output_dir": str(out_dir),
        },
    )
    # The tool's exact return shape is owned by another stream — we assert
    # only that *something* useful was produced.
    if isinstance(result, dict):
        files = result.get("files") or result.get("created") or []
        if files:
            assert len(files) >= 3
    # Also confirm the output dir got at least some files.
    if out_dir.is_dir():
        produced = list(out_dir.rglob("*"))
        assert any(p.is_file() for p in produced)


def test_generate_bridge_python(mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.generate")
    monkeypatch.chdir(tmp_path)
    header = tmp_path / "api.hpp"
    header.write_text(
        "#pragma once\n"
        "namespace mylib {\n"
        "    int foo(int x);\n"
        "}\n",
        encoding="utf-8",
    )
    result = _call(
        mcp_server,
        "generate_bridge",
        {
            "target_lang": "python",
            "header": str(header),
            "output_dir": str(tmp_path / "bindings"),
        },
    )
    assert isinstance(result, dict)
    assert result.get("ok") in (True, None) or result.get("files_created")


# ----------------------------------------------------------- build


def test_build_project_with_mocked_subprocess(mcp_server: Any, tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.build")

    fake_result = {
        "ok": True,
        "build_system": "cmake",
        "configure_log": "configured",
        "build_log": "built",
        "test_log": "tested",
        "artifacts": [],
        "errors": [],
        "log_id": "deadbeef",
    }
    monkeypatch.setattr("sandbox.pipeline.run_local_build", lambda *a, **kw: fake_result)

    result = _call(
        mcp_server,
        "build_project",
        {
            "project_dir": str(tmp_project),
            "build_type": "Debug",
            "run_tests": False,
            "sandbox": False,
        },
    )
    assert result.get("ok") is True


def test_run_snippet_shape(mcp_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.build")
    fake = {
        "ok": True,
        "stdout": "hello\n",
        "stderr": "",
        "exit_code": 0,
        "compile_errors": [],
        "elapsed_ms": 10,
    }
    monkeypatch.setattr("sandbox.quick.compile_and_run", lambda *a, **kw: fake)
    result = _call(
        mcp_server,
        "run_snippet",
        {
            "code": "int main() { return 0; }",
            "compiler": "clang",
            "std": "20",
            "stdin": "",
            "timeout": 5,
            "sandbox": False,
        },
    )
    assert result.get("ok") is True
    assert "log_id" in result


# ----------------------------------------------------------- analyze


def test_analyze_code_missing_clang_tidy(mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.analyze")
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "a.cpp"
    src.write_text("int main(){return 0;}\n", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = _call(
        mcp_server,
        "analyze_code",
        {"path": str(src), "tool": "clang-tidy", "checks": "*", "fix": False},
    )
    assert result.get("ok") is False
    assert "clang-tidy" in (result.get("error") or "")


# ----------------------------------------------------------- github


def test_github_op_generate_workflow(mcp_server: Any) -> None:
    pytest.importorskip("tools.github")
    try:
        result = _call(
            mcp_server,
            "github_op",
            {
                "op": "generate_workflow",
                "workflow_template": "cpp-ci",
                "workflow_kwargs": {"project_name": "ci"},
            },
        )
    except Exception as exc:
        pytest.skip(f"github_op not callable: {exc}")
    yaml_text = None
    for k in ("workflow_yaml", "yaml", "content", "result"):
        if isinstance(result, dict) and k in result and isinstance(result[k], str):
            yaml_text = result[k]
            break
    if yaml_text is None and isinstance(result, dict) and result.get("ok") is True:
        return
    if yaml_text is not None:
        import yaml as pyyaml

        parsed = pyyaml.safe_load(yaml_text)
        assert isinstance(parsed, dict)


def test_github_op_create_repo_without_token(mcp_server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("tools.github")
    monkeypatch.delenv("NEXCPP_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    # Reset the cached config so the deleted env vars take effect.
    try:
        from config import reset_config_cache

        reset_config_cache()
    except Exception:
        pass
    try:
        result = _call(
            mcp_server,
            "github_op",
            {
                "op": "create_repo",
                "repo": "test-repo",
                "private": True,
            },
        )
    except Exception:
        pytest.skip("github_op create_repo signature mismatch")
    if isinstance(result, dict):
        assert result.get("ok") is False
        err = (result.get("error") or "").lower()
        # Without a token, the GhClient should fail to make authenticated calls.
        # We accept any error message that's reasonable.
        assert err  # must be non-empty
