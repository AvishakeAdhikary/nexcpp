"""Built-in plugin: quick clang-tidy linting via ``cpp_quick_lint``.

Wraps clang-tidy with a curated check list focused on bug-prone code,
modernization opportunities, performance, and readability — so an agent
can sanity-check a file in one call without picking checks itself.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from sdk import PluginContext

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "cpp-analyzer",
    "version": "1.0.0",
    "description": "Quick clang-tidy lint with a curated check list.",
    "author": "nexcpp",
}

_CHECKS = "bugprone-*,modernize-*,performance-*,readability-*"

_TIDY_LINE_RE = re.compile(
    r"^(?P<file>[^\s:][^:\n]*?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<severity>warning|error|note):\s+(?P<message>.+?)"
    r"(?:\s+\[(?P<check>[\w\-\.,]+)\])?$"
)


def _parse(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = _TIDY_LINE_RE.match(line)
        if not m:
            continue
        out.append(
            {
                "file": m.group("file"),
                "line": int(m.group("line")),
                "column": int(m.group("col")),
                "severity": m.group("severity"),
                "check": m.group("check"),
                "message": m.group("message").strip(),
            }
        )
    return out


def _resolve_target(file: str) -> Path | None:
    path = Path(file).expanduser()
    path = (Path.cwd() / path).resolve() if not path.is_absolute() else path.resolve()
    return path if path.is_file() else None


def register(ctx: PluginContext) -> None:
    @ctx.tool(
        description=(
            "Run clang-tidy on a single file with a curated check list "
            "(bugprone-*, modernize-*, performance-*, readability-*). "
            "Returns concise diagnostics."
        )
    )
    def cpp_quick_lint(file: str) -> dict[str, Any]:
        tidy = shutil.which("clang-tidy")
        if not tidy:
            return {
                "ok": False,
                "diagnostics": [],
                "error": "clang-tidy not found in PATH",
            }
        target = _resolve_target(file)
        if target is None:
            return {
                "ok": False,
                "diagnostics": [],
                "error": f"file not found: {file}",
            }
        project_dir = target.parent
        argv = [
            tidy,
            f"-checks={_CHECKS}",
            str(target),
            "--",
            "-std=c++20",
            "-Wall",
        ]
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
                cwd=str(project_dir),
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "diagnostics": [],
                "error": "clang-tidy timed out after 120s",
            }
        except OSError as exc:
            return {
                "ok": False,
                "diagnostics": [],
                "error": f"failed to invoke clang-tidy: {exc}",
            }
        diags = _parse((proc.stdout or "") + "\n" + (proc.stderr or ""))
        summary_by_check: dict[str, int] = {}
        for d in diags:
            key = d.get("check") or "uncategorized"
            summary_by_check[key] = summary_by_check.get(key, 0) + 1
        return {
            "ok": True,
            "file": str(target),
            "diagnostics": diags,
            "summary": {"total": len(diags), "by_check": summary_by_check},
        }
