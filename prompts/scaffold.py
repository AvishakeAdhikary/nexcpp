"""``cpp_library_scaffold`` MCP prompt."""

from __future__ import annotations

from typing import Any


_TEMPLATE = """\
You are scaffolding a brand-new C++ library with nexcpp tools.

Project request
- name: {name}
- description: {description}
- kind: {kind}

Run these steps, IN ORDER, using the listed nexcpp tools:

1. Gather requirements
   - Ask the user (if anything is unclear): C++ standard (17/20/23),
     test framework (catch2/gtest/doctest/none), package managers
     (vcpkg/conan/cpm), third-party deps.

2. Consult docs for any non-trivial stdlib or CMake feature you intend
   to use BEFORE writing code. Example tool call:

       search_cpp_docs(query="std::expected", source="std", cpp_std="23", max_results=3)
       search_cpp_docs(query="target_compile_features", source="cmake", max_results=2)

3. Generate the package skeleton:

       generate_package(
           name="{name}",
           description="{description}",
           kind="{kind}",
           cpp_std="20",
           test_framework="catch2",
           package_managers=["vcpkg"],
           dependencies=[],
           ci=True,
       )

   Use the returned `package_dir` as the working directory for the rest.

4. Verify it builds:

       build_project(directory=<package_dir>, build_type="Release", run_tests=True)

   If the build fails, parse the error, call search_cpp_docs and
   manage_file(op="patch", path=..., patch=...) until ctest is green.

5. Stage any custom code the user wanted (manage_file op="write"),
   then re-run build_project and analyze_code on the new sources.

6. Offer to publish: if the user agrees, run

       github_op(op="create_repo", repo="{name}", private=false, description="{description}")
       github_op(op="push", repo_dir="<package_dir>")
       github_op(op="open_pr", repo="<owner>/{name}", title="Initial commit", head="main", base="main")

Tone: concise, decisive. Report each tool result before moving on.
"""


def register(mcp: Any) -> None:  # noqa: ANN401
    @mcp.prompt(
        description="Guide creating a complete C++ library from scratch."
    )
    def cpp_library_scaffold(
        name: str,
        description: str = "",
        kind: str = "static",
    ) -> str:
        return _TEMPLATE.format(name=name, description=description, kind=kind)
