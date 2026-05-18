"""``generate_package`` and ``generate_bridge`` MCP tools.

Renders Jinja2 template trees under ``templates/`` into a fresh project
directory. Path components containing ``{{var}}`` are themselves rendered
so file names can carry the project name.
"""

from __future__ import annotations

import datetime as _dt
import logging
import re
from pathlib import Path
from typing import Any, Literal

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import Field

log = logging.getLogger(__name__)

# ---- locate template root --------------------------------------------------

_HERE = Path(__file__).resolve().parent
_TEMPLATES_ROOT = (_HERE.parent / "templates").resolve()

_KIND_TO_DIR = {
    "header-only": "header_only",
    "static": "cpp_library",
    "shared": "cpp_library",
    "executable": "executable",
}

_LANG_TO_METHOD = {
    "python": "pybind11",
    "rust": "cxx",
    "go": "cgo",
    "node": "napi",
    "wasm": "emscripten",
    "java": "jni",
}

_METHOD_TO_DIR = {
    "pybind11": "pybind11",
    "cxx": "cxx_rust",
    "cgo": "cgo",
    "napi": "napi",
    "emscripten": "emscripten",
    "jni": "jni",
}

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


# ---- shared rendering helpers ---------------------------------------------


def _make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_ROOT)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
        undefined=StrictUndefined,
    )


def _render_path(env: Environment, raw: str, ctx: dict[str, Any]) -> str:
    if "{{" not in raw:
        return raw
    return env.from_string(raw).render(**ctx)


def _is_test_file_for_other_framework(rel_path: Path, framework: str) -> bool:
    """Return True if this is a test_<name>_<fw>.cpp.j2 for a different fw."""
    name = rel_path.name
    if not name.startswith("test_") or not name.endswith(".cpp.j2"):
        return False
    for fw in ("catch2", "gtest", "doctest"):
        if name.endswith(f"_{fw}.cpp.j2"):
            return fw != framework
    return False


def _render_tree(template_dir: Path, output_dir: Path, ctx: dict[str, Any]) -> list[Path]:
    """Render every ``.j2`` in ``template_dir`` to ``output_dir``.

    Path components matching ``{{var}}`` are expanded against ``ctx``.
    Test-framework-specific files are filtered to the active framework
    and the suffix is dropped on output. Returns absolute paths created.
    """
    env = _make_env()
    rel_template_root = template_dir.relative_to(_TEMPLATES_ROOT)
    created: list[Path] = []
    framework = ctx.get("test_framework", "none")

    for src in sorted(template_dir.rglob("*")):
        if src.is_dir():
            continue
        if src.suffix != ".j2":
            continue

        rel_to_template = src.relative_to(template_dir)

        # Skip test files for other frameworks
        if _is_test_file_for_other_framework(rel_to_template, framework):
            continue

        # Skip every tests/* file when framework is 'none'
        if framework == "none" and rel_to_template.parts and rel_to_template.parts[0] == "tests":
            continue

        # Compute destination path with {{var}} expansion + ".j2" stripped
        dest_parts = [_render_path(env, part, ctx) for part in rel_to_template.parts]
        # Strip trailing .j2 from filename
        if dest_parts[-1].endswith(".j2"):
            dest_parts[-1] = dest_parts[-1][: -len(".j2")]

        # If the file is a per-framework test (test_<name>_<fw>.cpp), rename to test_<name>.cpp
        last = dest_parts[-1]
        for fw in ("catch2", "gtest", "doctest"):
            suffix = f"_{fw}.cpp"
            if last.startswith("test_") and last.endswith(suffix):
                dest_parts[-1] = last[: -len(suffix)] + ".cpp"
                break

        dest_path = output_dir.joinpath(*dest_parts)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Render template by loader-relative name to keep includes working
        template_name = (rel_template_root / rel_to_template).as_posix()
        template = env.get_template(template_name)
        rendered = template.render(**ctx)
        # Force LF endings: write_text translates "\n" to os.linesep on
        # Windows by default, which gives CRLF in our generated files.
        dest_path.write_bytes(rendered.encode("utf-8"))
        created.append(dest_path.resolve())
        log.debug("rendered %s -> %s", template_name, dest_path)

    return created


# ---- generate_package ------------------------------------------------------


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise ValueError(
            f"invalid package name {name!r}: must match {_NAME_RE.pattern}"
        )


def _generate_package_impl(
    *,
    name: str,
    description: str,
    kind: str = "static",
    cpp_std: str = "20",
    test_framework: str = "catch2",
    package_managers: list[str] | None = None,
    dependencies: list[str] | None = None,
    output_dir: str | None = None,
    ci: bool = True,
) -> dict[str, Any]:
    package_managers = package_managers or ["vcpkg"]
    dependencies = dependencies or []

    try:
        _validate_name(name)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    if kind not in _KIND_TO_DIR:
        return {"ok": False, "error": f"unknown kind: {kind!r}"}
    template_subdir = _KIND_TO_DIR[kind]
    template_dir = _TEMPLATES_ROOT / template_subdir
    if not template_dir.is_dir():
        return {"ok": False, "error": f"template dir missing: {template_dir}"}

    out_root = Path(output_dir).expanduser() if output_dir else Path.cwd() / name
    out_root = out_root.resolve()
    if out_root.exists() and any(out_root.iterdir()):
        return {
            "ok": False,
            "error": (
                f"output_dir {out_root} exists and is non-empty; "
                "refusing to overwrite. Delete it or choose another path."
            ),
        }
    out_root.mkdir(parents=True, exist_ok=True)

    namespace = name.replace("_", "::")
    ctx: dict[str, Any] = {
        "name": name,
        "description": description,
        "kind": kind,
        "cpp_std": cpp_std,
        "test_framework": test_framework,
        "package_managers": package_managers,
        "dependencies": dependencies,
        "namespace": namespace,
        "year": _dt.date.today().year,
    }

    try:
        created = _render_tree(template_dir, out_root, ctx)
    except Exception as exc:  # noqa: BLE001
        log.exception("template rendering failed")
        return {"ok": False, "error": f"render failed: {exc}"}

    # Strip CI workflow if disabled
    if not ci:
        ci_path = out_root / ".github" / "workflows" / "ci.yml"
        if ci_path.exists():
            ci_path.unlink()
            try:
                ci_path.parent.rmdir()
                ci_path.parent.parent.rmdir()
            except OSError:
                pass
            created = [p for p in created if p != ci_path.resolve()]

    next_steps = [
        f"cd {out_root}",
        "cmake -S . -B build -DCMAKE_BUILD_TYPE=Release",
        "cmake --build build -j",
    ]
    if test_framework != "none":
        next_steps.append("ctest --test-dir build --output-on-failure")

    return {
        "ok": True,
        "files_created": [str(p) for p in created],
        "package_dir": str(out_root),
        "summary": (
            f"Generated {kind} C++ library {name!r} (C++{cpp_std}) with "
            f"{test_framework} tests, {len(created)} files, "
            f"package_managers={package_managers}."
        ),
        "next_steps": next_steps,
    }


# ---- header scanning for generate_bridge ----------------------------------


_FUNC_RE = re.compile(
    r"""(?P<ret>[A-Za-z_][\w:<>\s*&,]*?)\s+
        (?P<name>[A-Za-z_]\w*)\s*
        \((?P<params>[^)]*)\)\s*(?:const)?\s*[{;]""",
    re.VERBOSE,
)
_CLASS_RE = re.compile(
    r"\b(class|struct)\s+(?P<name>[A-Za-z_]\w*)\s*(?:final\s*)?(?::[^{]+)?\{",
)


def _parse_header_regex(text: str) -> dict[str, list[dict[str, Any]]]:
    """Best-effort regex extractor for top-level functions and classes."""
    # Strip line and block comments
    text_nocomments = re.sub(r"//[^\n]*", "", text)
    text_nocomments = re.sub(r"/\*.*?\*/", "", text_nocomments, flags=re.DOTALL)

    classes: list[dict[str, Any]] = []
    for cm in _CLASS_RE.finditer(text_nocomments):
        classes.append({"name": cm.group("name"), "methods": [], "fields": []})

    functions: list[dict[str, Any]] = []
    for fm in _FUNC_RE.finditer(text_nocomments):
        ret = fm.group("ret").strip()
        fn_name = fm.group("name")
        if fn_name in {"if", "for", "while", "switch", "return", "sizeof", "class", "struct"}:
            continue
        if ret in {"return", "if", "for", "while", "else", "class", "struct"}:
            continue
        # Skip constructor-like (no return type)
        if not ret:
            continue
        params_raw = fm.group("params").strip()
        params: list[dict[str, str]] = []
        if params_raw and params_raw != "void":
            for raw in params_raw.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                tokens = raw.rsplit(" ", 1)
                if len(tokens) == 2:
                    p_type, p_name = tokens
                    p_name = p_name.lstrip("*&")
                else:
                    p_type, p_name = raw, ""
                params.append({"name": p_name or "arg", "type": p_type})
        functions.append(
            {"name": fn_name, "return_type": ret, "params": params, "doc": ""}
        )

    return {"functions": functions, "classes": classes}


def _parse_header_libclang(path: Path) -> dict[str, list[dict[str, Any]]] | None:
    try:
        from clang import cindex  # type: ignore[import-not-found]
    except ImportError:
        return None

    try:
        index = cindex.Index.create()
        tu = index.parse(
            str(path),
            args=["-x", "c++", "-std=c++20"],
            options=cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("libclang parse failed: %s", exc)
        return None

    functions: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []

    for cur in tu.cursor.get_children():
        if cur.location.file is None or Path(cur.location.file.name).resolve() != path.resolve():
            continue
        if cur.kind == cindex.CursorKind.FUNCTION_DECL:
            params = []
            for arg in cur.get_arguments():
                params.append({"name": arg.spelling or "arg", "type": arg.type.spelling})
            functions.append(
                {
                    "name": cur.spelling,
                    "return_type": cur.result_type.spelling,
                    "params": params,
                    "doc": cur.brief_comment or "",
                }
            )
        elif cur.kind in (cindex.CursorKind.CLASS_DECL, cindex.CursorKind.STRUCT_DECL):
            methods: list[dict[str, Any]] = []
            fields: list[dict[str, Any]] = []
            for ch in cur.get_children():
                if ch.kind == cindex.CursorKind.CXX_METHOD and ch.access_specifier == cindex.AccessSpecifier.PUBLIC:
                    methods.append(
                        {"name": ch.spelling, "return_type": ch.result_type.spelling}
                    )
                elif ch.kind == cindex.CursorKind.FIELD_DECL and ch.access_specifier == cindex.AccessSpecifier.PUBLIC:
                    fields.append({"name": ch.spelling, "type": ch.type.spelling})
            classes.append({"name": cur.spelling, "methods": methods, "fields": fields})

    return {"functions": functions, "classes": classes}


def _parse_header(path: Path) -> dict[str, list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        clang_result = _parse_header_libclang(path)
    except Exception as exc:  # noqa: BLE001
        log.debug("libclang unavailable: %s", exc)
        clang_result = None
    if clang_result and (clang_result["functions"] or clang_result["classes"]):
        return clang_result
    return _parse_header_regex(text)


# ---- generate_bridge -------------------------------------------------------


_BUILD_INSTRUCTIONS = {
    "pybind11": (
        "From the output dir: `pip install pybind11 scikit-build-core` then "
        "`pip install .` (or `python setup.py build_ext --inplace`). "
        "Test with `python -c 'import {module_name}; print(dir({module_name}))'`."
    ),
    "cxx": (
        "Initialise a Rust crate: copy these files into a crate root, then "
        "`cargo build --release`. The bridge is generated from src/bridge.rs."
    ),
    "cgo": (
        "Place wrapper.go and wrapper.h alongside your C++ implementation, "
        "then run `go build ./...`. Pure-C++ symbols need an extern \"C\" shim."
    ),
    "napi": (
        "`npm install` then `npm run build`. Import with "
        "`require('bindings')('{module_name}')`."
    ),
    "emscripten": (
        "With emsdk activated: `emcmake cmake -S . -B build && cmake --build build`. "
        "Load the produced {module_name}.js / .wasm in the browser or Node."
    ),
    "jni": (
        "`mkdir build && cd build && cmake .. && cmake --build .`, then "
        "`javac {module_name}.java` and "
        "`java -Djava.library.path=build {module_name}`."
    ),
}


def _generate_bridge_impl(
    *,
    target_lang: str,
    header: str,
    method: str | None = None,
    output_dir: str | None = None,
    java_package: str | None = None,
) -> dict[str, Any]:
    if target_lang not in _LANG_TO_METHOD:
        return {"ok": False, "error": f"unknown target_lang: {target_lang!r}"}

    chosen_method = method or _LANG_TO_METHOD[target_lang]
    if chosen_method not in _METHOD_TO_DIR:
        return {"ok": False, "error": f"unknown bridge method: {chosen_method!r}"}

    header_path = Path(header).expanduser().resolve()
    if not header_path.is_file():
        return {"ok": False, "error": f"header not found: {header_path}"}

    module_name = header_path.stem
    template_dir = _TEMPLATES_ROOT / "bridges" / _METHOD_TO_DIR[chosen_method]
    if not template_dir.is_dir():
        return {"ok": False, "error": f"bridge template missing: {template_dir}"}

    try:
        parsed = _parse_header(header_path)
    except Exception as exc:  # noqa: BLE001
        log.exception("header parsing failed")
        return {"ok": False, "error": f"header parse failed: {exc}"}

    out_root = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else (Path.cwd() / f"{module_name}_bindings").resolve()
    )
    if out_root.exists() and any(out_root.iterdir()):
        return {
            "ok": False,
            "error": (
                f"output_dir {out_root} exists and is non-empty. "
                "Delete it or pick a fresh path."
            ),
        }
    out_root.mkdir(parents=True, exist_ok=True)

    ctx: dict[str, Any] = {
        "header": str(header_path),
        "header_basename": header_path.name,
        "header_includes": [header_path.name],
        "functions": parsed["functions"],
        "classes": parsed["classes"],
        "module_name": module_name,
    }

    if chosen_method == "jni":
        jpkg = java_package or f"com.example.{module_name}"
        ctx["java_package"] = jpkg
        # JNI mangles dots to underscores in the symbol name; underscores
        # in package segments become "_1" but we keep the simple form.
        ctx["java_package_path"] = jpkg.replace(".", "_")

    try:
        created = _render_tree(template_dir, out_root, ctx)
    except Exception as exc:  # noqa: BLE001
        log.exception("bridge rendering failed")
        return {"ok": False, "error": f"render failed: {exc}"}

    # Copy the header next to the bindings so #include "<file>" resolves.
    try:
        target = out_root / header_path.name
        target.write_bytes(header_path.read_bytes())
        created.append(target.resolve())
    except OSError as exc:
        log.warning("could not copy header into bridge dir: %s", exc)

    instructions = _BUILD_INSTRUCTIONS.get(chosen_method, "")
    if instructions:
        instructions = instructions.format(module_name=module_name)

    return {
        "ok": True,
        "files_created": [str(p) for p in created],
        "bridge_dir": str(out_root),
        "method": chosen_method,
        "target_lang": target_lang,
        "module_name": module_name,
        "build_instructions": instructions,
        "summary": (
            f"Bridge for {target_lang} (method={chosen_method}) generated "
            f"with {len(parsed['functions'])} functions and "
            f"{len(parsed['classes'])} classes."
        ),
    }


# ---- registration ----------------------------------------------------------


def register(mcp: Any) -> None:  # noqa: ANN401
    @mcp.tool()
    def generate_package(
        name: str = Field(..., description="snake_case package name."),
        description: str = Field("", description="One-line package description."),
        kind: Literal["header-only", "static", "shared", "executable"] = Field(
            "static", description="Library kind or executable."
        ),
        cpp_std: Literal["17", "20", "23"] = Field("20", description="C++ standard."),
        test_framework: Literal["catch2", "gtest", "doctest", "none"] = Field(
            "catch2", description="Test framework to scaffold."
        ),
        package_managers: list[Literal["vcpkg", "conan", "cpm"]] = Field(
            default_factory=lambda: ["vcpkg"],
            description="Package managers to generate manifests for.",
        ),
        dependencies: list[str] = Field(
            default_factory=list,
            description="Third-party deps (e.g. ['fmt','spdlog']).",
        ),
        output_dir: str | None = Field(
            None, description="Destination dir. Default: ./<name>/"
        ),
        ci: bool = Field(True, description="Emit .github/workflows/ci.yml."),
    ) -> dict[str, Any]:
        """Generate a complete, buildable C++ project skeleton.

        Returns ``{ok, files_created, package_dir, summary, next_steps}``.
        Refuses to overwrite a non-empty directory.
        """
        return _generate_package_impl(
            name=name,
            description=description,
            kind=kind,
            cpp_std=cpp_std,
            test_framework=test_framework,
            package_managers=list(package_managers),
            dependencies=list(dependencies),
            output_dir=output_dir,
            ci=ci,
        )

    @mcp.tool()
    def generate_bridge(
        target_lang: Literal["python", "rust", "go", "node", "wasm", "java"] = Field(
            ..., description="Target language for the FFI bridge."
        ),
        header: str = Field(..., description="Path to the C++ header to bind."),
        method: str | None = Field(
            None,
            description=(
                "Override bridge method (pybind11/cxx/cgo/napi/emscripten/jni). "
                "Auto-picked from target_lang."
            ),
        ),
        output_dir: str | None = Field(
            None, description="Destination dir. Default: ./<header_stem>_bindings/"
        ),
        java_package: str | None = Field(
            None,
            description=(
                "Java package for the JNI bridge (default: com.example.<module>)."
            ),
        ),
    ) -> dict[str, Any]:
        """Generate FFI bridge code from a C++ header.

        Parses the header (libclang if available, else regex) and emits
        binding source plus a build manifest for the chosen toolchain.
        """
        return _generate_bridge_impl(
            target_lang=target_lang,
            header=header,
            method=method,
            output_dir=output_dir,
            java_package=java_package,
        )
