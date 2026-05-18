---
name: cpp-performance
description: "Diagnose and improve C++ performance: profiling with perf and Tracy, generating flamegraphs, microbenchmarking with Google Benchmark, and reading optimization reports. Use when the user wants to make their C++ code faster, profile a slow program, set up benchmarks, or read assembly output."
---

# C++ Performance

This skill covers the full performance workflow: instrumenting a build
for profiling, gathering samples, interpreting flamegraphs, writing
microbenchmarks, and making targeted optimizations.

## When to use

- "Make this C++ code faster"
- "Set up Google Benchmark"
- "Profile this program — where's the time going?"
- "Generate a flamegraph"
- "Why is my hot loop slow?"
- "Compare two implementations' speed"
- "Inspect the assembly for this function"

## When NOT to use

- Memory safety issues (`sanitizer-debugging`)
- Build system performance (`cmake-mastery`)
- Algorithmic complexity from scratch (general design discussion)

## Mental model

Performance work is a **measurement loop**:

1. Define what "fast" means (latency, throughput, memory).
2. Build a release profile that's representative.
3. Measure. Don't guess.
4. Identify the bottleneck (top function in flamegraph).
5. Hypothesize and apply ONE change.
6. Re-measure. Confirm the change helped (and didn't regress others).
7. Repeat.

Never optimize without numbers, and never optimize more than one thing
between measurements.

## Step 1 — Build for profiling

Release with frame pointers and debug info:

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "RelWithDebInfo"
```

Make sure the compile flags include:
- `-O2` or `-O3` (perf characteristics)
- `-g` (line-level mapping in profiler)
- `-fno-omit-frame-pointer` (clean stack traces for perf record)

If your CMakeLists strips frame pointers in Release, add a target option:

```cmake
target_compile_options(myapp PRIVATE
    $<$<CXX_COMPILER_ID:GNU,Clang>:-fno-omit-frame-pointer>
)
```

## Step 2 — Add a benchmark

For a microbenchmark, use Google Benchmark. Add to `vcpkg.json`:

```yaml
tool: manage_file
args:
  op: "patch"
  path: "vcpkg.json"
  patch: |
    --- a/vcpkg.json
    +++ b/vcpkg.json
    @@ -5,5 +5,6 @@
       "dependencies": [
         "fmt",
    -    "spdlog"
    +    "spdlog",
    +    "benchmark"
       ]
     }
```

Then create `bench/bench_main.cpp`:

```cpp
#include <benchmark/benchmark.h>
#include <mylib/foo.hpp>

static void BM_Foo(benchmark::State& state) {
    std::string input(state.range(0), 'x');
    for (auto _ : state) {
        auto out = mylib::foo(input);
        benchmark::DoNotOptimize(out);
    }
    state.SetBytesProcessed(state.iterations() * state.range(0));
}
BENCHMARK(BM_Foo)->Range(64, 64 << 10);

BENCHMARK_MAIN();
```

And wire it into CMake:

```cmake
find_package(benchmark CONFIG REQUIRED)
add_executable(bench_mylib bench/bench_main.cpp)
target_link_libraries(bench_mylib PRIVATE mylib::mylib benchmark::benchmark)
```

Key Google Benchmark idioms:

- `benchmark::DoNotOptimize(x)` — prevent the compiler eliminating x.
- `benchmark::ClobberMemory()` — force a memory fence; rarely needed.
- `state.range(0)` / `state.range(1)` — multi-dimensional ranges.
- `->Range(min, max)` / `->RangeMultiplier(2)` — geometric scan.
- `->Iterations(N)` — fixed iteration count.
- `state.SetBytesProcessed(...)` — emits MB/s in the output.

Build and run:

```yaml
tool: build_project
args:
  project_dir: "."
  build_type: "Release"
  target: "bench_mylib"
  run_tests: false
```

## Step 3 — Profile with perf (Linux)

```bash
perf record -F 999 -g -- ./build/bench_mylib --benchmark_filter=BM_Foo/4096
perf report
```

Or generate a flamegraph (requires
[FlameGraph](https://github.com/brendangregg/FlameGraph)):

```bash
perf record -F 999 -g -- ./bench_mylib --benchmark_filter=BM_Foo/4096
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

For sandboxed profiling (no host perf installed), use the
`nexcpp/build-linux` docker image which has perf + FlameGraph
pre-installed.

## Step 4 — Read the flamegraph

A flamegraph shows the **stack** on the y-axis and **time spent** on the
x-axis. Wider boxes = more time. Read from the top down:

- **The hottest leaf** is what to look at first.
- **A wide common ancestor** is where to refactor for big wins.
- Beware sampling noise — if the top function is < 5%, the bottleneck
  is likely *everywhere*, suggesting a structural problem
  (cache misses, contention, syscall storm) rather than one hot spot.

## Step 5 — Common hot-spot patterns

### Allocation churn

If `malloc`/`operator new`/`free`/`operator delete` are in the top 10,
you're allocating too often. Fixes:

- Reserve `std::vector` capacity once.
- Use `std::string_view` instead of `std::string` for read-only paths.
- Use a pool allocator or `std::pmr` for small frequent allocations.
- Profile with `tcmalloc` or `mimalloc` linked in.

### Cache misses

If `__memcpy` or basic loops show up but you don't see "hot work", check
cache. `perf stat -e cache-misses,cache-references ./bench` gives a
ratio. >10% miss rate is a problem.

Fixes:
- Pack hot structs to fit in cache lines.
- AoS → SoA: transform `std::vector<Particle>` into
  `struct { vector<float> x, y, z; }`.
- Pre-fetch (`__builtin_prefetch`) for predictable access patterns.

### Branch mispredictions

`perf stat -e branch-misses,branches` — >5% is suspect. Fixes:
- Sort data so similar branches go together.
- Use branchless code (e.g., `cmov` patterns).
- Use `[[likely]]` / `[[unlikely]]` hints.

### Lock contention

In multi-threaded code, profile with TSan (off) + perf. Watch for time
in `pthread_mutex_lock`. Fixes:
- Reduce critical section size.
- Use `std::atomic` for simple counters.
- Replace shared state with thread-local + reduce.
- Use a lock-free queue if the access pattern allows.

## Step 6 — Inspect the assembly

For a tight loop, look at the generated code. Use
[Compiler Explorer](https://godbolt.org/) for ad-hoc, or generate
locally:

```yaml
tool: run_snippet
args:
  code: |
    [[gnu::noinline]] int sum(const int* a, int n) {
        int s = 0;
        for (int i = 0; i < n; ++i) s += a[i];
        return s;
    }
    int main() {
        int a[] = {1,2,3,4,5,6,7,8};
        return sum(a, 8);
    }
  compiler: "clang"
  std: "20"
  flags: ["-O3", "-S", "-masm=intel"]
```

(For `run_snippet`, `-S` produces assembly to stdout instead of running
— check the stderr / compile output.)

Things to look for in hot inner loops:
- **Vectorization**: `xmm`/`ymm`/`zmm` registers and `vmov...` /
  `vfma...` / `vpadd...` instructions.
- **No spills**: no extra `mov` to/from the stack inside the loop.
- **No surprise calls**: a function called every iteration that you
  thought was inlined.

If you don't see vectorization, check `-fno-trapping-math` /
`-ffast-math` (for floats), use `#pragma omp simd`, or restructure the
loop to remove aliasing.

## Step 7 — Apply ONE change and re-measure

Make one change. Re-run the benchmark with `--benchmark_repetitions=10`
to get stable numbers, and compare:

```bash
./bench_mylib --benchmark_format=json --benchmark_repetitions=10 \
    --benchmark_filter=BM_Foo > before.json

# apply change

./bench_mylib --benchmark_format=json --benchmark_repetitions=10 \
    --benchmark_filter=BM_Foo > after.json

# compare
python -m benchmark.tools.compare benchmarks before.json after.json
```

Look for the `cv` (coefficient of variation) — if it's > 5%, the
numbers aren't stable enough yet; increase repetitions or pin a CPU
with `taskset`.

## Step 8 — Tracy (continuous profiling)

For long-running workloads or production-like profiling, use Tracy:

```cpp
#include <tracy/Tracy.hpp>

void hot_function() {
    ZoneScoped;        // RAII zone — appears in the timeline
    // ...
}
```

Link `Tracy::TracyClient` to your target. Run the Tracy GUI on the
developer machine and connect to the program. Tracy shows zones, lock
contention, frame markers (for game-loop programs), and memory
allocations live.

## Optimization decision matrix

| Bottleneck      | Where to look                          |
|-----------------|----------------------------------------|
| CPU-bound       | flamegraph, assembly, vectorization    |
| Memory-bound    | cache misses, data layout, SoA         |
| I/O-bound       | syscalls, io_uring, async              |
| Lock contention | mutex %, replace with atomics or sharding |
| GC pauses (n/a) | not applicable to C++                  |

## Common pitfalls

### Microbenchmarking the wrong thing

`DoNotOptimize` matters. Without it, the optimizer can hoist the
benchmarked work out of the loop, giving you a "0 ns" result.

### Comparing Debug to Release

Always compare like-for-like. A 10× speedup that's just "I forgot the
-O3" tells you nothing.

### Forgetting LTO / PGO

For final shipping perf:
- LTO: `set_target_properties(myapp PROPERTIES INTERPROCEDURAL_OPTIMIZATION TRUE)`
- PGO: see Clang's `-fprofile-generate` / `-fprofile-use`.

These typically buy another 5-15%.

### Optimizing without profiling

The #1 mistake. The hot spot is almost never where you think it is.

## Tool reference quick card

- `build_project(..., build_type="RelWithDebInfo")` — profiling build
- `run_snippet(code, flags=["-O3", "-S"])` — inspect assembly
- `analyze_code(path, tool="clang-tidy", checks="performance-*")` — pre-profile lint
- `manage_file(op=patch)` — surgical changes between benchmarks

## References

- Google Benchmark: https://github.com/google/benchmark
- Tracy: https://github.com/wolfpld/tracy
- FlameGraph: https://github.com/brendangregg/FlameGraph
- "What Every Programmer Should Know About Memory" — Ulrich Drepper
