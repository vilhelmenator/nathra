# Benchmarks & Project Structure

## Benchmark

### Python vs nathra

`bench/bench.py` is a dual-mode file that runs as plain Python and compiles with nathra. `bench/run.py` builds the binary with `-O2`, runs both, and prints a comparison:

```
benchmark             python ms    nathra ms   speedup
--------------------  ----------  ----------  --------
float_sum                   1373           8      171x
leibniz_pi                  2451          14      175x
int_sum                     1215           7      173x
fib_36                      4868         112       43x
```

```sh
cd bench
python3 run.py
```

### Compiler optimizations vs naive C

`bench/run_opts.py` builds three versions of the same algorithms — Python, hand-written idiomatic C, and nathra — and prints a side-by-side comparison. It demonstrates seven automatic nathra optimizations:

```
benchmark              python ms  naive C ms   nathra ms   speedup  optimization
--------------------  ----------  ----------  ----------  --------  ----------------------------------------
saxpy                      23200         134         134      1.0x  restrict → no aliasing-check prelude
strided_sum                 5080          94          94      1.0x  constant specialisation (stride=4 folded in)
small_alloc                49000         198          38      5.2x  alloca substitution (no malloc/free per call)
soa_sum                    32600         123          30      4.1x  @soa → 8B/elem read vs 64B/elem AoS (8-field struct, extract one field)
restrict_short                 —         542         548      1.0x  restrict → no overlap-check preamble (N=64, cost is large fraction of call)
hot_cold                       —          72          74      1.0x  hot/cold split → 3 error paths outlined, hot loop fits in fewer cache lines
linked_list                    —         943         962      1.0x  prefetch(next->next) → hides L3 miss latency on pointer-chase traversal
```

- **small_alloc** — `alloca` substitution is a real win everywhere: stack allocation costs ~1 ns (one `sub rsp` instruction) vs 30–100 ns for `malloc/free` on typical allocators. 5.2× with 5 M calls to a 512-byte scratch-buffer function.
- **soa_sum** — the `@soa` benchmark extracts one field from a particle array (8 fields, 64 B/particle). AoS loads a full 64-byte cache line to get 8 B of `.x`; SoA reads only the `particles_x[]` stream (8 B/element). 4.1× speedup at 5 M particles, `@noinline` on both sides to prevent the optimizer from collapsing the rep loop.
- **saxpy / strided_sum / restrict_short** — Apple Clang at `-O2 -march=native` on Apple Silicon already applies vectorization strategies that match nathra's `restrict` and constant-specialisation output on this target; speedup is architecture-dependent and more visible on x86 toolchains where the overlap-check preamble is costlier.
- **hot_cold** — nathra outlines all three `raise` branches into `static __attribute__((cold, noreturn))` helpers, keeping the hot loop in fewer I-cache lines. The benefit is measurable under I-cache pressure from a larger surrounding binary; Apple Silicon's large L1-I cache absorbs the inline cold paths on this isolated benchmark.
- **linked_list** — nathra inserts `NR_PREFETCH(head->next->next, 0, 1)` before each pointer-chase load. The list is built with a stride-permuted layout (~12 MB hops) to defeat hardware prefetchers. Apple Silicon's stream-detection hardware is unusually aggressive and partially covers irregular pointer-chase patterns; the prefetch benefit is larger on Intel/AMD where L3-miss latency is higher relative to core speed.

```sh
cd bench
python3 run_opts.py
```

## Bootstrap performance

The native compiler is written in nathra and compiles itself. Self-compilation benchmark — the native compiler compiling its own 8 source modules (~4,000 lines) to C:

| Module | Python | Native | Speedup |
|--------|--------|--------|---------|
| native_analysis.py | 139 ms | 0.22 ms | 624x |
| native_compile_file.py | 637 ms | 1.25 ms | 511x |
| native_infer.py | 147 ms | 0.27 ms | 540x |
| native_type_map.py | 144 ms | 0.33 ms | 436x |
| native_codegen_stmt.py | 383 ms | 1.04 ms | 367x |
| native_codegen_call.py | 311 ms | 0.94 ms | 331x |
| native_codegen_expr.py | 225 ms | 0.78 ms | 287x |
| native_compiler_state.py | 43 ms | 0.17 ms | 248x |
| **Total** | **2,029 ms** | **5.01 ms** | **405x** |

The native compiler compiles ~4,000 lines of its own source in 5 milliseconds. Total compile time becomes dominated by `gcc`, which is the correct steady state — the compiler should never be slower than the C compiler it feeds.

Run `python3 scripts/benchmark.py` to reproduce.

See [BOOTSTRAP.md](BOOTSTRAP.md) for the full bootstrap roadmap and architecture.

## Generated header rules

Generated `.h` files include only `nathra_types.h` — a minimal header containing forward declarations, `stdint.h`, and `stddef.h`. They never include `nathra_rt.h`, `stdio.h`, `pthread.h`, or any other heavy header.

The full runtime is included exactly once, in the generated `.c` file. Each `.c` includes its own `.h`, which transitively brings in any project module dependencies.

This means including a nathra module header in C++ or C code never silently pulls in platform headers. Compile times stay flat as the project grows.

## Project structure

```
nathra/
  Makefile                          Build the native compiler dylib
  compiler/                         Python compiler (stage 0)
    compiler.py                       Front-end: parse, first-pass, emit glue
    codegen_stmts.py                  Statement code generation
    codegen_exprs.py                  Expression code generation
    type_map.py                       Type annotation → C type mapping
    ast_serial.py                     Binary AST serializer
  cli/                              User-facing tools
    nathra.py                         CLI entry point
    snekc.py                          Interactive REPL shell
    nathra_stubs.py                   IDE stubs (from nathra import *)
  runtime/                          C headers shipped with the project
    nathra_rt.h                      Full runtime: strings, lists, dicts, I/O, concurrency
    nathra_types.h                   Forward declarations — safe to include from any header
    nathra_test.h                    Test runner infrastructure
  native/                           Bootstrap native compiler (405x faster)
    src/                              .py source for the native compiler
    generated/                        Pre-generated .c/.h — just run make
  lib/
    build.py                          Build script interpreter
  scripts/
    regenerate.py                     Regenerate native/generated/ from .py sources
    bootstrap_test.py                 Bootstrap verification
  build/                            Build artifacts (gitignored)
    compiler_native.dylib             Native compiler shared library
  tests/                            Test suite (48 tests)
  bench/                            Benchmarks
  examples/                         Example programs
```

### Build targets

```sh
make                    # build native compiler from pre-generated C (~2 sec)
make regenerate         # regenerate C from .py sources (needs Python compiler)
make test               # run the test suite
make bootstrap          # run bootstrap verification
make clean              # remove build artifacts
```