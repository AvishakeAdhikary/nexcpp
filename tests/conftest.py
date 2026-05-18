"""Shared test fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# Ensure the project root is on sys.path for the tests to import bare modules.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: integration tests that touch the filesystem or spawn processes",
    )
    config.addinivalue_line(
        "markers",
        "docker: tests that require a running docker daemon",
    )


# ---------------------------------------------------------- mcp_server fixture


@pytest.fixture()
def mcp_server() -> Any:
    """A fresh FastMCP instance with every available register() applied.

    Modules that aren't ready yet (other streams still authoring) are
    silently skipped so collection doesn't blow up.
    """
    pytest.importorskip("mcp.server.fastmcp")
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("nexcpp-test")
    targets = [
        "tools.docs",
        "tools.files",
        "tools.build",
        "tools.analyze",
        "tools.generate",
        "tools.github",
        "resources.cpp_docs",
        "resources.project",
        "resources.build_log",
        "prompts.scaffold",
        "prompts.cmake",
        "prompts.vcpkg",
        "prompts.bridge",
    ]
    for target in targets:
        try:
            module = __import__(target, fromlist=["register"])
        except ImportError:
            continue
        register = getattr(module, "register", None)
        if register is None:
            continue
        try:
            register(mcp)
        except Exception:
            # Skip broken modules rather than fail collection.
            continue
    return mcp


# -------------------------------------------------------- tmp_project fixture


@pytest.fixture()
def tmp_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal CMake project with one .cpp file and a CMakeLists.txt."""
    (tmp_path / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.20)\n"
        "project(tinyproj VERSION 0.1.0 LANGUAGES CXX)\n"
        "add_executable(tinyproj src/main.cpp)\n"
        "target_compile_features(tinyproj PRIVATE cxx_std_20)\n",
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "main.cpp").write_text(
        "#include <iostream>\nint main() { std::cout << \"hi\\n\"; return 0; }\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------- mock_clang_tidy


@pytest.fixture()
def mock_clang_tidy(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Patch subprocess.run so clang-tidy returns canned output."""

    canned = {
        "stdout": (
            "/proj/src/foo.cpp:10:5: warning: use 'auto' [modernize-use-auto]\n"
            "/proj/src/foo.cpp:20:7: warning: unused variable 'x' [misc-unused-parameters]\n"
        ),
        "stderr": "",
        "returncode": 0,
    }

    def fake_which(name: str) -> str | None:
        if name in {"clang-tidy", "cppcheck"}:
            return f"/usr/bin/{name}"
        # everything else: fall through to default behavior
        import shutil

        return shutil.which.__wrapped__(name) if hasattr(shutil.which, "__wrapped__") else None

    import shutil as _shutil_mod

    monkeypatch.setattr(_shutil_mod, "which", lambda name: f"/usr/bin/{name}" if name in {"clang-tidy", "cppcheck"} else None)

    class FakeProc:
        def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    import subprocess as _subprocess_mod

    def fake_run(*args: Any, **kwargs: Any) -> FakeProc:
        return FakeProc(canned["stdout"], canned["stderr"], canned["returncode"])

    monkeypatch.setattr(_subprocess_mod, "run", fake_run)
    return canned


# ----------------------------------------------------------- mock_docker


@pytest.fixture()
def mock_docker(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace docker.from_env() with a Mock returning canned results."""

    fake_client = MagicMock(name="docker.client")
    fake_client.ping.return_value = True

    image_obj = MagicMock(name="image")
    fake_client.images.get.return_value = image_obj

    container = MagicMock(name="container")
    container.wait.return_value = {"StatusCode": 0}
    container.logs.side_effect = lambda **kw: (
        b"hello\n" if kw.get("stdout") else b""
    )
    container.attach_socket.return_value = MagicMock()
    fake_client.containers.create.return_value = container

    try:
        import docker as _docker_mod  # type: ignore[import-not-found]
    except ImportError:
        _docker_mod = MagicMock(name="docker")
        sys.modules["docker"] = _docker_mod
    monkeypatch.setattr(_docker_mod, "from_env", lambda: fake_client)
    return fake_client


# ------------------------------------------------- isolate home for plugins


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point HOME and the cwd-relative .nexcpp dir at a tmp_path subtree.

    Each test using this fixture starts with an empty plugin scope so the
    plugin loader sees only what the test adds.
    """
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))  # Windows
    # Best-effort: also patch Path.home in case the env var doesn't take.
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    workdir = tmp_path / "work"
    workdir.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(workdir)
    return tmp_path
