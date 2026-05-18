"""In-process C++ compile + run helper.

Used by ``run_snippet`` when ``sandbox=False``. Picks the best available
compiler (clang++, g++, or MSVC's ``cl.exe`` on Windows), compiles a
single source file, runs it with a stdin and timeout, and returns a
structured result.
"""

from __future__ import annotations

import logging
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# Regex covers GCC / Clang ("file:line:col: severity: message") and MSVC
# ("file(line): severity Cxxxx: message"). Tolerates Windows drive letters.
_GCC_CLANG_RE = re.compile(
    r"^(?P<file>[^\s:][^:\n]*?):(?P<line>\d+)(?::(?P<col>\d+))?: "
    r"(?P<severity>error|fatal error|warning|note): (?P<message>.+)$"
)
_MSVC_RE = re.compile(
    r"^(?P<file>[^\s(][^(\n]*)\((?P<line>\d+)(?:,(?P<col>\d+))?\): "
    r"(?P<severity>fatal error|error|warning|note) (?P<code>[A-Z]\d+): (?P<message>.+)$"
)


_SUGGESTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"undefined reference to"), "missing source file or library link"),
    (re.compile(r"unresolved external symbol"), "missing library or .lib link"),
    (re.compile(r"was not declared in this scope"), "missing #include or typo"),
    (re.compile(r"no such file or directory"), "missing header — install dep or fix include path"),
    (re.compile(r"expected ';'"), "syntax error: missing semicolon"),
    (re.compile(r"redefinition of"), "duplicate symbol — check headers/include guards"),
    (re.compile(r"use of undeclared identifier"), "missing #include or typo"),
    (re.compile(r"template argument deduction"), "template arg mismatch — specify explicitly"),
    (re.compile(r"cannot convert"), "type mismatch — add explicit cast or fix types"),
)


def _suggest(message: str) -> str | None:
    for pattern, hint in _SUGGESTIONS:
        if pattern.search(message):
            return hint
    return None


def parse_compile_errors(text: str) -> list[dict[str, Any]]:
    """Parse compiler output into a list of structured diagnostics."""
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = _GCC_CLANG_RE.match(line)
        if m:
            out.append(
                {
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "column": int(m.group("col")) if m.group("col") else None,
                    "severity": m.group("severity"),
                    "message": m.group("message").strip(),
                    "suggestion": _suggest(m.group("message")),
                }
            )
            continue
        m = _MSVC_RE.match(line)
        if m:
            out.append(
                {
                    "file": m.group("file"),
                    "line": int(m.group("line")),
                    "column": int(m.group("col")) if m.group("col") else None,
                    "severity": m.group("severity"),
                    "code": m.group("code"),
                    "message": m.group("message").strip(),
                    "suggestion": _suggest(m.group("message")),
                }
            )
    return out


def _which(*candidates: str) -> str | None:
    for cand in candidates:
        found = shutil.which(cand)
        if found:
            return found
    return None


def _resolve_compiler(compiler: str) -> tuple[str, str] | None:
    """Resolve a compiler name to (kind, path). Falls back across families.

    Returns one of:
      * ("clang", path-to-clang++)
      * ("gcc", path-to-g++)
      * ("msvc", path-to-cl.exe)
    """
    if compiler == "clang":
        path = _which("clang++", "clang")
        if path:
            return ("clang", path)
    if compiler == "gcc":
        path = _which("g++", "gcc")
        if path:
            return ("gcc", path)
    # Try the other one as fallback.
    path = _which("clang++", "g++", "clang", "gcc")
    if path:
        kind = "clang" if "clang" in Path(path).stem else "gcc"
        return (kind, path)
    # MSVC last resort on Windows.
    if platform.system() == "Windows":
        cl = _which("cl", "cl.exe")
        if cl:
            return ("msvc", cl)
    return None


def compile_and_run(
    code: str,
    *,
    compiler: str = "clang",
    std: str = "20",
    flags: list[str] | None = None,
    stdin: str = "",
    timeout: int = 10,
) -> dict[str, Any]:
    """Compile and run a single C++ source snippet.

    Returns a dict with keys: ok, stdout, stderr, exit_code,
    compile_errors, elapsed_ms.
    """
    extra_flags = list(flags or [])
    started = time.perf_counter()

    resolved = _resolve_compiler(compiler)
    if resolved is None:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "compile_errors": [],
            "elapsed_ms": 0,
            "error": (
                "No C++ compiler found. Install clang/gcc (or MSVC on Windows) "
                "or use sandbox=True with Docker."
            ),
        }
    kind, cc_path = resolved

    with tempfile.TemporaryDirectory(prefix="nexcpp-snippet-") as tmpdir:
        src = Path(tmpdir) / "main.cpp"
        src.write_text(code, encoding="utf-8")
        exe_suffix = ".exe" if platform.system() == "Windows" else ""
        exe = Path(tmpdir) / f"a.out{exe_suffix}"

        if kind == "msvc":
            # cl.exe wants /Fe: with no space and /Fo: for the obj dir.
            argv = [
                cc_path,
                "/nologo",
                "/EHsc",
                f"/std:c++{std}",
                "/W3",
                str(src),
                f"/Fe:{exe}",
                f"/Fo:{tmpdir}\\",
                *extra_flags,
            ]
        else:
            argv = [
                cc_path,
                f"-std=c++{std}",
                "-Wall",
                "-O0",
                "-g",
                str(src),
                "-o",
                str(exe),
                *extra_flags,
            ]

        try:
            compile_proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"compiler timed out after {timeout}s",
                "exit_code": None,
                "compile_errors": [],
                "elapsed_ms": elapsed_ms,
            }
        except OSError as exc:
            return {
                "ok": False,
                "stdout": "",
                "stderr": "",
                "exit_code": None,
                "compile_errors": [],
                "elapsed_ms": 0,
                "error": f"failed to invoke compiler: {exc}",
            }

        compile_output = (compile_proc.stdout or "") + (compile_proc.stderr or "")
        if compile_proc.returncode != 0:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": False,
                "stdout": "",
                "stderr": compile_output,
                "exit_code": None,
                "compile_errors": parse_compile_errors(compile_output),
                "elapsed_ms": elapsed_ms,
            }

        if not exe.exists():
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": False,
                "stdout": "",
                "stderr": "compiler reported success but no binary was produced",
                "exit_code": None,
                "compile_errors": parse_compile_errors(compile_output),
                "elapsed_ms": elapsed_ms,
            }

        try:
            run_proc = subprocess.run(
                [str(exe)],
                input=stdin,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                cwd=tmpdir,
            )
        except subprocess.TimeoutExpired as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return {
                "ok": False,
                "stdout": exc.stdout or "",
                "stderr": (exc.stderr or "") + f"\nprocess timed out after {timeout}s",
                "exit_code": None,
                "compile_errors": [],
                "elapsed_ms": elapsed_ms,
            }
        except OSError as exc:
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"failed to execute binary: {exc}",
                "exit_code": None,
                "compile_errors": [],
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            "ok": run_proc.returncode == 0,
            "stdout": run_proc.stdout or "",
            "stderr": run_proc.stderr or "",
            "exit_code": run_proc.returncode,
            "compile_errors": [],
            "elapsed_ms": elapsed_ms,
        }
