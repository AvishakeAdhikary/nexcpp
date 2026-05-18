"""nexcpp — Model Context Protocol server for C++ tooling intelligence.

Launches a FastMCP server that exposes:

* Tools     — search_cpp_docs, manage_file, build_project, run_snippet,
              analyze_code, generate_package, generate_bridge, github_op
* Resources — nexcpp://docs/*, nexcpp://project/*, nexcpp://build/*
* Prompts   — cpp_library_scaffold, cmake_error_fix, vcpkg_port_authoring,
              pybind11_binding, github_release, sanitizer_debug

Modules are loaded lazily via a ``register(mcp)`` contract so each agent
stream can ship independently — missing modules are reported on stderr
and skipped (the server still boots).
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

# IMPORTANT: under stdio transport stdout is reserved for JSON-RPC.
# All human-readable output goes to stderr.
_STDERR_CONSOLE = Console(stderr=True)

log = logging.getLogger("nexcpp")


def _configure_logging(level: int = logging.INFO) -> None:
    handler = RichHandler(
        console=_STDERR_CONSOLE,
        show_time=True,
        show_path=False,
        markup=True,
    )
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[handler],
        force=True,
    )


def _build_argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexcpp",
        description=(
            "nexcpp — MCP server giving AI agents deep C++ tooling intelligence."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "sse"),
        default="stdio",
        help="MCP transport (default: stdio).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7777,
        help="Port for SSE transport (default: 7777). Ignored for stdio.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for SSE transport (default: 127.0.0.1). Ignored for stdio.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to a config TOML (default: ./.nexcpp/config.toml).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity (stderr only).",
    )
    return parser


def _try_register(mcp, target: str) -> None:
    """Import ``target.register`` and call it. Log and skip on failure."""
    try:
        module = __import__(target, fromlist=["register"])
    except ImportError as exc:
        log.warning("skipping %s (not available yet): %s", target, exc)
        return
    register = getattr(module, "register", None)
    if register is None:
        log.warning("skipping %s (no register())", target)
        return
    try:
        register(mcp)
        log.info("registered %s", target)
    except Exception as exc:  # pragma: no cover - registration faults
        log.exception("registration failed for %s: %s", target, exc)


def _try_plugin_loader(mcp) -> None:
    try:
        module = __import__("plugins.loader", fromlist=["load_all"])
    except ImportError as exc:
        log.info("plugin loader not available: %s", exc)
        return
    load_all = getattr(module, "load_all", None)
    if load_all is None:
        log.info("plugin loader missing load_all()")
        return
    try:
        load_all(mcp)
        log.info("plugins loaded")
    except Exception as exc:  # pragma: no cover
        log.exception("plugin loading failed: %s", exc)


def create_server():
    """Construct and populate the FastMCP server instance."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "The 'mcp' package is required. Install it with: uv sync (or pip install 'mcp[cli]>=1.2.0')."
        ) from exc

    mcp = FastMCP("nexcpp")

    # Tools
    _try_register(mcp, "tools.docs")
    _try_register(mcp, "tools.files")
    _try_register(mcp, "tools.build")
    _try_register(mcp, "tools.analyze")
    _try_register(mcp, "tools.generate")
    _try_register(mcp, "tools.github")

    # Resources
    _try_register(mcp, "resources.cpp_docs")
    _try_register(mcp, "resources.project")
    _try_register(mcp, "resources.build_log")

    # Prompts
    _try_register(mcp, "prompts.scaffold")
    _try_register(mcp, "prompts.cmake")
    _try_register(mcp, "prompts.vcpkg")
    _try_register(mcp, "prompts.bridge")

    # Plugins (external)
    _try_plugin_loader(mcp)

    return mcp


def _install_signal_handlers() -> None:
    """Translate SIGINT/SIGTERM (and SIGBREAK on Windows) into KeyboardInterrupt.

    Windows lacks a Unix-style SIGTERM; we guard with ``hasattr``. SIGBREAK
    is the rough Ctrl-Break equivalent on Windows console apps.
    """

    def _raise_interrupt(signum: int, _frame: Any) -> None:
        log.info("received signal %s; shutting down nexcpp...", signum)
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGINT, _raise_interrupt)
    except (ValueError, OSError) as exc:  # not in main thread, etc.
        log.debug("could not install SIGINT handler: %s", exc)
    if hasattr(signal, "SIGTERM"):
        try:
            signal.signal(signal.SIGTERM, _raise_interrupt)
        except (ValueError, OSError) as exc:
            log.debug("could not install SIGTERM handler: %s", exc)
    if hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, _raise_interrupt)  # type: ignore[attr-defined]
        except (ValueError, OSError) as exc:
            log.debug("could not install SIGBREAK handler: %s", exc)


def main(argv: list[str] | None = None) -> int:
    parser = _build_argparser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(logging, args.log_level))

    if args.config is not None:
        # Pre-populate the config cache with the explicit file.
        try:
            from config import get_config, load_config

            cfg = load_config(args.config)
            get_config.cache_clear()
            # cache the value
            import config as _cfg_module

            _cfg_module.get_config = lambda _c=cfg: _c  # type: ignore[assignment]
            log.info("loaded config from %s", args.config)
        except Exception as exc:
            log.error("failed to load --config %s: %s", args.config, exc)

    _install_signal_handlers()

    try:
        mcp = create_server()
    except Exception as exc:
        log.exception("failed to create MCP server: %s", exc)
        return 1

    try:
        if args.transport == "stdio":
            log.info("nexcpp listening on stdio (use --transport sse for HTTP).")
            mcp.run(transport="stdio")
        else:
            # FastMCP exposes host/port through settings.
            try:
                mcp.settings.host = args.host  # type: ignore[attr-defined]
                mcp.settings.port = args.port  # type: ignore[attr-defined]
            except AttributeError:
                pass
            log.info("nexcpp listening on SSE %s:%s", args.host, args.port)
            mcp.run(transport="sse")
    except KeyboardInterrupt:
        log.info("shutting down nexcpp...")
        return 0
    except SystemExit as exc:
        # uvicorn calls sys.exit on SIGINT; propagate the code.
        log.info("shutting down nexcpp (exit %s)...", exc.code)
        return int(exc.code) if isinstance(exc.code, int) else 0
    except Exception as exc:
        log.exception("nexcpp terminated with unhandled exception: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
