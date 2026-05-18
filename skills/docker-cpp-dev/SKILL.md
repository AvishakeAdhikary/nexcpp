---
name: docker-cpp-dev
description: "Use nexcpp's Docker sandbox tooling for hermetic C++ builds, cross-compilation, and reproducible CI: when to run sandbox=true, picking the right image, debugging container-side build failures, and shipping multi-arch images. Use when the user asks about Docker, sandboxed builds, hermetic CI, cross-compilation via container, or producing portable Linux binaries."
---

# Docker for C++ Development

This skill is the canonical guide for using nexcpp's Docker integration:
when to switch to `sandbox=true`, which image to pick, how to debug
container-side failures, and how to package projects for reproducible
builds.

## When to use

- "Build my project in a sandbox / container"
- "Cross-compile to ARM64 / WebAssembly"
- "Reproduce the CI build locally"
- "My local toolchain is too old — build in a container"
- "Run the project with sanitizers in an isolated env"
- "Build a multi-arch docker image of my binary"

## When NOT to use

- A working local toolchain that's already producing the right output
  (Docker adds latency and complexity).
- macOS-only or Windows-only build targets (Docker Linux images can't
  produce these).

## Mental model

nexcpp's build/snippet tools all take a `sandbox: bool` parameter. When
`sandbox=true`, the tool runs inside a docker container based on one of
the `nexcpp/*` images. The container has:

- No network (`--network none` by default).
- Capped memory (2 GiB) and CPU (2 cores).
- All capabilities dropped (`--cap-drop ALL`).
- Project mounted read-write at `/work`.

This makes builds **hermetic** (no system-pkg drift) and **safe** (can't
accidentally rm -rf the home dir).

## Available images

| Image                | Base               | Purpose                       |
|----------------------|--------------------|-------------------------------|
| `nexcpp/build-linux` | ubuntu 22.04 + clang16 + gcc12 + cmake/ninja | default x86_64 builds |
| `nexcpp/build-arm64` | multi-arch buildx target | ARM64 cross / native builds |
| `nexcpp/build-wasm`  | emscripten/emsdk   | WebAssembly via Emscripten    |
| `nexcpp/analyze`     | clang-tidy + cppcheck + iwyu | static analysis dedicated image |
| `nexcpp/server`      | distroless + nexcpp | the MCP server itself        |

## Step 1 — Build the images locally

The Dockerfiles live in `docker/`. Build everything once:

```bash
docker build -t nexcpp/build-linux -f docker/build-linux.Dockerfile .
docker build -t nexcpp/build-arm64 --platform linux/arm64 \
    -f docker/build-arm64.Dockerfile .
docker build -t nexcpp/build-wasm -f docker/build-wasm.Dockerfile .
docker build -t nexcpp/analyze -f docker/analyze.Dockerfile .
```

If you push to a registry, use `docker buildx build --push
--platform linux/amd64,linux/arm64 -t ghcr.io/<you>/nexcpp-build-linux .`

(The CI workflow `docker.yml` does this automatically for you on
release tags.)

## Step 2 — Sandboxed snippet

The simplest entry point — compile and run a snippet inside the
container:

```yaml
tool: run_snippet
args:
  code: |
    #include <iostream>
    #include <thread>
    int main() {
        std::cout << "threads: "
                  << std::thread::hardware_concurrency() << "\n";
    }
  compiler: "clang"
  std: "20"
  sandbox: true
```

Note `hardware_concurrency()` may report 2 (the cgroup cap) inside the
container even on a 16-core host — that's the sandbox limit working as
intended.

## Step 3 — Sandboxed project build

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "RelWithDebInfo"
  sandbox: true
  run_tests: true
```

The container mounts your project at `/work`, runs:

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo -G Ninja
cmake --build build -j
ctest --test-dir build --output-on-failure
```

Output (stdout / stderr / parsed errors) comes back via the tool result.

## Step 4 — Picking the right image

For cross-compilation, pass an explicit `image`:

```yaml
tool: build_project
args:
  project_dir: "."
  sandbox: true
  # The build module accepts image="..." when wired; otherwise wrap with
  # run_snippet for a quick one-off:
```

For the actual ARM64 cross build, you'd configure CMake with the
toolchain file inside the ARM64 image. Generate a toolchain file with
`generate_package` or write it directly:

```yaml
tool: manage_file
args:
  op: "write"
  path: "cmake/toolchain-arm64.cmake"
  content: |
    set(CMAKE_SYSTEM_NAME Linux)
    set(CMAKE_SYSTEM_PROCESSOR aarch64)
```

When the image already has the right native compiler (which
`nexcpp/build-arm64` does on ARM64 hosts and via QEMU on x86 hosts), you
may not need a toolchain file at all.

## Step 5 — WebAssembly builds

```yaml
tool: build_project
args:
  project_dir: "."
  sandbox: true
  # use the wasm image
```

Inside the container, the configure command should be:

```
emcmake cmake -S . -B build
emmake cmake --build build
```

If you're driving from MCP, set the build flags in `CMakePresets.json`
under a `wasm` preset that uses the `Emscripten` toolchain:

```json
{
    "name": "wasm",
    "toolchainFile": "/emsdk/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake",
    "cacheVariables": { "CMAKE_BUILD_TYPE": "Release" }
}
```

## Step 6 — Static analysis in a dedicated image

`nexcpp/analyze` ships with clang-tidy, cppcheck, and
include-what-you-use pre-installed. Useful when you don't want to pollute
the build container with analyzer tools (faster baseline builds).

```yaml
tool: analyze_code
args:
  path: "src"
  tool: "all"
  checks: "bugprone-*,modernize-*"
  # if/when the analyze tool gains a sandbox param, set sandbox: true
```

## Step 7 — Multi-stage Dockerfiles for shipping

When you want to ship your *own* binary as a docker image, use a
multi-stage Dockerfile that uses the nexcpp build image for the build
stage and a minimal distroless base for the runtime stage:

```dockerfile
# syntax=docker/dockerfile:1.6

FROM nexcpp/build-linux AS build
COPY . /work
WORKDIR /work
RUN cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build -j && \
    cmake --install build --prefix /out

FROM gcr.io/distroless/cc-debian12 AS runtime
COPY --from=build /out/bin/myapp /usr/local/bin/myapp
ENTRYPOINT ["/usr/local/bin/myapp"]
```

This pattern gives you a < 30 MB runtime image with no shell, no
package manager, and only the binary + minimal libc.

## Step 8 — Multi-arch with buildx

```yaml
tool: github_op
args:
  op: "generate_workflow"
  template: "docker-publish"
  args:
    name: "docker"
    platforms: ["linux/amd64", "linux/arm64"]
    image: "ghcr.io/${{ github.repository_owner }}/myapp"
```

The generated workflow uses `docker/setup-qemu-action`,
`docker/setup-buildx-action`, and `docker/build-push-action` to build
multi-arch in one shot.

## Common pitfalls

### "Docker daemon not running"

The sandbox tool returns this when the host can't reach the docker
socket. On Linux: `sudo systemctl start docker`. On macOS / Windows:
start Docker Desktop. Or set `sandbox: false` to fall back to a local
build.

### "Image not found"

The first run after a fresh checkout, you must build the images. nexcpp
prints a helpful command, e.g.:

```
Image nexcpp/build-linux not found. Run:
    docker build -t nexcpp/build-linux -f docker/build-linux.Dockerfile .
```

### Volume permission errors on Linux

The container runs as a non-root user. If your project files are owned
by root (rare) or another UID, the build may fail with `permission
denied`. Either run `chown -R $(id -u):$(id -g) .` on the host or pass
`--user $(id -u):$(id -g)` to the container (the build module does this
by default on Linux).

### Slow builds because no ccache

The base images do not ship with ccache enabled by default. For
iterative dev, layer a derived image that mounts a host ccache dir at
`~/.ccache`.

### Network needed (vcpkg manifest mode)

By default the sandbox runs with `--network none`. If your build needs
to download deps (vcpkg manifest mode), pre-install them in a layer or
pass `network: true` to the build call. The smart pattern: vendor a
read-only vcpkg `installed/` tree into the image and have CMake point at
it.

## Step 9 — Reproducibility checklist

For truly reproducible builds inside docker:

- [ ] Pin the image by digest (`nexcpp/build-linux@sha256:...`).
- [ ] Pin all vcpkg dependencies to specific versions (`overrides` in
      `vcpkg.json`).
- [ ] Pin the vcpkg baseline commit in `vcpkg-configuration.json`.
- [ ] Use `SOURCE_DATE_EPOCH` env var if your build embeds timestamps.
- [ ] Avoid `-march=native` (varies by host CPU); pick an explicit ISA
      like `-march=x86-64-v3`.

## Tool reference quick card

- `run_snippet(code, sandbox=true, ...)` — sandboxed snippet
- `build_project(project_dir, sandbox=true, ...)` — sandboxed build
- `analyze_code(path, ...)` — static analysis (use nexcpp/analyze)
- `manage_file(op=write, path="docker/...")` — author Dockerfiles
- `github_op(op="generate_workflow", template="docker-publish")` — CI

## References

- Docker buildx: https://docs.docker.com/build/buildx/
- distroless: https://github.com/GoogleContainerTools/distroless
- vcpkg in containers: https://learn.microsoft.com/en-us/vcpkg/users/containers
- emscripten/emsdk image: https://hub.docker.com/r/emscripten/emsdk
