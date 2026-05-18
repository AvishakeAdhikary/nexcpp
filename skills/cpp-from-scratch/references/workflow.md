# cpp-from-scratch — Long-form workflow reference

This is the supporting reference for the `cpp-from-scratch` skill. It
walks through the same workflow in finer detail, with extra context for
common decisions.

## Phase 0: Discovery

Before any tool call, the agent must establish:

| Question                  | Why it matters                                  |
|---------------------------|-------------------------------------------------|
| Library or executable?    | Different scaffold; different install rules.    |
| Header-only OK?           | Eliminates build complexity but limits API.     |
| C++17, C++20, C++23?      | Decides feature availability and CI footprint.  |
| Platforms?                | Limits toolchain choices and CI matrix.         |
| Dependencies?             | Drives `vcpkg.json` and `find_package` calls.   |
| License?                  | Required before any code is checked in.         |
| Public API stability?     | Drives 0.x vs 1.0 versioning approach.          |

If the answer to any of these is "I don't know", **ask the user**. Do
not guess defaults silently — name choice, C++ standard, and license are
high-cost to change.

### Recommended defaults

When the user gives no preference:

- C++ standard: **C++20** (broad compiler support in 2024+, plus
  `concepts`, `ranges`, `format`, `span`, `jthread`).
- Build system: **CMake 3.20+** with `CMakePresets.json`.
- Test framework: **Catch2 v3** (header + linkable).
- Dependency manager: **vcpkg** with manifest mode.
- License: **MIT** (broad acceptance, simple text).

## Phase 1: Scaffold

Call `generate_package`. The scaffold should be a complete, immediately
buildable project. The agent's responsibility after scaffolding:

1. **Sanity-check the file tree** with `manage_file op=list`. Expected
   files for a static library:
   - `CMakeLists.txt` (top-level)
   - `include/<name>/<name>.hpp` (public header)
   - `src/<name>.cpp` (implementation)
   - `src/CMakeLists.txt`
   - `tests/CMakeLists.txt`, `tests/test_<name>.cpp`
   - `examples/CMakeLists.txt`, `examples/example.cpp`
   - `CMakePresets.json`
   - `vcpkg.json`
   - `.clang-format`, `.clang-tidy`, `.editorconfig`
   - `.gitignore`, `LICENSE`, `README.md`

2. **Inspect the top-level `CMakeLists.txt`** with `manage_file op=read`.
   It should have:
   - `cmake_minimum_required(VERSION 3.20)`
   - `project(<name> VERSION 0.1.0 LANGUAGES CXX)`
   - `option(<NAME>_BUILD_TESTS "..." OFF)` and similar
   - `add_subdirectory(src)` (and `tests` / `examples` behind options)
   - An exported `<name>::<name>` alias

3. **Verify the install rules.** A scaffold without proper `install()`
   calls is broken — consumers cannot use `find_package`. Look for:
   - `install(TARGETS <name> EXPORT <name>Targets ...)`
   - `install(EXPORT <name>Targets ... NAMESPACE <name>:: ...)`
   - `install(DIRECTORY include/ ...)`
   - A configured `<name>Config.cmake.in` template.

## Phase 2: First green build

`build_project` with `build_type: Debug, run_tests: true`. The first build
either compiles cleanly or surfaces a problem in the scaffold itself.

If it fails:

- Read `nexcpp://build/log/latest` for the full log.
- Parse the `errors` array for structured diagnostics.
- Patch one file at a time. Avoid shotgun changes.

## Phase 3: Hardening

In order:

1. **Warnings as errors**: add `target_compile_options(<name> PRIVATE
   -Wall -Wextra -Wpedantic -Werror)` (and `/W4 /WX` for MSVC). Rebuild
   and fix every diagnostic.
2. **Sanitizers**: re-build with `sanitizers: [asan, ubsan]`. Run tests.
   Fix every report.
3. **Static analysis**: `analyze_code` with the curated check list.
4. **Format**: ensure `.clang-format` is honoured (`clang-format -i` on
   all sources via `manage_file op=patch` if needed).

## Phase 4: API stability gate

Before publishing 0.1.0:

- All public headers should compile under `-Wmissing-declarations` and
  `-Wundef`.
- Move everything not part of the public API to `src/internal/`.
- Run `nm -DC` (Linux) or `dumpbin /EXPORTS` (Windows) and verify only
  intended symbols are exported (for shared libs).

## Phase 5: CI

Generate `.github/workflows/ci.yml` with:
- Matrix over `{ubuntu, macos, windows}` × `{Debug, Release}` × C++ std.
- Sanitizer job on Linux only.
- Coverage upload (gcovr / lcov) — optional.
- A release job that fires on tag push.

## Phase 6: Publish

- Update version in `vcpkg.json` and `CMakeLists.txt`.
- Tag `v0.1.0`.
- Open a vcpkg port (see `vcpkg-authoring`).
- Announce in the README.

## Decision flowchart

```
              ┌─────────────────────┐
              │ User wants new lib  │
              └──────────┬──────────┘
                         │
              Library or executable?
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
          library              executable
              │                     │
        Header-only?        skip vcpkg.json
              │              (often)
        ┌─────┴─────┐
        ▼           ▼
       yes          no
        │           │
   kind=header   kind=static
   _only         (or shared)
```

## Anti-patterns to flag

If the user proposes any of these, push back politely:

- **Vendor-included third-party** instead of vcpkg/Conan — only OK for
  tiny header-only deps.
- **Pre-3.0 CMake idioms** — link via `target_link_libraries(X PRIVATE
  Boost_LIBRARIES)` instead of `target_link_libraries(X
  PRIVATE Boost::system)`.
- **Mixing `using namespace std;` in headers** — guaranteed ODR pain.
- **Header-only with TU-private constants in `inline namespace detail`**
  — fine, but warn that ABI is impossible to keep stable.
- **One giant `CMakeLists.txt`** — split per directory.

## Glossary

- **ALIAS target**: a CMake target that's another name for an existing
  one, conventionally `Project::Project`. Required for `add_subdirectory`
  consumers to use the same syntax as `find_package` consumers.
- **Manifest mode**: vcpkg mode where `vcpkg.json` lives in the project
  root and dependencies are installed per-project.
- **Configure preset**: a named bundle of cache vars + generator in
  `CMakePresets.json`, invoked with `cmake --preset <name>`.
