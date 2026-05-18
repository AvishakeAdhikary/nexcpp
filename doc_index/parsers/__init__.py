"""Source-specific parsers that produce :class:`doc_index.DocEntry` lists."""

from . import cmake_docs, cppreference, vcpkg_catalog

__all__ = ["cmake_docs", "cppreference", "vcpkg_catalog"]
