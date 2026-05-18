import { useState } from "react";

const nav = [
  { id: "what",       icon: "◎", label: "What nexcpp Is",      color: "#00d4ff" },
  { id: "how",        icon: "⟡", label: "How MCP Works",       color: "#a855f7" },
  { id: "primitives", icon: "◇", label: "Tools / Resources / Prompts", color: "#f59e0b" },
  { id: "tools",      icon: "⬡", label: "All Tools",           color: "#10b981" },
  { id: "resources",  icon: "◈", label: "Resources",           color: "#ec4899" },
  { id: "prompts",    icon: "▣", label: "Prompts & Skills",    color: "#84cc16" },
  { id: "plugins",    icon: "◉", label: "Plugin System",       color: "#f97316" },
  { id: "clients",    icon: "▷", label: "Agent Clients",       color: "#3b82f6" },
  { id: "docker",     icon: "▦", label: "Docker & Platform",   color: "#06b6d4" },
  { id: "structure",  icon: "⊞", label: "Project Structure",   color: "#e879f9" },
  { id: "roadmap",    icon: "▷", label: "Roadmap",             color: "#34d399" },
];

const Code = ({ children, color = "#00d4ff" }) => (
  <pre style={{
    background: "#030b12", border: `1px solid ${color}25`,
    borderLeft: `3px solid ${color}`, borderRadius: 6,
    padding: "14px 16px", margin: "10px 0", overflowX: "auto",
    fontFamily: "'JetBrains Mono','Fira Code',monospace",
    fontSize: 12, lineHeight: 1.8, color: "#8ab8cc",
  }}>{children}</pre>
);

const H = ({ children, color }) => (
  <div style={{
    color, fontFamily: "monospace", fontSize: 10,
    letterSpacing: "2px", textTransform: "uppercase",
    margin: "24px 0 10px",
    display: "flex", alignItems: "center", gap: 8,
  }}>
    <div style={{ width: 16, height: 1, background: color, opacity: .5 }} />
    {children}
    <div style={{ flex: 1, height: 1, background: color, opacity: .1 }} />
  </div>
);

const Tag = ({ t, c }) => (
  <span style={{
    display: "inline-block", background: `${c}15`,
    border: `1px solid ${c}40`, color: c,
    borderRadius: 4, padding: "2px 9px",
    fontSize: 11, fontFamily: "monospace", margin: "3px 3px 3px 0",
  }}>{t}</span>
);

const Callout = ({ text, color = "#f59e0b", icon = "⚡" }) => (
  <div style={{
    background: `${color}0e`, border: `1px solid ${color}30`,
    borderRadius: 7, padding: "10px 14px",
    color: `${color}cc`, fontSize: 13, margin: "12px 0", lineHeight: 1.7,
  }}>{icon} {text}</div>
);

const Row = ({ label, value, color }) => (
  <div style={{ display: "flex", gap: 12, padding: "5px 0", borderBottom: "1px solid #0e1f2d" }}>
    <div style={{ color, fontFamily: "monospace", fontSize: 12, minWidth: 180, flexShrink: 0 }}>{label}</div>
    <div style={{ color: "#6a8a9a", fontSize: 13 }}>{value}</div>
  </div>
);

const pages = {
  what: (
    <div>
      <p style={{ color: "#7a9aaa", fontSize: 14, lineHeight: 1.8, marginBottom: 20 }}>
        <strong style={{ color: "#00d4ff" }}>nexcpp</strong> is a <strong style={{ color: "#fff" }}>Model Context Protocol (MCP) server</strong> that gives any MCP-compatible AI agent — Claude, Codex, Cursor, Windsurf, and more — deep, structured knowledge of C++ development: language docs, build systems, package managers, sandbox compilation, GitHub automation, and cross-language interoperability.
      </p>

      <Callout color="#00d4ff" icon="◎" text="nexcpp is NOT a CLI tool. It is a server process that speaks JSON-RPC over stdio. AI agents connect to it and call its tools. It has no terminal UI and no user-facing commands." />

      <H color="#00d4ff">The Core Idea</H>
      <p style={{ color: "#6a8a9a", fontSize: 13, lineHeight: 1.75 }}>
        When an agent like Claude needs to build a C++ library, it doesn't know the right CMake incantations, the vcpkg port format, or how to set up pybind11 bindings. nexcpp fills that gap. The agent calls nexcpp's tools, gets precise answers from an offline C++ docs index, scaffolds complete packages, compiles them in a sandbox, and publishes them to GitHub — all through standard MCP tool calls.
      </p>

      <H color="#00d4ff">What nexcpp Is Not</H>
      {[
        ["Not a CLI", "It does not have commands you type in a terminal. Agents call it."],
        ["Not a C++ compiler", "It invokes system compilers (clang, gcc, msvc) as tools internally."],
        ["Not agent-specific", "Any MCP-compatible agent works. Claude, Codex, Cursor — all the same config pattern."],
        ["Not a C++ program", "nexcpp is written in Python using the official MCP SDK. It serves C++ intelligence."],
        ["Not standalone", "It is a subprocess launched by an MCP host (Claude Desktop, Claude Code, etc.)."],
      ].map(([l, v]) => <Row key={l} label={l} value={v} color="#00d4ff" />)}

      <H color="#00d4ff">What nexcpp Provides</H>
      {[
        ["Tools", "Functions the LLM calls: search docs, build, scaffold, sandbox, GitHub, analyze"],
        ["Resources", "File-like data agents subscribe to: C++ docs, project files, build logs"],
        ["Prompts", "Pre-written templates: 'scaffold a C++ library', 'fix this CMake error'"],
        ["Agent Skills", "Portable SKILL.md files agents install for guided C++ workflows"],
      ].map(([l, v]) => <Row key={l} label={l} value={v} color="#a855f7" />)}
    </div>
  ),

  how: (
    <div>
      <H color="#a855f7">The MCP Server/Client Model</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        MCP follows a strict client/server separation. nexcpp is the <strong style={{ color: "#a855f7" }}>server</strong>. Claude Desktop, Claude Code, Codex CLI, Cursor are <strong style={{ color: "#a855f7" }}>clients (hosts)</strong>. The client launches nexcpp as a subprocess and communicates over stdio using JSON-RPC 2.0.
      </p>

      <Code color="#a855f7">{`┌─────────────────────────────────────────────────────┐
│                   MCP Host / Client                  │
│  (Claude Desktop, Claude Code, Codex CLI, Cursor...) │
│                                                      │
│   User: "Create a header-only C++ JSON library"      │
│        ↓                                             │
│   LLM decides to call nexcpp tools                   │
│        ↓                                             │
│   JSON-RPC over stdio ──────────────────────────┐    │
└────────────────────────────────────────────────│────┘
                                                  │ stdin/stdout
┌────────────────────────────────────────────────▼────┐
│              nexcpp MCP Server (Python)              │
│                                                      │
│   tools/    resources/    prompts/    skills/        │
│   ─────     ─────────     ────────    ───────        │
│   search    cpp docs      scaffold    SKILL.md       │
│   build     build log     cmake_fix   files          │
│   sandbox   proj files    vcpkg_port                 │
│   github                                             │
│   analyze                                            │
└──────────────────────────────────────────────────────┘`}</Code>

      <H color="#a855f7">Transport: stdio (default)</H>
      <Callout color="#f59e0b" icon="⚡" text="For STDIO transport: nexcpp NEVER writes to stdout. All logging goes to stderr. stdout is reserved exclusively for JSON-RPC messages to the host." />
      <p style={{ color: "#6a8a9a", fontSize: 13, lineHeight: 1.75 }}>
        The host launches nexcpp as a subprocess. nexcpp reads JSON-RPC requests from stdin, handles them, and writes JSON-RPC responses to stdout. This is the standard local MCP pattern used by all official examples (weather server, etc.).
      </p>

      <H color="#a855f7">How Agents Connect</H>
      <p style={{ color: "#6a8a9a", fontSize: 13, lineHeight: 1.75 }}>
        Every MCP client has a config file where you register servers. Adding nexcpp to Claude Desktop, Claude Code, Codex, or Cursor is the same pattern: register the command that launches the server process.
      </p>
      <Code color="#a855f7">{`# claude_desktop_config.json  (Claude Desktop)
# %APPDATA%\\Claude\\claude_desktop_config.json (Windows)
# ~/Library/Application Support/Claude/claude_desktop_config.json (macOS)

{
  "mcpServers": {
    "nexcpp": {
      "command": "uv",
      "args": ["--directory", "/path/to/nexcpp", "run", "server.py"]
    }
  }
}

# That's all. Restart the client. nexcpp tools appear automatically.`}</Code>

      <H color="#a855f7">Message Flow</H>
      {[
        ["1. User prompt", "User asks agent to 'create a header-only C++ JSON parsing library'"],
        ["2. LLM reasoning", "Agent sees available nexcpp tools and decides which to call"],
        ["3. Tool call", "Agent sends tools/call JSON-RPC to nexcpp via stdio"],
        ["4. nexcpp executes", "nexcpp runs the tool: scaffolds files, invokes cmake, etc."],
        ["5. Result returned", "nexcpp returns structured text/JSON result to the agent"],
        ["6. Agent continues", "Agent reads results, may call more tools, then responds to user"],
      ].map(([l, v]) => <Row key={l} label={l} value={v} color="#a855f7" />)}
    </div>
  ),

  primitives: (
    <div>
      <H color="#f59e0b">The Three MCP Primitives</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 20 }}>
        MCP defines exactly three capability types. nexcpp implements all three correctly.
      </p>

      {[
        {
          name: "Tools", color: "#10b981",
          def: "Functions that the LLM can call (with user approval). The agent actively decides to invoke a tool based on context.",
          analogy: "Like calling a function in code — the agent picks the tool, passes arguments, gets a result back.",
          examples: ["search_cpp_docs", "build_project", "run_snippet", "generate_package", "analyze_code", "github_op"],
        },
        {
          name: "Resources", color: "#ec4899",
          def: "File-like data that clients can read on demand. Resources are passive — the client reads them, the LLM doesn't call them like functions.",
          analogy: "Like reading a file or URL. The agent or user browses and subscribes to resource URIs.",
          examples: ["nexcpp://docs/std/vector", "nexcpp://docs/cmake/find_package", "nexcpp://project/files", "nexcpp://build/log/latest"],
        },
        {
          name: "Prompts", color: "#f59e0b",
          def: "Pre-written reusable templates that help users accomplish specific tasks. Exposed as slash commands or template invocations in the client.",
          analogy: "Like a macro or snippet — a structured starting point the user picks from a menu.",
          examples: ["cpp_library_scaffold", "cmake_error_fix", "vcpkg_port_authoring", "pybind11_binding", "sanitizer_debug"],
        },
      ].map(p => (
        <div key={p.name} style={{ border: `1px solid ${p.color}33`, borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <div style={{ color: p.color, fontWeight: 700, fontSize: 16, marginBottom: 6 }}>{p.name}</div>
          <p style={{ color: "#8aacba", fontSize: 13, lineHeight: 1.7, margin: "0 0 8px" }}>{p.def}</p>
          <p style={{ color: "#4a6a7a", fontSize: 12, fontStyle: "italic", margin: "0 0 10px" }}>Analogy: {p.analogy}</p>
          <div style={{ display: "flex", flexWrap: "wrap" }}>
            {p.examples.map(e => <Tag key={e} t={e} c={p.color} />)}
          </div>
        </div>
      ))}
    </div>
  ),

  tools: (
    <div>
      <H color="#10b981">All nexcpp Tools</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        These are the functions agents call via MCP <code style={{ color: "#10b981" }}>tools/call</code>. Each is declared with a name, description, and JSON Schema for input validation.
      </p>

      {[
        {
          name: "search_cpp_docs", color: "#10b981",
          desc: "Search the offline C++ documentation index. Covers the C++ standard library, CMake, vcpkg, Conan, Boost, Qt, LLVM, and common libraries.",
          inputs: [
            { n: "query", t: "string", r: true, d: "Symbol name, topic, or natural language (e.g. 'std::ranges::transform', 'RAII', 'how to use coroutines')" },
            { n: "source", t: "string", r: false, d: "Filter: std | cmake | vcpkg | conan | boost | qt | llvm | all (default: all)" },
            { n: "cpp_std", t: "string", r: false, d: "Filter by standard version: 11 | 14 | 17 | 20 | 23" },
            { n: "max_results", t: "integer", r: false, d: "Max results (default 5, max 20)" },
          ],
          returns: "Array of DocEntry: symbol, header, since, brief, signature, example, url, source",
        },
        {
          name: "generate_package", color: "#10b981",
          desc: "Scaffold a complete C++ library or executable from scratch. Generates all files: headers, sources, CMakeLists.txt, vcpkg.json, tests, CI workflow, README.",
          inputs: [
            { n: "name", t: "string", r: true, d: "Package name (snake_case)" },
            { n: "description", t: "string", r: true, d: "What the library does" },
            { n: "kind", t: "string", r: false, d: "header-only | static | shared | executable (default: static)" },
            { n: "cpp_std", t: "string", r: false, d: "17 | 20 | 23 (default: 20)" },
            { n: "test_framework", t: "string", r: false, d: "catch2 | gtest | doctest | none (default: catch2)" },
            { n: "package_managers", t: "array", r: false, d: "vcpkg | conan | cpm (default: [vcpkg])" },
            { n: "dependencies", t: "array", r: false, d: "List of vcpkg/Conan dependency names" },
            { n: "output_dir", t: "string", r: false, d: "Where to write files (default: ./<name>/)" },
            { n: "ci", t: "boolean", r: false, d: "Generate GitHub Actions CI workflow (default: true)" },
          ],
          returns: "List of created file paths + summary",
        },
        {
          name: "build_project", color: "#10b981",
          desc: "Configure, build, and test a C++ project. Auto-detects CMake, Meson, or Bazel. Returns build output and artifact paths.",
          inputs: [
            { n: "project_dir", t: "string", r: false, d: "Path to project root (default: cwd)" },
            { n: "build_type", t: "string", r: false, d: "Debug | Release | RelWithDebInfo (default: Debug)" },
            { n: "target", t: "string", r: false, d: "Specific build target (default: all)" },
            { n: "run_tests", t: "boolean", r: false, d: "Run tests after build (default: true)" },
            { n: "sandbox", t: "boolean", r: false, d: "Run in Docker container for isolation (default: false)" },
            { n: "sanitizers", t: "array", r: false, d: "asan | ubsan | tsan | msan" },
            { n: "static_analysis", t: "boolean", r: false, d: "Run clang-tidy (default: false)" },
          ],
          returns: "Build output log, test results, artifact paths, any errors with suggestions",
        },
        {
          name: "run_snippet", color: "#10b981",
          desc: "Compile and run a C++ snippet in an isolated sandbox. Fast in-process compilation for quick experiments.",
          inputs: [
            { n: "code", t: "string", r: true, d: "C++ source code to compile and run" },
            { n: "compiler", t: "string", r: false, d: "gcc | clang (default: clang)" },
            { n: "std", t: "string", r: false, d: "17 | 20 | 23 (default: 20)" },
            { n: "flags", t: "array", r: false, d: "Extra compiler flags" },
            { n: "stdin", t: "string", r: false, d: "Input to pass to the program" },
            { n: "timeout", t: "integer", r: false, d: "Timeout in seconds (default: 10)" },
          ],
          returns: "stdout, stderr, exit code, compile errors if any",
        },
        {
          name: "analyze_code", color: "#10b981",
          desc: "Run static analysis on a C++ file or project using clang-tidy and/or cppcheck.",
          inputs: [
            { n: "path", t: "string", r: true, d: "File or directory to analyze" },
            { n: "tool", t: "string", r: false, d: "clang-tidy | cppcheck | all (default: clang-tidy)" },
            { n: "checks", t: "string", r: false, d: "clang-tidy check string (default: *)" },
            { n: "fix", t: "boolean", r: false, d: "Auto-apply fixits (default: false)" },
          ],
          returns: "List of diagnostics with file:line, severity, message, suggested fix",
        },
        {
          name: "manage_file", color: "#10b981",
          desc: "Create, read, update, delete, or list project files. Supports patch/diff application and template instantiation.",
          inputs: [
            { n: "op", t: "string", r: true, d: "read | write | append | delete | move | patch | list" },
            { n: "path", t: "string", r: false, d: "File or directory path" },
            { n: "content", t: "string", r: false, d: "File content for write/append" },
            { n: "patch", t: "string", r: false, d: "Unified diff to apply" },
          ],
          returns: "File content, operation result, or directory listing",
        },
        {
          name: "generate_bridge", color: "#10b981",
          desc: "Generate FFI bindings or interop code between C++ and another language.",
          inputs: [
            { n: "target_lang", t: "string", r: true, d: "python | rust | go | node | wasm | java" },
            { n: "header", t: "string", r: true, d: "C++ header file to bind" },
            { n: "method", t: "string", r: false, d: "Auto-picks best: pybind11 / cxx / cgo / napi / emscripten / jni" },
            { n: "output_dir", t: "string", r: false, d: "Where to write generated bindings" },
          ],
          returns: "Generated binding files + build instructions",
        },
        {
          name: "github_op", color: "#10b981",
          desc: "Perform GitHub operations: create repos, open PRs, publish releases, manage issues, generate CI workflows.",
          inputs: [
            { n: "op", t: "string", r: true, d: "create_repo | open_pr | create_issue | create_release | push | generate_workflow | publish_package" },
            { n: "repo", t: "string", r: false, d: "owner/repo" },
            { n: "title", t: "string", r: false, d: "Title for PR or issue" },
            { n: "body", t: "string", r: false, d: "Body for PR, issue, or release" },
            { n: "tag", t: "string", r: false, d: "Tag name for release" },
            { n: "branch", t: "string", r: false, d: "Branch name" },
          ],
          returns: "Created resource URL, workflow YAML, or operation result",
        },
      ].map(tool => (
        <div key={tool.name} style={{ border: `1px solid ${tool.color}22`, borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <div style={{ color: tool.color, fontFamily: "monospace", fontWeight: 700, fontSize: 14, marginBottom: 6 }}>{tool.name}</div>
          <p style={{ color: "#7a9aaa", fontSize: 13, margin: "0 0 12px", lineHeight: 1.65 }}>{tool.desc}</p>
          <div style={{ fontSize: 11, color: "#2a4a5a", letterSpacing: "1px", marginBottom: 6, fontFamily: "monospace" }}>INPUT SCHEMA</div>
          {tool.inputs.map(i => (
            <div key={i.n} style={{ display: "flex", gap: 10, padding: "3px 0", fontSize: 12 }}>
              <span style={{ color: tool.color, fontFamily: "monospace", minWidth: 150, flexShrink: 0 }}>{i.n}{i.r ? "" : "?"}</span>
              <span style={{ color: "#4a6070", fontFamily: "monospace", minWidth: 60, flexShrink: 0 }}>{i.t}</span>
              <span style={{ color: "#4a6070" }}>{i.d}</span>
            </div>
          ))}
          <div style={{ marginTop: 8, fontSize: 12, color: "#3a6a5a" }}>
            <span style={{ color: "#10b981", fontFamily: "monospace" }}>returns </span>{tool.returns}
          </div>
        </div>
      ))}
    </div>
  ),

  resources: (
    <div>
      <H color="#ec4899">MCP Resources in nexcpp</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        Resources are file-like data that agents read via URI. Agents subscribe to resources for live updates (e.g. a streaming build log). Resources use URI templates with path parameters.
      </p>
      <Callout color="#ec4899" icon="◈" text="Resources are READ-ONLY from the agent's perspective. The agent calls resources/read with a URI. nexcpp responds with text content or binary data." />

      {[
        {
          group: "C++ Documentation",
          color: "#ec4899",
          items: [
            { uri: "nexcpp://docs/std/{symbol}", desc: "C++ standard library reference for a specific symbol (e.g. nexcpp://docs/std/vector)" },
            { uri: "nexcpp://docs/cmake/{topic}", desc: "CMake documentation (e.g. nexcpp://docs/cmake/find_package)" },
            { uri: "nexcpp://docs/vcpkg/{package}", desc: "vcpkg package information and port details" },
            { uri: "nexcpp://docs/conan/{recipe}", desc: "Conan recipe documentation" },
            { uri: "nexcpp://docs/boost/{lib}", desc: "Boost library documentation (e.g. nexcpp://docs/boost/asio)" },
            { uri: "nexcpp://docs/index", desc: "Full documentation index — list of all indexed symbols and topics" },
          ],
        },
        {
          group: "Project State",
          color: "#f97316",
          items: [
            { uri: "nexcpp://project/files", desc: "File tree of the current project directory" },
            { uri: "nexcpp://project/config", desc: "Current nexcpp project config (.nexcpp/config.toml)" },
            { uri: "nexcpp://project/build-system", desc: "Detected build system info (CMakeLists.txt, presets, etc.)" },
            { uri: "nexcpp://project/dependencies", desc: "Current vcpkg.json or conanfile.py dependency list" },
          ],
        },
        {
          group: "Build & Analysis Logs",
          color: "#10b981",
          items: [
            { uri: "nexcpp://build/log/latest", desc: "Full output of the most recent build" },
            { uri: "nexcpp://build/log/{id}", desc: "Output of a specific build run (subscribable for streaming)" },
            { uri: "nexcpp://analysis/report/latest", desc: "Latest clang-tidy / cppcheck report" },
            { uri: "nexcpp://sandbox/log/{id}", desc: "Snippet run output (subscribable for live output)" },
          ],
        },
        {
          group: "Plugin & Skill Registry",
          color: "#a855f7",
          items: [
            { uri: "nexcpp://plugins/list", desc: "All installed plugins (local + global scope)" },
            { uri: "nexcpp://skills/list", desc: "All available Agent Skills" },
            { uri: "nexcpp://skills/{name}", desc: "Full SKILL.md content for a named skill" },
          ],
        },
      ].map(g => (
        <div key={g.group} style={{ marginBottom: 20 }}>
          <div style={{ color: g.color, fontFamily: "monospace", fontSize: 11, letterSpacing: "1.5px", marginBottom: 8 }}>▸ {g.group}</div>
          {g.items.map(i => (
            <div key={i.uri} style={{ display: "flex", gap: 12, padding: "5px 0 5px 12px", borderBottom: "1px solid #0d1d2d" }}>
              <span style={{ color: g.color, fontFamily: "monospace", fontSize: 11, minWidth: 300, flexShrink: 0 }}>{i.uri}</span>
              <span style={{ color: "#5a7080", fontSize: 12 }}>{i.desc}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  ),

  prompts: (
    <div>
      <H color="#84cc16">MCP Prompts</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        Prompts are pre-written templates exposed in the client's prompt menu. When a user picks one, the agent receives a structured prompt that guides it through a specific C++ task.
      </p>

      {[
        { name: "cpp_library_scaffold", color: "#84cc16", args: ["name", "description", "kind"], desc: "Guides the agent through creating a complete C++ library from scratch: headers, sources, tests, CMake, vcpkg manifest, CI workflow, and README." },
        { name: "cmake_error_fix", color: "#84cc16", args: ["error_output"], desc: "Takes raw CMake error output and guides the agent through diagnosing and fixing the root cause using nexcpp docs and managed file edits." },
        { name: "vcpkg_port_authoring", color: "#84cc16", args: ["library_name", "version", "github_url"], desc: "Step-by-step guide for writing a vcpkg port from scratch: portfile.cmake, vcpkg.json manifest, usage file, CI integration." },
        { name: "pybind11_binding", color: "#84cc16", args: ["header_file", "module_name"], desc: "Guides the agent through generating pybind11 bindings, setting up CMake for the Python extension, and building/testing the module." },
        { name: "sanitizer_debug", color: "#84cc16", args: ["asan_output"], desc: "Takes AddressSanitizer or UBSan output and guides a systematic bug-finding workflow using nexcpp's analyze and build tools." },
        { name: "github_release", color: "#84cc16", args: ["version", "notes"], desc: "Guides through building for release, running tests, tagging, generating a GitHub Release, and optionally publishing to vcpkg registry." },
      ].map(p => (
        <div key={p.name} style={{ border: `1px solid #84cc1625`, borderRadius: 8, padding: 14, marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
            <span style={{ color: "#84cc16", fontFamily: "monospace", fontWeight: 700, fontSize: 13 }}>{p.name}</span>
            {p.args.map(a => <Tag key={a} t={a} c="#84cc16" />)}
          </div>
          <p style={{ color: "#6a8a7a", fontSize: 13, margin: 0, lineHeight: 1.65 }}>{p.desc}</p>
        </div>
      ))}

      <H color="#84cc16">Agent Skills</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        Agent Skills are <strong style={{ color: "#84cc16" }}>portable SKILL.md instruction files</strong> that AI coding agents install to get domain knowledge for specific tasks. nexcpp ships a set of C++ development skills. Agents install them via their skills/plugin marketplace (e.g. <code style={{ color: "#84cc16" }}>/plugin install nexcpp-skills</code> in Claude Code).
      </p>
      <Callout color="#84cc16" icon="◉" text="Skills are NOT tools or prompts. They are SKILL.md files the agent reads to understand HOW to approach a task using nexcpp's tools. They encode expertise, not just a template." />

      {[
        { name: "cpp-from-scratch", desc: "Complete workflow for creating a C++ library end-to-end, from design to published vcpkg package" },
        { name: "cmake-mastery", desc: "CMake target model, modern CMake patterns, presets, cross-compilation, and debugging configuration errors" },
        { name: "vcpkg-authoring", desc: "Writing, testing, and publishing vcpkg ports and maintaining a private registry" },
        { name: "cpp-python-bridge", desc: "Exposing C++ code to Python using pybind11, CFFI, or ctypes — from headers to published wheel" },
        { name: "cpp-rust-bridge", desc: "C++/Rust interop with the cxx crate: bridge file authoring, Cargo+CMake integration, safety patterns" },
        { name: "sanitizer-debugging", desc: "Reading ASan/UBSan/TSan reports and systematically hunting memory bugs using nexcpp tools" },
        { name: "cpp-performance", desc: "Profiling with perf/Tracy, reading flamegraphs, benchmark authoring with Google Benchmark" },
        { name: "docker-cpp-dev", desc: "Setting up and using Docker-based C++ build environments via nexcpp's sandbox tool" },
      ].map(s => (
        <div key={s.name} style={{ display: "flex", gap: 12, padding: "7px 0", borderBottom: "1px solid #0d1d2d" }}>
          <span style={{ color: "#84cc16", fontFamily: "monospace", fontSize: 12, minWidth: 200, flexShrink: 0 }}>{s.name}</span>
          <span style={{ color: "#5a7a6a", fontSize: 13 }}>{s.desc}</span>
        </div>
      ))}
    </div>
  ),

  plugins: (
    <div>
      <H color="#f97316">Plugin System</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        nexcpp is extensible. Plugins are Python modules that add new Tools, Resources, or Prompts to the running server. Plugins are discovered from three scopes in priority order.
      </p>

      <Callout color="#f97316" icon="◇" text="Plugins extend the MCP server — they add more tools/resources/prompts. They are NOT separate agents or CLIs. They're Python files loaded by the nexcpp server at startup." />

      {[
        {
          scope: "Local Scope", color: "#10b981",
          path: ".nexcpp/plugins/",
          desc: "Project-specific plugins. Git-tracked with the project. Highest priority — override global plugins of the same name. Useful for project-specific doc sources or custom generators.",
          features: ["Auto-discovered when server starts in a project dir", "Hot-reloaded on file change (dev mode)", "Version-locked with the project", "Declared in .nexcpp/config.toml [plugins]"],
        },
        {
          scope: "Global Scope", color: "#a855f7",
          path: "~/.nexcpp/plugins/",
          desc: "User-wide plugins available in all projects. Installed via nexcpp's plugin management resource or manually dropped into the directory.",
          features: ["Persisted between sessions", "Managed via nexcpp://plugins/install resource", "Signed packages from the nexcpp plugin registry", "Lower priority than local plugins"],
        },
        {
          scope: "Sandbox Scope", color: "#f59e0b",
          path: "/tmp/nexcpp-sandbox-<id>/plugins/",
          desc: "Ephemeral plugins created for a specific sandbox build session. Automatically destroyed when the session ends. Cannot escape the sandbox.",
          features: ["Generated per-session by the sandbox tool", "Isolated from host file system", "Can be promoted to local scope if approved", "Used for testing plugin ideas safely"],
        },
      ].map(s => (
        <div key={s.scope} style={{ border: `1px solid ${s.color}33`, borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
            <div style={{ color: s.color, fontWeight: 700, fontSize: 14 }}>{s.scope}</div>
            <div style={{ color: s.color, fontFamily: "monospace", fontSize: 10, background: `${s.color}15`, padding: "2px 8px", borderRadius: 4 }}>{s.path}</div>
          </div>
          <p style={{ color: "#7a8a9a", fontSize: 13, margin: "0 0 10px", lineHeight: 1.65 }}>{s.desc}</p>
          {s.features.map(f => <div key={f} style={{ color: "#4a6070", fontSize: 12, padding: "2px 0" }}><span style={{ color: s.color }}>✓ </span>{f}</div>)}
        </div>
      ))}

      <H color="#f97316">Plugin Module Format</H>
      <Code color="#f97316">{`# .nexcpp/plugins/my_plugin.py
# A nexcpp plugin — just a Python module with a register() function

from nexcpp.sdk import PluginContext

def register(ctx: PluginContext):
    """Called once when nexcpp loads this plugin."""

    # Add a new tool
    @ctx.tool(description="Generate a custom DSL parser in C++")
    def generate_parser(grammar: str, output_dir: str) -> str:
        # ... implementation
        return f"Generated parser at {output_dir}"

    # Add a new resource
    @ctx.resource("nexcpp://my-org/conventions")
    def my_org_conventions(uri: str) -> str:
        return open(".nexcpp/conventions.md").read()

    # Add a new prompt
    @ctx.prompt(description="Scaffold our internal service template")
    def internal_service_scaffold(name: str, team: str) -> str:
        return f"Create an internal C++ service called {name} for team {team}..."

# Plugin metadata (optional, for registry publishing)
PLUGIN_META = {
    "name": "my-org-cpp",
    "version": "1.0.0",
    "description": "Custom C++ tooling for my org",
    "author": "my-org",
}`}</Code>
    </div>
  ),

  clients: (
    <div>
      <H color="#3b82f6">Connecting AI Agents to nexcpp</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        Because nexcpp follows the standard MCP protocol, <strong style={{ color: "#3b82f6" }}>any MCP-compatible agent works out of the box</strong>. There are no special adapters, no per-agent code, no CLI wrappers. You register nexcpp in the agent's config file and restart. The agent discovers all tools, resources, and prompts automatically.
      </p>

      {[
        {
          client: "Claude Desktop",
          color: "#00d4ff",
          config: `# ~/Library/Application Support/Claude/claude_desktop_config.json
# (macOS) or %APPDATA%\\Claude\\claude_desktop_config.json (Windows)

{
  "mcpServers": {
    "nexcpp": {
      "command": "uv",
      "args": [
        "--directory", "/absolute/path/to/nexcpp",
        "run", "server.py"
      ]
    }
  }
}`,
          notes: "Restart Claude Desktop after editing. Tools appear in the + menu under Connectors.",
        },
        {
          client: "Claude Code (CLI)",
          color: "#a855f7",
          config: `# Claude Code reads .claude/settings.json in the project,
# OR the global ~/.claude/settings.json

{
  "mcpServers": {
    "nexcpp": {
      "command": "uv",
      "args": ["--directory", "/path/to/nexcpp", "run", "server.py"],
      "type": "stdio"
    }
  }
}

# Or add via CLI:
# claude mcp add nexcpp -- uv --directory /path/to/nexcpp run server.py`,
          notes: "Claude Code also reads CLAUDE.md in the project root. nexcpp can generate this file via the manage_file tool to give Claude project context.",
        },
        {
          client: "Codex CLI",
          color: "#f59e0b",
          config: `# ~/.codex/config.yaml  (Codex CLI configuration)

mcp_servers:
  nexcpp:
    command: uv
    args:
      - --directory
      - /absolute/path/to/nexcpp
      - run
      - server.py`,
          notes: "Codex reads its config from ~/.codex/. Once registered, nexcpp tools are available in every Codex session.",
        },
        {
          client: "Cursor / Windsurf / VS Code",
          color: "#10b981",
          config: `# .cursor/mcp.json (project-local) or
# ~/.cursor/mcp.json (global)

{
  "mcpServers": {
    "nexcpp": {
      "command": "uv",
      "args": ["--directory", "/path/to/nexcpp", "run", "server.py"]
    }
  }
}

# Windsurf: ~/.codeium/windsurf/mcp_config.json (same format)
# VS Code + Copilot: .vscode/mcp.json`,
          notes: "All these editors use the same JSON-RPC MCP format. The config key names match.",
        },
        {
          client: "Remote / SSE mode (any HTTP client)",
          color: "#f97316",
          config: `# Run nexcpp in SSE mode for remote agents
uv run server.py --transport sse --port 7777

# Client config for remote SSE:
{
  "mcpServers": {
    "nexcpp": {
      "url": "http://localhost:7777/sse",
      "type": "sse"
    }
  }
}

# Or run in Docker and expose the port:
docker run -p 7777:7777 nexcpp/server --transport sse`,
          notes: "SSE mode is for team-shared deployments. One running nexcpp instance serves multiple developers.",
        },
      ].map(c => (
        <div key={c.client} style={{ border: `1px solid ${c.color}33`, borderRadius: 8, padding: 16, marginBottom: 20 }}>
          <div style={{ color: c.color, fontWeight: 700, fontSize: 14, marginBottom: 10 }}>{c.client}</div>
          <Code color={c.color}>{c.config}</Code>
          <div style={{ color: "#4a6a5a", fontSize: 12, marginTop: 8 }}>
            <span style={{ color: c.color }}>ℹ </span>{c.notes}
          </div>
        </div>
      ))}
    </div>
  ),

  docker: (
    <div>
      <H color="#06b6d4">Docker Support</H>
      <p style={{ color: "#7a9aaa", fontSize: 13, lineHeight: 1.75, marginBottom: 16 }}>
        Docker is used in nexcpp in two distinct ways: running the <strong style={{ color: "#06b6d4" }}>nexcpp server itself</strong> in a container, and running <strong style={{ color: "#06b6d4" }}>C++ build sandboxes</strong> inside Docker via the build and run_snippet tools.
      </p>

      <H color="#06b6d4">1 — The nexcpp Server in Docker</H>
      <Code color="#06b6d4">{`# docker/Dockerfile — Run nexcpp itself as a container
FROM python:3.12-slim

# Install system C++ toolchain (for build/analyze tools)
RUN apt-get update && apt-get install -y \\
    build-essential clang clang-tidy cmake ninja-build \\
    git curl ca-certificates \\
    && rm -rf /var/lib/apt/lists/*

# Install vcpkg
ENV VCPKG_ROOT=/opt/vcpkg
RUN git clone --depth 1 https://github.com/microsoft/vcpkg $VCPKG_ROOT \\
    && $VCPKG_ROOT/bootstrap-vcpkg.sh -disableMetrics

# Install nexcpp Python dependencies
WORKDIR /nexcpp
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

# Copy nexcpp source
COPY . .

# Expose SSE port (for remote agent connections)
EXPOSE 7777

# Default: stdio transport (for local Docker usage)
ENTRYPOINT ["uv", "run", "server.py"]
CMD ["--transport", "stdio"]`}</Code>

      <Code color="#06b6d4">{`# docker-compose.yml — Team deployment (SSE mode)
services:
  nexcpp:
    build: .
    image: nexcpp/server:latest
    ports:
      - "7777:7777"
    environment:
      - NEXCPP_TRANSPORT=sse
      - NEXCPP_GITHUB_TOKEN=${"${GITHUB_TOKEN}"}
    volumes:
      - nexcpp-docs:/nexcpp/docs_mirror   # persistent doc index
      - vcpkg-cache:/opt/vcpkg/installed  # persistent vcpkg cache
    command: ["--transport", "sse", "--port", "7777"]

volumes:
  nexcpp-docs:
  vcpkg-cache:`}</Code>

      <H color="#06b6d4">2 — Docker Sandboxes Inside nexcpp Tools</H>
      <p style={{ color: "#6a8a9a", fontSize: 13, lineHeight: 1.75 }}>
        The <code style={{ color: "#06b6d4" }}>build_project</code> and <code style={{ color: "#06b6d4" }}>run_snippet</code> tools spin up Docker containers for isolated, reproducible builds when <code style={{ color: "#06b6d4" }}>sandbox: true</code>.
      </p>
      {[
        { img: "nexcpp/build-linux", desc: "Ubuntu 24.04 + GCC 14 + Clang 18 + vcpkg", size: "~1.2GB" },
        { img: "nexcpp/build-windows", desc: "Windows Server + MSVC 2022 (via wine/cross)", size: "~2.5GB" },
        { img: "nexcpp/build-macos", desc: "macOS cross-compile sysroot (Clang)", size: "~1.8GB" },
        { img: "nexcpp/build-arm64", desc: "aarch64 cross-compilation (QEMU)", size: "~1.4GB" },
        { img: "nexcpp/build-wasm", desc: "Emscripten + WASI toolchain", size: "~1.6GB" },
        { img: "nexcpp/analyze", desc: "clang-tidy + cppcheck only (lightweight)", size: "~500MB" },
      ].map(i => (
        <div key={i.img} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #0d1d2d", fontSize: 12 }}>
          <span style={{ color: "#06b6d4", fontFamily: "monospace" }}>{i.img}</span>
          <span style={{ color: "#4a6070", flex: 1, margin: "0 16px" }}>{i.desc}</span>
          <span style={{ color: "#2a5060", fontFamily: "monospace" }}>{i.size}</span>
        </div>
      ))}

      <H color="#06b6d4">Cross-Platform Matrix</H>
      {[
        ["Linux", "Ubuntu 22/24, Debian, Alpine (musl/static)", "GCC 12–14, Clang 16–18"],
        ["macOS", "macOS 13+, Universal binary (x86_64 + arm64)", "Apple Clang, Homebrew LLVM"],
        ["Windows", "Windows 10/11, Server 2022, WSL2", "MSVC 2022, MinGW-w64, Clang-cl"],
        ["Cross", "ARM64, RISC-V, MIPS, WebAssembly", "Crosstool-NG, Emscripten, WASI SDK"],
      ].map(([p, v, t]) => (
        <div key={p} style={{ display: "flex", gap: 16, padding: "6px 0", borderBottom: "1px solid #0d1d2d", fontSize: 12 }}>
          <span style={{ color: "#06b6d4", fontFamily: "monospace", minWidth: 80 }}>{p}</span>
          <span style={{ color: "#4a6070", flex: 1 }}>{v}</span>
          <span style={{ color: "#2a5a6a" }}>{t}</span>
        </div>
      ))}
    </div>
  ),

  structure: (
    <div>
      <H color="#e879f9">Repository Structure</H>
      <Code color="#e879f9">{`nexcpp/
│
├── server.py                      # Entry point — FastMCP server
├── pyproject.toml                 # Python project (uv / pip)
├── uv.lock                        # Locked dependencies
│
├── tools/                         # MCP Tool implementations
│   ├── __init__.py                # Auto-registers all tools
│   ├── docs.py                    # search_cpp_docs
│   ├── generate.py                # generate_package, generate_bridge
│   ├── build.py                   # build_project, run_snippet
│   ├── files.py                   # manage_file
│   ├── analyze.py                 # analyze_code
│   └── github.py                  # github_op
│
├── resources/                     # MCP Resource implementations
│   ├── __init__.py
│   ├── cpp_docs.py                # nexcpp://docs/std/*, cmake/*, vcpkg/*
│   ├── project.py                 # nexcpp://project/*
│   └── build_log.py               # nexcpp://build/log/*
│
├── prompts/                       # MCP Prompt implementations
│   ├── __init__.py
│   ├── scaffold.py                # cpp_library_scaffold
│   ├── cmake.py                   # cmake_error_fix
│   ├── vcpkg.py                   # vcpkg_port_authoring
│   └── bridge.py                  # pybind11_binding, rust_bridge
│
├── skills/                        # Agent Skills (SKILL.md files)
│   ├── cpp-from-scratch/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── cmake-mastery/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── vcpkg-authoring/
│   ├── cpp-python-bridge/
│   ├── cpp-rust-bridge/
│   └── sanitizer-debugging/
│
├── docs_mirror/                   # Offline documentation (fetched separately)
│   ├── cppreference/              # Offline cppreference HTML mirror
│   ├── cmake/                     # CMake docs mirror
│   ├── vcpkg/                     # vcpkg package catalog
│   └── boost/                     # Boost docs mirror
│
├── doc_index/                     # Built documentation index
│   ├── index.py                   # BM25 + symbol lookup engine
│   ├── parsers/
│   │   ├── cppreference.py        # Parse cppreference HTML
│   │   ├── cmake_docs.py          # Parse CMake docs
│   │   └── vcpkg_catalog.py       # Parse vcpkg package JSON
│   └── fetch.py                   # nexcpp docs fetch <source>
│
├── sandbox/                       # Build sandbox implementation
│   ├── quick.py                   # In-process compile+run
│   ├── docker_sandbox.py          # Docker-based sandbox
│   └── pipeline.py                # Full build pipeline
│
├── github/                        # GitHub API client
│   ├── client.py                  # REST + GraphQL
│   └── workflow_gen.py            # CI workflow generator
│
├── sdk/                           # Plugin SDK (for plugin authors)
│   ├── context.py                 # PluginContext class
│   └── decorators.py              # @ctx.tool, @ctx.resource, @ctx.prompt
│
├── plugins/                       # Plugin loader
│   ├── loader.py                  # 3-scope discovery + loading
│   └── builtin/                   # Built-in plugins
│       ├── cpp_analyzer.py        # clang-tidy plugin
│       └── cmake_helper.py        # CMake intelligence plugin
│
├── config.py                      # Configuration loader (TOML)
│
├── .nexcpp/                       # Project-local config (when used in a project)
│   ├── config.toml                # Server config
│   └── plugins/                   # Local plugin directory
│
├── docker/
│   ├── Dockerfile                 # nexcpp server image
│   ├── build-linux.Dockerfile     # Linux C++ build sandbox
│   ├── build-arm64.Dockerfile     # ARM64 cross-compile sandbox
│   ├── build-wasm.Dockerfile      # Emscripten sandbox
│   └── docker-compose.yml         # Team deployment
│
├── tests/
│   ├── test_tools.py              # Tool unit tests
│   ├── test_resources.py          # Resource tests
│   ├── test_prompts.py            # Prompt tests
│   └── test_e2e.py                # End-to-end MCP protocol tests
│
└── .github/
    └── workflows/
        ├── ci.yml                 # Test on Linux/macOS/Windows
        └── docker.yml             # Build and push Docker images`}</Code>
    </div>
  ),

  roadmap: (
    <div>
      <H color="#34d399">Development Roadmap</H>
      {[
        {
          phase: "Phase 1 — Core MCP Server", weeks: "Weeks 1–3", color: "#00d4ff",
          items: [
            "FastMCP server entry point (server.py) with stdio transport",
            "Tool skeleton: search_cpp_docs, manage_file, run_snippet",
            "C++ standard library doc index (offline cppreference mirror)",
            "Basic BM25 search over indexed symbols",
            "Claude Desktop and Claude Code config validation",
            "Tests: MCP Inspector integration, tool call round-trips",
          ],
        },
        {
          phase: "Phase 2 — Full Documentation", weeks: "Weeks 4–6", color: "#a855f7",
          items: [
            "Full doc index: CMake, vcpkg, Conan, Boost, LLVM, Qt, spdlog, fmt",
            "Resources: nexcpp://docs/* URI tree fully implemented",
            "Resource subscription (streaming build logs)",
            "Symbol trie for exact lookup (std::vector::push_back etc.)",
            "SSE transport mode for remote/team deployments",
            "Codex CLI and Cursor client config docs",
          ],
        },
        {
          phase: "Phase 3 — Package Generation", weeks: "Weeks 7–9", color: "#f59e0b",
          items: [
            "generate_package tool: all file types (headers, sources, CMake, vcpkg, tests)",
            "CMakePackageConfig and GNUInstallDirs template",
            "vcpkg port file generator",
            "Conan recipe generator",
            "GitHub Actions CI workflow generator",
            "Prompts: cpp_library_scaffold, cmake_error_fix",
          ],
        },
        {
          phase: "Phase 4 — Build & Sandbox", weeks: "Weeks 10–12", color: "#10b981",
          items: [
            "build_project tool: auto-detect CMake/Meson/Bazel",
            "run_snippet: in-process clang compile + execute",
            "Docker sandbox integration (build_project with sandbox:true)",
            "analyze_code tool (clang-tidy + cppcheck)",
            "Sanitizer report parsing",
            "Cross-compile sandbox images (ARM64, WASM)",
          ],
        },
        {
          phase: "Phase 5 — Language Bridges & GitHub", weeks: "Weeks 13–16", color: "#ec4899",
          items: [
            "generate_bridge tool: pybind11, cxx, cgo, N-API, Emscripten",
            "github_op tool: repos, PRs, issues, releases, CI workflow push",
            "Prompts: pybind11_binding, rust_bridge, github_release",
            "Plugin system: 3-scope loader, Plugin SDK, hot-reload",
            "Built-in plugins: cpp_analyzer, cmake_helper",
          ],
        },
        {
          phase: "Phase 6 — Agent Skills & Polish", weeks: "Weeks 17–20", color: "#84cc16",
          items: [
            "Ship Agent Skills: cpp-from-scratch, cmake-mastery, vcpkg-authoring, sanitizer-debugging",
            "Publish mcp-server-dev compatible skill plugin to Claude Code marketplace",
            "Docker images: build-linux, build-arm64, build-wasm, analyze",
            "Windows MSVC support in sandbox",
            "Performance tuning: doc search < 50ms",
            "MCP Registry publication",
            "nexcpp.dev documentation site",
          ],
        },
      ].map(p => (
        <div key={p.phase} style={{ marginBottom: 22, borderLeft: `3px solid ${p.color}`, paddingLeft: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <div style={{ color: p.color, fontWeight: 700, fontSize: 14 }}>{p.phase}</div>
            <div style={{ color: p.color, fontFamily: "monospace", fontSize: 10, background: `${p.color}15`, padding: "2px 8px", borderRadius: 4 }}>{p.weeks}</div>
          </div>
          {p.items.map(i => (
            <div key={i} style={{ color: "#5a7a8a", fontSize: 13, padding: "3px 0", display: "flex", gap: 8 }}>
              <span style={{ color: p.color, flexShrink: 0, opacity: 0.7 }}>▷</span> {i}
            </div>
          ))}
        </div>
      ))}
    </div>
  ),
};

export default function NexcppPlan() {
  const [active, setActive] = useState("what");
  const cur = nav.find(n => n.id === active);

  return (
    <div style={{ display: "flex", height: "100vh", background: "#050d14", color: "#c0d4de", fontFamily: "'Inter','Segoe UI',sans-serif", overflow: "hidden" }}>
      {/* Sidebar */}
      <div style={{ width: 215, flexShrink: 0, background: "#070f18", borderRight: "1px solid #0d1d2c", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "18px 15px 14px", borderBottom: "1px solid #0d1d2c" }}>
          <div style={{ color: "#00d4ff", fontFamily: "monospace", fontSize: 18, fontWeight: 700, letterSpacing: "2px" }}>
            nex<span style={{ color: "#a855f7" }}>cpp</span>
          </div>
          <div style={{ color: "#1a3040", fontSize: 9, letterSpacing: "2px", marginTop: 2 }}>MCP SERVER — REDESIGNED</div>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "6px 0" }}>
          {nav.map(n => (
            <button key={n.id} onClick={() => setActive(n.id)} style={{
              width: "100%", textAlign: "left",
              background: active === n.id ? `${n.color}12` : "transparent",
              border: "none", borderLeft: `2px solid ${active === n.id ? n.color : "transparent"}`,
              color: active === n.id ? n.color : "#3a5a6a",
              padding: "8px 14px", cursor: "pointer",
              display: "flex", alignItems: "center", gap: 9,
              fontSize: 12, fontWeight: active === n.id ? 600 : 400,
              transition: "all 0.1s", lineHeight: 1.4,
            }}>
              <span style={{ fontSize: 13, flexShrink: 0 }}>{n.icon}</span>
              {n.label}
            </button>
          ))}
        </div>
        <div style={{ padding: "10px 14px", borderTop: "1px solid #0d1d2c" }}>
          <div style={{ color: "#0f2030", fontSize: 9, letterSpacing: "1px" }}>Python · FastMCP SDK</div>
          <div style={{ color: "#0f2030", fontSize: 9 }}>MCP 2024-11-05 Compliant</div>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <div style={{ padding: "17px 26px 13px", borderBottom: "1px solid #0d1d2c", background: "#060e16", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ color: cur?.color, fontSize: 18 }}>{cur?.icon}</span>
            <div style={{ color: "#ddeaf4", fontSize: 18, fontWeight: 700, letterSpacing: "-0.4px" }}>{cur?.label}</div>
          </div>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: "20px 26px" }}>
          {pages[active]}
        </div>
      </div>
    </div>
  );
}
