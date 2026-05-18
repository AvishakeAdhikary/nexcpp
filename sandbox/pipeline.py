"""Local build pipeline: configure -> build -> test for CMake / Meson / Bazel."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_LOG_DIR = Path.home() / ".nexcpp" / "logs"


def _log_dir() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


def _new_log_path(prefix: str = "build") -> tuple[str, Path]:
    log_id = uuid.uuid4().hex
    return log_id, _log_dir() / f"{prefix}-{log_id}.log"


def detect_build_system(project_dir: Path) -> str | None:
    if (project_dir / "CMakeLists.txt").is_file():
        return "cmake"
    if (project_dir / "meson.build").is_file():
        return "meson"
    if (project_dir / "BUILD.bazel").is_file() or (project_dir / "WORKSPACE").is_file():
        return "bazel"
    return None


def _stream_run(
    argv: list[str],
    cwd: Path,
    log_fh: Any,  # noqa: ANN401
    timeout: int | None = None,
) -> tuple[int, str]:
    """Run ``argv`` and capture combined stdout+stderr to log_fh and memory."""
    log_fh.write(f"\n$ {' '.join(argv)}\n")
    log_fh.flush()
    buf: list[str] = []
    try:
        proc = subprocess.Popen(  # noqa: S603
            argv,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except FileNotFoundError as exc:
        msg = f"command not found: {argv[0]} ({exc})"
        log_fh.write(msg + "\n")
        return 127, msg
    except OSError as exc:
        msg = f"failed to invoke {argv[0]}: {exc}"
        log_fh.write(msg + "\n")
        return 1, msg

    deadline = time.time() + timeout if timeout else None
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            log_fh.write(line)
            log_fh.flush()
            buf.append(line)
            if deadline and time.time() > deadline:
                proc.kill()
                buf.append(f"\n[timeout after {timeout}s]\n")
                log_fh.write(f"\n[timeout after {timeout}s]\n")
                break
    finally:
        proc.wait()
    return proc.returncode, "".join(buf)


def _discover_artifacts(project_dir: Path) -> list[str]:
    out: list[str] = []
    suffixes = {".exe", ".dll", ".so", ".dylib", ".a", ".lib"}
    for sub in ("build", "bin", project_dir / "build" / "bin"):
        root = sub if isinstance(sub, Path) else project_dir / sub
        if not root.is_dir():
            continue
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() in suffixes:
                out.append(str(p))
                continue
            # Unix executable bit
            try:
                mode = p.stat().st_mode
            except OSError:
                continue
            if os.name != "nt" and mode & 0o111 and not p.name.startswith("CMake"):
                # Skip object/text files
                if p.suffix in {".o", ".cmake", ".txt", ".json", ".log"}:
                    continue
                out.append(str(p))
    # Dedupe, keep insertion order
    seen: set[str] = set()
    deduped: list[str] = []
    for item in out:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _run_clang_tidy(project_dir: Path, log_fh: Any) -> str:  # noqa: ANN401
    tidy = shutil.which("clang-tidy")
    if not tidy:
        log_fh.write("\n[clang-tidy not found in PATH; skipping static analysis]\n")
        return ""
    sources: list[str] = []
    for ext in ("*.cpp", "*.cxx", "*.cc"):
        sources.extend(str(p) for p in project_dir.rglob(ext) if "build" not in p.parts)
    if not sources:
        return ""
    argv = [tidy, "-p", str(project_dir / "build"), *sources[:50]]
    _rc, output = _stream_run(argv, project_dir, log_fh, timeout=300)
    return output


def run_local_build(
    project_dir: Path,
    *,
    build_type: str = "Debug",
    target: str | None = None,
    run_tests: bool = True,
    sanitizers: list[str] | None = None,
    static_analysis: bool = False,
    build_system: str | None = None,
) -> dict[str, Any]:
    """Run a local build pipeline against ``project_dir``.

    Returns a dict with keys: ok, build_system, configure_log, build_log,
    test_log, artifacts, errors (parsed compile errors), log_id.
    """
    project_dir = Path(project_dir).resolve()
    if not project_dir.is_dir():
        return {
            "ok": False,
            "build_system": None,
            "error": f"project_dir does not exist: {project_dir}",
            "configure_log": "",
            "build_log": "",
            "test_log": "",
            "artifacts": [],
            "errors": [],
            "log_id": None,
        }

    bs = build_system or detect_build_system(project_dir)
    if bs is None:
        return {
            "ok": False,
            "build_system": None,
            "error": "no supported build system found (CMakeLists.txt / meson.build / BUILD.bazel)",
            "configure_log": "",
            "build_log": "",
            "test_log": "",
            "artifacts": [],
            "errors": [],
            "log_id": None,
        }

    log_id, log_path = _new_log_path("build")
    configure_log = build_log = test_log = ""
    started = time.perf_counter()

    with log_path.open("w", encoding="utf-8") as log_fh:
        log_fh.write(f"# nexcpp build log {log_id}\n")
        log_fh.write(f"project_dir: {project_dir}\n")
        log_fh.write(f"build_system: {bs}\n")
        log_fh.write(f"build_type: {build_type}\n")
        if sanitizers:
            log_fh.write(f"sanitizers: {sanitizers}\n")

        rc_configure = 0
        rc_build = 0
        rc_test = 0

        if bs == "cmake":
            argv = ["cmake", "-S", ".", "-B", "build", f"-DCMAKE_BUILD_TYPE={build_type}"]
            if shutil.which("ninja"):
                argv.extend(["-G", "Ninja"])
            if sanitizers:
                argv.append(f"-DCMAKE_CXX_FLAGS=-fsanitize={','.join(sanitizers)}")
            rc_configure, configure_log = _stream_run(argv, project_dir, log_fh, timeout=600)

            if rc_configure == 0:
                build_argv = ["cmake", "--build", "build", "-j"]
                if target:
                    build_argv.extend(["--target", target])
                rc_build, build_log = _stream_run(build_argv, project_dir, log_fh, timeout=1800)

            if rc_build == 0 and run_tests:
                test_argv = ["ctest", "--test-dir", "build", "--output-on-failure"]
                rc_test, test_log = _stream_run(test_argv, project_dir, log_fh, timeout=900)

        elif bs == "meson":
            argv = ["meson", "setup", "build", f"--buildtype={build_type.lower()}"]
            rc_configure, configure_log = _stream_run(argv, project_dir, log_fh, timeout=600)
            if rc_configure == 0:
                rc_build, build_log = _stream_run(
                    ["meson", "compile", "-C", "build"], project_dir, log_fh, timeout=1800
                )
            if rc_build == 0 and run_tests:
                rc_test, test_log = _stream_run(
                    ["meson", "test", "-C", "build"], project_dir, log_fh, timeout=900
                )

        elif bs == "bazel":
            mode = {"Debug": "dbg", "Release": "opt", "RelWithDebInfo": "fastbuild"}.get(
                build_type, "dbg"
            )
            rc_build, build_log = _stream_run(
                ["bazel", "build", "//...", f"--compilation_mode={mode}"],
                project_dir,
                log_fh,
                timeout=1800,
            )
            if rc_build == 0 and run_tests:
                rc_test, test_log = _stream_run(
                    ["bazel", "test", "//..."], project_dir, log_fh, timeout=900
                )

        if static_analysis:
            tidy_out = _run_clang_tidy(project_dir, log_fh)
            build_log += "\n" + tidy_out

        log_fh.write(f"\n# elapsed: {time.perf_counter() - started:.1f}s\n")

    from sandbox.quick import parse_compile_errors

    errors = parse_compile_errors(configure_log + "\n" + build_log)
    ok = (rc_configure == 0) and (rc_build == 0) and (rc_test == 0)
    artifacts = _discover_artifacts(project_dir) if rc_build == 0 else []

    return {
        "ok": ok,
        "build_system": bs,
        "configure_log": configure_log,
        "build_log": build_log,
        "test_log": test_log,
        "artifacts": artifacts,
        "errors": errors,
        "log_id": log_id,
    }
