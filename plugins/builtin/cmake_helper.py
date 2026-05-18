"""Built-in plugin: CMake intelligence helpers.

Registers:

* Tool ``cmake_explain(command)`` — looks up a CMake command in the offline
  doc index.
* Resource ``nexcpp://cmake/presets/{name}`` — reads CMakePresets.json from
  the project root and returns the named preset.
* Prompt ``cmake_modernize(legacy_cmake)`` — guidance for migrating
  pre-3.0 CMake to modern target-based CMake.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from sdk import PluginContext

log = logging.getLogger(__name__)

PLUGIN_META = {
    "name": "cmake-helper",
    "version": "1.0.0",
    "description": "CMake intelligence helpers (explain, presets, modernize).",
    "author": "nexcpp",
}


def _format_entry(entry: Any) -> dict[str, Any]:
    return {
        "symbol": getattr(entry, "symbol", ""),
        "since": getattr(entry, "since", ""),
        "brief": getattr(entry, "brief", ""),
        "signature": getattr(entry, "signature", ""),
        "example": getattr(entry, "example", ""),
        "url": getattr(entry, "url", ""),
    }


def register(ctx: PluginContext) -> None:
    @ctx.tool(
        description=(
            "Explain a CMake command or variable using the offline doc index. "
            "Returns signature, brief, example, and upstream URL when known."
        )
    )
    def cmake_explain(command: str) -> dict[str, Any]:
        try:
            from doc_index import get_index
        except Exception as exc:  # pragma: no cover
            return {"ok": False, "error": f"doc_index unavailable: {exc}"}
        index = get_index()
        results = index.search(query=command, source="cmake", max_results=1)
        if not results:
            return {
                "ok": True,
                "found": False,
                "command": command,
                "hint": (
                    "Not in index. Run `nexcpp-fetch cmake` to populate the "
                    "CMake docs, or check the spelling."
                ),
            }
        entry = results[0]
        return {
            "ok": True,
            "found": True,
            "command": command,
            "doc": _format_entry(entry),
        }

    @ctx.resource(
        "nexcpp://cmake/presets/{name}",
        description="Single CMake preset by name from CMakePresets.json in cwd.",
    )
    def cmake_preset(name: str) -> str:
        presets_file = Path.cwd() / "CMakePresets.json"
        if not presets_file.is_file():
            return json.dumps(
                {"error": "CMakePresets.json not found in project root", "name": name},
                indent=2,
            )
        try:
            data = json.loads(presets_file.read_text(encoding="utf-8"))
        except Exception as exc:
            return json.dumps({"error": f"failed to parse presets: {exc}", "name": name}, indent=2)

        for bucket in ("configurePresets", "buildPresets", "testPresets", "packagePresets"):
            for preset in data.get(bucket, []) or []:
                if preset.get("name") == name:
                    return json.dumps({"bucket": bucket, "preset": preset}, indent=2)
        return json.dumps(
            {
                "error": f"preset {name!r} not found",
                "available": [
                    p.get("name")
                    for bucket in ("configurePresets", "buildPresets", "testPresets")
                    for p in data.get(bucket, []) or []
                ],
            },
            indent=2,
        )

    @ctx.prompt(
        description="Guide migration of legacy CMake to modern target-based CMake.",
    )
    def cmake_modernize(legacy_cmake: str) -> str:
        return (
            "You are modernizing CMake. Convert the following legacy CMake to "
            "modern target-based style.\n\n"
            "Apply these rules:\n"
            "- Require cmake_minimum_required(VERSION 3.20) or newer.\n"
            "- Use `target_include_directories`, `target_link_libraries`, "
            "`target_compile_features`, `target_compile_definitions` — never "
            "the directory-level `include_directories`, `link_libraries`, etc.\n"
            "- Replace `set(CMAKE_CXX_FLAGS ...)` with target-level flags.\n"
            "- Prefer `find_package(Pkg CONFIG REQUIRED)` and `Pkg::Pkg` "
            "imported targets over raw variable usage.\n"
            "- Use `add_library(name STATIC|SHARED|INTERFACE ...)` with "
            "PUBLIC/PRIVATE/INTERFACE keywords on all target_* calls.\n"
            "- Move tests behind `if(BUILD_TESTING) ... endif()` and use "
            "`enable_testing()` + `add_test(NAME ... COMMAND ...)`.\n"
            "- Add `CMakePresets.json` with `default`, `release`, and "
            "`asan` configure presets when reasonable.\n"
            "Then call `build_project` to verify the migration compiles.\n\n"
            "## Legacy CMake\n\n```cmake\n"
            f"{legacy_cmake}\n"
            "```\n"
        )
