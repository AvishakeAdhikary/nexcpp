# Sandbox image for compiling and running Linux x86_64 C++ projects.
# Built with `docker build -t nexcpp/build-linux -f docker/build-linux.Dockerfile .`
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    CMAKE_GENERATOR=Ninja

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc-14 g++-14 \
        clang-18 clang-tidy-18 clang-format-18 lld-18 lldb-18 \
        cmake ninja-build meson \
        ccache \
        git curl ca-certificates \
        pkg-config zip unzip tar xz-utils \
        python3 python3-pip \
        gdb \
        lcov valgrind \
        cppcheck \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 60 \
       --slave /usr/bin/g++ g++ /usr/bin/g++-14 \
    && update-alternatives --install /usr/bin/clang clang /usr/bin/clang-18 60 \
       --slave /usr/bin/clang++ clang++ /usr/bin/clang++-18 \
       --slave /usr/bin/clang-tidy clang-tidy /usr/bin/clang-tidy-18

RUN git clone --depth 1 https://github.com/microsoft/vcpkg.git /opt/vcpkg \
    && /opt/vcpkg/bootstrap-vcpkg.sh -disableMetrics
ENV VCPKG_ROOT=/opt/vcpkg \
    PATH="/opt/vcpkg:${PATH}"

# CMAKE_BUILD_PARALLEL_LEVEL is best set per-container via -e so it
# picks up the cgroup-visible CPU count; we leave a sensible default.
ENV CMAKE_BUILD_PARALLEL_LEVEL=4

WORKDIR /work
ENTRYPOINT ["/bin/bash"]
