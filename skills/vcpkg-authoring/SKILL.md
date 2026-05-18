---
name: vcpkg-authoring
description: "Author, test, and publish vcpkg ports. Use when the user wants to submit a port to vcpkg, write a portfile.cmake, set up a private vcpkg registry, debug a vcpkg install error, or publish their C++ library to vcpkg."
---

# vcpkg Authoring

This skill covers the lifecycle of a vcpkg port: writing
`portfile.cmake`, writing the `vcpkg.json` manifest, testing locally,
setting up a private registry, and submitting upstream.

## When to use

- "Publish my library to vcpkg"
- "Write a portfile.cmake for this CMake project"
- "Set up a private vcpkg registry"
- "Debug vcpkg install foo failure"
- "Update my port to a new upstream version"
- "Convert a Conan recipe to a vcpkg port"

## When NOT to use

- General CMake authoring (`cmake-mastery`)
- Writing a Conan recipe (different ecosystem)
- Scaffolding a project from scratch (`cpp-from-scratch`)

## Mental model

vcpkg has two ways to consume packages:

1. **Classic mode** — `vcpkg install foo` installs foo and its deps into
   a global `installed/` directory; project pulls from it.
2. **Manifest mode** — `vcpkg.json` in the project root lists deps;
   `cmake -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake`
   auto-installs them at configure time. **This is the modern default.**

A vcpkg **port** is the recipe that builds a library. It lives in
`ports/<name>/` and contains at minimum:

- `vcpkg.json` — port metadata + dependencies
- `portfile.cmake` — the build script
- Optional: `usage` (how-to text shown after install)

## Workflow: authoring a new port

### Step 1 — Discover existing similar ports

Most vcpkg ports follow a pattern based on upstream's build system. Find
a port that uses CMake (most common):

```yaml
tool: search_cpp_docs
args:
  query: "fmt"
  source: "vcpkg"
```

You can also read existing ports on disk if `$VCPKG_ROOT` is set:

```yaml
tool: manage_file
args:
  op: "read"
  path: "${VCPKG_ROOT}/ports/fmt/portfile.cmake"
```

(Set `file_allowlist` in `.nexcpp/config.toml` so manage_file is allowed
outside cwd.)

### Step 2 — Write the manifest

```yaml
tool: manage_file
args:
  op: "write"
  path: "ports/mylib/vcpkg.json"
  content: |
    {
      "name": "mylib",
      "version": "0.1.0",
      "description": "Fast foo computation.",
      "homepage": "https://github.com/me/mylib",
      "license": "MIT",
      "supports": "!uwp",
      "dependencies": [
        "fmt",
        { "name": "vcpkg-cmake", "host": true },
        { "name": "vcpkg-cmake-config", "host": true }
      ]
    }
```

Key fields:

- `version` — the semver. `version-semver` is the strict form.
  `version-string` for non-semver tags.
- `homepage` — the upstream repo URL.
- `supports` — boolean expression of platforms. `!uwp` means "anything
  except UWP". `linux & x64` restricts to 64-bit Linux.
- `dependencies` with `"host": true` means a build-time dep — vcpkg's
  helper modules.

### Step 3 — Write `portfile.cmake`

The standard template:

```cmake
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO me/mylib
    REF v${VERSION}
    SHA512 0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
    HEAD_REF main
)

vcpkg_cmake_configure(
    SOURCE_PATH "${SOURCE_PATH}"
    OPTIONS
        -DMYLIB_BUILD_TESTS=OFF
        -DMYLIB_BUILD_EXAMPLES=OFF
)

vcpkg_cmake_install()
vcpkg_cmake_config_fixup(PACKAGE_NAME mylib CONFIG_PATH lib/cmake/mylib)

file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")

file(INSTALL "${SOURCE_PATH}/LICENSE"
     DESTINATION "${CURRENT_PACKAGES_DIR}/share/${PORT}"
     RENAME copyright)
```

The SHA512 is intentionally zeros — vcpkg will tell you the real one
when you first attempt to install (search the error output for "Actual
hash:").

### Step 4 — Compute the real SHA512

```bash
$VCPKG_ROOT/vcpkg install mylib --overlay-ports=$(pwd)/ports
```

Expect failure. The error includes `Actual hash: <real-hash>`. Paste it
into the portfile.

### Step 5 — Local install loop

Iterate until install succeeds:

```yaml
tool: run_snippet
args:
  code: |
    #include <mylib/mylib.hpp>
    int main() { mylib::foo("hi"); }
  flags: ["-lmylib"]
```

For a more thorough test, generate a tiny consumer project:

```yaml
tool: generate_package
args:
  name: "mylib-consumer"
  kind: "executable"
  dependencies: ["mylib"]
  vcpkg: true
```

And build it pointing at your overlay-ports:

```yaml
tool: build_project
args:
  project_dir: "mylib-consumer"
```

### Step 6 — Verify port metadata

Run vcpkg's lint:

```yaml
tool: run_snippet
args:
  code: |
    int main() {}
  # ^ unused; we actually want to call vcpkg
```

Wait — better to use a shell wrapper. Use `manage_file` to create a
script and invoke via the local pipeline. Alternatively call vcpkg
directly via the build pipeline.

Run `$VCPKG_ROOT/vcpkg format-manifest ports/mylib/vcpkg.json` to
canonicalize.

### Step 7 — Submit upstream

1. Fork `microsoft/vcpkg` on GitHub.
2. Copy your `ports/mylib/` into the fork's `ports/` directory.
3. Run `$VCPKG_ROOT/vcpkg x-add-version mylib` to update version
   tracking.
4. Open a PR using `github_op`:

```yaml
tool: github_op
args:
  op: "open_pr"
  owner: "microsoft"
  repo: "vcpkg"
  head: "me:mylib-0.1.0"
  base: "master"
  title: "[mylib] Add new port"
  body: |
    Adds mylib 0.1.0 — fast foo computation.

    Tested on:
    - x64-linux
    - x64-osx
    - x64-windows
```

## Private registries

When your library isn't ready for upstream (or shouldn't go upstream),
use a private registry.

### Step 1 — Layout

```
mylib-registry/
    versions/
        baseline.json
        m-/mylib.json
    ports/
        mylib/
            vcpkg.json
            portfile.cmake
```

### Step 2 — `versions/baseline.json`

```json
{
    "default": {
        "mylib": { "baseline": "0.1.0", "port-version": 0 }
    }
}
```

### Step 3 — `versions/m-/mylib.json`

```json
{
    "versions": [
        {
            "version": "0.1.0",
            "port-version": 0,
            "git-tree": "<git ls-tree HEAD ports/mylib output>"
        }
    ]
}
```

### Step 4 — Consumer `vcpkg-configuration.json`

In the consumer project root next to `vcpkg.json`:

```json
{
    "default-registry": {
        "kind": "git",
        "repository": "https://github.com/microsoft/vcpkg",
        "baseline": "<commit sha of vcpkg>"
    },
    "registries": [
        {
            "kind": "git",
            "repository": "https://github.com/me/mylib-registry",
            "baseline": "<commit sha of registry>",
            "packages": ["mylib"]
        }
    ]
}
```

## Versioning gotchas

- vcpkg distinguishes `version-semver`, `version-string`, and `version-date`.
  Pick the one that matches upstream's tagging.
- Every change to a port requires bumping `port-version` (a numeric
  suffix) OR `version`. Bumping `port-version` re-runs the install for
  consumers without an upstream change.
- `x-add-version` MUST be run after every port change before publishing.

## Common errors

### `Error: while looking for "mylib": no version is available`

`baseline.json` doesn't list this port at this version, or the
`versions/m-/mylib.json` file is missing.

### `Error: SHA hash check for downloaded file failed`

The SHA512 in `portfile.cmake` doesn't match. Update it from the
"Actual hash:" line in the error output.

### `error: while looking for "fmt": no version is available which satisfies the constraint`

A dependency requires a newer fmt than your baseline pins. Either bump
the baseline or add an override block in your `vcpkg.json`.

### Port builds but consumer can't `find_package(mylib)`

Run `vcpkg_cmake_config_fixup` in the portfile. The `CONFIG_PATH` arg
must match where upstream's CMake installs its config files (usually
`lib/cmake/<name>`).

## Tool reference quick card

- `search_cpp_docs(query, source="vcpkg")` — find existing ports
- `manage_file(op=read|write)` — edit portfile.cmake and vcpkg.json
- `generate_package(name, ..., vcpkg=true)` — scaffold a consumer project
- `build_project(...)` — verify the port via a consumer
- `github_op(op="open_pr", ...)` — submit upstream

## References

- `nexcpp://docs/vcpkg/{package}` for any existing port
- vcpkg documentation: https://learn.microsoft.com/en-us/vcpkg/
- vcpkg ports tree: https://github.com/microsoft/vcpkg/tree/master/ports
