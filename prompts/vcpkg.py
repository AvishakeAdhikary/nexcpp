"""``vcpkg_port_authoring`` MCP prompt."""

from __future__ import annotations

from typing import Any

_TEMPLATE = """\
You are authoring a new vcpkg port.

Library
- name: {library_name}
- version: {version}
- source: {github_url}

Step-by-step:

1. Consult vcpkg conventions:

       search_cpp_docs(query="portfile.cmake vcpkg_from_github", source="vcpkg", max_results=3)
       search_cpp_docs(query="vcpkg.json schema", source="vcpkg", max_results=2)

2. Compute the source archive SHA512. Either fetch the tarball locally
   and `sha512sum` it, or instruct the user. Capture it as <SHA512>.

3. Create the port directory and files:

       manage_file(op="write", path="ports/{library_name}/vcpkg.json",
                   content='<JSON manifest with name/version/dependencies/license>')

       manage_file(op="write", path="ports/{library_name}/portfile.cmake",
                   content='vcpkg_from_github(\\n    OUT_SOURCE_PATH SOURCE_PATH\\n    REPO ...\\n    REF v{version}\\n    SHA512 <SHA512>\\n)\\nvcpkg_cmake_configure(SOURCE_PATH ${{SOURCE_PATH}})\\nvcpkg_cmake_install()\\nvcpkg_cmake_config_fixup(PACKAGE_NAME {library_name})\\nfile(INSTALL ...)\\n')

       manage_file(op="write", path="ports/{library_name}/usage",
                   content='{library_name} provides CMake targets:\\n\\n    find_package({library_name} CONFIG REQUIRED)\\n    target_link_libraries(main PRIVATE {library_name}::{library_name})\\n')

4. Validate locally:

       build_project(directory="ports/{library_name}", extra_args=["--x-builtin-ports-root", "."])

5. Open the PR upstream:

       github_op(op="publish_package", registry="vcpkg",
                 port_dir="ports/{library_name}",
                 repo="microsoft/vcpkg")

Be exact: vcpkg PRs are reviewed by humans and small mistakes get
rejected.
"""


def register(mcp: Any) -> None:
    @mcp.prompt(
        description="Guide authoring a vcpkg port for a C++ library."
    )
    def vcpkg_port_authoring(
        library_name: str,
        version: str,
        github_url: str,
    ) -> str:
        return _TEMPLATE.format(
            library_name=library_name,
            version=version,
            github_url=github_url,
        )
