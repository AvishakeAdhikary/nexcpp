"""Sandbox subpackage: local + docker compile/run/build helpers."""

from __future__ import annotations

from sandbox.quick import compile_and_run

# Lazy re-exports for docker and pipeline (avoid heavy imports if unused).

__all__ = [
    "compile_and_run",
    "run_build",
    "run_local_build",
    "run_snippet",
]


def __getattr__(name: str):
    if name == "run_local_build":
        from sandbox.pipeline import run_local_build

        return run_local_build
    if name == "run_build":
        from sandbox.docker_sandbox import run_build

        return run_build
    if name == "run_snippet":
        from sandbox.docker_sandbox import run_snippet

        return run_snippet
    raise AttributeError(f"module 'sandbox' has no attribute {name!r}")
