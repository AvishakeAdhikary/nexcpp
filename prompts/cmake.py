"""``cmake_error_fix`` MCP prompt."""

from __future__ import annotations

from typing import Any

_TEMPLATE = """\
A CMake invocation failed. Diagnose and fix it.

Error output
------------
{error_output}
------------

Procedure:

1. Identify the FIRST diagnostic line in the output above. Later
   messages are usually cascading.

2. Extract the relevant CMake command, variable, or target. Then:

       search_cpp_docs(query="<that command or variable>", source="cmake", max_results=2)

   Read the example carefully.

3. Open the offending file:

       manage_file(op="read", path="<path/to/CMakeLists.txt>")

4. Apply a minimal fix:

       manage_file(op="patch", path="<same path>", patch="<unified diff>")

   The patch should only touch the broken construct. Do not reformat
   the whole file.

5. Verify with build_project:

       build_project(directory="<project root>", build_type="Release")

   If still failing, iterate. After three failed iterations on the
   same error class, stop and report to the user with the remaining
   diagnostic.

Be terse. One sentence per step. Show the diff before applying it.
"""


def register(mcp: Any) -> None:
    @mcp.prompt(
        description="Diagnose and fix a CMake configure/build error."
    )
    def cmake_error_fix(error_output: str) -> str:
        return _TEMPLATE.format(error_output=error_output)
