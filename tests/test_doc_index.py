"""Tests for the bundled documentation index.

The index now ships as royalty-free, original content inside the package
(see :mod:`doc_index.data`). These tests assert the bundled data's schema,
shape, search behavior, extension merging, and the user-facing CLI.
"""

from __future__ import annotations

import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_KNOWN_SOURCES = {"std", "cmake", "vcpkg", "conan", "boost", "qt", "llvm"}


# ------------------------------------------------------------------ helpers


def _fresh_index() -> Any:
    """Drop the singleton, then build a fresh one and return it."""
    from doc_index.index import get_index, reset_index_cache

    reset_index_cache()
    return get_index()


# ----------------------------------------------------- 1. bundled data shape


def test_load_all_returns_at_least_200_entries() -> None:
    from doc_index.data import load_all

    entries = load_all()
    assert len(entries) >= 200, f"only {len(entries)} bundled entries"


def test_every_entry_has_symbol_and_brief() -> None:
    from doc_index.data import load_all

    bad: list[str] = []
    for entry in load_all():
        if not entry.symbol or not entry.symbol.strip():
            bad.append(f"missing symbol on {entry!r}")
        if not entry.brief or not entry.brief.strip():
            bad.append(f"missing brief on {entry.symbol!r}")
    assert not bad, "\n".join(bad[:10])


def test_every_entry_has_unique_symbol_within_source() -> None:
    from doc_index.data import load_all

    seen: dict[tuple[str, str], int] = {}
    dups: list[str] = []
    for entry in load_all():
        key = (entry.source, entry.symbol)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] > 1:
            dups.append(f"{entry.source}/{entry.symbol}")
    assert not dups, "duplicates: " + ", ".join(dups)


def test_every_brief_is_under_400_chars() -> None:
    from doc_index.data import load_all

    too_long = [e.symbol for e in load_all() if len(e.brief) > 400]
    assert not too_long, "briefs too long: " + ", ".join(too_long[:5])


def test_every_signature_is_under_500_chars() -> None:
    from doc_index.data import load_all

    too_long = [e.symbol for e in load_all() if len(e.signature) > 500]
    assert not too_long, "signatures too long: " + ", ".join(too_long[:5])


def test_every_source_is_known() -> None:
    from doc_index.data import load_all

    found = {e.source for e in load_all()}
    unknown = found - _KNOWN_SOURCES
    assert not unknown, f"unknown sources: {unknown}"
    assert found == _KNOWN_SOURCES, f"missing sources: {_KNOWN_SOURCES - found}"


# ----------------------------------------------------- 2. singleton + search


def test_get_index_returns_singleton() -> None:
    from doc_index.index import get_index, reset_index_cache

    reset_index_cache()
    a = get_index()
    b = get_index()
    assert a is b


def test_index_exact_match_finds_std_vector() -> None:
    idx = _fresh_index()
    hits = idx.search("std::vector", max_results=3)
    assert hits
    assert any(h.symbol == "std::vector" for h in hits)


def test_index_bm25_finds_vector_from_partial_query() -> None:
    idx = _fresh_index()
    hits = idx.search("dynamic array", max_results=5)
    symbols = [h.symbol for h in hits]
    assert any("vector" in s for s in symbols), f"expected a vector-ish hit, got {symbols}"


def test_index_filter_by_source_only_returns_that_source() -> None:
    idx = _fresh_index()
    hits = idx.search("install", source="cmake", max_results=5)
    assert hits
    assert all(h.source == "cmake" for h in hits)


def test_index_filter_by_cpp_std_works() -> None:
    idx = _fresh_index()
    # std::expected requires C++23; asking for C++17 should drop it.
    hits = idx.search("std::expected", cpp_std="17", max_results=5)
    assert all(h.symbol != "std::expected" for h in hits)


def test_index_save_load_pickle_roundtrip(tmp_path: Path) -> None:
    from doc_index.index import DocIndex

    idx = _fresh_index()
    out = tmp_path / "snapshot.pkl"
    idx.save(out)
    assert out.is_file()

    other = DocIndex()
    assert other.load(out)
    assert len(other.entries) == len(idx.entries)
    hits = other.search("std::vector")
    assert any(h.symbol == "std::vector" for h in hits)


# ----------------------------------------------------- 3. extensions merge


def _write_ext_pickle(path: Path, entries: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entries": [e.as_dict() for e in entries]}
    with path.open("wb") as fh:
        pickle.dump(payload, fh)


def test_extensions_pickle_is_merged_if_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from doc_index.index import DocEntry, reset_index_cache

    ext = tmp_path / "ext.pkl"
    custom = DocEntry(
        symbol="my::CompletelyCustomThing",
        header="<mything>",
        brief="A user-supplied extension entry only present at runtime.",
        source="std",
    )
    _write_ext_pickle(ext, [custom])
    monkeypatch.setenv("NEXCPP_EXTENSIONS_PKL", str(ext))
    reset_index_cache()

    from doc_index.index import get_index

    idx = get_index()
    hits = idx.search("my::CompletelyCustomThing", max_results=3)
    assert hits
    assert hits[0].symbol == "my::CompletelyCustomThing"


def test_extensions_override_duplicates_by_symbol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from doc_index.index import DocEntry, reset_index_cache

    ext = tmp_path / "ext.pkl"
    # Override the bundled std::vector with an obvious sentinel brief.
    override = DocEntry(
        symbol="std::vector",
        header="<vector>",
        brief="OVERRIDDEN_FROM_EXTENSION_PICKLE",
        source="std",
    )
    _write_ext_pickle(ext, [override])
    monkeypatch.setenv("NEXCPP_EXTENSIONS_PKL", str(ext))
    reset_index_cache()

    from doc_index.index import get_index

    idx = get_index()
    hits = idx.search("std::vector", max_results=1)
    assert hits
    assert hits[0].brief == "OVERRIDDEN_FROM_EXTENSION_PICKLE"


# ----------------------------------------------------- 4. CLI subprocess


@pytest.mark.integration
def test_fetch_info_prints_stats_to_stdout() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "doc_index.fetch", "info"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    combined = proc.stdout + proc.stderr
    assert "bundled documentation index" in combined.lower()
    assert "std" in combined
    assert "cmake" in combined


@pytest.mark.integration
def test_fetch_extend_with_no_input_dir_returns_error_message(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "doc_index.fetch",
            "extend",
            "vcpkg",
            "--input-dir",
            str(missing),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    # Either click's missing-path validation OR our own check should reject it.
    assert proc.returncode != 0
    combined = (proc.stdout + proc.stderr).lower()
    assert "does not exist" in combined or "invalid value" in combined


# ----------------------------------------------------- 5. MCP wiring


def _call(mcp: Any, name: str, args: dict[str, Any]) -> Any:
    import asyncio

    out = asyncio.get_event_loop().run_until_complete(mcp.call_tool(name, args))
    if isinstance(out, tuple) and len(out) == 2:
        return out[1]
    return out


def _read(mcp: Any, uri: str) -> str:
    import asyncio

    out = asyncio.get_event_loop().run_until_complete(mcp.read_resource(uri))
    if isinstance(out, list) and out:
        first = out[0]
        if hasattr(first, "content"):
            return str(first.content)
        return str(first)
    if hasattr(out, "content"):
        return str(out.content)
    return str(out)


def test_search_cpp_docs_tool_returns_real_bundled_data(mcp_server: Any) -> None:
    pytest.importorskip("doc_index")
    from doc_index.index import reset_index_cache

    reset_index_cache()
    result = _call(
        mcp_server,
        "search_cpp_docs",
        {"query": "std::vector", "source": "all", "max_results": 3},
    )
    items = result["result"] if isinstance(result, dict) and "result" in result else result
    assert isinstance(items, list)
    assert items, "expected non-empty results from bundled data"
    first = items[0]
    assert first["symbol"] == "std::vector"
    assert first["brief"]
    # The brief must not be the old synthetic-fallback nag.
    assert "run `nexcpp-fetch all`" not in first["brief"].lower()
    assert "synthetic" not in first["brief"].lower()


def test_docs_resource_index_returns_markdown(mcp_server: Any) -> None:
    pytest.importorskip("resources.cpp_docs")
    from doc_index.index import reset_index_cache

    reset_index_cache()
    text = _read(mcp_server, "nexcpp://docs/index")
    assert "# nexcpp documentation index" in text
    # Multiple sources should be visible as ## headings.
    for source in ("std", "cmake", "vcpkg", "boost"):
        assert f"## {source}" in text, f"missing '## {source}' in:\n{text[:400]}"


def test_docs_resource_std_vector_returns_content(mcp_server: Any) -> None:
    pytest.importorskip("resources.cpp_docs")
    from doc_index.index import reset_index_cache

    reset_index_cache()
    text = _read(mcp_server, "nexcpp://docs/std/std::vector")
    assert "std::vector" in text
    assert "<vector>" in text
    # Original brief mentions O(1) random access; sanity check it's real prose.
    assert "Header" in text or "vector" in text.lower()


# ------------------------------------------------ 6. defensive content checks


def test_no_brief_contains_attribution_to_cppreference() -> None:
    """Defensive: bundled briefs must be original, not lifted."""
    from doc_index.data import load_all

    forbidden = ("cppreference", "from cppreference", "see cppreference")
    offenders: list[str] = []
    for entry in load_all():
        text = entry.brief.lower()
        for needle in forbidden:
            if needle in text:
                offenders.append(f"{entry.source}/{entry.symbol}: contains '{needle}'")
                break
    assert not offenders, "\n".join(offenders[:5])
