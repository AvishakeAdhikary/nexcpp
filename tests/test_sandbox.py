"""Tests for the sandbox helpers (quick / docker / pipeline)."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest


def test_quick_compile_and_run_mocked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("sandbox.quick")
    from sandbox import quick

    # Pretend clang++ exists.
    monkeypatch.setattr(quick, "_which", lambda *cands: "/usr/bin/clang++")
    # platform.system() on Windows shells out to `cmd /c ver`, which would
    # consume one of our mocked subprocess.run calls; pin it explicitly.
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    class FakeProc:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    calls = {"n": 0}

    def fake_run(argv: list[str], **kwargs: Any) -> FakeProc:
        calls["n"] += 1
        if calls["n"] == 1:
            # Compile step — pretend it succeeded.
            # Write the "binary" to wherever -o pointed so the file exists.
            for i, arg in enumerate(argv):
                if arg == "-o" and i + 1 < len(argv):
                    Path(argv[i + 1]).write_text("fake", encoding="utf-8")
                    if hasattr(Path(argv[i + 1]), "chmod"):
                        try:
                            Path(argv[i + 1]).chmod(0o755)
                        except OSError:
                            pass
            return FakeProc(0)
        # Run step — return stdout.
        return FakeProc(0, stdout="hi\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = quick.compile_and_run("int main(){return 0;}", compiler="clang", std="20", timeout=5)
    assert result["ok"] is True
    assert "hi" in result["stdout"]


def test_quick_compile_no_compiler(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("sandbox.quick")
    from sandbox import quick

    monkeypatch.setattr(quick, "_which", lambda *cands: None)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    result = quick.compile_and_run("int main(){}", compiler="clang", std="20")
    assert result["ok"] is False
    assert "compiler" in (result.get("error") or "").lower()


def test_pipeline_detect_build_system(tmp_path: Path) -> None:
    pytest.importorskip("sandbox.pipeline")
    from sandbox.pipeline import detect_build_system

    assert detect_build_system(tmp_path) is None
    (tmp_path / "CMakeLists.txt").write_text("project(t)\n", encoding="utf-8")
    assert detect_build_system(tmp_path) == "cmake"


def test_pipeline_run_local_build_no_build_system(tmp_path: Path) -> None:
    pytest.importorskip("sandbox.pipeline")
    from sandbox.pipeline import run_local_build

    result = run_local_build(tmp_path)
    assert result["ok"] is False
    assert "no supported build system" in (result.get("error") or "").lower()


@pytest.mark.docker
def test_docker_run_snippet_with_mock(mock_docker: MagicMock) -> None:
    pytest.importorskip("sandbox.docker_sandbox")
    from sandbox import docker_sandbox

    result = docker_sandbox.run_snippet(
        "int main(){return 0;}",
        compiler="clang",
        std="20",
        timeout=5,
    )
    assert "ok" in result
    assert "stdout" in result
    assert "stderr" in result
