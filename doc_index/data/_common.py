"""Tiny constructor shorthand for bundled DocEntry data modules.

All content in modules that import this helper is original work, released
under the MIT License along with the rest of nexcpp.
"""

from __future__ import annotations

from doc_index.index import DocEntry


def e(
    symbol: str,
    *,
    header: str = "",
    since: str = "",
    brief: str = "",
    signature: str = "",
    example: str = "",
    url: str = "",
    source: str = "",
) -> DocEntry:
    """Compact DocEntry constructor used by every bundled data module."""
    return DocEntry(
        symbol=symbol,
        header=header,
        since=since,
        brief=brief,
        signature=signature,
        example=example,
        url=url,
        source=source,
    )
