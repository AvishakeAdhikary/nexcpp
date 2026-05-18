---
name: sanitizer-debugging
description: "Read ASan / UBSan / TSan / MSan reports, narrow down bugs, and ship a fix. Use when the user is debugging a sanitizer crash, sees a heap-buffer-overflow or use-after-free message, has UndefinedBehaviorSanitizer warnings to fix, or wants to add sanitizer coverage to their build."
---

# Sanitizer Debugging

This skill is the canonical workflow for diagnosing and fixing
sanitizer-detected bugs: AddressSanitizer (ASan),
UndefinedBehaviorSanitizer (UBSan), ThreadSanitizer (TSan), and
MemorySanitizer (MSan).

## When to use

- "I got an ASan report — what does it mean?"
- "Fix this heap-buffer-overflow"
- "Run my project with sanitizers"
- "Why is TSan saying data race?"
- "Add sanitizer CI to my repo"

## When NOT to use

- General memory profiling (use `cpp-performance`)
- Compiler errors / link errors (use `cmake-mastery`)
- High-level performance tuning (use `cpp-performance`)

## Mental model

Each sanitizer instruments the binary at compile time to catch specific
classes of bugs at runtime. They are **not** mutually compatible; you
pick one per build:

| Sanitizer | Detects                                        | Slowdown |
|-----------|------------------------------------------------|----------|
| ASan      | heap/stack/global buffer overflows, UAF, leaks | 2-3×     |
| UBSan     | UB: signed overflow, oob enums, null deref     | 1.2×     |
| TSan      | data races, deadlocks                          | 5-15×    |
| MSan      | uninitialized memory reads                     | 3×       |

ASan + UBSan can be combined: `-fsanitize=address,undefined`. TSan and
MSan are mutually exclusive with ASan and each other.

## Step 1 — Run with sanitizers

Always start with ASan + UBSan:

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "Debug"
  sanitizers: ["asan", "ubsan"]
  run_tests: true
```

The build flags you should see in the configure log:
- `-fsanitize=address,undefined`
- `-fno-omit-frame-pointer`
- `-g`

If you don't see the sanitizer flags, the build system didn't pick them
up. Add them explicitly:

```cmake
target_compile_options(mylib PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
target_link_options(mylib PRIVATE -fsanitize=address,undefined)
```

For ASan to give symbols, ensure debug info is on (`-g`) and frame
pointers aren't omitted (`-fno-omit-frame-pointer`).

For ASan to give clean stack traces on Linux, install `llvm-symbolizer`
and ensure `ASAN_SYMBOLIZER_PATH` is set, or just have `llvm-symbolizer`
on PATH.

## Step 2 — Read the report

A typical ASan heap-buffer-overflow:

```
==12345==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x602000000018
READ of size 4 at 0x602000000018 thread T0
    #0 0x... in mylib::process(int*, int) src/mylib.cpp:42
    #1 0x... in main src/main.cpp:10
    #2 ...

0x602000000018 is located 0 bytes to the right of 8-byte region [0x602000000010,0x602000000018)
allocated by thread T0 here:
    #0 0x... in operator new(unsigned long)
    #1 0x... in main src/main.cpp:8

SUMMARY: AddressSanitizer: heap-buffer-overflow src/mylib.cpp:42 in mylib::process
```

Read the report in this order:

1. **The summary line** — what kind of error and where (file:line).
2. **The error stack trace** — the access that triggered.
3. **The allocation site** — where the buffer came from.
4. **Optional: the deallocation site** — for use-after-free.

## Step 3 — Read the relevant source

```yaml
tool: manage_file
args:
  op: "read"
  path: "src/mylib.cpp"
```

Focus on the line and 5-10 lines of context above. The bug is almost
always *exactly* at the line ASan points to, but the *root cause* may be
several lines up where the size assumption was made.

## Step 4 — Narrow the failure case

If the report came from a test, get a minimal reproducer:

```yaml
tool: run_snippet
args:
  code: |
    #include <iostream>
    int main() {
        int a[8] = {0};
        // Try to reproduce the OOB access in isolation
        std::cout << a[8] << "\n";
        return 0;
    }
  compiler: "clang"
  std: "20"
  flags: ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g"]
```

The snippet should crash with the same kind of report as the real
program. If it doesn't, you haven't isolated the bug yet.

## Step 5 — Diagnose the bug type

| ASan output                  | Typical cause                              |
|------------------------------|---------------------------------------------|
| heap-buffer-overflow         | wrong size in `new[]` / `malloc` / index   |
| stack-buffer-overflow        | array index OOB on a local                 |
| heap-use-after-free          | dangling pointer after delete/free         |
| use-after-scope              | reference to a stack object outlived scope |
| double-free                  | two paths free the same pointer            |
| memory leak                  | new without delete; flagged at exit        |
| container-overflow           | `vector::operator[]` past end              |

| UBSan output                 | Typical cause                               |
|------------------------------|---------------------------------------------|
| signed-integer-overflow      | a + b overflowed; use checked arithmetic    |
| division by zero             | denominator can be 0                        |
| null pointer dereference     | unchecked pointer                           |
| misaligned-pointer           | reinterpret_cast through wrong alignment    |
| enum value out of range      | cast to enum without bounds check           |
| vptr                         | virtual call on wrong type / freed object   |

| TSan output                  | Typical cause                               |
|------------------------------|---------------------------------------------|
| data race                    | two threads access shared data, ≥1 writes   |
| lock-order-inversion         | classic AB / BA deadlock pattern            |
| signal-unsafe call           | calling non-async-signal-safe in handler    |

## Step 6 — Apply the fix

Use `manage_file op=patch` to make surgical changes. Example fix for an
OOB:

```diff
--- a/src/mylib.cpp
+++ b/src/mylib.cpp
@@ -39,7 +39,7 @@ void process(int* data, int n) {
-    for (int i = 0; i <= n; ++i) {
+    for (int i = 0; i < n; ++i) {
         data[i] = data[i] * 2;
     }
 }
```

## Step 7 — Re-run sanitizers

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "Debug"
  sanitizers: ["asan", "ubsan"]
  run_tests: true
```

Verify the report is gone. Then check no new reports appeared.

## Step 8 — Run other sanitizers

After ASan+UBSan is clean, run TSan separately:

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "Debug"
  sanitizers: ["tsan"]
  run_tests: true
```

If you don't use threading, skip this.

MSan is only worth running if you suspect uninitialized reads. It
requires libc++/libstdc++ rebuilt with MSan; in practice, only enable in
docker (`docker-cpp-dev` image).

## Common patterns

### ASan: "container-overflow" on a known-bounded vector

```cpp
std::vector<int> v = {1, 2, 3};
auto* p = v.data();
p[3] = 4;   // ← container-overflow
```

`v.data()` gives a valid pointer for `[0, v.size())`. Writing past it is
UB even though the underlying allocation may have capacity. Use `push_back`
or `resize`.

### ASan: "heap-use-after-free" on a captured lambda

```cpp
std::function<void()> f;
{
    std::string s = "hi";
    f = [&s]() { std::cout << s; };
}
f();   // s is gone
```

Capture by value, or use shared_ptr to ensure lifetime.

### TSan: "data race" on atomic

`std::atomic<T>` operations are race-free for the underlying load/store,
but the *value* you load may still race if you use it to do non-atomic
work. TSan reports the data race on the non-atomic side. Fix: protect
the broader operation with a mutex.

### UBSan: "signed integer overflow" in size calculation

```cpp
int n = read_user_input();
int* buf = new int[n * 4];   // ← overflow if n > INT_MAX / 4
```

Cast to a wider type or use `std::size_t`:

```cpp
auto n = static_cast<std::size_t>(read_user_input());
int* buf = new int[n * 4];
```

## Disabling sanitizers for specific code

Sometimes you have intentional UB (e.g., a hardened crypto library that
does pointer alignment tricks). Use attributes:

```cpp
__attribute__((no_sanitize("undefined")))
int safe_intentional_ub() { ... }
```

Use sparingly — every suppression is a future bug.

## Suppression files

For third-party libraries you can't fix, write a suppression file:

```
# asan-suppressions.txt
leak:libthirdparty.so
race:libthirdparty.so::racy_function
```

Then `ASAN_OPTIONS=suppressions=$(pwd)/asan-suppressions.txt`.

## Adding sanitizer CI

```yaml
tool: github_op
args:
  op: "generate_workflow"
  template: "cpp-ci"
  args:
    name: "ci"
    sanitizers: ["asan", "ubsan", "tsan"]
```

The generated workflow should have separate jobs for each sanitizer
combo. TSan failures are often flaky on shared runners — consider
gating that job to a single OS.

## Tool reference quick card

- `build_project(..., sanitizers=[...])` — build & run with sanitizers
- `run_snippet(code, flags=["-fsanitize=..."])` — reproduce in isolation
- `manage_file(op=read|patch)` — read the source, apply the fix
- `analyze_code(path, checks="bugprone-*")` — find related bug patterns
- `nexcpp://build/log/latest` — full sanitizer output

## References

- AddressSanitizer: https://clang.llvm.org/docs/AddressSanitizer.html
- UBSan: https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html
- TSan: https://clang.llvm.org/docs/ThreadSanitizer.html
- MSan: https://clang.llvm.org/docs/MemorySanitizer.html
