---
name: cpp-python-bridge
description: "Author a Python-callable C++ extension end-to-end with pybind11: from a clean C++ header to an installable Python wheel. Use when the user wants to expose C++ code to Python, write pybind11 bindings, build a Python wheel from C++, or integrate a C++ library into a Python codebase."
---

# C++ ↔ Python Bridge (pybind11)

This skill is the canonical recipe for exposing a C++ library to Python
using pybind11. It covers binding generation, build system integration,
type conversions, GIL handling, and wheel packaging.

For Rust bindings, see `cpp-rust-bridge`.

## When to use

- "Expose this C++ class to Python"
- "Generate pybind11 bindings for header.hpp"
- "Make my C++ library pip-installable"
- "Why is my pybind11 binding crashing?"
- "How do I return a numpy array from C++?"
- "Build a wheel for Linux + macOS + Windows"

## When NOT to use

- C ABI extensions without pybind11 (use raw `Python.h`)
- Rust ↔ Python (use pyo3)
- C++ ↔ Rust (use `cpp-rust-bridge`)

## Mental model

A pybind11 binding has three pieces:

1. **The C++ library** — your actual code, header + source.
2. **The binding TU** — one `.cpp` file with `PYBIND11_MODULE(name, m) { ... }`.
3. **A build system** that produces a `.so` / `.pyd` Python can import.

Two build paths:

- **CMake + pybind11_add_module** — best for in-tree C++ projects.
- **scikit-build-core + pyproject.toml** — best for wheels.

## Step 1 — Identify the C++ surface

Read the public header you want to expose:

```yaml
tool: manage_file
args:
  op: "read"
  path: "include/mylib/api.hpp"
```

Decide which symbols are part of the Python API. **Not every C++ class
needs to be exposed.** Prefer a narrow, Pythonic facade.

## Step 2 — Generate the binding skeleton

Use `generate_bridge` with `language: python`:

```yaml
tool: generate_bridge
args:
  language: "python"
  header: "include/mylib/api.hpp"
  module_name: "mylib_py"
  output_dir: "bindings/python"
```

If libclang is installed, this produces full bindings via AST parsing.
If not, it falls back to a regex-based scan and produces a skeleton with
TODOs.

Expected output:

- `bindings/python/CMakeLists.txt` — pybind11_add_module wiring
- `bindings/python/mylib_py.cpp` — the binding TU
- `bindings/python/pyproject.toml` — scikit-build-core config
- `bindings/python/python/mylib_py/__init__.py` — re-exports

## Step 3 — Inspect the binding TU

The generated file looks like:

```cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <mylib/api.hpp>

namespace py = pybind11;

PYBIND11_MODULE(mylib_py, m) {
    m.doc() = "Python bindings for mylib";

    py::class_<mylib::Foo>(m, "Foo")
        .def(py::init<>())
        .def(py::init<int>(), py::arg("value"))
        .def("compute", &mylib::Foo::compute)
        .def_property_readonly("value", &mylib::Foo::value);

    m.def("foo", &mylib::foo,
          py::arg("input"),
          "Compute the foo of input.");
}
```

Patch what the generator got wrong. Common edits:

- Add `py::arg("name")` to every parameter so Python kwargs work.
- Use `py::overload_cast<T>(&Class::method)` for overloaded methods.
- Add `py::keep_alive<1, 2>()` when a method stores a reference.
- Replace raw pointers with `std::shared_ptr` or `py::object`.

## Step 4 — Configure build (CMake side)

For in-tree CMake build:

```cmake
find_package(pybind11 CONFIG REQUIRED)
pybind11_add_module(mylib_py mylib_py.cpp)
target_link_libraries(mylib_py PRIVATE mylib::mylib)
```

`pybind11_add_module` handles Python headers, the right link flags
(symbol hiding!), and the correct output suffix (`.so` / `.pyd`).

## Step 5 — Configure build (wheel side)

For pip-installable wheels via scikit-build-core, `pyproject.toml`:

```toml
[build-system]
requires = ["scikit-build-core>=0.8", "pybind11>=2.11"]
build-backend = "scikit_build_core.build"

[project]
name = "mylib"
version = "0.1.0"
description = "Python bindings for mylib."
requires-python = ">=3.9"

[tool.scikit-build]
cmake.version = ">=3.20"
build-dir = "build/{wheel_tag}"
wheel.packages = ["python/mylib_py"]
```

Build a wheel locally:

```yaml
tool: run_snippet
args:
  code: |
    int main() { return 0; }
  # placeholder; we actually want to run python -m build
```

Better: use a manage_file + build_project loop, or invoke `python -m
build` from the local pipeline. For CI, use `cibuildwheel`.

## Step 6 — Type conversion cheat sheet

| C++ type                          | Python type     | Header to include                     |
|-----------------------------------|-----------------|---------------------------------------|
| `std::vector<T>` / `std::array`   | `list`          | `<pybind11/stl.h>`                    |
| `std::map<K, V>`                  | `dict`          | `<pybind11/stl.h>`                    |
| `std::optional<T>`                | `T \| None`     | `<pybind11/stl.h>`                    |
| `std::variant<...>`               | union           | `<pybind11/stl.h>`                    |
| `std::tuple<...>`                 | `tuple`         | `<pybind11/stl.h>`                    |
| `std::string` / `std::string_view`| `str`           | auto                                  |
| `std::span<T>`                    | `list` or buffer | manual converter or `<pybind11/stl.h>` (C++20+) |
| `numpy::array<T>`                 | `numpy.ndarray` | `<pybind11/numpy.h>`                  |
| `Eigen::MatrixXd`                 | `numpy.ndarray` | `<pybind11/eigen.h>`                  |
| `std::chrono::*`                  | `datetime`      | `<pybind11/chrono.h>`                 |
| `std::complex<double>`            | `complex`       | `<pybind11/complex.h>`                |

## Step 7 — GIL handling

By default, pybind11 holds the GIL during your C++ function. For long-
running C++ work, release it:

```cpp
m.def("heavy_compute", [](int n) {
    py::gil_scoped_release release;  // RAII: release while computing
    return mylib::heavy_compute(n);
});
```

If your C++ calls back into Python (e.g. a callback), reacquire:

```cpp
{
    py::gil_scoped_acquire acquire;
    callback(result);
}
```

## Step 8 — Numpy interop

The common pattern is `py::array_t<double>` for arrays:

```cpp
py::array_t<double> add_arrays(py::array_t<double> a, py::array_t<double> b) {
    auto buf_a = a.request();
    auto buf_b = b.request();
    if (buf_a.size != buf_b.size) {
        throw std::runtime_error("size mismatch");
    }
    auto result = py::array_t<double>(buf_a.size);
    auto buf_r = result.request();
    auto *pa = static_cast<double*>(buf_a.ptr);
    auto *pb = static_cast<double*>(buf_b.ptr);
    auto *pr = static_cast<double*>(buf_r.ptr);
    for (py::ssize_t i = 0; i < buf_a.size; ++i) {
        pr[i] = pa[i] + pb[i];
    }
    return result;
}
```

For 2D / N-D arrays, validate `buf.ndim` and use `buf.shape` and
`buf.strides`.

## Step 9 — Stub files for IDEs

Generate `.pyi` stub files so IDEs and mypy see the types:

```bash
pybind11-stubgen mylib_py -o python/
```

Or generate manually — for any non-trivial library, type hints make the
binding 10x friendlier.

## Step 10 — CI for wheels

Use cibuildwheel. Add `.github/workflows/wheels.yml`:

```yaml
tool: github_op
args:
  op: "generate_workflow"
  template: "cibuildwheel"
  args:
    name: "wheels"
    cibw_skip: "pp* *-musllinux_i686"
```

cibuildwheel will build wheels for all supported Python versions × OSes
in CI and (optionally) push them to PyPI.

## Common pitfalls

### `ImportError: dynamic module does not define module export function (PyInit_mylib_py)`

The `PYBIND11_MODULE` first argument MUST match the file/library name
exactly. If your module is named `mylib_py` in CMake, the macro must be
`PYBIND11_MODULE(mylib_py, m)`.

### Segfault on import after `pip install`

Almost always an ABI mismatch. The wheel was built with a different
Python ABI than the consumer. Use `manylinux` images via cibuildwheel.

### `RuntimeError: Tried to call pure virtual function`

You exposed an abstract base class without trampoline. Add a trampoline:

```cpp
class PyAnimal : public mylib::Animal {
public:
    using Animal::Animal;
    std::string speak() const override {
        PYBIND11_OVERRIDE_PURE(std::string, Animal, speak,);
    }
};
py::class_<mylib::Animal, PyAnimal>(m, "Animal")
    .def(py::init<>())
    .def("speak", &mylib::Animal::speak);
```

### `error: invalid use of incomplete type 'class std::optional<...>'`

Missing `#include <pybind11/stl.h>`. Always include it for STL containers.

### Slow imports / large `.so`

You're statically linking the entire C++ library into the binding. Link
shared instead, or split the binding into multiple modules.

## Tool reference quick card

- `generate_bridge(language="python", header, module_name)` — scaffold
- `manage_file(op=read|write|patch)` — edit binding TU
- `build_project(...)` — verify CMake build
- `search_cpp_docs(query, source="std")` — look up types being bound
- `github_op(op="generate_workflow", template="cibuildwheel")` — CI

## References

- pybind11 docs: https://pybind11.readthedocs.io/
- cibuildwheel: https://cibuildwheel.pypa.io/
- scikit-build-core: https://scikit-build-core.readthedocs.io/
- pybind11 reference card: bundled examples in the pybind11 repo
