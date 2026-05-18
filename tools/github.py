"""``github_op`` MCP tool: thin dispatcher over ``github.client.GhClient``.

Builds the GitHub client lazily so the tool registers even when the
``PyGithub`` package is missing — auth-required ops just return a clean
error in that case.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import Field

log = logging.getLogger(__name__)

Op = Literal[
    "create_repo",
    "open_pr",
    "create_issue",
    "create_release",
    "push",
    "generate_workflow",
    "publish_package",
]


def _build_client() -> tuple[Any | None, str | None]:
    """Return (client, error). Either the client or a stringified error."""
    try:
        from config import get_config

        token = get_config().github_token
    except Exception as exc:
        return None, f"config load failed: {exc}"

    try:
        from github.client import GhClient
    except ImportError as exc:
        return None, f"github client unavailable: {exc}"

    return GhClient(token=token), None


def register(mcp: Any) -> None:
    @mcp.tool()
    def github_op(
        op: Op = Field(..., description="GitHub operation to perform."),
        repo: str | None = Field(
            None, description="owner/repo. Required for most ops except create_repo."
        ),
        title: str | None = Field(None, description="PR/issue/release title."),
        body: str | None = Field(None, description="PR/issue/release body."),
        tag: str | None = Field(None, description="Release tag (e.g. v0.1.0)."),
        branch: str | None = Field(None, description="Branch for push op."),
        head: str | None = Field(None, description="PR head branch."),
        base: str = Field("main", description="PR base branch."),
        private: bool = Field(False, description="create_repo: private?"),
        workflow_template: str | None = Field(
            None,
            description=(
                "generate_workflow: one of "
                "'cpp-ci', 'docker', 'release', 'vcpkg-port'."
            ),
        ),
        registry: Literal["vcpkg", "conan"] = Field(
            "vcpkg", description="publish_package: target registry."
        ),
        port_dir: str | None = Field(
            None, description="publish_package: local port directory for vcpkg."
        ),
        repo_dir: str | None = Field(
            None, description="push: local git checkout."
        ),
        labels: list[str] | None = Field(
            None, description="create_issue: labels to apply."
        ),
        description: str | None = Field(
            None, description="create_repo: repo description."
        ),
        workflow_kwargs: dict[str, Any] | None = Field(
            None,
            description=(
                "generate_workflow: extra kwargs forwarded to the template "
                "(cpp_std, package_managers, sanitizers, etc.)."
            ),
        ),
    ) -> dict[str, Any]:
        """Dispatch a GitHub operation.

        Returns ``{ok, ...}``; on auth-required ops without a token,
        returns ``{ok:false, error:"NEXCPP_GITHUB_TOKEN not set"}``.
        """
        # generate_workflow needs no auth.
        if op == "generate_workflow":
            if not workflow_template:
                return {"ok": False, "error": "workflow_template required"}
            try:
                from github.workflow_gen import render
            except ImportError as exc:
                return {"ok": False, "error": f"workflow_gen unavailable: {exc}"}
            try:
                yaml_text = render(workflow_template, **(workflow_kwargs or {}))
            except (ValueError, Exception) as exc:
                log.exception("workflow render failed")
                return {"ok": False, "error": f"render failed: {exc}"}
            return {
                "ok": True,
                "workflow_yaml": yaml_text,
                "template": workflow_template,
            }

        client, err = _build_client()
        if err is not None or client is None:
            return {"ok": False, "error": err or "client unavailable"}

        if op == "create_repo":
            if not repo:
                return {"ok": False, "error": "repo (the new repo name) is required"}
            # For create_repo, `repo` is treated as the bare name.
            return client.create_repo(
                name=repo,
                private=private,
                description=description or "",
            )

        if op == "open_pr":
            if not (repo and title and head):
                return {"ok": False, "error": "repo, title, head required"}
            return client.open_pr(
                repo=repo, title=title, body=body or "", head=head, base=base
            )

        if op == "create_issue":
            if not (repo and title):
                return {"ok": False, "error": "repo and title required"}
            return client.create_issue(
                repo=repo, title=title, body=body or "", labels=labels
            )

        if op == "create_release":
            if not (repo and tag):
                return {"ok": False, "error": "repo and tag required"}
            return client.create_release(
                repo=repo, tag=tag, name=title, body=body or ""
            )

        if op == "push":
            target_dir = repo_dir or "."
            return client.push(target_dir, branch=branch)

        if op == "publish_package":
            if not repo:
                return {"ok": False, "error": "repo required"}
            return client.publish_package(
                repo=repo, registry=registry, port_dir=port_dir
            )

        return {"ok": False, "error": f"unknown op: {op}"}
