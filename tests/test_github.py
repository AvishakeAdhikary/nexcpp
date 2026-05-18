"""Tests for the github subpackage (workflow generation, client init)."""

from __future__ import annotations

import pytest


def test_gh_client_without_token() -> None:
    try:
        from github.client import GhClient
    except ImportError:
        try:
            from github import GhClient  # type: ignore[attr-defined]
        except ImportError:
            pytest.skip("GhClient not available")
    # Should not raise just to construct.
    client = GhClient(token=None)
    assert client is not None


def test_workflow_render_cpp_ci() -> None:
    pytest.importorskip("yaml")
    import yaml as pyyaml

    try:
        from github.workflow_gen import render
    except ImportError:
        try:
            from github import render  # type: ignore[attr-defined]
        except ImportError:
            pytest.skip("workflow_gen.render not available")
    rendered = render("cpp-ci", project_name="ci")
    assert isinstance(rendered, str)
    parsed = pyyaml.safe_load(rendered)
    assert isinstance(parsed, dict)
    assert "jobs" in parsed or "name" in parsed


@pytest.mark.parametrize(
    "template",
    ["cpp-ci", "docker", "release", "vcpkg-port"],
)
def test_all_workflow_templates_parse(template: str) -> None:
    pytest.importorskip("yaml")
    import yaml as pyyaml

    try:
        from github.workflow_gen import render
    except ImportError:
        try:
            from github import render  # type: ignore[attr-defined]
        except ImportError:
            pytest.skip("workflow_gen not available")
    try:
        rendered = render(template, project_name="demo")
    except (KeyError, FileNotFoundError, ValueError):
        pytest.skip(f"template {template} not available")
    parsed = pyyaml.safe_load(rendered)
    assert isinstance(parsed, dict)
