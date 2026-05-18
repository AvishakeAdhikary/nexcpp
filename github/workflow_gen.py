"""Generate GitHub Actions workflow YAML for common C++ scenarios.

Templates are kept inline so this module has no external file deps.
Every result is validated with :func:`yaml.safe_load` before returning;
malformed templates raise :class:`ValueError`.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

log = logging.getLogger(__name__)


def _validate(yaml_text: str, template: str) -> str:
    try:
        yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        raise ValueError(
            f"workflow template {template!r} produced invalid YAML: {exc}"
        ) from exc
    return yaml_text


# ----------------------------------------------------------- templates


def _cpp_ci(
    *,
    cpp_std: str = "20",
    package_managers: list[str] | None = None,
    test_framework: str = "catch2",
    sanitizers: list[str] | None = None,
    project_name: str = "project",
    **_: Any,
) -> str:
    pms = package_managers or []
    sans = sanitizers or []
    use_vcpkg = "vcpkg" in pms

    lines: list[str] = [
        "name: CI",
        "",
        "on:",
        "  push:",
        "    branches: [main]",
        "  pull_request:",
        "    branches: [main]",
        "",
        "jobs:",
        "  build:",
        "    name: ${{ matrix.os }} / ${{ matrix.build_type }}",
        "    runs-on: ${{ matrix.os }}",
        "    strategy:",
        "      fail-fast: false",
        "      matrix:",
        "        os: [ubuntu-latest, macos-latest, windows-latest]",
        "        build_type: [Release, Debug]",
        "    steps:",
        "      - uses: actions/checkout@v4",
        "        with:",
        "          submodules: recursive",
    ]

    if use_vcpkg:
        lines.extend(
            [
                "      - name: Setup vcpkg",
                "        uses: lukka/run-vcpkg@v11",
                "        with:",
                "          vcpkgGitCommitId: '2024.01.12'",
            ]
        )

    configure_cmd = (
        "cmake -S . -B build -DCMAKE_BUILD_TYPE=${{ matrix.build_type }} "
        f"-DCMAKE_CXX_STANDARD={cpp_std}"
    )
    if use_vcpkg:
        configure_cmd += (
            " -DCMAKE_TOOLCHAIN_FILE=${{ env.VCPKG_ROOT }}/scripts/buildsystems/vcpkg.cmake"
        )

    lines.extend(
        [
            "      - name: Configure",
            f"        run: {configure_cmd}",
            "      - name: Build",
            "        run: cmake --build build --config ${{ matrix.build_type }} -j",
        ]
    )

    if test_framework != "none":
        lines.extend(
            [
                "      - name: Test",
                "        run: ctest --test-dir build -C ${{ matrix.build_type }} --output-on-failure",
            ]
        )

    if sans:
        lines.extend(
            [
                "",
                "  sanitizers:",
                "    name: Sanitizers (${{ matrix.sanitizer }})",
                "    runs-on: ubuntu-latest",
                "    strategy:",
                "      fail-fast: false",
                "      matrix:",
                "        sanitizer: [" + ", ".join(sans) + "]",
                "    steps:",
                "      - uses: actions/checkout@v4",
                "        with:",
                "          submodules: recursive",
                "      - name: Configure",
                "        run: |",
                "          FLAGS=\"-fsanitize=${{ matrix.sanitizer }} -fno-omit-frame-pointer -g\"",
                f"          cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug -DCMAKE_CXX_STANDARD={cpp_std} "
                "-DCMAKE_CXX_FLAGS=\"$FLAGS\" -DCMAKE_EXE_LINKER_FLAGS=\"$FLAGS\"",
                "      - name: Build",
                "        run: cmake --build build -j",
                "      - name: Test",
                "        run: ctest --test-dir build --output-on-failure",
            ]
        )

    return "\n".join(lines) + "\n"


def _docker(
    *,
    image_name: str = "app",
    dockerfile: str = "Dockerfile",
    **_: Any,
) -> str:
    return (
        "name: Docker\n"
        "\n"
        "on:\n"
        "  push:\n"
        "    branches: [main]\n"
        "    tags: ['v*']\n"
        "\n"
        "jobs:\n"
        "  build-and-push:\n"
        "    runs-on: ubuntu-latest\n"
        "    permissions:\n"
        "      contents: read\n"
        "      packages: write\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - name: Log in to GHCR\n"
        "        uses: docker/login-action@v3\n"
        "        with:\n"
        "          registry: ghcr.io\n"
        "          username: ${{ github.actor }}\n"
        "          password: ${{ secrets.GITHUB_TOKEN }}\n"
        "      - name: Extract metadata\n"
        "        id: meta\n"
        "        uses: docker/metadata-action@v5\n"
        "        with:\n"
        f"          images: ghcr.io/${{{{ github.repository_owner }}}}/{image_name}\n"
        "          tags: |\n"
        "            type=ref,event=branch\n"
        "            type=semver,pattern={{version}}\n"
        "            type=sha\n"
        "      - name: Build and push\n"
        "        uses: docker/build-push-action@v5\n"
        "        with:\n"
        "          context: .\n"
        f"          file: {dockerfile}\n"
        "          push: true\n"
        "          tags: ${{ steps.meta.outputs.tags }}\n"
        "          labels: ${{ steps.meta.outputs.labels }}\n"
    )


def _release(
    *,
    project_name: str = "project",
    cpp_std: str = "20",
    **_: Any,
) -> str:
    return (
        "name: Release\n"
        "\n"
        "on:\n"
        "  push:\n"
        "    tags: ['v*']\n"
        "\n"
        "jobs:\n"
        "  build:\n"
        "    name: ${{ matrix.os }}\n"
        "    runs-on: ${{ matrix.os }}\n"
        "    strategy:\n"
        "      fail-fast: false\n"
        "      matrix:\n"
        "        os: [ubuntu-latest, macos-latest, windows-latest]\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "        with:\n"
        "          submodules: recursive\n"
        "      - name: Configure\n"
        f"        run: cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_STANDARD={cpp_std}\n"
        "      - name: Build\n"
        "        run: cmake --build build --config Release -j\n"
        "      - name: Package\n"
        "        run: cmake --install build --prefix dist --config Release\n"
        "      - name: Archive\n"
        "        shell: bash\n"
        "        run: |\n"
        f"          tar czf {project_name}-${{{{ matrix.os }}}}.tar.gz -C dist .\n"
        "      - uses: actions/upload-artifact@v4\n"
        "        with:\n"
        f"          name: {project_name}-${{{{ matrix.os }}}}\n"
        f"          path: {project_name}-${{{{ matrix.os }}}}.tar.gz\n"
        "\n"
        "  release:\n"
        "    needs: build\n"
        "    runs-on: ubuntu-latest\n"
        "    permissions:\n"
        "      contents: write\n"
        "    steps:\n"
        "      - uses: actions/download-artifact@v4\n"
        "        with:\n"
        "          path: artifacts\n"
        "      - uses: softprops/action-gh-release@v2\n"
        "        with:\n"
        "          files: artifacts/**/*.tar.gz\n"
        "          generate_release_notes: true\n"
    )


def _vcpkg_port(
    *,
    port_name: str = "my-port",
    registry_repo: str = "microsoft/vcpkg",
    **_: Any,
) -> str:
    return (
        "name: vcpkg port PR\n"
        "\n"
        "on:\n"
        "  workflow_dispatch:\n"
        "    inputs:\n"
        "      version:\n"
        "        description: 'Release tag to package'\n"
        "        required: true\n"
        "\n"
        "jobs:\n"
        "  open-port-pr:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - name: Compute SHA512\n"
        "        id: hash\n"
        "        run: |\n"
        "          url=\"https://github.com/${{ github.repository }}/archive/refs/tags/${{ inputs.version }}.tar.gz\"\n"
        "          curl -L \"$url\" -o src.tar.gz\n"
        "          echo \"sha512=$(sha512sum src.tar.gz | cut -d' ' -f1)\" >> $GITHUB_OUTPUT\n"
        "      - name: Open PR\n"
        f"        run: echo 'Open PR against {registry_repo} for port {port_name} ${{{{ inputs.version }}}} sha=${{{{ steps.hash.outputs.sha512 }}}}'\n"
    )


# ----------------------------------------------------------- entry point


_TEMPLATES = {
    "cpp-ci": _cpp_ci,
    "docker": _docker,
    "release": _release,
    "vcpkg-port": _vcpkg_port,
}


def render(template: str, **kwargs: Any) -> str:
    """Render a workflow YAML by name. Raises ``ValueError`` on unknowns."""
    if template not in _TEMPLATES:
        raise ValueError(
            f"unknown workflow template: {template!r}. "
            f"Known: {sorted(_TEMPLATES)}"
        )
    yaml_text = _TEMPLATES[template](**kwargs)
    return _validate(yaml_text, template)


__all__ = ["render"]
