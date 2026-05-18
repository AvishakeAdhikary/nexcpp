# ARM64 cross-compile sandbox.
# Provides aarch64-linux-gnu GCC 14 + QEMU user-mode so cross-built
# binaries can be smoke-tested inline.
#
# Usage hint (CMake):
#   cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=/opt/aarch64-linux-gnu.cmake
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-14-aarch64-linux-gnu g++-14-aarch64-linux-gnu \
        binutils-aarch64-linux-gnu \
        cmake ninja-build meson \
        git curl ca-certificates pkg-config \
        qemu-user-static binfmt-support \
        python3 \
    && rm -rf /var/lib/apt/lists/*

# CMake toolchain file for aarch64-linux-gnu.
RUN printf '%s\n' \
    'set(CMAKE_SYSTEM_NAME Linux)' \
    'set(CMAKE_SYSTEM_PROCESSOR aarch64)' \
    'set(CMAKE_C_COMPILER aarch64-linux-gnu-gcc-14)' \
    'set(CMAKE_CXX_COMPILER aarch64-linux-gnu-g++-14)' \
    'set(CMAKE_FIND_ROOT_PATH /usr/aarch64-linux-gnu)' \
    'set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)' \
    'set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)' \
    'set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)' \
    'set(CMAKE_CROSSCOMPILING_EMULATOR /usr/bin/qemu-aarch64-static)' \
    > /opt/aarch64-linux-gnu.cmake

ENV CMAKE_TOOLCHAIN_FILE=/opt/aarch64-linux-gnu.cmake \
    CMAKE_GENERATOR=Ninja

WORKDIR /work
ENTRYPOINT ["/bin/bash"]
