"""Bridge / release / debug prompts.

Registers four ``@mcp.prompt`` callables:
``pybind11_binding``, ``rust_bridge``, ``sanitizer_debug``, ``github_release``.
"""

from __future__ import annotations

from typing import Any


_PYBIND11 = """\
Generate Python bindings for a C++ header via pybind11.

Inputs
- header_file: {header_file}
- module_name: {module_name}

Steps:

1. Inspect the header:

       manage_file(op="read", path="{header_file}")

   Note the public functions and classes you want exposed.

2. Generate the bridge:

       generate_bridge(target_lang="python", header="{header_file}",
                       output_dir="./{module_name}_bindings")

3. Review the rendered files (bindings.cpp, setup.py, pyproject.toml,
   CMakeLists.txt). Add or tighten signatures for any function whose
   regex-detected type is wrong:

       manage_file(op="patch", path="./{module_name}_bindings/bindings.cpp", patch="...")

4. Build the wheel:

       build_project(directory="./{module_name}_bindings",
                     extra_args=["--target", "{module_name}"])

   Or `pip install ./{module_name}_bindings`.

5. Smoke test:

       run_snippet(language="python", code="import {module_name}; print(dir({module_name}))")

Stop when import succeeds and dir() shows your symbols.
"""


_RUST_BRIDGE = """\
Generate a Rust cxx bridge for a C++ header.

Inputs
- header_file: {header_file}
- crate_name:  {crate_name}

Steps:

1. Examine the header to plan the bridge surface:

       manage_file(op="read", path="{header_file}")
       search_cpp_docs(query="cxx crate bridge mod", source="all", max_results=3)

2. Scaffold the crate skeleton:

       generate_bridge(target_lang="rust", header="{header_file}",
                       output_dir="./{crate_name}")

   This creates `src/bridge.rs`, `Cargo.toml`, `build.rs`.

3. Add the C++ shim (`src/shim.cpp`) implementing any free functions
   the bridge declares but the header inlines. Use manage_file(op=write).

4. Build:

       run_snippet(language="bash", code="cd {crate_name} && cargo build --release")

5. From CMake-driven projects, expose the crate as a static library and
   `corrosion_import_crate(MANIFEST_PATH {crate_name}/Cargo.toml)`.

Keep the cxx bridge surface narrow. Wrap pointers in opaque types.
"""


_SANITIZER_DEBUG = """\
Diagnose a sanitizer report.

Sanitizer output
----------------
{asan_output}
----------------

Procedure:

1. Identify the sanitizer (ASan / UBSan / TSan / MSan) from the first
   "==<pid>==ERROR" or "runtime error:" line.

2. Extract the SUMMARY line and the top frame in user code (skip frames
   in libc / runtime). Note file:line.

3. Re-read the offending source:

       manage_file(op="read", path="<file from frame>")

4. Search for the relevant memory / UB rule:

       search_cpp_docs(query="<rule>", source="std", max_results=3)

5. Apply a minimal fix:

       manage_file(op="patch", path="<file>", patch="<diff>")

6. Re-build WITH the sanitizer to confirm:

       build_project(directory="<root>", build_type="Debug",
                     extra_args=["-DCMAKE_CXX_FLAGS=-fsanitize=address -fno-omit-frame-pointer -g"])
       run_snippet(language="bash", code="./<root>/build/<test_binary>")

7. Then re-run analyze_code on the touched file to spot residual
   issues:

       analyze_code(target="<file>")

Stop when the sanitizer is silent on the affected test.
"""


_GH_RELEASE = """\
Cut a tagged release on GitHub.

Inputs
- version: {version}
- notes:   {notes}

Steps:

1. Sanity-check the working tree:

       run_snippet(language="bash", code="git status --porcelain && git log -1 --oneline")

   Refuse to release if uncommitted changes remain.

2. Build & test in Release on this machine first:

       build_project(directory=".", build_type="Release", run_tests=True)

3. Tag and push:

       run_snippet(language="bash", code="git tag -a {version} -m 'Release {version}' && git push origin {version}")

4. Create the GitHub release:

       github_op(op="create_release", repo="<owner>/<repo>", tag="{version}",
                 title="{version}", body="{notes}")

5. (Optional) Publish to vcpkg if applicable:

       github_op(op="publish_package", registry="vcpkg",
                 port_dir="ports/<library>", repo="microsoft/vcpkg")

6. (Optional) Emit a release workflow if the repo lacks one:

       github_op(op="generate_workflow", workflow_template="release",
                 workflow_kwargs={{"project_name": "<repo>", "cpp_std": "20"}})

       manage_file(op="write", path=".github/workflows/release.yml", content=<yaml>)

Report each result. Stop on the first failing step.
"""


def register(mcp: Any) -> None:  # noqa: ANN401
    @mcp.prompt(description="Guide creating pybind11 Python bindings for a C++ header.")
    def pybind11_binding(header_file: str, module_name: str) -> str:
        return _PYBIND11.format(header_file=header_file, module_name=module_name)

    @mcp.prompt(description="Guide creating a Rust cxx bridge for a C++ header.")
    def rust_bridge(header_file: str, crate_name: str) -> str:
        return _RUST_BRIDGE.format(header_file=header_file, crate_name=crate_name)

    @mcp.prompt(description="Diagnose an ASan/UBSan/TSan/MSan report and apply a fix.")
    def sanitizer_debug(asan_output: str) -> str:
        return _SANITIZER_DEBUG.format(asan_output=asan_output)

    @mcp.prompt(description="Cut a GitHub release with binaries and optional registry publish.")
    def github_release(version: str, notes: str = "") -> str:
        return _GH_RELEASE.format(version=version, notes=notes)
