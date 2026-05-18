"""``build_project`` and ``run_snippet`` MCP tools."""

from __future__ import annotations

import logging
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from config import get_config

log = logging.getLogger(__name__)

BuildType = Literal["Debug", "Release", "RelWithDebInfo"]
Sanitizer = Literal["asan", "ubsan", "tsan", "msan"]
SnippetCompiler = Literal["gcc", "clang"]
CppStd = Literal["17", "20", "23"]


_LOG_DIR = Path.home() / ".nexcpp" / "logs"


def _log_dir() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


def _persist_snippet_log(log_id: str, result: dict[str, Any]) -> None:
    """Persist a snippet run so it can be retrieved via the sandbox log resource."""
    path = _log_dir() / f"sandbox-{log_id}.log"
    try:
        with path.open("w", encoding="utf-8") as fh:
            fh.write(f"# nexcpp snippet log {log_id}\n")
            fh.write(f"exit_code: {result.get('exit_code')}\n")
            fh.write(f"elapsed_ms: {result.get('elapsed_ms')}\n\n")
            fh.write("## stdout\n")
            fh.write(result.get("stdout", "") or "")
            fh.write("\n\n## stderr\n")
            fh.write(result.get("stderr", "") or "")
    except OSError as exc:
        log.warning("failed to write snippet log %s: %s", path, exc)


def _run_static_analysis_merge(project_dir: Path) -> list[dict[str, Any]]:
    """Run clang-tidy across project sources and parse diagnostics."""
    tidy = shutil.which("clang-tidy")
    if not tidy:
        return []
    sources: list[str] = []
    for ext in ("*.cpp", "*.cxx", "*.cc"):
        for p in project_dir.rglob(ext):
            if "build" in p.parts:
                continue
            sources.append(str(p))
    if not sources:
        return []
    cmd = [tidy, "-p", str(project_dir / "build"), *sources[:50]]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300,
            cwd=str(project_dir),
        )
    except (subprocess.TimeoutExpired, OSError):
        return []

    from sandbox.quick import parse_compile_errors

    return parse_compile_errors(proc.stdout + "\n" + proc.stderr)


def register(mcp: Any) -> None:  # noqa: ANN401
    @mcp.tool()
    def build_project(
        project_dir: str = Field(".", description="Path to project root."),
        build_type: BuildType = Field(
            "Debug", description="CMake/Meson build configuration."
        ),
        target: str | None = Field(None, description="Single target to build."),
        run_tests: bool = Field(True, description="Run tests after build."),
        sandbox: bool = Field(
            False, description="Run build inside a docker container for isolation."
        ),
        sanitizers: list[Sanitizer] = Field(
            default_factory=list,
            description="Enable sanitizers: asan/ubsan/tsan/msan.",
        ),
        static_analysis: bool = Field(
            False, description="Run clang-tidy after build and merge diagnostics."
        ),
    ) -> dict[str, Any]:
        """Configure, build, and (optionally) test a C++ project.

        Auto-detects CMake / Meson / Bazel. Returns structured logs,
        parsed compile errors, discovered artifacts, and a ``log_id``
        usable with ``nexcpp://build/log/{id}``.
        """
        cfg = get_config()
        effective_sandbox = sandbox or cfg.sandbox_default
        proj = Path(project_dir).expanduser()
        if not proj.is_absolute():
            proj = (Path.cwd() / proj).resolve()
        else:
            proj = proj.resolve()

        if effective_sandbox:
            try:
                from sandbox.docker_sandbox import run_build
            except Exception as exc:  # pragma: no cover
                return {
                    "ok": False,
                    "build_system": None,
                    "configure_log": "",
                    "build_log": "",
                    "test_log": "",
                    "artifacts": [],
                    "errors": [],
                    "log_id": None,
                    "error": f"docker sandbox unavailable: {exc}",
                }
            result = run_build(
                proj,
                build_type=build_type,
                target=target,
                run_tests=run_tests,
                sanitizers=list(sanitizers) if sanitizers else None,
            )
            # Persist a log so the resource can serve it.
            log_id = uuid.uuid4().hex
            try:
                (_log_dir() / f"build-{log_id}.log").write_text(
                    (result.get("stdout") or "") + (result.get("stderr") or ""),
                    encoding="utf-8",
                )
            except OSError:
                pass
            return {
                "ok": result.get("ok", False),
                "build_system": "cmake",
                "configure_log": result.get("stdout", ""),
                "build_log": result.get("stdout", ""),
                "test_log": "",
                "artifacts": [],
                "errors": result.get("compile_errors", []) or [],
                "log_id": log_id,
                "error": result.get("error"),
            }

        from sandbox.pipeline import run_local_build

        result = run_local_build(
            proj,
            build_type=build_type,
            target=target,
            run_tests=run_tests,
            sanitizers=list(sanitizers) if sanitizers else None,
            static_analysis=static_analysis,
        )

        if static_analysis:
            extra = _run_static_analysis_merge(proj)
            if extra:
                result["errors"] = (result.get("errors") or []) + extra

        return result

    @mcp.tool()
    def run_snippet(
        code: str = Field(..., description="C++ source code to compile and run."),
        compiler: SnippetCompiler = Field(
            "clang", description="Preferred compiler (gcc or clang)."
        ),
        std: CppStd = Field("20", description="C++ standard."),
        flags: list[str] = Field(
            default_factory=list, description="Extra compiler flags."
        ),
        stdin: str = Field("", description="Standard input passed to the binary."),
        timeout: int = Field(10, ge=1, le=120, description="Total timeout (seconds)."),
        sandbox: bool = Field(False, description="Compile/run inside docker container."),
    ) -> dict[str, Any]:
        """Compile and run a self-contained C++ snippet.

        Without ``sandbox``, runs locally using an available compiler.
        With ``sandbox=True``, executes in the ``nexcpp/build-linux``
        image (no network, capped CPU/RAM).
        """
        cfg = get_config()
        effective_sandbox = sandbox or cfg.sandbox_default

        if effective_sandbox:
            from sandbox.docker_sandbox import run_snippet as docker_run

            result = docker_run(
                code,
                compiler=compiler,
                std=std,
                flags=list(flags),
                stdin=stdin,
                timeout=timeout,
            )
        else:
            from sandbox.quick import compile_and_run

            result = compile_and_run(
                code,
                compiler=compiler,
                std=std,
                flags=list(flags),
                stdin=stdin,
                timeout=timeout,
            )

        log_id = uuid.uuid4().hex
        _persist_snippet_log(log_id, result)
        result["log_id"] = log_id
        return result
