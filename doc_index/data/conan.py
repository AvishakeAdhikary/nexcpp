"""Bundled Conan recipe reference entries for nexcpp.

All content in this module is original work, released under the MIT License
along with the rest of nexcpp. Conan recipe names and typical
``requires`` / ``find_package`` snippets are facts about the public
ConanCenter registry and the upstream projects each recipe wraps. All prose
descriptions and code examples in this file are original; they do not derive
from upstream documentation or other copyrighted sources.
"""

from __future__ import annotations

from ._common import e

_URL = "https://conan.io/center/recipes/"


def _conan(name: str, *, brief: str, requires: str, example: str) -> object:
    return e(
        name,
        header="conanfile.txt",
        since="",
        brief=brief,
        signature=requires,
        example=example,
        url=_URL + name,
        source="conan",
    )


ENTRIES = [
    _conan(
        "fmt",
        brief="Conan recipe for the fmt formatting library; provides the fmt::fmt CMake target.",
        requires="[requires]\nfmt/10.2.1",
        example="find_package(fmt REQUIRED)\ntarget_link_libraries(app PRIVATE fmt::fmt)",
    ),
    _conan(
        "spdlog",
        brief="Conan recipe for spdlog. Pulls in fmt as a transitive dependency by default.",
        requires="[requires]\nspdlog/1.13.0",
        example="find_package(spdlog REQUIRED)\ntarget_link_libraries(app PRIVATE spdlog::spdlog)",
    ),
    _conan(
        "boost",
        brief="Monolithic Boost recipe with options to enable or disable individual sub-libraries.",
        requires="[requires]\nboost/1.84.0",
        example="find_package(Boost REQUIRED COMPONENTS system)\ntarget_link_libraries(app PRIVATE Boost::system)",
    ),
    _conan(
        "catch2",
        brief="Conan recipe for the Catch2 v3 test framework.",
        requires="[requires]\ncatch2/3.5.2",
        example="find_package(Catch2 REQUIRED)\ntarget_link_libraries(tests PRIVATE Catch2::Catch2WithMain)",
    ),
    _conan(
        "gtest",
        brief="Conan recipe for GoogleTest. The same recipe ships GoogleMock targets.",
        requires="[requires]\ngtest/1.14.0",
        example="find_package(GTest REQUIRED)\ntarget_link_libraries(tests PRIVATE GTest::gtest_main)",
    ),
    _conan(
        "nlohmann_json",
        brief="Conan recipe for nlohmann/json, the header-only JSON library.",
        requires="[requires]\nnlohmann_json/3.11.3",
        example="find_package(nlohmann_json REQUIRED)\ntarget_link_libraries(app PRIVATE nlohmann_json::nlohmann_json)",
    ),
    _conan(
        "range-v3",
        brief="Conan recipe for range-v3.",
        requires="[requires]\nrange-v3/0.12.0",
        example="find_package(range-v3 REQUIRED)\ntarget_link_libraries(app PRIVATE range-v3::range-v3)",
    ),
    _conan(
        "abseil",
        brief="Conan recipe for Google Abseil. Exposes individual absl::* CMake targets.",
        requires="[requires]\nabseil/20240116.1",
        example="find_package(absl REQUIRED)\ntarget_link_libraries(app PRIVATE absl::strings)",
    ),
    _conan(
        "protobuf",
        brief="Conan recipe for Protocol Buffers. Ships the protoc compiler and runtime.",
        requires="[requires]\nprotobuf/3.21.12",
        example="find_package(Protobuf REQUIRED)\ntarget_link_libraries(app PRIVATE protobuf::libprotobuf)",
    ),
    _conan(
        "grpc",
        brief="Conan recipe for gRPC; depends on protobuf and OpenSSL.",
        requires="[requires]\ngrpc/1.54.3",
        example="find_package(gRPC REQUIRED)\ntarget_link_libraries(app PRIVATE gRPC::grpc++)",
    ),
    _conan(
        "openssl",
        brief="Conan recipe for OpenSSL 3.x.",
        requires="[requires]\nopenssl/3.2.0",
        example="find_package(OpenSSL REQUIRED)\ntarget_link_libraries(app PRIVATE OpenSSL::SSL OpenSSL::Crypto)",
    ),
    _conan(
        "zlib",
        brief="Conan recipe for zlib.",
        requires="[requires]\nzlib/1.3.1",
        example="find_package(ZLIB REQUIRED)\ntarget_link_libraries(app PRIVATE ZLIB::ZLIB)",
    ),
    _conan(
        "libcurl",
        brief="Conan recipe for libcurl. Supports multiple TLS backends via options.",
        requires="[requires]\nlibcurl/8.5.0",
        example="find_package(CURL REQUIRED)\ntarget_link_libraries(app PRIVATE CURL::libcurl)",
    ),
    _conan(
        "sqlite3",
        brief="Conan recipe for SQLite 3.",
        requires="[requires]\nsqlite3/3.45.0",
        example="find_package(SQLite3 REQUIRED)\ntarget_link_libraries(app PRIVATE SQLite::SQLite3)",
    ),
    _conan(
        "sdl",
        brief="Conan recipe for SDL2.",
        requires="[requires]\nsdl/2.28.5",
        example="find_package(SDL2 REQUIRED)\ntarget_link_libraries(app PRIVATE SDL2::SDL2)",
    ),
    _conan(
        "qt",
        brief="Conan recipe for Qt 5 or Qt 6 (selected via the qt_version option).",
        requires="[requires]\nqt/6.6.1",
        example="find_package(Qt6 REQUIRED COMPONENTS Widgets)\ntarget_link_libraries(app PRIVATE Qt6::Widgets)",
    ),
    _conan(
        "eigen",
        brief="Conan recipe for the Eigen header-only linear algebra library.",
        requires="[requires]\neigen/3.4.0",
        example="find_package(Eigen3 REQUIRED)\ntarget_link_libraries(app PRIVATE Eigen3::Eigen)",
    ),
    _conan(
        "opencv",
        brief="Conan recipe for OpenCV; many feature options (contrib, dnn, gstreamer, ...) tune the build.",
        requires="[requires]\nopencv/4.9.0",
        example="find_package(OpenCV REQUIRED)\ntarget_link_libraries(app PRIVATE opencv::opencv)",
    ),
    _conan(
        "asio",
        brief="Conan recipe for stand-alone Asio.",
        requires="[requires]\nasio/1.29.0",
        example="find_package(asio REQUIRED)\ntarget_link_libraries(app PRIVATE asio::asio)",
    ),
    _conan(
        "cli11",
        brief="Conan recipe for the CLI11 argument parser.",
        requires="[requires]\ncli11/2.3.2",
        example="find_package(CLI11 REQUIRED)\ntarget_link_libraries(app PRIVATE CLI11::CLI11)",
    ),
    _conan(
        "doctest",
        brief="Conan recipe for doctest.",
        requires="[requires]\ndoctest/2.4.11",
        example="find_package(doctest REQUIRED)\ntarget_link_libraries(tests PRIVATE doctest::doctest)",
    ),
    _conan(
        "benchmark",
        brief="Conan recipe for Google Benchmark.",
        requires="[requires]\nbenchmark/1.8.3",
        example="find_package(benchmark REQUIRED)\ntarget_link_libraries(bench PRIVATE benchmark::benchmark_main)",
    ),
]
