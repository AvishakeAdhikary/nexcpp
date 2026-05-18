"""Bundled Boost library reference entries for nexcpp.

All content in this module is original work, released under the MIT License
along with the rest of nexcpp. Boost library names, header paths, and
namespace names are facts about the public Boost C++ Libraries API and are
not copyrightable. All prose descriptions and code examples in this file
are original; they do not derive from upstream documentation or other
copyrighted sources.
"""

from __future__ import annotations

from ._common import e

_URL = "https://www.boost.org/doc/libs/release/libs/"


def _boost(name: str, *, slug: str, brief: str, header: str, example: str) -> object:
    return e(
        "boost::" + name,
        header=header,
        since="",
        brief=brief,
        signature="",
        example=example,
        url=_URL + slug + "/",
        source="boost",
    )


ENTRIES = [
    _boost(
        "asio",
        slug="asio",
        brief="Cross-platform asynchronous I/O, networking, timers, and coroutines built on an executor model.",
        header="<boost/asio.hpp>",
        example="boost::asio::io_context io;\nboost::asio::steady_timer t(io, std::chrono::seconds(1));\nt.wait();",
    ),
    _boost(
        "beast",
        slug="beast",
        brief="HTTP and WebSocket library implemented on top of Boost.Asio.",
        header="<boost/beast.hpp>",
        example="namespace http = boost::beast::http;\nhttp::request<http::string_body> req{http::verb::get, \"/\", 11};",
    ),
    _boost(
        "filesystem",
        slug="filesystem",
        brief="Predecessor of std::filesystem. Useful where the toolchain lacks <filesystem>.",
        header="<boost/filesystem.hpp>",
        example="boost::filesystem::path p = \"src\";\nbool ok = boost::filesystem::exists(p);",
    ),
    _boost(
        "system",
        slug="system",
        brief="Portable error codes and categories. Foundation used by Asio and many other Boost libraries.",
        header="<boost/system/error_code.hpp>",
        example="boost::system::error_code ec;\nif (ec) {}",
    ),
    _boost(
        "thread",
        slug="thread",
        brief="Threading primitives that pre-date std::thread, including thread_group and richer mutex variants.",
        header="<boost/thread.hpp>",
        example="boost::thread t([] {});\nt.join();",
    ),
    _boost(
        "fiber",
        slug="fiber",
        brief="User-mode cooperative threads (fibers) with channels and synchronization primitives.",
        header="<boost/fiber/all.hpp>",
        example="boost::fibers::fiber f([] {});\nf.join();",
    ),
    _boost(
        "iostreams",
        slug="iostreams",
        brief="Framework for composing streams from filters and devices (gzip, bzip2, tee, etc.).",
        header="<boost/iostreams/filtering_stream.hpp>",
        example="boost::iostreams::filtering_ostream out;\nout.push(std::cout);",
    ),
    _boost(
        "optional",
        slug="optional",
        brief="Pre-C++17 optional template; still used by libraries that target older standards.",
        header="<boost/optional.hpp>",
        example="boost::optional<int> x = 42;\nif (x) {}",
    ),
    _boost(
        "variant",
        slug="variant",
        brief="Pre-C++17 type-safe union with visitation via boost::apply_visitor.",
        header="<boost/variant.hpp>",
        example="boost::variant<int, std::string> v = 1;\nv = std::string(\"x\");",
    ),
    _boost(
        "any",
        slug="any",
        brief="Pre-C++17 type-erased value container with boost::any_cast.",
        header="<boost/any.hpp>",
        example="boost::any a = 42;\nint x = boost::any_cast<int>(a);",
    ),
    _boost(
        "regex",
        slug="regex",
        brief="Mature regular-expression library that pre-dates std::regex and is often faster on complex patterns.",
        header="<boost/regex.hpp>",
        example="boost::regex re(\"\\\\d+\");\nbool ok = boost::regex_match(\"42\", re);",
    ),
    _boost(
        "format",
        slug="format",
        brief="printf-style formatting with operator% and type-safe argument insertion.",
        header="<boost/format.hpp>",
        example="auto s = (boost::format(\"%1% %2%\") % \"x\" % 42).str();",
    ),
    _boost(
        "lexical_cast",
        slug="lexical_cast",
        brief="Generic stream-based conversion between strings and arithmetic types.",
        header="<boost/lexical_cast.hpp>",
        example="int x = boost::lexical_cast<int>(\"42\");",
    ),
    _boost(
        "program_options",
        slug="program_options",
        brief="Builder-style command-line and config-file parser with positional and value-validated options.",
        header="<boost/program_options.hpp>",
        example="namespace po = boost::program_options;\npo::options_description desc(\"opts\");",
    ),
    _boost(
        "property_tree",
        slug="property_tree",
        brief="Tree data structure with parsers for JSON, XML, INI, and INFO formats.",
        header="<boost/property_tree/ptree.hpp>",
        example="boost::property_tree::ptree pt;\npt.put(\"name\", \"x\");",
    ),
    _boost(
        "json",
        slug="json",
        brief="Modern JSON value, parser, and serializer with allocator-aware design and incremental parsing.",
        header="<boost/json.hpp>",
        example="auto v = boost::json::parse(\"{\\\"x\\\":1}\");\nauto x = v.at(\"x\").as_int64();",
    ),
    _boost(
        "spirit",
        slug="spirit",
        brief="Header-only parser combinator framework that builds recursive-descent parsers from C++ expressions.",
        header="<boost/spirit/home/x3.hpp>",
        example="namespace x3 = boost::spirit::x3;\nauto digits = +x3::digit;",
    ),
    _boost(
        "geometry",
        slug="geometry",
        brief="Generic geometry algorithms (intersection, distance, R-tree) over user-defined point and polygon types.",
        header="<boost/geometry.hpp>",
        example="namespace bg = boost::geometry;\nbg::model::point<double, 2, bg::cs::cartesian> p{1.0, 2.0};",
    ),
    _boost(
        "graph",
        slug="graph",
        brief="Generic graph data structures and algorithms (BFS, DFS, Dijkstra, A*, connected components).",
        header="<boost/graph/adjacency_list.hpp>",
        example="boost::adjacency_list<> g;\nauto v = boost::add_vertex(g);",
    ),
    _boost(
        "multiprecision",
        slug="multiprecision",
        brief="Arbitrary-precision integer, rational, and floating-point types with a uniform numeric interface.",
        header="<boost/multiprecision/cpp_int.hpp>",
        example="boost::multiprecision::cpp_int n = 1;\nfor (int i = 1; i <= 50; ++i) n *= i;",
    ),
    _boost(
        "fusion",
        slug="fusion",
        brief="Heterogeneous container library; manipulate tuples, structs, and lists with algorithm-style calls.",
        header="<boost/fusion/include/vector.hpp>",
        example="boost::fusion::vector<int, std::string> v(1, \"x\");",
    ),
    _boost(
        "mpl",
        slug="mpl",
        brief="Classical compile-time template metaprogramming library (vectors, sequences, lambdas).",
        header="<boost/mpl/vector.hpp>",
        example="using v = boost::mpl::vector<int, char, double>;",
    ),
    _boost(
        "hana",
        slug="hana",
        brief="Modern heterogeneous metaprogramming library that uses values instead of types for computation.",
        header="<boost/hana.hpp>",
        example="namespace hana = boost::hana;\nauto xs = hana::make_tuple(1, \"x\", 3.0);",
    ),
    _boost(
        "signals2",
        slug="signals2",
        brief="Thread-safe signal/slot library for managed multicast callbacks.",
        header="<boost/signals2.hpp>",
        example="boost::signals2::signal<void()> sig;\nsig.connect([]{});\nsig();",
    ),
    _boost(
        "uuid",
        slug="uuid",
        brief="UUID generation (random, name-based) and string parsing.",
        header="<boost/uuid/uuid.hpp>",
        example="boost::uuids::random_generator gen;\nauto id = gen();",
    ),
    _boost(
        "algorithm",
        slug="algorithm",
        brief="String, range, and search algorithms that complement std::algorithm (split, join, trim, Boyer-Moore).",
        header="<boost/algorithm/string.hpp>",
        example="std::string s = \"  hi  \";\nboost::algorithm::trim(s);",
    ),
    _boost(
        "range",
        slug="range",
        brief="Pre-C++20 range concepts, range-based algorithms, and lazy range adaptors.",
        header="<boost/range/algorithm.hpp>",
        example="std::vector<int> v{3, 1, 2};\nboost::range::sort(v);",
    ),
]
