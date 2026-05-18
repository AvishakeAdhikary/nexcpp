# WebAssembly / WASI sandbox.
# Provides Emscripten + WASI-SDK so projects can be built to both
# browser-targeted WASM and standalone wasi-sdk binaries.
FROM emscripten/emsdk:latest

ENV DEBIAN_FRONTEND=noninteractive

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        cmake ninja-build meson \
        git curl ca-certificates pkg-config \
        xz-utils tar \
    && rm -rf /var/lib/apt/lists/*

# wasi-sdk for standalone WASI builds.
ARG WASI_SDK_VERSION=22
RUN curl -fsSL \
        "https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-${WASI_SDK_VERSION}/wasi-sdk-${WASI_SDK_VERSION}.0-linux.tar.gz" \
        | tar -xz -C /opt \
    && mv /opt/wasi-sdk-* /opt/wasi-sdk
ENV WASI_SDK_PATH=/opt/wasi-sdk \
    PATH="/opt/wasi-sdk/bin:${PATH}"

# Helpful entry helpers (CMake projects).
#   emcmake cmake -S . -B build && emmake cmake --build build
# For wasi-sdk:
#   cmake -DCMAKE_TOOLCHAIN_FILE=/opt/wasi-sdk/share/cmake/wasi-sdk.cmake -S . -B build

WORKDIR /work
ENTRYPOINT ["/bin/bash"]
