"""Cross-platform behavior tests.

Exercises code paths whose correctness depends on the host OS — Windows
path separators, locale-dependent encodings, signal handling, etc. Each
test that targets one OS is guarded by ``pytest.mark.skipif`` so the
suite is green on whatever platform the developer runs.
"""

from __future__ import annotations

import ast
import asyncio
import os
import pickle
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------- helpers


def _call(mcp: Any, name: str, args: dict[str, Any]) -> Any:
    loop = asyncio.new_event_loop()
    try:
        out = loop.run_until_complete(mcp.call_tool(name, args))
    finally:
        loop.close()
    if isinstance(out, tuple) and len(out) == 2:
        return out[1]
    return out


_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------- manage_file paths


def test_path_separator_normalization_in_manage_file(
    mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("tools.files")
    monkeypatch.chdir(tmp_path)

    write = _call(
        mcp_server,
        "manage_file",
        {"op": "write", "path": "subdir/file.txt", "content": "hi"},
    )
    assert write.get("ok") is True, write

    expected = tmp_path / "subdir" / "file.txt"
    assert expected.is_file(), f"file did not land at {expected}"
    assert expected.read_text(encoding="utf-8") == "hi"

    listing = _call(mcp_server, "manage_file", {"op": "list", "path": "subdir"})
    assert listing.get("ok") is True

    def _walk(node: dict[str, Any]) -> list[str]:
        if node.get("type") == "file":
            return [node["name"]]
        names: list[str] = []
        for child in node.get("children") or []:
            names.extend(_walk(child))
        return names

    names = _walk(listing.get("result") or {})
    assert "file.txt" in names


# ---------------------------------------------------------- unicode


def test_unicode_filename_roundtrip(
    mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("tools.files")
    monkeypatch.chdir(tmp_path)
    name = "café_テスト_文档.txt"
    content = "héllo 你好 こんにちは"

    write = _call(
        mcp_server,
        "manage_file",
        {"op": "write", "path": name, "content": content},
    )
    assert write.get("ok") is True, write

    read = _call(mcp_server, "manage_file", {"op": "read", "path": name})
    assert read.get("ok") is True
    assert read.get("result") == content


# -------------------------------------------------- CRLF preservation


def test_crlf_lf_preservation_on_read(
    mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("tools.files")
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "crlf.txt"
    raw = b"alpha\r\nbeta\r\ngamma\r\n"
    target.write_bytes(raw)

    read = _call(mcp_server, "manage_file", {"op": "read", "path": "crlf.txt"})
    assert read.get("ok") is True
    text = read.get("result")
    assert "\r\n" in text, "CRLF was silently translated by the read path"
    assert text.count("\r\n") == 3


# ------------------------------------------- snippet compile flag paths


@pytest.mark.skipif(
    platform.system() != "Windows", reason="MSVC layout is Windows-only"
)
def test_quick_compile_msvc_path_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    from sandbox import quick

    captured: dict[str, Any] = {}

    def fake_which(name: str) -> str | None:
        if name in {"cl", "cl.exe"}:
            return "C:/fake/cl.exe"
        return None

    monkeypatch.setattr(quick.shutil, "which", fake_which)

    class FakeProc:
        def __init__(self, *_a: Any, **_kw: Any) -> None:
            self.returncode = 1  # force fail so we don't try to run
            self.stdout = ""
            self.stderr = "compile failed"

    def fake_run(argv: list[str], **kwargs: Any) -> FakeProc:
        captured["argv"] = argv
        return FakeProc()

    monkeypatch.setattr(quick.subprocess, "run", fake_run)
    monkeypatch.setattr(quick.platform, "system", lambda: "Windows")

    quick.compile_and_run("int main(){return 0;}", compiler="clang", std="20", timeout=5)
    argv = captured.get("argv")
    assert argv is not None
    joined = " ".join(argv)
    assert "/std:c++20" in joined
    assert any(a.startswith("/Fe:") for a in argv)
    assert any(a.startswith("/Fo:") for a in argv)


@pytest.mark.skipif(
    platform.system() == "Windows", reason="POSIX clang layout"
)
def test_quick_compile_clang_path_on_unix(monkeypatch: pytest.MonkeyPatch) -> None:
    from sandbox import quick

    captured: dict[str, Any] = {}

    def fake_which(name: str) -> str | None:
        if name in {"clang++", "clang"}:
            return "/usr/bin/clang++"
        return None

    monkeypatch.setattr(quick.shutil, "which", fake_which)

    class FakeProc:
        def __init__(self, *_a: Any, **_kw: Any) -> None:
            self.returncode = 1
            self.stdout = ""
            self.stderr = "compile failed"

    def fake_run(argv: list[str], **kwargs: Any) -> FakeProc:
        captured["argv"] = argv
        return FakeProc()

    monkeypatch.setattr(quick.subprocess, "run", fake_run)

    quick.compile_and_run("int main(){return 0;}", compiler="clang", std="20", timeout=5)
    argv = captured.get("argv")
    assert argv is not None
    assert "-std=c++20" in argv
    assert "-o" in argv


# ------------------------------------------ generate_package line endings


def test_generate_package_respects_platform_line_endings(
    mcp_server: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("tools.generate")
    monkeypatch.chdir(tmp_path)
    out_dir = tmp_path / "lf_pkg"
    result = _call(
        mcp_server,
        "generate_package",
        {
            "name": "lf_pkg",
            "description": "LF check",
            "kind": "static",
            "cpp_std": "20",
            "test_framework": "none",
            "package_managers": ["vcpkg"],
            "dependencies": [],
            "output_dir": str(out_dir),
            "ci": False,
        },
    )
    assert result.get("ok") is True

    for created in result.get("files_created") or []:
        p = Path(created)
        if p.suffix in {".png", ".ico"}:
            continue
        data = p.read_bytes()
        assert b"\r\n" not in data, f"unexpected CRLF in generated file: {p}"


# ----------------------------------- doc_index pickle protocol


def test_doc_index_pickle_loads_across_platforms(tmp_path: Path) -> None:
    assert pickle.DEFAULT_PROTOCOL >= 4, (
        "pickle.DEFAULT_PROTOCOL must be >= 4 for cross-platform compat"
    )
    sample = {"alpha": [1, 2, 3], "beta": "héllo"}
    blob = tmp_path / "sample.pkl"
    with blob.open("wb") as fh:
        pickle.dump(sample, fh, protocol=4)
    with blob.open("rb") as fh:
        loaded = pickle.load(fh)
    assert loaded == sample


# ------------------- static checks across nexcpp source tree

_SUBPROCESS_DIRS = ("tools", "sandbox", "github", "plugins")


def _iter_project_python_files(subdirs: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for sub in subdirs:
        root = _ROOT / sub
        if not root.is_dir():
            continue
        for p in root.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            out.append(p)
    # Add conftest.py individually since tests/ is otherwise excluded.
    conf = _ROOT / "tests" / "conftest.py"
    if conf.is_file():
        out.append(conf)
    return out


def _collect_subprocess_calls(path: Path) -> list[ast.Call]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    calls: list[ast.Call] = []
    target_funcs = {"run", "Popen", "check_output", "check_call", "call"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in target_funcs:
            inner = func.value
            if isinstance(inner, ast.Name) and inner.id == "subprocess":
                calls.append(node)
            elif isinstance(inner, ast.Attribute) and inner.attr == "subprocess":
                calls.append(node)
    return calls


def test_subprocess_calls_use_utf8_explicitly() -> None:
    offenders: list[str] = []
    for path in _iter_project_python_files(_SUBPROCESS_DIRS):
        for call in _collect_subprocess_calls(path):
            kwargs = {kw.arg: kw.value for kw in call.keywords if kw.arg}
            text_kw = kwargs.get("text")
            uses_text = isinstance(text_kw, ast.Constant) and text_kw.value is True
            if not uses_text:
                continue
            enc_kw = kwargs.get("encoding")
            if not isinstance(enc_kw, ast.Constant) or enc_kw.value != "utf-8":
                offenders.append(
                    f"{path}:{call.lineno} subprocess call uses text=True without encoding='utf-8'"
                )
    assert not offenders, "\n".join(offenders)


def test_temp_dir_creation_uses_pathlib_not_strings() -> None:
    offenders: list[str] = []
    for path in _iter_project_python_files(_SUBPROCESS_DIRS):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            if node.attr != "join":
                continue
            inner = node.value
            if isinstance(inner, ast.Attribute) and inner.attr == "path":
                outer = inner.value
                if isinstance(outer, ast.Name) and outer.id == "os":
                    offenders.append(f"{path}:{node.lineno} uses os.path.join")
    assert not offenders, "\n".join(offenders)


# --------------------------------- server SIGINT integration


@pytest.mark.integration
def test_server_responds_to_sigint_gracefully() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    is_windows = platform.system() == "Windows"
    popen_kwargs: dict[str, Any] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "utf-8",
        "bufsize": 1,
        "env": env,
        "cwd": str(_ROOT),
    }
    if is_windows:
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    proc = subprocess.Popen(
        [sys.executable, "server.py", "--transport", "stdio", "--log-level", "INFO"],
        **popen_kwargs,
    )

    try:
        # Wait for the server to register tools and reach the run() loop.
        time.sleep(4.0)
        if is_windows:
            os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
        else:
            os.kill(proc.pid, signal.SIGINT)
        try:
            _, stderr = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate(timeout=5)
            pytest.fail("server did not exit within 10s of SIGINT")
        assert proc.returncode == 0, f"exit={proc.returncode} stderr={stderr!r}"
        assert "shutting down" in (stderr or "").lower(), f"stderr={stderr!r}"
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


@pytest.mark.integration
def test_server_handles_stdin_closed_gracefully() -> None:
    pytest.importorskip("mcp.server.fastmcp")

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")

    proc = subprocess.Popen(
        [sys.executable, "server.py", "--transport", "stdio", "--log-level", "INFO"],
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
        time.sleep(0.5)
        assert proc.stdin is not None
        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
            pytest.fail("server did not exit within 10s of stdin close")
        assert proc.returncode == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
