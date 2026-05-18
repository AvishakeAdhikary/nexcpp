"""``manage_file`` MCP tool: safe project file operations.

Supports read / write / append / delete / move / patch / list. All paths
are validated against the current working directory (or an explicit
allowlist in config) to prevent path traversal.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from config import get_config

log = logging.getLogger(__name__)

Op = Literal["read", "write", "append", "delete", "move", "patch", "list"]


# ----------------------------------------------------------- safety helpers


def _allowed_roots() -> list[Path]:
    cfg = get_config()
    roots = [Path.cwd().resolve()]
    for extra in cfg.file_allowlist:
        roots.append(Path(extra).expanduser().resolve())
    return roots


def _resolve(path: str) -> Path:
    """Resolve a user-supplied path safely.

    Relative paths are joined to cwd. Absolute paths must fall inside the
    cwd or an explicit allowlist entry. Symlinks are resolved.
    """
    if not path:
        raise ValueError("path is required")
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.resolve()
    for root in _allowed_roots():
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise PermissionError(
        f"path {resolved} is outside cwd and not in file_allowlist"
    )


def _ok(result: Any = None) -> dict[str, Any]:
    return {"ok": True, "result": result, "error": None}


def _err(msg: str) -> dict[str, Any]:
    return {"ok": False, "result": None, "error": msg}


# --------------------------------------------------------- unified diff


def apply_unified_diff(original: str, patch: str) -> str:
    """Apply a unified diff to ``original`` and return the new text.

    Implements the subset of unified-diff syntax that real tools produce.
    Raises ``ValueError`` if any hunk fails to apply.
    """
    if not patch:
        return original

    src_lines = original.splitlines(keepends=True)
    out: list[str] = []
    cursor = 0  # index into src_lines

    lines = patch.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Skip file headers
        if line.startswith(("--- ", "+++ ", "diff ", "index ")):
            i += 1
            continue
        if not line.startswith("@@"):
            i += 1
            continue
        # Parse hunk header: @@ -l,s +l,s @@
        try:
            header = line[2:]
            header = header.split("@@", 1)[0].strip()
            parts = header.split()
            src_part = parts[0]  # -l,s
            assert src_part.startswith("-")
            src_start_str = src_part[1:].split(",")[0]
            src_start = int(src_start_str) if src_start_str else 1
        except (AssertionError, ValueError, IndexError) as exc:
            raise ValueError(f"invalid hunk header: {line!r}") from exc

        # Emit unchanged lines from cursor up to src_start - 1
        target = max(src_start - 1, 0)
        if target < cursor:
            raise ValueError("hunks out of order")
        out.extend(src_lines[cursor:target])
        cursor = target

        i += 1
        while i < len(lines) and not lines[i].startswith("@@"):
            hunk_line = lines[i]
            if hunk_line.startswith("\\"):
                i += 1
                continue
            tag = hunk_line[:1]
            payload = hunk_line[1:] + "\n"
            if tag == " ":
                if cursor >= len(src_lines):
                    raise ValueError("context line past end of source")
                if src_lines[cursor].rstrip("\n") != payload.rstrip("\n"):
                    raise ValueError(
                        f"context mismatch at source line {cursor + 1}: "
                        f"expected {src_lines[cursor]!r}, got {payload!r}"
                    )
                out.append(src_lines[cursor])
                cursor += 1
            elif tag == "-":
                if cursor >= len(src_lines):
                    raise ValueError("deletion past end of source")
                if src_lines[cursor].rstrip("\n") != payload.rstrip("\n"):
                    raise ValueError(
                        f"deletion mismatch at source line {cursor + 1}"
                    )
                cursor += 1
            elif tag == "+":
                out.append(payload)
            elif tag == "":
                # blank line in patch — treat as context blank.
                if cursor < len(src_lines) and src_lines[cursor].strip() == "":
                    out.append(src_lines[cursor])
                    cursor += 1
            else:
                raise ValueError(f"unknown patch line tag: {hunk_line!r}")
            i += 1

    out.extend(src_lines[cursor:])
    return "".join(out)


# ----------------------------------------------------------- listing


def _tree(path: Path, max_depth: int = 4, depth: int = 0) -> dict[str, Any]:
    if path.is_file():
        try:
            size = path.stat().st_size
        except OSError:
            size = -1
        return {"name": path.name, "type": "file", "size": size}
    children: list[dict[str, Any]] = []
    if depth < max_depth and path.is_dir():
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            entries = []
        for child in entries:
            if child.name in {".git", "__pycache__", ".venv", "node_modules"}:
                continue
            children.append(_tree(child, max_depth, depth + 1))
    return {"name": path.name or str(path), "type": "dir", "children": children}


# ----------------------------------------------------------- operations


def _op_read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return _err(f"not a file: {path}")
    # Read as bytes then decode so universal-newlines translation never
    # silently rewrites \r\n -> \n on the way back to callers.
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return _err(f"read failed: {exc}")
    try:
        return _ok(raw.decode("utf-8"))
    except UnicodeDecodeError:
        return _ok(raw.decode("utf-8", errors="replace"))


def _op_write(path: Path, content: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return _ok({"path": str(path), "bytes": len(content.encode("utf-8"))})


def _op_append(path: Path, content: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(content)
    return _ok({"path": str(path), "appended_bytes": len(content.encode("utf-8"))})


def _op_delete(path: Path) -> dict[str, Any]:
    if path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        return _err(f"no such path: {path}")
    return _ok({"deleted": str(path)})


def _op_move(src: Path, dest_raw: str) -> dict[str, Any]:
    if not src.exists():
        return _err(f"source missing: {src}")
    dest = _resolve(dest_raw)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(os.fspath(src), os.fspath(dest))
    return _ok({"from": str(src), "to": str(dest)})


def _op_patch(path: Path, patch: str) -> dict[str, Any]:
    if not path.is_file():
        return _err(f"not a file: {path}")
    original = path.read_text(encoding="utf-8")
    try:
        new_text = apply_unified_diff(original, patch)
    except ValueError as exc:
        return _err(f"patch failed: {exc}")
    path.write_text(new_text, encoding="utf-8")
    return _ok({"path": str(path), "bytes": len(new_text.encode("utf-8"))})


def _op_list(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _err(f"no such path: {path}")
    return _ok(_tree(path))


# ----------------------------------------------------------- register


def register(mcp: Any) -> None:  # noqa: ANN401
    @mcp.tool()
    def manage_file(
        op: Op = Field(..., description="Operation to perform."),
        path: str | None = Field(None, description="Target file or directory."),
        content: str | None = Field(None, description="Content for write/append."),
        patch: str | None = Field(None, description="Unified diff for op=patch."),
        dest: str | None = Field(None, description="Destination path for op=move."),
    ) -> dict[str, Any]:
        """Create, read, modify, delete, move, patch, or list project files.

        Returns ``{"ok": bool, "result": ..., "error": str | None}``.
        Refuses to touch paths outside the project root unless they appear
        in ``file_allowlist`` in ``.nexcpp/config.toml``.
        """
        try:
            if op == "list" and path in (None, ""):
                resolved = Path.cwd().resolve()
            else:
                if not path:
                    return _err("path is required for this op")
                resolved = _resolve(path)
        except (ValueError, PermissionError) as exc:
            return _err(str(exc))

        try:
            if op == "read":
                return _op_read(resolved)
            if op == "write":
                if content is None:
                    return _err("content is required for op=write")
                return _op_write(resolved, content)
            if op == "append":
                if content is None:
                    return _err("content is required for op=append")
                return _op_append(resolved, content)
            if op == "delete":
                return _op_delete(resolved)
            if op == "move":
                if not dest:
                    return _err("dest is required for op=move")
                return _op_move(resolved, dest)
            if op == "patch":
                if not patch:
                    return _err("patch is required for op=patch")
                return _op_patch(resolved, patch)
            if op == "list":
                return _op_list(resolved)
            return _err(f"unknown op: {op}")
        except OSError as exc:
            return _err(f"{op} failed: {exc}")
