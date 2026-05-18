"""Parse user-supplied vcpkg port manifests into :class:`DocEntry` records.

This parser only runs against files that the user provides via
``nexcpp-fetch extend vcpkg --input-dir <path>`` (typically pointing at a
local ``ports/`` directory of a vcpkg checkout). The bundled royalty-free
vcpkg entries live in :mod:`doc_index.data.vcpkg`.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from doc_index.index import DocEntry

log = logging.getLogger(__name__)

_BASE_URL = "https://github.com/microsoft/vcpkg/tree/master/ports/"


def parse_manifest(path: Path) -> DocEntry | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None
    name = raw.get("name") or path.parent.name
    version = (
        raw.get("version")
        or raw.get("version-semver")
        or raw.get("version-date")
        or raw.get("version-string")
        or ""
    )
    description = raw.get("description") or ""
    if isinstance(description, list):
        description = " ".join(description)
    homepage = raw.get("homepage") or (_BASE_URL + name)
    deps = raw.get("dependencies") or []
    dep_names: list[str] = []
    for d in deps:
        if isinstance(d, str):
            dep_names.append(d)
        elif isinstance(d, dict) and "name" in d:
            dep_names.append(d["name"])
    return DocEntry(
        symbol=name,
        header="vcpkg.json",
        since=str(version),
        brief=description,
        signature=f'"dependencies": ["{name}"]',
        example=f"find_package({name} CONFIG REQUIRED)",
        url=homepage,
        source="vcpkg",
        extra={"dependencies": dep_names},
    )


def parse_dir(path: Path) -> list[DocEntry]:
    """Parse every ``*/vcpkg.json`` under ``path``. Returns ``[]`` if none found."""
    if not path.is_dir():
        return []
    entries: list[DocEntry] = []
    for manifest in path.glob("*/vcpkg.json"):
        try:
            entry = parse_manifest(manifest)
        except Exception as exc:  # pragma: no cover - resilience
            log.warning("parse_manifest failed on %s: %s", manifest, exc)
            continue
        if entry is not None:
            entries.append(entry)
    return entries
