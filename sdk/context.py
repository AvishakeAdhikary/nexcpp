"""PluginContext — the SDK handle passed to plugin ``register()`` callbacks.

Plugins are expected to look like:

    from sdk import PluginContext

    PLUGIN_META = {"name": "my-plugin", "version": "1.0.0", "description": "..."}

    def register(ctx: PluginContext) -> None:
        @ctx.tool(description="...")
        def my_tool(x: int) -> dict:
            return {"x": x}

A ``PluginContext`` wraps a ``FastMCP`` instance and exposes decorators that
auto-namespace plugin-registered tools/resources/prompts with the plugin's
name so that multiple plugins can ship a tool of the same short name without
clashing on the MCP wire.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP

Scope = Literal["local", "global", "sandbox", "builtin"]

_PLUGIN_LOG_PREFIX = "nexcpp.plugin"


def get_logger(plugin_name: str) -> logging.Logger:
    """Return a logger scoped to a plugin (always logs to stderr via root)."""
    return logging.getLogger(f"{_PLUGIN_LOG_PREFIX}.{plugin_name}")


class PluginContext:
    """Per-plugin SDK handle.

    Tools registered through this context get a ``<plugin_name>__<tool_name>``
    naming convention on the wire (double underscore separator). This means two
    plugins can both register e.g. a ``lint`` tool — they'll show up as
    ``alice__lint`` and ``bob__lint`` to MCP clients.
    """

    def __init__(
        self,
        mcp: FastMCP,
        scope: Scope,
        plugin_name: str,
        plugin_dir: Path,
    ) -> None:
        self._mcp = mcp
        self._scope: Scope = scope
        self._plugin_name = plugin_name
        self._plugin_dir = Path(plugin_dir)
        self.log = get_logger(plugin_name)

    # ------------------------------------------------------------------ meta

    @property
    def scope(self) -> Scope:
        return self._scope

    @property
    def plugin_name(self) -> str:
        return self._plugin_name

    @property
    def dir(self) -> Path:
        """The plugin's on-disk directory (for assets / templates)."""
        return self._plugin_dir

    @property
    def config(self) -> Any:
        """The currently-effective nexcpp config (lazy import to avoid cycles)."""
        from config import get_config

        return get_config()

    # ----------------------------------------------------------- decorators

    def _ns(self, name: str) -> str:
        # Double underscore between plugin and tool name is the namespace convention.
        return f"{self._plugin_name}__{name}"

    def tool(
        self,
        *,
        name: str | None = None,
        description: str = "",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that wraps ``@mcp.tool()`` with namespaced naming.

        Use ``name`` to override the tool's short name (default: the function
        name). The final wire name will be ``<plugin_name>__<short_name>``.
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            short = name or fn.__name__
            wire_name = self._ns(short)
            kwargs: dict[str, Any] = {"name": wire_name}
            if description:
                kwargs["description"] = description
            try:
                decorated = self._mcp.tool(**kwargs)(fn)
            except TypeError:
                # Older FastMCP that doesn't accept name/description: fall back.
                decorated = self._mcp.tool()(fn)
            self.log.debug("registered tool %s", wire_name)
            return decorated

        return decorator

    def resource(
        self,
        uri: str,
        *,
        description: str = "",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator wrapping ``@mcp.resource(uri)``.

        Resource URIs are NOT auto-namespaced — plugin authors are responsible
        for choosing a unique URI prefix (e.g. ``nexcpp://my-plugin/...``).
        """

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            kwargs: dict[str, Any] = {}
            if description:
                kwargs["description"] = description
            try:
                decorated = self._mcp.resource(uri, **kwargs)(fn)
            except TypeError:
                decorated = self._mcp.resource(uri)(fn)
            self.log.debug("registered resource %s", uri)
            return decorated

        return decorator

    def prompt(
        self,
        *,
        name: str | None = None,
        description: str = "",
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator wrapping ``@mcp.prompt()`` with namespaced naming."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            short = name or fn.__name__
            wire_name = self._ns(short)
            kwargs: dict[str, Any] = {"name": wire_name}
            if description:
                kwargs["description"] = description
            try:
                decorated = self._mcp.prompt(**kwargs)(fn)
            except TypeError:
                decorated = self._mcp.prompt()(fn)
            self.log.debug("registered prompt %s", wire_name)
            return decorated

        return decorator
