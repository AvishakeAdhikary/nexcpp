---
name: cmake-mastery
description: "Deep CMake authoring and debugging skill: modern target-based design, presets, cross-compilation, and common error diagnosis. Use when the user is writing CMake, debugging a CMake error, modernizing legacy CMake, adding cross-compilation, configuring presets, or asking how to express something in CMake."
---

# CMake Mastery

Use this skill whenever the work is about CMake itself: writing
`CMakeLists.txt`, debugging configure errors, adding cross-compilation,
managing dependencies via `find_package` or `FetchContent`, defining
`CMakePresets.json`, or modernizing legacy CMake.

For the broader "scaffold a new project" workflow, defer to
`cpp-from-scratch`. For diagnosing build-system-detected sanitizer
crashes, defer to `sanitizer-debugging`.

## When to use

- "Add a new library target to my CMake project"
- "Why is `find_package(fmt)` failing?"
- "Convert my old CMake to modern style"
- "Add a `release` configure preset"
- "Cross-compile to ARM64 with CMake"
- "Why is my install rule installing to the wrong place?"
- "How do I link against Boost.Asio in CMake?"

## When NOT to use

- Designing a brand-new project (start with `cpp-from-scratch`)
- Authoring a vcpkg port (`vcpkg-authoring`)
- Diagnosing sanitizer reports (`sanitizer-debugging`)

## Mental model — modern CMake in one sentence

> Everything is a **target**, every property is **attached to a target**
> with **PUBLIC / PRIVATE / INTERFACE** visibility, and you communicate
> with consumers via **imported targets**.

## Core workflow

When asked to modify CMake, the loop is:

1. Read the existing `CMakeLists.txt` with `manage_file op=read`.
2. Use `cmake_explain` (built-in plugin) for any command you're unsure
   about. Example: `cmake_explain("target_link_libraries")`.
3. Plan the patch — keep edits minimal and target-based.
4. Apply with `manage_file op=patch` (unified diff) or `op=write` for
   small files.
5. Re-configure with `build_project` and read the configure log.
6. Iterate.

## Reading existing CMake

Always look at the project's full structure first:

```yaml
tool: manage_file
args:
  op: "list"
  path: "."
```

Then read the top-level CMake and any subdirectory CMakeLists:

```yaml
tool: manage_file
args:
  op: "read"
  path: "CMakeLists.txt"
```

For very large CMake files, use `nexcpp://project/build-system` to get a
parsed JSON summary of project name, targets, and presets.

## Modern target-based patterns

### Adding a library target

```cmake
add_library(mylib STATIC
    src/foo.cpp
    src/bar.cpp
)
add_library(mylib::mylib ALIAS mylib)

target_include_directories(mylib
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_compile_features(mylib PUBLIC cxx_std_20)

target_compile_options(mylib PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-Wall -Wextra -Wpedantic>
    $<$<CXX_COMPILER_ID:MSVC>:/W4>
)
```

The key elements:

- **`ALIAS` target** lets in-tree and `find_package` consumers use the
  same `mylib::mylib` name.
- **`PUBLIC` vs `PRIVATE` vs `INTERFACE`** controls what propagates to
  consumers: PUBLIC = used by mylib **and** propagated; PRIVATE = used
  by mylib only; INTERFACE = propagated only.
- **Generator expressions** (`$<...>`) let one target description work
  for build tree + install tree, GCC vs MSVC, Debug vs Release.

### Linking dependencies

Always use imported targets (`Pkg::Comp`), never raw variables:

```cmake
find_package(fmt CONFIG REQUIRED)
find_package(Threads REQUIRED)
find_package(Boost CONFIG REQUIRED COMPONENTS system filesystem)

target_link_libraries(mylib
    PUBLIC
        fmt::fmt
    PRIVATE
        Threads::Threads
        Boost::system
        Boost::filesystem
)
```

If `find_package(Foo)` fails, the user almost always needs:

1. A CMake toolchain file via `-DCMAKE_TOOLCHAIN_FILE` (e.g. vcpkg).
2. `find_package(Foo CONFIG REQUIRED)` instead of MODULE mode.
3. `Foo_DIR` set explicitly to point at `FooConfig.cmake`.

Use `cmake_explain("find_package")` to check the exact arguments.

### Installing

A library that isn't installable isn't a library. The minimum:

```cmake
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

install(TARGETS mylib
    EXPORT mylibTargets
    LIBRARY  DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE  DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME  DESTINATION ${CMAKE_INSTALL_BINDIR}
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(DIRECTORY include/
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(EXPORT mylibTargets
    FILE mylibTargets.cmake
    NAMESPACE mylib::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/mylib
)

configure_package_config_file(
    cmake/mylibConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/mylibConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/mylib
)
write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/mylibConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMinorVersion
)
install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/mylibConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/mylibConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/mylib
)
```

## CMakePresets.json

Presets are the modern way to invoke CMake. A minimal presets file:

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "default",
            "generator": "Ninja",
            "binaryDir": "${sourceDir}/build/default",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
            }
        },
        {
            "name": "release",
            "inherits": "default",
            "binaryDir": "${sourceDir}/build/release",
            "cacheVariables": { "CMAKE_BUILD_TYPE": "Release" }
        },
        {
            "name": "asan",
            "inherits": "default",
            "binaryDir": "${sourceDir}/build/asan",
            "cacheVariables": {
                "CMAKE_CXX_FLAGS_INIT": "-fsanitize=address,undefined -fno-omit-frame-pointer -g"
            }
        }
    ],
    "buildPresets": [
        { "name": "default", "configurePreset": "default" },
        { "name": "release", "configurePreset": "release" }
    ],
    "testPresets": [
        {
            "name": "default",
            "configurePreset": "default",
            "output": { "outputOnFailure": true }
        }
    ]
}
```

To inspect a specific preset, use the built-in resource:

```
nexcpp://cmake/presets/release
```

## Cross-compilation

Cross-compilation in CMake means specifying a toolchain file:

```cmake
# toolchain-arm64-linux.cmake
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_C_COMPILER   aarch64-linux-gnu-gcc)
set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++)
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
```

Invoke with `cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-arm64-linux.cmake ...`,
or wire it into a configure preset.

For WASM, use the Emscripten toolchain (`emcmake cmake ...`) — see
`docker-cpp-dev` for the easier docker route.

## Diagnosing common errors

### `CMake Error: Could not find a package configuration file provided by "Foo"`

`find_package(Foo CONFIG REQUIRED)` couldn't locate `FooConfig.cmake`.
Causes (most common first):

1. The dependency isn't installed. If using vcpkg: check `vcpkg.json`
   and confirm `-DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake`.
2. The toolchain file isn't being used. Verify with
   `nexcpp://project/build-system` that the configure command includes
   `-DCMAKE_TOOLCHAIN_FILE=...`.
3. `Foo_DIR` is wrong. Set it explicitly to the directory containing
   `FooConfig.cmake`.
4. The package only ships MODULE config (`FindFoo.cmake`). Drop `CONFIG`.

### `undefined reference` / `LNK2019`

The library is found but not linked. Usually because:

- `target_link_libraries(X PRIVATE Foo)` missing.
- Linking against the wrong target name (use `Foo::Foo` not `Foo`).
- Order matters in static link lines on GCC — put dependents first.

### `error C7555: use of designated initializers requires at least '/std:c++20'`

CMake didn't apply the C++ standard. Use:

```cmake
target_compile_features(X PUBLIC cxx_std_20)
```

Not `set(CMAKE_CXX_STANDARD 20)` — the latter is global and easy to miss.

### `Unknown CMake command "..."`

You're missing an `include()` or the command was renamed. Use
`cmake_explain` to find the modern equivalent.

## Modernization workflow

When asked to modernize legacy CMake:

1. Use the `cmake_modernize` prompt (built-in plugin) for guidance.
2. Patch in this order:
   - Bump `cmake_minimum_required` to 3.20.
   - Convert `include_directories` → `target_include_directories(...)`.
   - Convert `link_libraries` / `LINK_LIBRARIES` → `target_link_libraries(...)`.
   - Convert raw `${Boost_LIBRARIES}` to imported `Boost::system` etc.
   - Add ALIAS targets.
   - Add `CMakePresets.json`.
3. Re-configure with `build_project`. Fix one error at a time.
4. Run `analyze_code` to catch any C++ regressions exposed by tighter warnings.

## Tool reference quick card

- `cmake_explain(command)` — built-in plugin: explain a CMake command
- `search_cpp_docs(query, source="cmake")` — broader search
- `manage_file(op=read|write|patch|list)` — edit CMakeLists.txt
- `build_project(...)` — verify changes
- `nexcpp://cmake/presets/{name}` — read a preset
- `nexcpp://project/build-system` — parsed CMake summary

See `references/modern-cmake.md` for the long-form modern CMake guide.
