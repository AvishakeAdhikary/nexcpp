"""Parse user-supplied CMake docs (HTML or RST) into :class:`DocEntry` records.

This parser only runs against files that the user provides via
``nexcpp-fetch extend cmake --input-dir <path>``. The bundled royalty-free
CMake entries live in :mod:`doc_index.data.cmake`.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from doc_index.index import DocEntry

log = logging.getLogger(__name__)

_BASE_URL = "https://cmake.org/cmake/help/latest/command/"


def _load_bs4() -> type:  # pragma: no cover - import-time path
    try:
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "beautifulsoup4 is required to parse HTML input. "
            "Install it with `pip install beautifulsoup4 lxml`."
        ) from exc
    return BeautifulSoup


def _parse_rst(path: Path) -> DocEntry | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    symbol = path.stem
    brief = ""
    signature = ""
    in_signature = False
    sig_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            if in_signature and sig_lines:
                signature = "\n".join(sig_lines)
                in_signature = False
            continue
        if line.startswith(".. code-block"):
            in_signature = True
            continue
        if in_signature and line.startswith("   "):
            sig_lines.append(line.strip())
            continue
        if not brief and not line.startswith(("..", "=", "-", "~")):
            brief = line.strip()
    return DocEntry(
        symbol=symbol,
        header="CMake",
        since="",
        brief=brief,
        signature=signature,
        example="",
        url=_BASE_URL + symbol + ".html",
        source="cmake",
    )


def _parse_html(path: Path) -> DocEntry | None:
    BeautifulSoup = _load_bs4()
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    symbol = h1.get_text(strip=True) if h1 else path.stem
    symbol = re.sub(r"[\s\xb6].*$", "", symbol).strip() or path.stem
    p = soup.find("p")
    brief = p.get_text(" ", strip=True) if p else ""
    pre = soup.find("pre")
    signature = pre.get_text("\n", strip=True) if pre else ""
    return DocEntry(
        symbol=symbol,
        header="CMake",
        since="",
        brief=brief,
        signature=signature,
        example="",
        url=_BASE_URL + path.stem + ".html",
        source="cmake",
    )


def parse_file(path: Path) -> DocEntry | None:
    if path.suffix.lower() == ".rst":
        return _parse_rst(path)
    if path.suffix.lower() in {".html", ".htm"}:
        return _parse_html(path)
    return None


def parse_dir(path: Path) -> list[DocEntry]:
    """Parse every *.rst, *.html, *.htm file under ``path``. Returns ``[]`` if none found."""
    if not path.is_dir():
        return []
    entries: list[DocEntry] = []
    for f in path.rglob("*"):
        if f.is_file() and f.suffix.lower() in {".rst", ".html", ".htm"}:
            try:
                entry = parse_file(f)
            except Exception as exc:  # pragma: no cover - resilience
                log.warning("parse_file failed on %s: %s", f, exc)
                continue
            if entry is not None:
                entries.append(entry)
    return entries
