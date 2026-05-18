# Modern CMake — long-form reference

Companion to the `cmake-mastery` skill. This file is the deeper "why" and
"when to break the rules" reference for CMake authoring.

## The visibility model

`target_link_libraries(X PUBLIC|PRIVATE|INTERFACE ...)` is the most
important CMake concept. Mental model:

- **PRIVATE**: X uses it, but consumers of X don't see it. The classic
  case is an implementation-detail dependency.
- **INTERFACE**: X doesn't compile against it, but consumers do. Header-
  only libraries use this exclusively.
- **PUBLIC**: both. X uses it AND consumers transitively get it.

This applies to every `target_*` command: `target_include_directories`,
`target_link_libraries`, `target_compile_definitions`, etc.

Concrete examples:

```cmake
# A static library that uses fmt internally but doesn't expose any fmt
# types in its public API:
target_link_libraries(mylib PRIVATE fmt::fmt)

# A header-only library wrapping fmt — consumers need fmt to compile:
add_library(headeronly INTERFACE)
target_link_libraries(headeronly INTERFACE fmt::fmt)

# A library that returns std::shared_ptr<spdlog::logger> from a public
# function — consumers need spdlog headers to use that return type:
target_link_libraries(mylib PUBLIC spdlog::spdlog)
```

## Generator expressions

`$<...>` are evaluated at generation time. They let you express
conditional logic without ifs. Key ones:

- `$<BUILD_INTERFACE:...>` — only when building in-tree.
- `$<INSTALL_INTERFACE:...>` — only when consumed via install.
- `$<CONFIG:Debug>` — true if current configuration is Debug.
- `$<CXX_COMPILER_ID:GNU,Clang>` — true on GCC or Clang.
- `$<TARGET_FILE:foo>` — path to the built foo binary.
- `$<IF:$<bool>,yes,no>` — ternary.

The most common pattern is paired BUILD/INSTALL include dirs:

```cmake
target_include_directories(mylib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
```

This says: "When building in-tree, my headers are at `./include`. When
installed, they're at `<prefix>/include`."

## When to use FetchContent vs find_package

- **`find_package`** when the dependency is provided by the user's
  environment (vcpkg, Conan, system package manager).
- **`FetchContent`** when you want to vendor a small dependency at
  configure time, e.g. for a single test target.

Avoid `FetchContent` for transitive dependencies that consumers might
need a different version of — let `find_package` win there.

## Properties cheat sheet

| Property                       | Where to set                        |
|--------------------------------|-------------------------------------|
| C++ standard                   | `target_compile_features(X PUBLIC cxx_std_20)` |
| Position-independent code      | `set_target_properties(X PROPERTIES POSITION_INDEPENDENT_CODE ON)` |
| Output name                    | `set_target_properties(X PROPERTIES OUTPUT_NAME my-tool)` |
| Soname / version               | `set_target_properties(X PROPERTIES VERSION ${PROJECT_VERSION} SOVERSION 1)` |
| Hide symbols by default        | `set_target_properties(X PROPERTIES CXX_VISIBILITY_PRESET hidden VISIBILITY_INLINES_HIDDEN ON)` |
| Position-independent code      | `set_target_properties(X PROPERTIES POSITION_INDEPENDENT_CODE ON)` |

## Patterns to memorize

### Header-only library

```cmake
add_library(myheaders INTERFACE)
target_include_directories(myheaders INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(myheaders INTERFACE cxx_std_20)
add_library(myheaders::myheaders ALIAS myheaders)
```

### Test directory

```cmake
if(BUILD_TESTING)
    find_package(Catch2 CONFIG REQUIRED)
    include(CTest)
    include(Catch)
    add_executable(test_mylib test_basic.cpp test_edge.cpp)
    target_link_libraries(test_mylib PRIVATE mylib::mylib Catch2::Catch2WithMain)
    catch_discover_tests(test_mylib)
endif()
```

### Options with sensible defaults

```cmake
option(MYLIB_BUILD_TESTS    "Build mylib tests"    ${PROJECT_IS_TOP_LEVEL})
option(MYLIB_BUILD_EXAMPLES "Build mylib examples" ${PROJECT_IS_TOP_LEVEL})
option(MYLIB_INSTALL        "Generate install rules" ${PROJECT_IS_TOP_LEVEL})
```

`PROJECT_IS_TOP_LEVEL` (CMake 3.21+) is true when this project is the
top-level project — usually you only want tests built when this is the
project being directly developed.

## Anti-patterns

### `file(GLOB)` for sources

```cmake
# DO NOT DO THIS:
file(GLOB SOURCES "src/*.cpp")
add_library(mylib ${SOURCES})
```

Reason: when a new source file is added, CMake doesn't know to
re-configure. Use explicit lists. (`GLOB CONFIGURE_DEPENDS` is a band-aid
that adds re-glob overhead to every build.)

### `set(CMAKE_CXX_STANDARD 20)` in subdirectory

Setting it in a subdirectory only affects targets in that subdirectory
and below, and only those that don't override it. Use
`target_compile_features` per target instead.

### Mixing directory-level and target-level commands

`include_directories(...)` adds to every target in the directory. This
crosses target boundaries and breaks the visibility model. Always use
`target_include_directories`.

### Putting `find_package` in a `set(...)`-heavy block

```cmake
# Avoid:
set(BUILD_SHARED_LIBS ON)
find_package(Boost REQUIRED)
set(BUILD_SHARED_LIBS OFF)
```

Setting global variables to influence `find_package` is fragile. Use
target-level overrides where possible, or component flags
(`find_package(Boost COMPONENTS system REQUIRED)`).

## Cross-compilation deep dive

### Toolchain file structure

```cmake
set(CMAKE_SYSTEM_NAME      Linux)        # target OS
set(CMAKE_SYSTEM_PROCESSOR aarch64)      # target arch

set(triple aarch64-linux-gnu)
set(CMAKE_C_COMPILER   ${triple}-gcc)
set(CMAKE_CXX_COMPILER ${triple}-g++)
set(CMAKE_AR           ${triple}-ar)
set(CMAKE_STRIP        ${triple}-strip)

set(CMAKE_FIND_ROOT_PATH /usr/${triple})
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)
```

### Configure preset that uses it

```json
{
    "name": "arm64-linux",
    "inherits": "default",
    "toolchainFile": "${sourceDir}/cmake/toolchain-arm64-linux.cmake"
}
```

### Easier: docker

The `docker-cpp-dev` skill has a much simpler workflow for ARM64 cross-
compilation using nexcpp's `nexcpp/build-arm64` image. Recommend that
path for users who don't already have a cross toolchain installed.

## Migration checklist (legacy → modern)

- [ ] `cmake_minimum_required(VERSION 3.20)` or newer.
- [ ] `project(... VERSION ... LANGUAGES CXX)`.
- [ ] No `include_directories`, `link_libraries`,
  `add_definitions` at the directory level.
- [ ] No `${Boost_LIBRARIES}` — use `Boost::system` imported targets.
- [ ] Each library has a `::` alias.
- [ ] `target_compile_features` declares the C++ standard per target.
- [ ] Install rules (`install(TARGETS ... EXPORT ...)` + Config files).
- [ ] `CMakePresets.json` with at least `default` and `release`.
- [ ] `BUILD_TESTING` gated tests under `if(BUILD_TESTING)`.
- [ ] Warnings via `target_compile_options(... PRIVATE ...)` per target.

## Resources to cite

- [https://cliutils.gitlab.io/modern-cmake/](Modern CMake guide)
- [https://cmake.org/cmake/help/latest/](Official CMake docs)
- `nexcpp://docs/cmake/{topic}` for offline lookup

When the user asks "why?" about any of the above, link to the official
CMake docs entry via the `nexcpp://docs/cmake/<command>` resource.
