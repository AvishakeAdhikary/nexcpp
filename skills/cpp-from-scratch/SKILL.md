---
name: cpp-from-scratch
description: "Complete end-to-end workflow for creating a production-grade C++ library from initial design through to a published, installable vcpkg package. Use when the user asks to create a new C++ library, scaffold a new C++ project, build a new C++ package, start a C++ codebase, or take a C++ project from zero to release."
---

# C++ From Scratch

This skill is the canonical playbook for creating a new C++ library or
application end-to-end using nexcpp's MCP tools. It covers requirements
elicitation, scaffolding, dependency selection, building, testing, static
analysis, sanitizers, packaging, and release.

Invoke this skill whenever the user asks for a new C++ project, library,
package, or wants to start from a blank directory. Re-read
`references/workflow.md` for the long-form checklist of every step.

## When to use

- "Create a new C++ library called foo that does X"
- "Scaffold a header-only library with tests"
- "I want to start a new C++ project — set me up"
- "Bootstrap a CMake project for a CLI tool"
- "Make a vcpkg-publishable C++17 package"

## When NOT to use

- Modifying an existing project's build (use `cmake-mastery`)
- Authoring a vcpkg port for code you don't own (use `vcpkg-authoring`)
- Diagnosing a sanitizer report (use `sanitizer-debugging`)

## High-level workflow

1. Gather requirements
2. Search docs for any std features mentioned
3. Generate scaffold with `generate_package`
4. Add dependencies (vcpkg manifest)
5. Build with `build_project`
6. Run sanitizers + static analysis
7. Write tests
8. Wire CI via `github_op generate_workflow`
9. Tag and publish

## Step 1 — Requirements gathering

Before touching any tool, get answers to:

- **Name** of the library — lowercase, hyphenated for the project name,
  PascalCase or snake_case for the namespace.
- **Kind**: `header-only`, `static`, `shared`, or `executable`.
- **Minimum C++ standard**: 17 / 20 / 23. Default to 20 unless the user
  needs broader compiler support.
- **Dependencies**: e.g. `fmt`, `spdlog`, `Catch2`, `nlohmann_json`.
- **Target platforms**: Linux / macOS / Windows / WASM / ARM64?
- **License**: MIT / Apache-2.0 / BSL-1.0.

Confirm the name and kind explicitly with the user — these are the most
costly to change later.

## Step 2 — Look up unfamiliar std features

For every std symbol or feature mentioned in requirements, call
`search_cpp_docs` so you write idiomatic code from the start:

```yaml
tool: search_cpp_docs
args:
  query: "std::expected"
  source: "std"
  cpp_std: "23"
  max_results: 3
```

If the user mentioned `std::ranges`, `std::expected`, `std::format`,
`std::span`, `std::print`, or anything else that's standard-dependent,
verify the minimum C++ standard supports it. If it doesn't, push back to
the user with a recommendation.

## Step 3 — Generate the scaffold

Call `generate_package`. Pick the right template kind and standard:

```yaml
tool: generate_package
args:
  name: "fastfoo"
  kind: "static"            # or header_only, shared, executable
  cpp_std: "20"
  with_tests: true
  with_examples: true
  with_cmake_presets: true
  vcpkg: true               # generate vcpkg.json
  license: "MIT"
  description: "Fast foo computation library."
  dependencies: ["fmt", "spdlog"]
  output_dir: "."
```

The scaffold should produce at minimum:

- `CMakeLists.txt` with `target_*` calls and a `fastfoo::fastfoo` alias
- `include/fastfoo/fastfoo.hpp`
- `src/fastfoo.cpp` (omitted for header-only)
- `tests/CMakeLists.txt` and `tests/test_fastfoo.cpp` (Catch2)
- `examples/CMakeLists.txt` and `examples/example.cpp`
- `CMakePresets.json` with `default`, `release`, `asan`, `ubsan`
- `vcpkg.json` with the declared dependencies
- `.gitignore`, `LICENSE`, `README.md`
- `.clang-format`, `.clang-tidy`

Verify with `manage_file`:

```yaml
tool: manage_file
args:
  op: "list"
  path: "."
```

You should see ≥5 generated files.

## Step 4 — Customise the public header

Read the generated header, then patch it to reflect the requirements.
Public-header surface is what consumers will depend on, so design carefully:

```yaml
tool: manage_file
args:
  op: "read"
  path: "include/fastfoo/fastfoo.hpp"
```

Then write the real declarations:

```yaml
tool: manage_file
args:
  op: "write"
  path: "include/fastfoo/fastfoo.hpp"
  content: |
    #pragma once
    #include <string_view>
    namespace fastfoo {
        // Returns a foo'd version of the input.
        [[nodiscard]] std::string foo(std::string_view input);
    }
```

For implementation, prefer `op: write` for whole files and `op: patch`
(unified diff) for surgical edits.

## Step 5 — First build

Configure and build with sanitizers off (just to confirm it compiles):

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "Debug"
  run_tests: true
```

Inspect the `errors` array. If non-empty, fix each one by reading the
relevant file, applying a patch, and re-building. Don't loop more than 3
times without re-reading the build log resource `nexcpp://build/log/latest`.

Common failures:

- **`fatal error: foo.h: No such file or directory`** — the include path
  is wrong. Check `target_include_directories(fastfoo PUBLIC ...)`.
- **`undefined reference to`** — missing source file or library link.
- **`cmake_minimum_required not called`** — the generated CMakeLists is
  malformed; re-run `generate_package`.

## Step 6 — Sanitizers + analysis

Once the Debug build is green, re-run with sanitizers:

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "Debug"
  sanitizers: ["asan", "ubsan"]
  run_tests: true
  static_analysis: true
```

Sanitizer findings are usually crash reports in the test output. If you
get an ASan report, hand it off to `sanitizer-debugging`.

Static analysis diagnostics will appear in the `errors` array with
`check` populated (e.g. `bugprone-use-after-move`). Fix anything labelled
`bugprone-*` or `performance-*` immediately. `modernize-*` and
`readability-*` are nice-to-have but worth doing while the codebase is
small.

For a deeper pass:

```yaml
tool: analyze_code
args:
  path: "src"
  tool: "clang-tidy"
  checks: "bugprone-*,modernize-*,performance-*,readability-*,cert-*"
  fix: false
```

## Step 7 — Tests

Tests live under `tests/`. The scaffold uses Catch2 by default. Add new
`TEST_CASE` blocks for every public function. Build with `run_tests: true`
and read failures from the `test_log` field.

For benchmarks (Google Benchmark or Catch2's bench), see `cpp-performance`.

For property tests (rapidcheck), declare it in `vcpkg.json` and add
`target_link_libraries(test_fastfoo PRIVATE rapidcheck)`.

## Step 8 — CI

Generate a GitHub Actions workflow:

```yaml
tool: github_op
args:
  op: "generate_workflow"
  template: "cpp-ci"
  args:
    name: "ci"
    cpp_std: "20"
    matrix_os: ["ubuntu-latest", "macos-latest", "windows-latest"]
    matrix_build_type: ["Debug", "Release"]
    sanitizers: ["asan", "ubsan"]
```

Write the result to `.github/workflows/ci.yml`:

```yaml
tool: manage_file
args:
  op: "write"
  path: ".github/workflows/ci.yml"
  content: "<the rendered YAML>"
```

## Step 9 — README and License

The scaffold provides skeletons; fill them in with the real usage example
and an installation snippet. The minimum README has:

- One-paragraph description
- Quick install via vcpkg
- Quick install via CMake `FetchContent`
- Tiny code example
- Build-from-source instructions
- License line

## Step 10 — First release

When tests pass on all matrix runners:

1. Update version in `vcpkg.json` and `CMakeLists.txt` (`project(... VERSION 0.1.0)`).
2. Tag: `git tag v0.1.0 && git push --tags`.
3. Open a vcpkg port (see `vcpkg-authoring`).

## Common pitfalls

- **Mixing `target_*` and directory-level commands** — always pick
  target-based CMake and stick with it.
- **Hard-coding the C++ standard via `-std=c++20` in CXXFLAGS** — use
  `target_compile_features(fastfoo PUBLIC cxx_std_20)` instead.
- **Public-headers depending on private types** — separate `include/` and
  `src/` strictly; private types go in `src/internal/`.
- **No alias target** — always provide `add_library(fastfoo::fastfoo
  ALIAS fastfoo)` so downstream `find_package` and in-tree consumers can
  link the same way.
- **`vcpkg.json` missing `version` field** — vcpkg will refuse to publish.

## Tool reference quick card

- `search_cpp_docs(query, source, cpp_std, max_results)` — offline docs
- `generate_package(name, kind, cpp_std, dependencies, ...)` — scaffold
- `manage_file(op, path, content, patch, dest)` — file ops
- `build_project(project_dir, build_type, sanitizers, run_tests, static_analysis)` — build
- `analyze_code(path, tool, checks, fix)` — static analysis
- `run_snippet(code, compiler, std)` — quick playground
- `github_op(op, ...)` — generate workflows, create repos, open PRs

See `references/workflow.md` for the full annotated checklist.
