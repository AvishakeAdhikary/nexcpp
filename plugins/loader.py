"""Plugin discovery & loading across 3 scopes.

Discovery order (highest priority first):

1. **Local**:   ``./.nexcpp/plugins/``  — project-specific overrides
2. **Global**:  ``~/.nexcpp/plugins/``  — user-installed plugins
3. **Sandbox**: ``/tmp/nexcpp-sandbox-*/plugins/`` — ephemeral throw-away plugins

Built-in plugins under :mod:`plugins.builtin` ALWAYS load (lowest precedence
in the sense that they cannot be shadowed by name, but they cannot be
disabled either).

Each plugin is either:

* a single ``.py`` file with ``register(ctx)`` (and optional ``PLUGIN_META``)
* a package directory with ``__init__.py`` exposing ``register(ctx)``

De-duplication uses ``PLUGIN_META["name"]`` (falling back to filename
stem). When the same name appears in multiple scopes, the highest-priority
scope wins and the others are skipped (their entries appear in ``errors``
with a ``shadowed_by`` note for debuggability).
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import tempfile
import traceback
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from sdk import PluginContext
from sdk.context import Scope

if TYPE_CHECKING:  # pragma: no cover
    pass

log = logging.getLogger(__name__)


def _scope_dirs() -> list[tuple[Scope, Path]]:
    """Return the (scope, directory) pairs to scan, ordered by priority."""
    out: list[tuple[Scope, Path]] = []
    local = Path.cwd() / ".nexcpp" / "plugins"
    out.append(("local", local))
    global_dir = Path.home() / ".nexcpp" / "plugins"
    out.append(("global", global_dir))
    # Sandbox: any directory under the OS temp dir matching the pattern.
    tmp_root = Path(tempfile.gettempdir())
    try:
        for candidate in sorted(tmp_root.glob("nexcpp-sandbox-*")):
            plugins_dir = candidate / "plugins"
            if plugins_dir.is_dir():
                out.append(("sandbox", plugins_dir))
    except OSError:
        pass
    return out


def _iter_plugin_paths(directory: Path) -> list[Path]:
    """Yield candidate plugin paths in a directory (files + sub-packages)."""
    if not directory.is_dir():
        return []
    out: list[Path] = []
    try:
        entries = sorted(directory.iterdir())
    except OSError:
        return []
    for entry in entries:
        if entry.name.startswith((".", "_")):
            continue
        if (entry.is_file() and entry.suffix == ".py") or (entry.is_dir() and (entry / "__init__.py").is_file()):
            out.append(entry)
    return out


def _load_module_from_path(path: Path, module_name: str) -> ModuleType:
    """Load a module from ``path`` without polluting ``sys.path``."""
    if path.is_dir():
        init_path = path / "__init__.py"
        spec = importlib.util.spec_from_file_location(
            module_name,
            init_path,
            submodule_search_locations=[str(path)],
        )
    else:
        spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    # Stash in sys.modules so relative imports inside the plugin work.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _plugin_name(module: ModuleType, path: Path) -> str:
    meta = getattr(module, "PLUGIN_META", None)
    if isinstance(meta, dict):
        n = meta.get("name")
        if isinstance(n, str) and n:
            return n
    return path.stem if path.is_file() else path.name


def _register(
    mcp: Any,
    module: ModuleType,
    *,
    scope: Scope,
    plugin_name: str,
    plugin_dir: Path,
) -> None:
    register_fn = getattr(module, "register", None)
    if register_fn is None:
        raise AttributeError(f"plugin {plugin_name!r} has no register() function")
    ctx = PluginContext(mcp=mcp, scope=scope, plugin_name=plugin_name, plugin_dir=plugin_dir)
    register_fn(ctx)


def _safe_module_id(scope: Scope, name: str) -> str:
    safe = name.replace("-", "_").replace(" ", "_")
    return f"nexcpp_plugin_{scope}_{safe}"


# ----------------------------------------------------------- builtin loader


def _load_builtins(mcp: Any, loaded: list[dict[str, Any]], errors: list[dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    builtin_dir = Path(__file__).parent / "builtin"
    if not builtin_dir.is_dir():
        return seen
    for entry in sorted(builtin_dir.iterdir()):
        if entry.name.startswith(("_", ".")):
            continue
        if entry.suffix != ".py" and not (entry.is_dir() and (entry / "__init__.py").is_file()):
            continue
        try:
            module_id = f"plugins.builtin.{entry.stem}"
            module = importlib.import_module(module_id)
            name = _plugin_name(module, entry)
            _register(
                mcp,
                module,
                scope="builtin",
                plugin_name=name,
                plugin_dir=Path(getattr(module, "__file__", entry)).parent,
            )
            loaded.append({"name": name, "scope": "builtin", "path": str(entry)})
            seen.add(name)
        except Exception as exc:
            errors.append(
                {
                    "name": entry.stem,
                    "scope": "builtin",
                    "path": str(entry),
                    "error": f"{exc.__class__.__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                }
            )
    return seen


# --------------------------------------------------------------- public API


def load_all(mcp: Any) -> dict[str, Any]:
    """Discover and load all available plugins.

    Returns a dict ``{"loaded": [...], "errors": [...]}`` where each loaded
    entry is ``{"name", "scope", "path"}`` and each error additionally has
    an ``"error"`` (and ``"traceback"``) field.

    Hot-reload support is intentionally out of scope here; a future
    implementation could watch each scope directory with ``watchdog`` and
    call back into ``_load_builtins`` / per-scope reload helpers.
    """
    loaded: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    # 1. Built-ins always load first so their names are claimed before scoped
    #    plugins try to register the same name.
    seen = _load_builtins(mcp, loaded, errors)

    # 2. Walk the scopes in priority order. Local > global > sandbox.
    for scope, directory in _scope_dirs():
        for path in _iter_plugin_paths(directory):
            # Default name from filename; refined to PLUGIN_META["name"]
            # once the module is loaded.
            name = path.stem if path.is_file() else path.name
            try:
                module_id = _safe_module_id(scope, name)
                module = _load_module_from_path(path, module_id)
                name = _plugin_name(module, path)
                if name in seen:
                    errors.append(
                        {
                            "name": name,
                            "scope": scope,
                            "path": str(path),
                            "error": "shadowed by higher-priority scope",
                            "shadowed": True,
                        }
                    )
                    continue
                plugin_dir = path if path.is_dir() else path.parent
                _register(
                    mcp,
                    module,
                    scope=scope,
                    plugin_name=name,
                    plugin_dir=plugin_dir,
                )
                loaded.append({"name": name, "scope": scope, "path": str(path)})
                seen.add(name)
            except Exception as exc:
                errors.append(
                    {
                        "name": name,
                        "scope": scope,
                        "path": str(path),
                        "error": f"{exc.__class__.__name__}: {exc}",
                        "traceback": traceback.format_exc(),
                    }
                )
                log.warning("plugin failed: %s (%s)", path, exc)

    log.info("plugin load summary: %d loaded, %d errors", len(loaded), len(errors))
    return {"loaded": loaded, "errors": errors}
