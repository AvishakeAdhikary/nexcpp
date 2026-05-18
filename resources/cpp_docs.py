"""MCP resources serving the bundled offline C++ documentation.

URI patterns:

* ``nexcpp://docs/std/{symbol}``     -- C++ standard library symbol
* ``nexcpp://docs/cmake/{topic}``    -- CMake docs
* ``nexcpp://docs/vcpkg/{package}``  -- vcpkg port
* ``nexcpp://docs/conan/{recipe}``   -- Conan recipe
* ``nexcpp://docs/boost/{lib}``      -- Boost library
* ``nexcpp://docs/qt/{symbol}``      -- Qt class or macro
* ``nexcpp://docs/llvm/{symbol}``    -- LLVM / Clang API
* ``nexcpp://docs/index``            -- full markdown index of everything
"""

from __future__ import annotations

from typing import Any

from doc_index import DocEntry, get_index


def _format_entry(entry: DocEntry) -> str:
    lines: list[str] = [f"# {entry.symbol}", ""]
    meta: list[str] = []
    if entry.header:
        meta.append(f"**Header:** `{entry.header}`")
    if entry.since:
        meta.append(f"**Since:** {entry.since}")
    if entry.source:
        meta.append(f"**Source:** {entry.source}")
    if meta:
        lines.extend(meta)
        lines.append("")
    if entry.brief:
        lines.append(entry.brief)
        lines.append("")
    if entry.signature:
        lines.append("## Signature")
        lines.append("")
        lines.append("```cpp")
        lines.append(entry.signature)
        lines.append("```")
        lines.append("")
    if entry.example:
        lines.append("## Example")
        lines.append("")
        lines.append("```cpp")
        lines.append(entry.example)
        lines.append("```")
        lines.append("")
    if entry.url:
        lines.append(f"[Upstream documentation]({entry.url})")
    return "\n".join(lines).rstrip() + "\n"


def _lookup(symbol: str, source: str) -> str:
    index = get_index()
    results = index.search(symbol, source=source, max_results=1)
    if not results:
        return f"# {symbol}\n\n*No `{source}` documentation found for `{symbol}`.*\n"
    return _format_entry(results[0])


def register(mcp: Any) -> None:  # noqa: ANN401
    @mcp.resource("nexcpp://docs/std/{symbol}")
    def std_symbol(symbol: str) -> str:
        """C++ standard library reference for ``symbol``."""
        return _lookup(symbol, "std")

    @mcp.resource("nexcpp://docs/cmake/{topic}")
    def cmake_topic(topic: str) -> str:
        """CMake documentation entry for ``topic``."""
        return _lookup(topic, "cmake")

    @mcp.resource("nexcpp://docs/vcpkg/{package}")
    def vcpkg_package(package: str) -> str:
        """vcpkg port catalog entry for ``package``."""
        return _lookup(package, "vcpkg")

    @mcp.resource("nexcpp://docs/conan/{recipe}")
    def conan_recipe(recipe: str) -> str:
        """Conan recipe documentation for ``recipe``."""
        return _lookup(recipe, "conan")

    @mcp.resource("nexcpp://docs/boost/{lib}")
    def boost_library(lib: str) -> str:
        """Boost library documentation for ``lib``."""
        return _lookup(lib, "boost")

    @mcp.resource("nexcpp://docs/qt/{symbol}")
    def qt_symbol(symbol: str) -> str:
        """Qt framework documentation for ``symbol``."""
        return _lookup(symbol, "qt")

    @mcp.resource("nexcpp://docs/llvm/{symbol}")
    def llvm_symbol(symbol: str) -> str:
        """LLVM / Clang API documentation for ``symbol``."""
        return _lookup(symbol, "llvm")

    @mcp.resource("nexcpp://docs/index")
    def docs_index() -> str:
        """Full markdown index of every bundled documentation entry, organized by source."""
        return get_index().as_markdown_index()
