# nathra

A typed systems language in valid Python syntax that compiles to portable C. It preserves enough source structure for compile-time rewrites that a downstream C compiler usually cannot recover from handwritten C.

```python
@soa
struct Particle:
    x: float
    y: float
    vx: float
    vy: float

def update(particles: array[Particle, 1024], dt: float) -> void:
    for i in range(1024):
        particles[i].x += particles[i].vx * dt
        particles[i].y += particles[i].vy * dt
```

`@soa` expands the array into per-field flat arrays. The loop reads four contiguous streams instead of striding through a 32-byte struct. This preserves layout information explicitly, instead of hoping a downstream C compiler can reconstruct it from handwritten array-of-structs code.

## Quick start

```sh
make                                          # build the native compiler (~2 sec)
python3 cli/nathra.py program.py             # compile + link
python3 cli/nathra.py program.py --run       # compile, link, run
python3 cli/nathra.py program.py --emit-c    # emit C only
python3 cli/nathra.py program.py --safe      # enable runtime safety checks
python3 cli/nathra.py program.py --shared    # compile to shared library
python3 cli/nathra.py build.py               # run a project build script
python3 cli/snekc.py                          # interactive REPL
```

## Example

```python
# hello.py
"nathra"

struct Vec2:
    x: float
    y: float

def length(v: ptr[Vec2]) -> float:
    return sqrt(v.x * v.x + v.y * v.y)

def main() -> int:
    v: Vec2 = Vec2(3.0, 4.0)
    print(length(addr_of(v)))
    return 0
```

```sh
$ python3 cli/nathra.py hello.py --run
5.000000
```

The compiler emits readable C, invokes `gcc`, and runs the binary. Errors point to `hello.py` line numbers, and `#line` directives let native debuggers map stepping back to the original `.py` source.

## What makes it different

**Source-aware optimizations.** The compiler sees the full program AST and applies rewrites that a downstream C compiler usually cannot recover from flat C: `restrict` inference on non-aliasing pointers, `@soa` struct-of-arrays transformation, hot/cold code splitting, constant specialization, alloca substitution for small allocations, and stack variable lifetime narrowing. These are the transforms that justify writing nathra instead of C.

**Python syntax, C semantics.** Valid Python syntax means Python-aware editors can parse and highlight it, and the language is easy for humans and LLMs to read and write without learning a new grammar. But the semantics are C-level: no garbage collector, no Python runtime, no Python object model. Structs are value types. Pointers are explicit. You control the memory layout.

**Portable C output.** The compiler emits readable, auditable C. You can inspect it, diff it, and feed it to any C compiler on any platform. `#line` directives map compiler diagnostics and native debugger stepping back to the original `.py` source. No LLVM dependency, no custom backend.

**Automatic cleanup for local allocations.** The compiler's escape analysis detects local-only `str`, `list[T]`, and `dict` variables and inserts cleanup automatically. When you need more control, escalate to `defer`, `own[T]`, scoped arenas, or raw `alloc`/`free`.

**Safety checks.** `--safe` enables division-by-zero, bounds, overflow, and null pointer checks — all gated behind a single `#define`, disabled entirely in non-`--safe` builds. Static null analysis catches provably-null dereferences as compile errors with no flag needed.

**C library integration.** `import glut` maps to C headers via the build system. The compiler runs `gcc -E` at compile time to extract every function signature and `#define` constant. No manual extern declarations.

## Status

| Tier | Features |
|------|----------|
| **Stable** | Types, structs, enums, functions, modules, control flow, C emission, lists, dicts, strings, f-strings, defer, auto-defer, error handling (`Result[T]`), testing framework, build system, native bootstrap compiler |
| **Implemented** | Safety checks (`--safe`), `@soa`, `@hot`/`@cold`, serialization (`@serializable`), SIMD, concurrency (threads, mutexes, channels), hot-reload, REPL, codegen hooks, `c_import` |
| **New** | `own[T]` ownership tracking, scoped arenas (`with scope`), heap assertions, `c_modules` build integration, automatic build topology (dev/release/service modes) |

## Non-goals

- **Not Python-compatible.** No Python runtime, no Python object model, no Python import semantics. This is a C-level systems language that borrows Python's syntax.
- **Not memory-safe by default.** Raw pointer access is allowed. `--safe` adds runtime checks; `own[T]` adds compile-time ownership enforcement. Neither is mandatory.
- **Not aiming for C++ abstraction complexity.** No templates, no RAII, no move constructors, no exceptions. Nathra is closer to "typed C with Python syntax" than to Rust or C++.
- **Not hiding C-level costs.** Nathra does not hide costs behind a VM, GC, or dynamic dispatch. Heap-allocating types such as `str`, `list`, and `dict` remain explicit in the source.

## Memory model

The default is **auto-defer**: local-only `str`, `list[T]`, and `dict` variables are cleaned up automatically when the function returns. You write allocations; the compiler inserts the frees.

When auto-defer isn't enough, escalate:

```python
# 1. Explicit defer — you control the cleanup point
buf: ptr[byte] = alloc(4096)
defer(free(buf))

# 2. Ownership transfer — compile-time enforcement
def process(data: own[list[int]]) -> void:
    defer(list_free(data))
    # data must be freed or moved before return

# 3. Scoped arenas — batch allocation, single free
with scope(arena, 65536):
    s: str = arena_str_new(arena, "temp")
    # freed when scope exits

# 4. Raw control — escape hatch
p: ptr[int] = alloc(8)
p[0] = 42
free(p)
```

## Bootstrap performance

The native compiler — written in nathra — compiles its own ~4,000 lines of source in 5 milliseconds (405x faster than the Python implementation). Total build time is dominated by `gcc`, not the compiler.

```sh
python3 scripts/benchmark.py    # reproduce the numbers
```

See [docs/benchmarks.md](docs/benchmarks.md) for the full benchmark table.

## Project structure

```
nathra/
  cli/
    nathra.py                         CLI entry point
    snekc.py                          Interactive REPL shell
    nathra_stubs.py                   IDE stubs
  compiler/                           Python compiler (stage 0)
    compiler.py                       Front-end: parse, analyze, emit
    codegen_stmts.py                  Statement code generation
    codegen_exprs.py                  Expression code generation
    type_map.py                       Type annotation → C type mapping
    ast_serial.py                     Binary AST serializer
  runtime/                            C headers shipped with the project
    nathra_rt.h                       Full runtime
    nathra_types.h                    Forward declarations
    nathra_test.h                     Test runner infrastructure
  native/                             Bootstrap native compiler (405x faster)
    src/                              .py source for the native compiler
    generated/                        Pre-generated .c/.h — just run make
  lib/
    build.py                          Build script interpreter
  tests/                              Test suite (48 tests)
  bench/                              Benchmarks
  examples/                           Example programs
  docs/                               Detailed documentation
```

```sh
make                    # build native compiler from pre-generated C (~2 sec)
make regenerate         # regenerate C from .py sources (needs Python compiler)
make test               # run the test suite
make clean              # remove build artifacts
```

## Documentation

- [Language Reference](docs/language.md) — types, structs, functions, memory, modules, concurrency, serialization
- [Compiler Optimizations & Safety](docs/optimizations.md) — restrict inference, SoA, hot/cold, safety checks
- [Benchmarks & Project Structure](docs/benchmarks.md) — performance numbers, bootstrap details
- [Build Topology](docs/topology.md) — automatic .so partitioning, hot-swap, build modes (dev/release/service)
