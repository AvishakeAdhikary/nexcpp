"""``nexcpp-fetch`` -- inspect and extend the bundled documentation index.

The core documentation index ships inside the package as bundled,
royalty-free original content (see :mod:`doc_index.data`). This CLI is
*optional*: it lets a user point at locally available upstream content
(cppreference HTML mirror, CMake docs checkout, vcpkg ports tree, ...)
and append the parsed entries to the runtime index.

Extensions are written to ``~/.nexcpp/extended_index.pkl`` by default
(override with ``--output`` or ``$NEXCPP_EXTENSIONS_PKL``) and are merged
on top of the bundled entries the next time the index is built.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from doc_index.index import DocEntry, DocIndex, reset_index_cache
from doc_index.parsers import cmake_docs, cppreference, vcpkg_catalog

console = Console(stderr=True)
log = logging.getLogger("nexcpp.fetch")

_PARSERS = {
    "cppreference": cppreference.parse_dir,
    "std": cppreference.parse_dir,
    "cmake": cmake_docs.parse_dir,
    "vcpkg": vcpkg_catalog.parse_dir,
}


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, show_path=False, markup=True)],
    )


def _default_extension_path() -> Path:
    override = os.environ.get("NEXCPP_EXTENSIONS_PKL")
    if override:
        return Path(override)
    return Path.home() / ".nexcpp" / "extended_index.pkl"


def _load_existing_extensions(path: Path) -> list[DocEntry]:
    return DocIndex.load_entries_from_pickle(path)


def _save_extensions(path: Path, entries: list[DocEntry]) -> None:
    idx = DocIndex()
    idx.build_from_parsed(entries)
    idx.save(path)


# ------------------------------------------------------------------- CLI


@click.group(help="Inspect and extend the bundled C++ documentation index.")
def cli() -> None:
    _configure_logging()


@cli.command("info", help="Print bundled-index statistics: total entries and entries per source.")
def cmd_info() -> None:
    from doc_index.data import load_all

    bundled = load_all()
    by_source: dict[str, int] = {}
    for entry in bundled:
        by_source[entry.source] = by_source.get(entry.source, 0) + 1
    total = len(bundled)
    console.print(f"[bold]nexcpp bundled documentation index[/]: {total} entries")
    for source in sorted(by_source):
        console.print(f"  {source:<10} {by_source[source]}")
    ext_path = _default_extension_path()
    if ext_path.is_file():
        ext = _load_existing_extensions(ext_path)
        console.print(f"\nExtensions at [bold]{ext_path}[/]: {len(ext)} entries")
    else:
        console.print(f"\nNo extensions at {ext_path}")


@cli.command(
    "extend",
    help=(
        "Parse a local directory of upstream content (cppreference HTML mirror, "
        "CMake docs checkout, vcpkg ports tree, ...) and append the parsed entries "
        "to the user extension pickle."
    ),
)
@click.argument("source", type=click.Choice(sorted(_PARSERS.keys())))
@click.option(
    "--input-dir",
    "input_dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Local directory whose files will be parsed for entries.",
)
@click.option(
    "--output",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Where to write the extension pickle (default: ~/.nexcpp/extended_index.pkl).",
)
@click.option(
    "--replace",
    is_flag=True,
    help="Replace the existing extension pickle instead of merging into it.",
)
def cmd_extend(source: str, input_dir: Path, output: Path | None, replace: bool) -> None:
    if not input_dir.is_dir():
        console.print(f"[red]--input-dir does not exist:[/] {input_dir}")
        sys.exit(2)
    parser = _PARSERS[source]
    new_entries = parser(input_dir)
    if not new_entries:
        console.print(
            f"[yellow]No entries parsed from {input_dir} for source '{source}'.[/] "
            "Nothing to do."
        )
        sys.exit(1)
    out_path = output or _default_extension_path()
    existing = [] if replace else _load_existing_extensions(out_path)
    merged: dict[str, DocEntry] = {entry.symbol: entry for entry in existing}
    for entry in new_entries:
        merged[entry.symbol] = entry
    _save_extensions(out_path, list(merged.values()))
    reset_index_cache()
    console.print(
        f"[green]wrote[/] {out_path}: {len(merged)} entries "
        f"(+{len(new_entries)} parsed)"
    )


@cli.command("clear-extensions", help="Remove the extension pickle, returning to bundled-only docs.")
@click.option(
    "--output",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
    default=None,
    help="Path of the extension pickle to remove (default: ~/.nexcpp/extended_index.pkl).",
)
def cmd_clear(output: Path | None) -> None:
    path = output or _default_extension_path()
    if path.is_file():
        path.unlink()
        reset_index_cache()
        console.print(f"[green]removed[/] {path}")
    else:
        console.print(f"No extensions at {path}; nothing to do.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
