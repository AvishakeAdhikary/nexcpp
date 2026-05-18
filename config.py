"""Configuration loader for nexcpp.

Loads ``.nexcpp/config.toml`` from the current working directory and
``~/.nexcpp/config.toml`` for global defaults. Project config wins on key
collisions. Provides a cached :func:`get_config` accessor used by tools,
resources, and the plugin loader.
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - py<3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]

from pydantic import BaseModel, Field

PROJECT_CONFIG_RELATIVE = Path(".nexcpp") / "config.toml"
GLOBAL_CONFIG_PATH = Path.home() / ".nexcpp" / "config.toml"


class NexcppConfig(BaseModel):
    """Server-wide configuration."""

    docs_mirror_path: Path = Field(
        default_factory=lambda: Path.cwd() / "docs_mirror",
        description="Where the offline docs index lives.",
    )
    vcpkg_root: Path | None = Field(
        default=None,
        description="Path to a local vcpkg checkout (else $VCPKG_ROOT).",
    )
    github_token: str | None = Field(
        default=None,
        description="GitHub PAT for github_op tool. Env: NEXCPP_GITHUB_TOKEN.",
    )
    sandbox_default: bool = Field(
        default=False,
        description="Default value for tool 'sandbox' parameter.",
    )
    file_allowlist: list[Path] = Field(
        default_factory=list,
        description="Absolute paths outside cwd that manage_file may touch.",
    )
    plugins: list[str] = Field(
        default_factory=list,
        description="Plugin module names to load (in addition to scope discovery).",
    )

    project_root: Path = Field(
        default_factory=Path.cwd,
        description="Project root the server was launched in.",
    )

    model_config = {"arbitrary_types_allowed": True}


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _flatten(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept either ``[nexcpp]`` table or flat keys."""
    if "nexcpp" in raw and isinstance(raw["nexcpp"], dict):
        merged = dict(raw["nexcpp"])
        # preserve plugins table if separate
        if "plugins" in raw and isinstance(raw["plugins"], dict):
            merged.setdefault("plugins", list(raw["plugins"].keys()))
        return merged
    return raw


def load_config(explicit_path: Path | None = None) -> NexcppConfig:
    """Load configuration. ``explicit_path`` overrides default lookup."""

    if explicit_path is not None:
        data = _flatten(_load_toml(explicit_path))
    else:
        global_data = _flatten(_load_toml(GLOBAL_CONFIG_PATH))
        project_data = _flatten(_load_toml(Path.cwd() / PROJECT_CONFIG_RELATIVE))
        data = _merge(global_data, project_data)

    # Env overrides
    env_token = os.environ.get("NEXCPP_GITHUB_TOKEN")
    if env_token and not data.get("github_token"):
        data["github_token"] = env_token

    env_vcpkg = os.environ.get("VCPKG_ROOT")
    if env_vcpkg and not data.get("vcpkg_root"):
        data["vcpkg_root"] = env_vcpkg

    # Coerce path-like strings
    for key in ("docs_mirror_path", "vcpkg_root", "project_root"):
        if isinstance(data.get(key), str):
            data[key] = Path(data[key]).expanduser()

    if "file_allowlist" in data and isinstance(data["file_allowlist"], list):
        data["file_allowlist"] = [Path(p).expanduser() for p in data["file_allowlist"]]

    return NexcppConfig(**data)


@lru_cache(maxsize=1)
def get_config() -> NexcppConfig:
    """Cached accessor. Reset with :func:`reset_config_cache`."""
    return load_config()


def reset_config_cache() -> None:
    """Clear cached config (mainly for tests)."""
    get_config.cache_clear()
