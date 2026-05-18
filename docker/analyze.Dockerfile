# Lightweight static-analysis sandbox: clang-tidy + cppcheck only.
# Built with `docker build -t nexcpp/analyze -f docker/analyze.Dockerfile .`
# Target image size: ~500MB.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
        clang-tidy \
        cppcheck \
        python3 python3-pip \
        cmake \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir --break-system-packages compdb || true

WORKDIR /work
ENTRYPOINT ["/bin/bash"]
