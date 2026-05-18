"""Bundled vcpkg port reference entries for nexcpp.

All content in this module is original work, released under the MIT License
along with the rest of nexcpp. Port names, dependency manifests, and typical
include or find_package usage are facts about the public surface of each
upstream project and the vcpkg registry. All prose descriptions and code
examples in this file are original; they do not derive from upstream
documentation or other copyrighted sources.
"""

from __future__ import annotations

from ._common import e

_URL = "https://vcpkg.io/en/package/"


def _u(name: str) -> str:
    return _URL + name


def _vcpkg(name: str, *, brief: str, header: str, example: str, since: str = "") -> object:
    return e(
        name,
        header="vcpkg.json",
        since=since,
        brief=brief,
        signature='"dependencies": ["' + name + '"]',
        example=example,
        url=_u(name),
        source="vcpkg",
    )


ENTRIES = [
    _vcpkg(
        "fmt",
        brief="Modern formatting library; the basis for std::format. Header-only or compiled.",
        header="#include <fmt/core.h>",
        example="find_package(fmt CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE fmt::fmt)",
    ),
    _vcpkg(
        "spdlog",
        brief="Fast logging library with sinks for files, syslog, and consoles. Built on top of fmt.",
        header="#include <spdlog/spdlog.h>",
        example="find_package(spdlog CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE spdlog::spdlog)",
    ),
    _vcpkg(
        "boost",
        brief="Umbrella manifest pulling in the full set of Boost libraries. For lighter installs, depend on individual boost-* ports.",
        header="#include <boost/...>",
        example="find_package(Boost CONFIG REQUIRED COMPONENTS system filesystem)",
    ),
    _vcpkg(
        "catch2",
        brief="Single-header / single-target unit testing framework with expressive assertion macros and section-based fixtures.",
        header="#include <catch2/catch_test_macros.hpp>",
        example="find_package(Catch2 3 CONFIG REQUIRED)\ntarget_link_libraries(tests PRIVATE Catch2::Catch2WithMain)",
    ),
    _vcpkg(
        "gtest",
        brief="Google Test xUnit-style testing framework, often paired with GoogleMock for mocking.",
        header="#include <gtest/gtest.h>",
        example="find_package(GTest CONFIG REQUIRED)\ntarget_link_libraries(tests PRIVATE GTest::gtest_main)",
    ),
    _vcpkg(
        "nlohmann-json",
        brief="Header-only JSON parser, serializer, and DOM builder with idiomatic C++ syntax.",
        header="#include <nlohmann/json.hpp>",
        example="find_package(nlohmann_json CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE nlohmann_json::nlohmann_json)",
    ),
    _vcpkg(
        "range-v3",
        brief="The library that inspired C++20 std::ranges. Useful when targeting older standards or extra views.",
        header="#include <range/v3/all.hpp>",
        example="find_package(range-v3 CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE range-v3::range-v3)",
    ),
    _vcpkg(
        "abseil",
        brief="Common foundational types extracted from internal Google C++ code: flat_hash_map, Status, Cord, strings, time.",
        header="#include <absl/container/flat_hash_map.h>",
        example="find_package(absl CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE absl::flat_hash_map)",
    ),
    _vcpkg(
        "protobuf",
        brief="Protocol Buffers schema language, code generator, and runtime for compact binary serialization.",
        header="#include <google/protobuf/message.h>",
        example="find_package(Protobuf CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE protobuf::libprotobuf)",
    ),
    _vcpkg(
        "grpc",
        brief="High-performance RPC framework over HTTP/2 with Protocol Buffers as its default IDL.",
        header="#include <grpcpp/grpcpp.h>",
        example="find_package(gRPC CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE gRPC::grpc++)",
    ),
    _vcpkg(
        "openssl",
        brief="TLS and general-purpose cryptography toolkit.",
        header="#include <openssl/ssl.h>",
        example="find_package(OpenSSL REQUIRED)\ntarget_link_libraries(app PRIVATE OpenSSL::SSL OpenSSL::Crypto)",
    ),
    _vcpkg(
        "zlib",
        brief="Lossless compression library implementing the DEFLATE algorithm; a dependency of many other ports.",
        header="#include <zlib.h>",
        example="find_package(ZLIB REQUIRED)\ntarget_link_libraries(app PRIVATE ZLIB::ZLIB)",
    ),
    _vcpkg(
        "curl",
        brief="Cross-protocol client library for HTTP(S), FTP, and more, with native and pluggable TLS backends.",
        header="#include <curl/curl.h>",
        example="find_package(CURL REQUIRED)\ntarget_link_libraries(app PRIVATE CURL::libcurl)",
    ),
    _vcpkg(
        "libpng",
        brief="Reference PNG image read/write library.",
        header="#include <png.h>",
        example="find_package(PNG REQUIRED)\ntarget_link_libraries(app PRIVATE PNG::PNG)",
    ),
    _vcpkg(
        "sqlite3",
        brief="Embedded SQL database engine distributed as a single C source file plus header.",
        header="#include <sqlite3.h>",
        example="find_package(unofficial-sqlite3 CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE unofficial::sqlite3::sqlite3)",
    ),
    _vcpkg(
        "sdl2",
        brief="Cross-platform layer for windowing, input, audio, threads, and OpenGL/Vulkan contexts.",
        header="#include <SDL2/SDL.h>",
        example="find_package(SDL2 CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE SDL2::SDL2)",
    ),
    _vcpkg(
        "qtbase",
        brief="Qt 6 base modules (Core, Gui, Widgets, Network). Treat as a meta-port; individual Qt features live in sibling qt6-* manifests.",
        header="#include <QApplication>",
        example="find_package(Qt6 CONFIG REQUIRED COMPONENTS Widgets)\ntarget_link_libraries(app PRIVATE Qt6::Widgets)",
    ),
    _vcpkg(
        "qt5-base",
        brief="Qt 5 base modules. Used when a project must remain on the long-term Qt 5 series.",
        header="#include <QApplication>",
        example="find_package(Qt5 CONFIG REQUIRED COMPONENTS Widgets)\ntarget_link_libraries(app PRIVATE Qt5::Widgets)",
    ),
    _vcpkg(
        "eigen3",
        brief="Header-only linear algebra library covering matrices, vectors, decompositions, and geometry.",
        header="#include <Eigen/Dense>",
        example="find_package(Eigen3 CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE Eigen3::Eigen)",
    ),
    _vcpkg(
        "opencv",
        brief="Computer vision and image processing library covering classic CV, DNN inference, and camera I/O.",
        header="#include <opencv2/opencv.hpp>",
        example="find_package(OpenCV CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE ${OpenCV_LIBS})",
    ),
    _vcpkg(
        "ffmpeg",
        brief="Audio and video processing libraries: libavcodec, libavformat, libavutil, libswscale, libswresample.",
        header="#include <libavformat/avformat.h>",
        example="find_package(FFMPEG REQUIRED)\ntarget_link_libraries(app PRIVATE ${FFMPEG_LIBRARIES})",
    ),
    _vcpkg(
        "asio",
        brief="Stand-alone version of Boost.Asio: portable async I/O, timers, and networking on top of an executor model.",
        header="#include <asio.hpp>",
        example="find_package(asio CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE asio::asio)",
    ),
    _vcpkg(
        "expected-lite",
        brief="Header-only backport of std::expected for codebases that have not yet adopted C++23.",
        header="#include <nonstd/expected.hpp>",
        example="find_package(expected-lite CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE nonstd::expected-lite)",
    ),
    _vcpkg(
        "magic-enum",
        brief="Header-only library that reflects enum names, values, and counts at compile time without macros.",
        header="#include <magic_enum.hpp>",
        example="find_package(magic_enum CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE magic_enum::magic_enum)",
    ),
    _vcpkg(
        "doctest",
        brief="Lightweight single-header test framework focused on fast compile times and easy in-source tests.",
        header="#include <doctest/doctest.h>",
        example="find_package(doctest CONFIG REQUIRED)\ntarget_link_libraries(tests PRIVATE doctest::doctest)",
    ),
    _vcpkg(
        "benchmark",
        brief="Google's microbenchmark library for measuring small pieces of C++ code with statistical reporting.",
        header="#include <benchmark/benchmark.h>",
        example="find_package(benchmark CONFIG REQUIRED)\ntarget_link_libraries(bench PRIVATE benchmark::benchmark_main)",
    ),
    _vcpkg(
        "pybind11",
        brief="Header-only library for exposing C++ types and functions to Python with minimal boilerplate.",
        header="#include <pybind11/pybind11.h>",
        example="find_package(pybind11 CONFIG REQUIRED)\npybind11_add_module(my_ext binding.cpp)",
    ),
    _vcpkg(
        "sol2",
        brief="Modern C++ binding layer for Lua. Wraps lua_State* with strong typing and idiomatic syntax.",
        header="#include <sol/sol.hpp>",
        example="find_package(sol2 CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE sol2::sol2)",
    ),
    _vcpkg(
        "cli11",
        brief="Single-header command-line argument parser with subcommands, validation, and config-file support.",
        header="#include <CLI/CLI.hpp>",
        example="find_package(CLI11 CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE CLI11::CLI11)",
    ),
    _vcpkg(
        "cxxopts",
        brief="Tiny header-only argv parser that emphasizes simple usage and short option declarations.",
        header="#include <cxxopts.hpp>",
        example="find_package(cxxopts CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE cxxopts::cxxopts)",
    ),
    _vcpkg(
        "fast-cpp-csv-parser",
        brief="Header-only CSV reader optimized for throughput on well-formed inputs.",
        header="#include <csv.h>",
        example="find_package(fast-cpp-csv-parser CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE fast-cpp-csv-parser::fast-cpp-csv-parser)",
    ),
    _vcpkg(
        "freetype",
        brief="Font engine that rasterizes TrueType, OpenType, and other glyph formats.",
        header="#include <ft2build.h>",
        example="find_package(Freetype REQUIRED)\ntarget_link_libraries(app PRIVATE Freetype::Freetype)",
    ),
    _vcpkg(
        "glfw3",
        brief="Multi-platform library for OpenGL, OpenGL ES, and Vulkan window and context creation, plus input.",
        header="#include <GLFW/glfw3.h>",
        example="find_package(glfw3 CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE glfw)",
    ),
    _vcpkg(
        "glm",
        brief="Header-only math library with GLSL-style vector and matrix types for graphics work.",
        header="#include <glm/glm.hpp>",
        example="find_package(glm CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE glm::glm)",
    ),
    _vcpkg(
        "imgui",
        brief="Immediate-mode GUI toolkit that builds widgets from C++ code each frame; integrates with most graphics back-ends.",
        header="#include <imgui.h>",
        example="find_package(imgui CONFIG REQUIRED)\ntarget_link_libraries(app PRIVATE imgui::imgui)",
    ),
]
