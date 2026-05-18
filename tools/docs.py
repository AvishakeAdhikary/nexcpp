"""``search_cpp_docs`` MCP tool implementation."""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import Field

from doc_index import get_index

log = logging.getLogger(__name__)

Source = Literal["std", "cmake", "vcpkg", "conan", "boost", "qt", "llvm", "all"]
CppStd = Literal["11", "14", "17", "20", "23"]


def _entry_to_dict(entry: Any) -> dict[str, Any]:
    return {
        "symbol": entry.symbol,
        "header": entry.header,
        "since": entry.since,
        "brief": entry.brief,
        "signature": entry.signature,
        "example": entry.example,
        "url": entry.url,
        "source": entry.source,
    }


def register(mcp: Any) -> None:
    """Attach the ``search_cpp_docs`` tool to the given FastMCP server."""

    @mcp.tool()
    def search_cpp_docs(
        query: str = Field(..., description="Symbol name, topic, or natural language query."),
        source: Source = Field(
            "all",
            description="Restrict to a single doc source. 'all' = no filter.",
        ),
        cpp_std: CppStd | None = Field(
            None,
            description="Filter results to entries available in this C++ standard.",
        ),
        max_results: int = Field(
            5,
            ge=1,
            le=20,
            description="Maximum number of results (1-20).",
        ),
    ) -> list[dict[str, Any]]:
        """Search the offline, royalty-free C++ documentation index.

        The bundled index ships with the package and covers the C++ standard
        library, CMake, vcpkg ports, Conan recipes, Boost, Qt and LLVM/Clang.
        Users may extend it with their own data via ``nexcpp-fetch extend``.
        Each result is a ``DocEntry``-shaped dict.
        """
        index = get_index()
        results = index.search(
            query=query,
            source=None if source == "all" else source,
            cpp_std=cpp_std,
            max_results=max_results,
        )
        return [_entry_to_dict(e) for e in results]
