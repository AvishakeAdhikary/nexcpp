"""Source-specific parsers that produce :class:`doc_index.DocEntry` lists."""

from . import cmake_docs, cppreference, vcpkg_catalog

__all__ = ["cppreference", "cmake_docs", "vcpkg_catalog"]
