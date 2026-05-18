"""Thin wrapper around PyGithub for the ``github_op`` tool.

All methods catch :class:`github.GithubException` and surface
``{"ok": False, "error": ...}`` rather than raising. Construction is
deferred — ``GhClient(token=None)`` is OK; auth-required methods will
return a clear error.
"""

from __future__ import annotations

import importlib
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal

log = logging.getLogger(__name__)


def _load_pygithub() -> dict[str, Any] | None:
    """Import the real PyGithub package, dodging our own ``github`` package.

    The local ``github/`` directory shadows the PyPI ``github`` distribution
    in :data:`sys.modules`. We temporarily remove our entry, import the
    real one, then restore ours.
    """
    sentinel = sys.modules.get("github")
    sentinel_client = sys.modules.get("github.client")
    # Path manipulation: drop our cwd entries that would re-shadow.
    saved_path = list(sys.path)
    here = str(Path(__file__).resolve().parent.parent)
    pruned_path = [p for p in saved_path if Path(p).resolve() != Path(here).resolve()]
    try:
        sys.path[:] = pruned_path
        sys.modules.pop("github", None)
        try:
            pyg = importlib.import_module("github")
        except ImportError:
            return None
        if not hasattr(pyg, "Github"):
            # Our own package was re-imported; PyGithub really is missing.
            return None
        return {
            "Github": pyg.Github,
            "Auth": importlib.import_module("github.Auth"),
            "GithubException": importlib.import_module("github.GithubException").GithubException,
        }
    finally:
        sys.path[:] = saved_path
        if sentinel is not None:
            sys.modules["github"] = sentinel
        if sentinel_client is not None:
            sys.modules["github.client"] = sentinel_client


class GhClient:
    """Lazy PyGithub wrapper with structured-error returns."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token
        self._gh: Any | None = None

    # ----------------------------------------------------------- internals

    def _client(self) -> Any:
        if self._gh is not None:
            return self._gh
        pyg = _load_pygithub()
        if pyg is None:
            raise RuntimeError(
                "PyGithub is required. Install via: pip install PyGithub"
            )
        Github = pyg["Github"]
        Auth = pyg["Auth"]
        if self._token:
            self._gh = Github(auth=Auth.Token(self._token))
        else:
            self._gh = Github()
        return self._gh

    def _require_token(self) -> dict[str, Any] | None:
        if not self._token:
            return {"ok": False, "error": "NEXCPP_GITHUB_TOKEN not set"}
        return None

    def _safe(self, fn, *args, **kwargs) -> dict[str, Any]:
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            pyg = _load_pygithub()
            if pyg is not None and isinstance(exc, pyg["GithubException"]):
                msg = f"{exc.status}: {exc.data}"
            else:
                msg = f"{type(exc).__name__}: {exc}"
            log.error("github op failed: %s", msg)
            return {"ok": False, "error": msg}

    # ----------------------------------------------------------- ops

    def create_repo(
        self,
        name: str,
        *,
        private: bool = False,
        description: str = "",
        auto_init: bool = True,
    ) -> dict[str, Any]:
        if (err := self._require_token()):
            return err

        def _do() -> dict[str, Any]:
            user = self._client().get_user()
            repo = user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=auto_init,
            )
            return {
                "ok": True,
                "name": repo.name,
                "full_name": repo.full_name,
                "html_url": repo.html_url,
                "ssh_url": repo.ssh_url,
                "url": repo.html_url,
            }

        return self._safe(_do)

    def open_pr(
        self,
        repo: str,
        *,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any]:
        if (err := self._require_token()):
            return err

        def _do() -> dict[str, Any]:
            r = self._client().get_repo(repo)
            pr = r.create_pull(title=title, body=body, head=head, base=base)
            return {
                "ok": True,
                "number": pr.number,
                "html_url": pr.html_url,
                "url": pr.html_url,
            }

        return self._safe(_do)

    def create_issue(
        self,
        repo: str,
        *,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        if (err := self._require_token()):
            return err

        def _do() -> dict[str, Any]:
            r = self._client().get_repo(repo)
            issue = r.create_issue(title=title, body=body, labels=labels or [])
            return {
                "ok": True,
                "number": issue.number,
                "html_url": issue.html_url,
                "url": issue.html_url,
            }

        return self._safe(_do)

    def create_release(
        self,
        repo: str,
        *,
        tag: str,
        name: str | None = None,
        body: str = "",
        draft: bool = False,
        prerelease: bool = False,
    ) -> dict[str, Any]:
        if (err := self._require_token()):
            return err

        def _do() -> dict[str, Any]:
            r = self._client().get_repo(repo)
            rel = r.create_git_release(
                tag=tag,
                name=name or tag,
                message=body,
                draft=draft,
                prerelease=prerelease,
            )
            return {
                "ok": True,
                "id": rel.id,
                "tag_name": rel.tag_name,
                "html_url": rel.html_url,
                "url": rel.html_url,
            }

        return self._safe(_do)

    def push(
        self,
        repo_dir: str | Path,
        *,
        branch: str | None = None,
        remote: str = "origin",
    ) -> dict[str, Any]:
        def _do() -> dict[str, Any]:
            try:
                import git
            except ImportError as exc:  # pragma: no cover
                return {"ok": False, "error": f"gitpython required: {exc}"}

            repo_path = Path(repo_dir).expanduser().resolve()
            if not (repo_path / ".git").exists():
                return {"ok": False, "error": f"not a git repo: {repo_path}"}

            r = git.Repo(repo_path)
            br = branch or r.active_branch.name
            try:
                info = r.remote(remote).push(refspec=f"{br}:{br}")
            except git.GitCommandError as exc:
                return {"ok": False, "error": str(exc)}
            summary = [str(item) for item in info]
            sha = r.head.commit.hexsha
            return {"ok": True, "branch": br, "sha": sha, "summary": summary}

        return self._safe(_do)

    def publish_package(
        self,
        repo: str,
        *,
        registry: Literal["vcpkg", "conan"] = "vcpkg",
        port_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        if registry == "vcpkg":
            return self._publish_vcpkg(repo=repo, port_dir=port_dir)
        if registry == "conan":
            return self._publish_conan(remote=repo, port_dir=port_dir)
        return {"ok": False, "error": f"unknown registry: {registry}"}

    def _publish_conan(
        self,
        *,
        remote: str | None,
        port_dir: str | Path | None,
    ) -> dict[str, Any]:
        if port_dir is None:
            return {"ok": False, "error": "port_dir is required for conan publish"}
        port_path = Path(port_dir).expanduser().resolve()
        if not port_path.is_dir():
            return {"ok": False, "error": f"port_dir not a directory: {port_path}"}
        recipe_file = port_path / "conanfile.py"
        if not recipe_file.is_file():
            return {
                "ok": False,
                "error": f"missing conanfile.py in {port_path}",
            }

        if shutil.which("conan") is None:
            return {
                "ok": False,
                "error": (
                    "conan CLI not found in PATH. Install with: pip install conan>=2.0"
                ),
            }

        try:
            create_proc = subprocess.run(
                ["conan", "create", "."],
                cwd=str(port_path),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=600,
            )
        except subprocess.TimeoutExpired as exc:
            return {"ok": False, "error": f"conan create timed out: {exc}"}
        except OSError as exc:
            return {"ok": False, "error": f"conan create failed: {exc}"}

        create_log = (create_proc.stdout or "") + (create_proc.stderr or "")
        if create_proc.returncode != 0:
            return {
                "ok": False,
                "error": f"conan create exited {create_proc.returncode}",
                "create_log": create_log,
            }

        recipe_text = recipe_file.read_text(encoding="utf-8", errors="replace")
        name_match = re.search(r"""name\s*=\s*["']([^"']+)["']""", recipe_text)
        version_match = re.search(r"""version\s*=\s*["']([^"']+)["']""", recipe_text)
        if not name_match:
            return {
                "ok": False,
                "error": "could not parse recipe name from conanfile.py",
                "create_log": create_log,
            }
        recipe_name = name_match.group(1)
        recipe_version = version_match.group(1) if version_match else "latest"
        recipe_ref = f"{recipe_name}/{recipe_version}"

        upload_log = ""
        if remote:
            try:
                upload_proc = subprocess.run(
                    ["conan", "upload", recipe_ref, "-r", remote, "--confirm"],
                    cwd=str(port_path),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=600,
                )
            except subprocess.TimeoutExpired as exc:
                return {
                    "ok": False,
                    "error": f"conan upload timed out: {exc}",
                    "create_log": create_log,
                }
            except OSError as exc:
                return {
                    "ok": False,
                    "error": f"conan upload failed: {exc}",
                    "create_log": create_log,
                }
            upload_log = (upload_proc.stdout or "") + (upload_proc.stderr or "")
            if upload_proc.returncode != 0:
                return {
                    "ok": False,
                    "error": f"conan upload exited {upload_proc.returncode}",
                    "create_log": create_log,
                    "upload_log": upload_log,
                }

        return {
            "ok": True,
            "registry": "conan",
            "recipe": recipe_ref,
            "create_log": create_log,
            "upload_log": upload_log,
        }

    def _publish_vcpkg(
        self,
        *,
        repo: str,
        port_dir: str | Path | None,
    ) -> dict[str, Any]:
        if (err := self._require_token()):
            return err
        if port_dir is None:
            return {"ok": False, "error": "port_dir is required for vcpkg publish"}
        port_path = Path(port_dir).expanduser().resolve()
        if not port_path.is_dir():
            return {"ok": False, "error": f"port_dir not a directory: {port_path}"}

        try:
            import git
        except ImportError as exc:  # pragma: no cover
            return {"ok": False, "error": f"gitpython required: {exc}"}

        def _do() -> dict[str, Any]:
            gh = self._client()
            user = gh.get_user()
            user_login = user.login

            # Fork microsoft/vcpkg if not already forked
            try:
                upstream = gh.get_repo("microsoft/vcpkg")
                fork = user.create_fork(upstream)
            except Exception as exc:
                return {"ok": False, "error": f"fork failed: {exc}"}

            # Clone fork to temp dir, copy port files, commit, push, open PR
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                workdir = Path(tmp) / "vcpkg-fork"
                clone_url = fork.clone_url.replace(
                    "https://", f"https://{self._token}@"
                )
                git.Repo.clone_from(clone_url, workdir, depth=1)
                r = git.Repo(workdir)

                port_name = port_path.name
                dest = workdir / "ports" / port_name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(port_path, dest)

                branch_name = f"port/{port_name}"
                r.git.checkout("-B", branch_name)
                r.git.add("ports")
                r.index.commit(f"[{port_name}] add new port")
                r.remote("origin").push(refspec=f"{branch_name}:{branch_name}")

                # Open PR upstream
                pr = upstream.create_pull(
                    title=f"[{port_name}] add new port",
                    body=(
                        f"Adds a new vcpkg port for `{port_name}`.\n\n"
                        "Generated by nexcpp."
                    ),
                    head=f"{user_login}:{branch_name}",
                    base="master",
                )
                return {
                    "ok": True,
                    "number": pr.number,
                    "html_url": pr.html_url,
                    "url": pr.html_url,
                    "registry": "vcpkg",
                }

        return self._safe(_do)


__all__ = ["GhClient"]
