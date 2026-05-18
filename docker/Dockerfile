# nexcpp MCP server image.
# Provides a Python 3.12 runtime plus a full C++ toolchain so the server
# can both serve MCP and execute local builds when sandboxing is off.
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        clang \
        clang-tidy \
        cmake \
        ninja-build \
        git \
        curl \
        ca-certificates \
        cppcheck \
        pkg-config \
        zip unzip tar \
    && rm -rf /var/lib/apt/lists/*

# vcpkg
RUN git clone --depth 1 https://github.com/microsoft/vcpkg.git /opt/vcpkg \
    && /opt/vcpkg/bootstrap-vcpkg.sh -disableMetrics
ENV VCPKG_ROOT=/opt/vcpkg \
    PATH="/opt/vcpkg:${PATH}"

RUN pip install --no-cache-dir uv

WORKDIR /nexcpp
COPY pyproject.toml README.md ./
COPY server.py config.py ./
COPY tools ./tools
COPY resources ./resources
COPY sandbox ./sandbox
COPY doc_index ./doc_index
COPY prompts ./prompts
COPY sdk ./sdk
COPY plugins ./plugins

RUN uv sync || pip install --no-cache-dir \
    "mcp[cli]>=1.2.0" "pydantic>=2.6" "httpx>=0.27" "beautifulsoup4>=4.12" \
    "lxml>=5.0" "rank-bm25>=0.2.2" "jinja2>=3.1" "rich>=13.7" "click>=8.1" \
    "pyyaml>=6.0" "docker>=7.0" "gitpython>=3.1" "pygithub>=2.1"

EXPOSE 7777

ENTRYPOINT ["uv", "run", "server.py"]
CMD ["--transport", "stdio"]
