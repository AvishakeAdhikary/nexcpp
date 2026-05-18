"""``analyze_code`` MCP tool — clang-tidy / cppcheck wrapper."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Literal
from xml.etree import ElementTree as ET

from pydantic import Field

log = logging.getLogger(__name__)

Tool = Literal["clang-tidy", "cppcheck", "all"]


_LOG_DIR = Path.home() / ".nexcpp" / "logs"
_SRC_EXTENSIONS = {".cpp", ".cxx", ".cc", ".c", ".h", ".hpp", ".hxx"}


def _log_dir() -> Path:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    return _LOG_DIR


def _load_gitignore(root: Path) -> list[re.Pattern[str]]:
    f = root / ".gitignore"
    if not f.is_file():
        return []
    out: list[re.Pattern[str]] = []
    for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rx = re.escape(line).replace(r"\*", ".*").replace(r"\?", ".")
        out.append(re.compile(rx))
    return out


def _discover_sources(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if not target.is_dir():
        return []
    patterns = _load_gitignore(target)
    sources: list[Path] = []
    for p in target.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in _SRC_EXTENSIONS:
            continue
        rel = str(p.relative_to(target))
        if any("build" in part or part.startswith(".") for part in p.parts):
            continue
        if any(pat.search(rel) for pat in patterns):
            continue
        sources.append(p)
    return sources


def _clang_tidy_diag_from_yaml(yaml_path: Path) -> list[dict[str, Any]]:
    """Parse the export-fixes YAML to extract suggested fixes per diagnostic."""
    if not yaml_path.is_file():
        return []
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        return []
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for d in data.get("Diagnostics", []) or []:
        msg = d.get("DiagnosticMessage", {}) or {}
        fixes = msg.get("Replacements", []) or []
        out.append(
            {
                "file": msg.get("FilePath"),
                "line": None,
                "column": None,
                "severity": "warning",
                "check": d.get("DiagnosticName"),
                "message": msg.get("Message", ""),
                "suggested_fix": [
                    {
                        "file": r.get("FilePath"),
                        "offset": r.get("Offset"),
                        "length": r.get("Length"),
                        "replacement": r.get("ReplacementText"),
                    }
                    for r in fixes
                ]
                if fixes
                else None,
            }
        )
    return out


_TIDY_LINE_RE = re.compile(
    r"^(?P<file>[^\s:][^:\n]*?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<severity>warning|error|note):\s+(?P<message>.+?)(?:\s+\[(?P<check>[\w\-\.,]+)\])?$"
)


def _parse_clang_tidy_text(text: str) -> list[dict[str, Any]]:
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
                "suggested_fix": None,
            }
        )
    return out


def _parse_cppcheck_xml(xml_text: str) -> list[dict[str, Any]]:
    if not xml_text.strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out: list[dict[str, Any]] = []
    for err in root.iter("error"):
        loc = err.find("location")
        out.append(
            {
                "file": loc.get("file") if loc is not None else None,
                "line": int(loc.get("line", "0")) if loc is not None else None,
                "column": int(loc.get("column", "0")) if loc is not None else None,
                "severity": err.get("severity"),
                "check": err.get("id"),
                "message": err.get("msg") or err.get("verbose") or "",
                "suggested_fix": None,
            }
        )
    return out


def _run_clang_tidy(
    sources: list[Path],
    *,
    checks: str,
    fix: bool,
    project_dir: Path,
) -> tuple[bool, list[dict[str, Any]], str | None]:
    tidy = shutil.which("clang-tidy")
    if not tidy:
        return False, [], "clang-tidy not found in PATH"

    has_compile_db = (project_dir / "build" / "compile_commands.json").is_file()
    with tempfile.TemporaryDirectory(prefix="nexcpp-tidy-") as tmp:
        fixes_yaml = Path(tmp) / "fixes.yaml"
        argv: list[str] = [tidy, f"-checks={checks}", f"-export-fixes={fixes_yaml}"]
        if fix:
            argv.append("-fix")
        if has_compile_db:
            argv.extend(["-p", str(project_dir / "build")])
        argv.extend(str(s) for s in sources[:200])
        if not has_compile_db:
            argv.extend(["--", "-std=c++20", "-Wall"])

        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=600,
                cwd=str(project_dir),
            )
        except subprocess.TimeoutExpired:
            return False, [], "clang-tidy timed out after 600s"
        except OSError as exc:
            return False, [], f"failed to invoke clang-tidy: {exc}"

        text_diags = _parse_clang_tidy_text(proc.stdout + "\n" + proc.stderr)
        yaml_diags = _clang_tidy_diag_from_yaml(fixes_yaml)

        # Merge suggested fixes from YAML into matching text diagnostics.
        for td in text_diags:
            for yd in yaml_diags:
                if yd.get("check") == td.get("check") and yd.get("file") and td.get("file") and yd["file"].endswith(td["file"]):
                    td["suggested_fix"] = yd.get("suggested_fix")
                    break

        # If text parser missed everything (e.g. only YAML output), fall back.
        diags = text_diags if text_diags else yaml_diags
        return True, diags, None


def _run_cppcheck(
    sources: list[Path],
    *,
    project_dir: Path,
) -> tuple[bool, list[dict[str, Any]], str | None]:
    cppcheck = shutil.which("cppcheck")
    if not cppcheck:
        return False, [], "cppcheck not found in PATH"
    argv = [
        cppcheck,
        "--enable=warning,style,performance,portability",
        "--xml",
        "--xml-version=2",
        "--quiet",
        *[str(s) for s in sources[:200]],
    ]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=600,
            cwd=str(project_dir),
        )
    except subprocess.TimeoutExpired:
        return False, [], "cppcheck timed out after 600s"
    except OSError as exc:
        return False, [], f"failed to invoke cppcheck: {exc}"
    # cppcheck emits XML on stderr.
    return True, _parse_cppcheck_xml(proc.stderr), None


def _write_report(log_id: str, payload: dict[str, Any]) -> None:
    path = _log_dir() / f"analysis-{log_id}.json"
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        log.warning("failed to write analysis report %s: %s", path, exc)


def register(mcp: Any) -> None:
    @mcp.tool()
    def analyze_code(
        path: str = Field(..., description="File or directory to analyze."),
        tool: Tool = Field(
            "clang-tidy", description="Which static analyzer(s) to run."
        ),
        checks: str = Field(
            "*", description="clang-tidy check filter expression."
        ),
        fix: bool = Field(
            False, description="Apply clang-tidy suggested fixes in-place."
        ),
    ) -> dict[str, Any]:
        """Run clang-tidy and/or cppcheck against a file or directory.

        Returns ``{ok, diagnostics: [...], summary}``. Each diagnostic
        has file/line/column/severity/check/message and may include a
        ``suggested_fix`` (clang-tidy YAML replacements).
        """
        target = Path(path).expanduser()
        target = (Path.cwd() / target).resolve() if not target.is_absolute() else target.resolve()

        if not target.exists():
            return {"ok": False, "diagnostics": [], "summary": "", "error": f"path not found: {target}"}

        sources = _discover_sources(target)
        if not sources:
            return {
                "ok": True,
                "diagnostics": [],
                "summary": "no C/C++ source files found",
                "log_id": None,
            }

        project_dir = target if target.is_dir() else target.parent
        diagnostics: list[dict[str, Any]] = []
        errors: list[str] = []

        if tool in ("clang-tidy", "all"):
            ok, diags, err = _run_clang_tidy(
                sources, checks=checks, fix=fix, project_dir=project_dir
            )
            if err:
                errors.append(err)
            diagnostics.extend(diags)
            if not ok and tool == "clang-tidy":
                return {"ok": False, "diagnostics": [], "summary": "", "error": err}

        if tool in ("cppcheck", "all"):
            ok, diags, err = _run_cppcheck(sources, project_dir=project_dir)
            if err:
                errors.append(err)
            diagnostics.extend(diags)
            if not ok and tool == "cppcheck":
                return {"ok": False, "diagnostics": [], "summary": "", "error": err}

        severity_counts: dict[str, int] = {}
        for d in diagnostics:
            sev = d.get("severity") or "unknown"
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary = (
            f"{len(diagnostics)} diagnostic(s) across {len(sources)} file(s); "
            f"by severity: {severity_counts}"
        )
        if errors:
            summary += f"; notes: {', '.join(errors)}"

        log_id = uuid.uuid4().hex
        report = {
            "tool": tool,
            "checks": checks,
            "fix": fix,
            "path": str(target),
            "diagnostics": diagnostics,
            "summary": summary,
            "errors": errors,
        }
        _write_report(log_id, report)

        return {
            "ok": True,
            "diagnostics": diagnostics,
            "summary": summary,
            "log_id": log_id,
        }
