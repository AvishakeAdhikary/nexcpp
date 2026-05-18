"""BM25 + symbol-trie documentation index.

The index is bootstrapped at first access from the bundled, royalty-free
content shipped in :mod:`doc_index.data`. Optionally, an extension pickle at
``~/.nexcpp/extended_index.pkl`` (or ``$NEXCPP_EXTENSIONS_PKL``) is merged
on top, allowing users to add their own supplementary entries via the
``nexcpp-fetch extend`` CLI without modifying the package itself.
"""

from __future__ import annotations

import logging
import os
import pickle
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

from rank_bm25 import BM25Okapi

log = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z0-9_:]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


@dataclass
class DocEntry:
    """A single indexable documentation record."""

    symbol: str
    header: str = ""
    since: str = ""
    brief: str = ""
    signature: str = ""
    example: str = ""
    url: str = ""
    source: str = "std"
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class _SymbolTrie:
    """Tiny dict-based prefix index for exact symbol lookup."""

    def __init__(self) -> None:
        self.exact: dict[str, list[int]] = {}
        self.lower: dict[str, list[int]] = {}

    def add(self, key: str, doc_id: int) -> None:
        if not key:
            return
        self.exact.setdefault(key, []).append(doc_id)
        self.lower.setdefault(key.lower(), []).append(doc_id)

    def lookup(self, key: str) -> list[int]:
        if not key:
            return []
        if key in self.exact:
            return list(self.exact[key])
        return list(self.lower.get(key.lower(), []))


class DocIndex:
    """Searchable documentation index."""

    def __init__(self) -> None:
        self.entries: list[DocEntry] = []
        self._bm25: BM25Okapi | None = None
        self._trie = _SymbolTrie()
        self._loaded: bool = False

    # ------------------------------------------------------------------ build

    def build_from_parsed(self, entries: list[DocEntry]) -> None:
        self.entries = list(entries)
        self._trie = _SymbolTrie()
        corpus: list[list[str]] = []
        for i, entry in enumerate(self.entries):
            self._trie.add(entry.symbol, i)
            # Also index trailing namespace component (vector for std::vector).
            tail = entry.symbol.split("::")[-1]
            if tail and tail != entry.symbol:
                self._trie.add(tail, i)
            tokens = _tokenize(
                " ".join(
                    [
                        entry.symbol,
                        entry.brief,
                        entry.header,
                        entry.signature,
                        entry.source,
                    ]
                )
            )
            corpus.append(tokens or [entry.symbol.lower()])
        self._bm25 = BM25Okapi(corpus) if corpus else None
        self._loaded = True

    # ------------------------------------------------------------------ persist

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            pickle.dump({"entries": [e.as_dict() for e in self.entries]}, fh)

    def load(self, path: Path) -> bool:
        if not path.is_file():
            return False
        try:
            with path.open("rb") as fh:
                payload = pickle.load(fh)
            raw_entries = payload.get("entries", [])
            entries = [DocEntry(**e) for e in raw_entries]
            self.build_from_parsed(entries)
            return True
        except Exception as exc:  # pragma: no cover - corrupt index path
            log.warning("Failed to load index from %s: %s", path, exc)
            return False

    @staticmethod
    def load_entries_from_pickle(path: Path) -> list[DocEntry]:
        """Read a pickle of DocEntry dicts written by :meth:`save`."""
        if not path.is_file():
            return []
        try:
            with path.open("rb") as fh:
                payload = pickle.load(fh)
            raw_entries = payload.get("entries", [])
            return [DocEntry(**e) for e in raw_entries]
        except Exception as exc:  # pragma: no cover - corrupt input
            log.warning("Failed to read entries from %s: %s", path, exc)
            return []

    # ------------------------------------------------------------------ search

    def search(
        self,
        query: str,
        source: str | None = None,
        cpp_std: str | None = None,
        max_results: int = 5,
    ) -> list[DocEntry]:
        if not self._loaded:
            return []
        max_results = max(1, min(int(max_results or 5), 20))
        wanted_source = None if source in (None, "", "all") else source

        # 1. Exact symbol hits first.
        hits: list[int] = []
        seen: set[int] = set()
        for variant in (query, query.replace(" ", ""), query.strip("()")):
            for doc_id in self._trie.lookup(variant):
                if doc_id not in seen:
                    seen.add(doc_id)
                    hits.append(doc_id)
            if hits:
                break

        # 2. BM25 fallback / supplement.
        if self._bm25 is not None:
            tokens = _tokenize(query)
            if tokens:
                scores = self._bm25.get_scores(tokens)
                ranked = sorted(
                    range(len(scores)),
                    key=lambda i: scores[i],
                    reverse=True,
                )
                for doc_id in ranked:
                    if scores[doc_id] <= 0:
                        break
                    if doc_id in seen:
                        continue
                    seen.add(doc_id)
                    hits.append(doc_id)
                    if len(hits) >= max_results * 4:
                        break

        results: list[DocEntry] = []
        for doc_id in hits:
            entry = self.entries[doc_id]
            if wanted_source and entry.source != wanted_source:
                continue
            if cpp_std and entry.since:
                # Reject entries that require a newer standard than asked-for.
                requested = _std_year(cpp_std)
                got = _std_year(entry.since)
                if requested and got and got > requested:
                    continue
            results.append(entry)
            if len(results) >= max_results:
                break
        return results

    # ------------------------------------------------------------------ misc

    @property
    def is_synthetic(self) -> bool:
        """Retained for API compatibility. The bundled index is never synthetic."""
        return False

    def as_markdown_index(self) -> str:
        if not self.entries:
            return "# nexcpp documentation index\n\n*(empty)*\n"
        lines = ["# nexcpp documentation index", ""]
        lines.append(f"_{len(self.entries)} entries across "
                     f"{len({e.source for e in self.entries})} sources._")
        lines.append("")
        by_source: dict[str, list[DocEntry]] = {}
        for entry in self.entries:
            by_source.setdefault(entry.source, []).append(entry)
        for source, group in sorted(by_source.items()):
            lines.append(f"## {source}  ({len(group)})")
            lines.append("")
            for entry in sorted(group, key=lambda e: e.symbol):
                blurb = entry.brief[:80] + ("..." if len(entry.brief) > 80 else "")
                lines.append(f"- `{entry.symbol}` — {blurb}")
            lines.append("")
        return "\n".join(lines)


_STD_YEARS = {
    "98": 1998,
    "03": 2003,
    "11": 2011,
    "14": 2014,
    "17": 2017,
    "20": 2020,
    "23": 2023,
    "26": 2026,
}


def _std_year(token: str) -> int | None:
    if not token:
        return None
    t = token.strip().replace("C++", "").replace("c++", "")
    # Take the first 2-digit chunk.
    for length in (4, 2):
        if len(t) >= length and t[:length].isdigit():
            v = t[:length]
            if length == 4:
                try:
                    return int(v)
                except ValueError:
                    return None
            return _STD_YEARS.get(v)
    return None


# ----------------------------------------------------------------- singleton


_INDEX_LOCK = Lock()
_INDEX: DocIndex | None = None


def _extension_pickle_path() -> Path:
    """Return the path of the user's extension pickle.

    Honors ``$NEXCPP_EXTENSIONS_PKL`` so tests can point at a temp file.
    """
    override = os.environ.get("NEXCPP_EXTENSIONS_PKL")
    if override:
        return Path(override)
    return Path.home() / ".nexcpp" / "extended_index.pkl"


def _merge_entries(base: list[DocEntry], extension: list[DocEntry]) -> list[DocEntry]:
    """Merge ``extension`` into ``base``; extension entries override by symbol."""
    if not extension:
        return list(base)
    by_symbol: dict[str, DocEntry] = {entry.symbol: entry for entry in base}
    for entry in extension:
        by_symbol[entry.symbol] = entry
    return list(by_symbol.values())


def get_index() -> DocIndex:
    """Lazy singleton accessor.

    Loads the bundled royalty-free entries first, then merges any
    user-supplied extension pickle on top.
    """
    global _INDEX
    with _INDEX_LOCK:
        if _INDEX is not None:
            return _INDEX
        from doc_index.data import load_all  # local import: break cycle

        bundled = load_all()
        ext_path = _extension_pickle_path()
        extensions = DocIndex.load_entries_from_pickle(ext_path)
        if extensions:
            log.info("Merging %d extension entries from %s", len(extensions), ext_path)
        merged = _merge_entries(bundled, extensions)
        idx = DocIndex()
        idx.build_from_parsed(merged)
        _INDEX = idx
        return _INDEX


def reset_index_cache() -> None:
    """Drop the cached index (used by tests and ``nexcpp-fetch``)."""
    global _INDEX
    with _INDEX_LOCK:
        _INDEX = None
