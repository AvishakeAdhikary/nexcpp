"""Docker-backed build and snippet runners.

These functions defer importing ``docker`` until called so that the
package is fully importable even when the docker SDK or daemon is not
available.
"""

from __future__ import annotations

import contextlib
import logging
import shlex
import tempfile
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_BUILD_IMAGE = "nexcpp/build-linux"

# Container limits — conservative defaults.
_MEM_LIMIT = "2g"
_PIDS_LIMIT = 512
_CPU_PERIOD = 100_000
_CPU_QUOTA = 200_000  # 2 CPUs


def _docker_client():
    try:
        import docker  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - docker SDK absent
        raise RuntimeError(
            "docker SDK not installed. Add 'docker>=7.0' or set sandbox=False."
        ) from exc
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as exc:  # daemon unreachable
        raise RuntimeError(
            "Docker daemon not running. Set sandbox:false or start Docker Desktop."
        ) from exc


def _image_exists(client: Any, image: str) -> bool:
    try:
        client.images.get(image)
        return True
    except Exception:
        return False


def _missing_image_message(image: str) -> str:
    base = image.split(":", 1)[0].split("/", 1)[-1]
    dockerfile = f"docker/{base}.Dockerfile"
    return (
        f"Image {image} not found. Run: docker build -t {image} -f {dockerfile} ."
    )


def _run_container(
    client: Any,
    *,
    image: str,
    command: list[str] | str,
    volumes: dict[str, dict[str, str]],
    workdir: str,
    timeout: int,
    network: bool,
    stdin_payload: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    create_kwargs: dict[str, Any] = {
        "image": image,
        "command": command,
        "volumes": volumes,
        "working_dir": workdir,
        "network_disabled": not network,
        "mem_limit": _MEM_LIMIT,
        "pids_limit": _PIDS_LIMIT,
        "cpu_period": _CPU_PERIOD,
        "cpu_quota": _CPU_QUOTA,
        "cap_drop": ["ALL"],
        "detach": True,
        "stdin_open": stdin_payload is not None,
        "tty": False,
    }
    try:
        container = client.containers.create(**create_kwargs)
    except Exception as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "error": f"failed to create container: {exc}",
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    stdout_bytes = b""
    stderr_bytes = b""
    exit_code: int | None = None
    try:
        container.start()
        if stdin_payload is not None:
            try:
                sock = container.attach_socket(
                    params={"stdin": 1, "stream": 1, "stdout": 0, "stderr": 0}
                )
                sock._sock.sendall(stdin_payload.encode("utf-8"))
                sock.close()
            except Exception:
                pass

        try:
            result = container.wait(timeout=timeout)
            exit_code = int(result.get("StatusCode", 1))
        except Exception as exc:
            with contextlib.suppress(Exception):
                container.kill()
            return {
                "ok": False,
                "stdout": "",
                "stderr": f"container timed out after {timeout}s: {exc}",
                "exit_code": None,
                "elapsed_ms": int((time.perf_counter() - started) * 1000),
            }

        try:
            stdout_bytes = container.logs(stdout=True, stderr=False) or b""
            stderr_bytes = container.logs(stdout=False, stderr=True) or b""
        except Exception:
            pass
    finally:
        with contextlib.suppress(Exception):
            container.remove(force=True)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "ok": exit_code == 0,
        "stdout": stdout_bytes.decode("utf-8", errors="replace"),
        "stderr": stderr_bytes.decode("utf-8", errors="replace"),
        "exit_code": exit_code,
        "elapsed_ms": elapsed_ms,
    }


def run_snippet(
    code: str,
    *,
    compiler: str = "clang",
    std: str = "20",
    flags: list[str] | None = None,
    stdin: str = "",
    timeout: int = 10,
    image: str = DEFAULT_BUILD_IMAGE,
) -> dict[str, Any]:
    """Compile and run a snippet inside a docker container."""
    try:
        client = _docker_client()
    except RuntimeError as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "compile_errors": [],
            "elapsed_ms": 0,
            "error": str(exc),
        }

    if not _image_exists(client, image):
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "compile_errors": [],
            "elapsed_ms": 0,
            "error": _missing_image_message(image),
        }

    extra = " ".join(shlex.quote(f) for f in (flags or []))
    cc = "clang++" if compiler == "clang" else "g++"
    script = (
        f"set -e; cd /work; "
        f"{cc} -std=c++{std} -Wall -O0 main.cpp -o a.out {extra} 2>compile.err && "
        f"./a.out"
    )

    with tempfile.TemporaryDirectory(prefix="nexcpp-snippet-") as tmpdir:
        src = Path(tmpdir) / "main.cpp"
        src.write_text(code, encoding="utf-8")

        result = _run_container(
            client,
            image=image,
            command=["bash", "-lc", script],
            volumes={tmpdir: {"bind": "/work", "mode": "rw"}},
            workdir="/work",
            timeout=timeout,
            network=False,
            stdin_payload=stdin if stdin else None,
        )

        compile_err_path = Path(tmpdir) / "compile.err"
        compile_text = ""
        if compile_err_path.is_file():
            compile_text = compile_err_path.read_text(encoding="utf-8", errors="replace")

        from sandbox.quick import parse_compile_errors  # local import to avoid cycles

        compile_errors = parse_compile_errors(compile_text)
        # Stitch compile output into stderr for visibility.
        if compile_text and compile_text not in result.get("stderr", ""):
            result["stderr"] = compile_text + result.get("stderr", "")
        result["compile_errors"] = compile_errors
        return result


def run_build(
    project_dir: Path,
    *,
    build_type: str = "Debug",
    target: str | None = None,
    run_tests: bool = True,
    sanitizers: list[str] | None = None,
    image: str = DEFAULT_BUILD_IMAGE,
    network: bool = False,
    timeout: int = 1800,
) -> dict[str, Any]:
    """Run a CMake build inside a docker container.

    Currently only the CMake path is supported in-container; meson/bazel
    callers should fall back to the local pipeline.
    """
    project_dir = Path(project_dir).resolve()
    if not project_dir.is_dir():
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"project_dir does not exist: {project_dir}",
            "exit_code": None,
            "error": "no project dir",
        }

    try:
        client = _docker_client()
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": "", "exit_code": None}

    if not _image_exists(client, image):
        return {
            "ok": False,
            "error": _missing_image_message(image),
            "stdout": "",
            "stderr": "",
            "exit_code": None,
        }

    san_flag = ""
    if sanitizers:
        joined = ",".join(sanitizers)
        san_flag = f"-DCMAKE_CXX_FLAGS=-fsanitize={joined}"

    target_arg = f"--target {shlex.quote(target)}" if target else ""
    test_step = "ctest --test-dir build --output-on-failure" if run_tests else "true"
    script = (
        "set -e; cd /work; "
        f"cmake -S . -B build -DCMAKE_BUILD_TYPE={build_type} "
        f"-G Ninja {san_flag} && "
        f"cmake --build build {target_arg} -j && "
        f"{test_step}"
    )

    return _run_container(
        client,
        image=image,
        command=["bash", "-lc", script],
        volumes={str(project_dir): {"bind": "/work", "mode": "rw"}},
        workdir="/work",
        timeout=timeout,
        network=network,
    )
