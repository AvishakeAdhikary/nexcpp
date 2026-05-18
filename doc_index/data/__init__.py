"""Bundled royalty-free C++ tooling documentation for nexcpp.

All content under :mod:`doc_index.data` is original work, released under
the MIT License along with the rest of nexcpp. Public API symbol names,
function signatures, and version numbers are facts about the upstream
projects they describe and are not copyrightable. Prose descriptions and
code examples are original.
"""

from __future__ import annotations

from doc_index.index import DocEntry

from . import boost, cmake, conan, llvm, qt, std, vcpkg

__all__ = ["load_all", "boost", "cmake", "conan", "llvm", "qt", "std", "vcpkg"]


def load_all() -> list[DocEntry]:
    """Return a fresh list of every bundled DocEntry, across all sources."""
    return [
        *std.ENTRIES,
        *cmake.ENTRIES,
        *vcpkg.ENTRIES,
        *conan.ENTRIES,
        *boost.ENTRIES,
        *qt.ENTRIES,
        *llvm.ENTRIES,
    ]
