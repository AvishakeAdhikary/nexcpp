"""Project-state MCP resources.

URI patterns:

* ``nexcpp://project/files``         — recursive file tree of cwd
* ``nexcpp://project/config``        — current loaded config as TOML
* ``nexcpp://project/build-system``  — detected build system summary
* ``nexcpp://project/dependencies``  — parsed vcpkg.json / conanfile
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from config import get_config


_IGNORE_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "docs_mirror",
    "cmake-build-debug",
    "cmake-build-release",
}


def _load_gitignore(root: Path) -> list[re.Pattern[str]]:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return []
    patterns: list[re.Pattern[str]] = []
    for raw in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # Very minimal translation: glob -> regex
        rx = re.escape(line).replace(r"\*", ".*").replace(r"\?", ".")
        patterns.append(re.compile(rx))
    return patterns


def _is_ignored(rel: str, patterns: list[re.Pattern[str]]) -> bool:
    for pat in patterns:
        if pat.search(rel):
            return True
    return False


def _walk_tree(root: Path, max_depth: int = 5) -> dict[str, Any]:
    patterns = _load_gitignore(root)

    def recurse(path: Path, depth: int) -> dict[str, Any]:
        rel = str(path.relative_to(root)) if path != root else ""
        node: dict[str, Any] = {"name": path.name or str(path), "path": rel, "type": "dir", "children": []}
        if depth >= max_depth:
            return node
        try:
            kids = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return node
        for child in kids:
            if child.name in _IGNORE_DIRS:
                continue
            child_rel = str(child.relative_to(root))
            if _is_ignored(child_rel, patterns):
                continue
            if child.is_dir():
                node["children"].append(recurse(child, depth + 1))
            else:
                try:
                    size = child.stat().st_size
                except OSError:
                    size = -1
                node["children"].append(
                    {"name": child.name, "path": child_rel, "type": "file", "size": size}
                )
        return node

    return recurse(root, 0)


# ----------------------------------------------------- build-system detection


def _detect_build_system(root: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"root": str(root), "systems": []}

    cmake_lists = root / "CMakeLists.txt"
    if cmake_lists.is_file():
        text = cmake_lists.read_text(encoding="utf-8", errors="ignore")
        project_match = re.search(r"project\s*\(\s*([A-Za-z0-9_\-]+)", text)
        targets = re.findall(r"add_(?:library|executable)\s*\(\s*([A-Za-z0-9_\-]+)", text)
        cxx_std = None
        std_match = re.search(r"CMAKE_CXX_STANDARD\s+(\d+)", text)
        if std_match:
            cxx_std = std_match.group(1)
        presets = []
        presets_file = root / "CMakePresets.json"
        if presets_file.is_file():
            try:
                data = json.loads(presets_file.read_text(encoding="utf-8"))
                presets = [p.get("name") for p in data.get("configurePresets", [])]
            except Exception:
                presets = []
        info["systems"].append(
            {
                "type": "cmake",
                "file": "CMakeLists.txt",
                "project": project_match.group(1) if project_match else None,
                "targets": targets,
                "cxx_standard": cxx_std,
                "presets": presets,
            }
        )

    meson = root / "meson.build"
    if meson.is_file():
        text = meson.read_text(encoding="utf-8", errors="ignore")
        proj = re.search(r"project\s*\(\s*'([^']+)'", text)
        info["systems"].append(
            {
                "type": "meson",
                "file": "meson.build",
                "project": proj.group(1) if proj else None,
            }
        )

    for bazel_name in ("BUILD", "BUILD.bazel"):
        bazel = root / bazel_name
        if bazel.is_file():
            info["systems"].append({"type": "bazel", "file": bazel_name})
            break

    return info


def _detect_dependencies(root: Path) -> dict[str, Any]:
    deps: dict[str, Any] = {"vcpkg": None, "conan": None}

    vcpkg_json = root / "vcpkg.json"
    if vcpkg_json.is_file():
        try:
            data = json.loads(vcpkg_json.read_text(encoding="utf-8"))
            deps["vcpkg"] = {
                "name": data.get("name"),
                "version": data.get("version")
                or data.get("version-semver")
                or data.get("version-string"),
                "dependencies": data.get("dependencies", []),
            }
        except Exception as exc:
            deps["vcpkg"] = {"error": str(exc)}

    for conan_name in ("conanfile.py", "conanfile.txt"):
        conan = root / conan_name
        if conan.is_file():
            text = conan.read_text(encoding="utf-8", errors="ignore")
            requires: list[str] = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("requires") and "=" in stripped:
                    requires.append(stripped)
                if "[requires]" in stripped:
                    requires.append(stripped)
            deps["conan"] = {"file": conan_name, "raw_requires": requires}
            break

    return deps


def _config_as_toml() -> str:
    cfg = get_config()
    lines = ["[nexcpp]"]
    for field_name in cfg.model_fields:
        value = getattr(cfg, field_name)
        if isinstance(value, Path):
            lines.append(f'{field_name} = "{value.as_posix()}"')
        elif value is None:
            lines.append(f"# {field_name} = ")
        elif isinstance(value, bool):
            lines.append(f"{field_name} = {str(value).lower()}")
        elif isinstance(value, list):
            rendered = ", ".join(f'"{v}"' for v in value)
            lines.append(f"{field_name} = [{rendered}]")
        elif isinstance(value, str):
            lines.append(f'{field_name} = "{value}"')
        else:
            lines.append(f"{field_name} = {value}")
    return "\n".join(lines) + "\n"


def register(mcp: Any) -> None:  # noqa: ANN401
    @mcp.resource("nexcpp://project/files")
    def project_files() -> str:
        """JSON tree of the current project directory."""
        return json.dumps(_walk_tree(Path.cwd()), indent=2)

    @mcp.resource("nexcpp://project/config")
    def project_config() -> str:
        """Currently-effective nexcpp configuration in TOML."""
        return _config_as_toml()

    @mcp.resource("nexcpp://project/build-system")
    def project_build_system() -> str:
        """Detected build system(s) as JSON."""
        return json.dumps(_detect_build_system(Path.cwd()), indent=2)

    @mcp.resource("nexcpp://project/dependencies")
    def project_dependencies() -> str:
        """Parsed vcpkg / Conan dependency manifest."""
        return json.dumps(_detect_dependencies(Path.cwd()), indent=2)
