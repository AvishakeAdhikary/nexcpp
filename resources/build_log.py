"""Resources serving build / sandbox / analysis logs.

URI patterns:

* ``nexcpp://build/log/latest``        — most recent build log
* ``nexcpp://build/log/{id}``          — build log by UUID
* ``nexcpp://sandbox/log/{id}``        — snippet/sandbox log by UUID
* ``nexcpp://analysis/report/latest``  — most recent analysis JSON
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_LOG_DIR = Path.home() / ".nexcpp" / "logs"


def _log_dir() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


def _most_recent(prefix: str, suffix: str = ".log") -> Path | None:
    d = _log_dir()
    candidates = sorted(
        d.glob(f"{prefix}-*{suffix}"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _read_or_message(path: Path | None, kind: str) -> str:
    if path is None or not path.is_file():
        return f"# {kind}\n\n*No {kind} found in {_log_dir()}.*\n"
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"# {kind}\n\n*Failed to read {path}: {exc}*\n"


def register(mcp: Any) -> None:
    @mcp.resource("nexcpp://build/log/latest")
    def build_log_latest() -> str:
        """Most recent local build log."""
        return _read_or_message(_most_recent("build"), "build log")

    @mcp.resource("nexcpp://build/log/{id}")
    def build_log_by_id(id: str) -> str:
        """Specific build log by UUID."""
        path = _log_dir() / f"build-{id}.log"
        return _read_or_message(path, f"build log {id}")

    @mcp.resource("nexcpp://sandbox/log/{id}")
    def sandbox_log_by_id(id: str) -> str:
        """Specific sandbox/snippet log by UUID."""
        path = _log_dir() / f"sandbox-{id}.log"
        return _read_or_message(path, f"sandbox log {id}")

    @mcp.resource("nexcpp://analysis/report/latest")
    def analysis_report_latest() -> str:
        """Most recent analyze_code JSON report."""
        path = _most_recent("analysis", ".json")
        return _read_or_message(path, "analysis report")
