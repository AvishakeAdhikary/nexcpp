"""Parse user-supplied cppreference HTML mirrors into :class:`DocEntry` records.

This parser only runs against files that the user provides via
``nexcpp-fetch extend cppreference --input-dir <path>``. It does NOT produce
a synthetic dataset on its own; the bundled royalty-free index lives in
:mod:`doc_index.data` instead.

The parser is intentionally tolerant: a real cppreference mirror has many
page shapes. We extract whatever we can (symbol, header, brief, signature)
and skip pages we don't understand.
"""

from __future__ import annotations

import logging
from pathlib import Path

from doc_index.index import DocEntry

log = logging.getLogger(__name__)

_BASE_URL = "https://en.cppreference.com/w/"


def _load_bs4() -> type:  # pragma: no cover - import-time path
    try:
        from bs4 import BeautifulSoup  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "beautifulsoup4 is required to parse HTML input. "
            "Install it with `pip install beautifulsoup4 lxml`."
        ) from exc
    return BeautifulSoup


def _extract_symbol(soup: object, file_path: Path) -> str:
    h1 = soup.find("h1")
    if h1:
        text = h1.get_text(" ", strip=True)
        if text:
            return text.split(" - ")[0].strip()
    return file_path.stem


def _extract_brief(soup: object) -> str:
    p = soup.find("p")
    if p:
        return p.get_text(" ", strip=True)
    return ""


def _extract_signature(soup: object) -> str:
    pre = soup.find("pre")
    if pre:
        return pre.get_text("\n", strip=True)
    return ""


def _extract_header(soup: object) -> str:
    for code in soup.find_all("code"):
        text = code.get_text(strip=True)
        if text.startswith("<") and text.endswith(">"):
            return text
    return ""


def _extract_since(soup: object) -> str:
    for tag in soup.select(".t-mark-rev, .mark-since-cxx, .t-mark"):
        text = tag.get_text(strip=True)
        if text and text.lower().startswith("c++"):
            return text
    return ""


def parse_file(path: Path) -> DocEntry | None:
    BeautifulSoup = _load_bs4()
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    soup = BeautifulSoup(html, "lxml")
    symbol = _extract_symbol(soup, path)
    if not symbol:
        return None
    brief = _extract_brief(soup)
    return DocEntry(
        symbol=symbol,
        header=_extract_header(soup),
        since=_extract_since(soup),
        brief=brief,
        signature=_extract_signature(soup),
        example="",
        url=_BASE_URL + path.stem,
        source="std",
    )


def parse_dir(path: Path) -> list[DocEntry]:
    """Parse every *.html file under ``path``. Returns ``[]`` if none found."""
    if not path.is_dir():
        return []
    entries: list[DocEntry] = []
    for html_file in path.rglob("*.html"):
        try:
            entry = parse_file(html_file)
        except Exception as exc:  # pragma: no cover - resilience
            log.warning("parse_file failed on %s: %s", html_file, exc)
            continue
        if entry is not None:
            entries.append(entry)
    return entries
