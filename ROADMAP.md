# Micropy Compiler Roadmap

> Ordered within each section by **impact ÷ work** — highest ROI first.

---

## Correctness Pass

MicroPy compiles the whole program — every function body is an AST. That's the
structural advantage. The two foundational primitives unlock everything below them.
The correctness pass costs nothing at runtime; all of it is compile-time analysis.

### Foundation

- [x] **Escape analysis primitive** *(intraprocedural)*
  Walk a function body and classify each `alloc`'d local as *escaping* (returned,
  stored into a struct field, or passed to any call) or *local-only*. One function,
  called by all subsequent passes.

- [x] **Function allocation signature tagging** *(interprocedural foundation)*
  First-pass over every function body. Tag each function with its allocation role:

  | Tag | Meaning |
  |-----|---------|
  | **Producer** | Returns a pointer that came from `alloc` |
  | **Consumer** | Frees a pointer parameter |
  | **Borrows** | Takes a pointer, uses it, neither frees nor stores it |
  | **Stores** | Writes a pointer parameter into a struct field or global |

  This is just tracking which pointer-typed variables flow to `alloc`, `free`,
  `return`, or struct field assignments within each body. Tags are stored in a
  function metadata table used by every pass below.

### Auto-corrections *(uses both foundation primitives)*

- [x] **Scope-based auto-free**
  For any local-only pointer: automatically insert `free` on every exit path —
  including early `return` and `raise` branches. Uses the existing defer-stack
  mechanism. Programmer writes `alloc`, compiler handles cleanup. At call sites,
  check the function tag: if the callee is *Consumer*, ownership is discharged;
  if *Borrows*, the caller still owns it.

- [x] **Error-path auto-free**
  When a `raise` is emitted and there are live unfreed local-only allocations,
  emit `free` calls in reverse allocation order before the raise. This is the bug
  Rust's drop glue prevents; MicroPy does it as a codegen pass with no language
  changes.

- [x] **Debug-mode allocation tracking** *(`--debug` flag)*
  Wrap every `alloc` and `free` site with a counter increment/decrement and source
  location string. Assert the counter is zero at program exit. Zero cost in release
  builds. With function tags available, diagnostics can say *"pointer allocated in
  `make_buffer` at line 3, ownership received in `process` at line 8, leaked at
  line 10"* rather than just pointing at the alloc site.

### Warnings *(intraprocedural + one call-boundary)*

- [x] **Static leak detection**
  Fork the live-allocation set at each `if/else` branch, merge at the join point.
  At every `return` and `raise`, check for live allocations neither freed, returned,
  nor passed to a Consumer. With function tags: a variable that received its value
  from a *Producer* call is also a live allocation — catches the classic
  "factory function caller forgets to free" pattern across one call boundary.

  ```python
  def process() -> void:
      buf: ptr[byte] = make_buffer()  # make_buffer is tagged Producer
      if validate(buf) == False:
          return                      # warning: buf leaks here
      use(buf)
      free(buf)
  ```

- [x] **Double-free detection**
  Track the *freed* state of each local pointer. `free(p)` on an already-freed
  variable on any code path → compile-time error.

- [x] **Use-after-free detection**
  Same state tracking. Any read or write through `p` after `free(p)` on any code
  path → compile-time warning.

### Interprocedural ownership *(depth-capped, built on function tags)*

- [x] **Cross-function ownership chain analysis**
  Second pass over each function body. At every call site: did this variable receive
  its value from a *Producer*? If so, is ownership discharged on every path (passed
  to a *Consumer*, returned, or stored)? If not — leak warning, annotated with both
  the Producer source and the leaking path.

  Depth cap: chase the ownership chain through at most **two call levels**. This
  catches the vast majority of real bugs without the analysis cost or explanation
  burden of deep transitive chains.

  Hard stop: once a pointer is passed to a *Stores*-tagged function or assigned into
  a data structure (list, dict, any heap collection), it is marked "ownership
  transferred — programmer responsible." No points-to graph, no PhD thesis.

  For `extern` functions with no visible body: default to *Borrows* (conservative —
  warns on missing free) unless annotated otherwise.

---

## Optimization Pass

Items marked ✅ are already implemented.

### One-pass AST walks — no infrastructure needed

- ✅ **`MP_LIKELY`/`MP_UNLIKELY` on `is_ok`/`is_err`**
  Branch prediction hint on the result-type happy path.

- ✅ **`MP_UNLIKELY` on guard-raise patterns**
  `if cond: raise "msg"` → `if (MP_UNLIKELY(cond))`. Error branches are cold.

- ✅ **`MP_PREFETCH` in `@unroll` loops**
  Prefetch array elements ahead by `max(factor×4, 16)` at the start of each unrolled
  iteration.

- ✅ **`MP_PREFETCH` in regular `for`-`range` loops**
  Same prefetch logic, fixed 8-element lookahead, capped at 2 array streams per loop.

- ✅ **`@hot` struct cache-line alignment**
  `@hot` on a struct emits `__attribute__((aligned(64)))`.

- [x] **Read-only inference (`const T*`)**
  Scan each function body for writes through `ptr[T]` parameters. If none found,
  emit `const T*`. Hard aliasing promise to the C compiler — unlocks vectorization
  and instruction reordering it would otherwise refuse. Detection is a single AST
  walk. Highest value item in this section.

- [x] **Match/case cold-arm ordering**
  When emitting the `if/else if` chain for a `match`, sort arms so any arm whose
  body is a single `raise` or calls a `@cold` function goes last. Direct extension
  of the guard-raise logic.

- [x] **String literal stack optimization**
  `s: str = "literal"` emits a block-scope `MpStr` struct on the stack — no `malloc`,
  no `str_free` needed. String literals passed directly to `str_*` functions also
  auto-coerce to stack compound literals. `str_new` still works for runtime `cstr`
  values. Removes `str_new("literal")` boilerplate from idiomatic code.

- [x] **`@compile_time` array prewarm**
  When a `@compile_time`-generated array is referenced in a function body, emit
  `MP_PREFETCH` for its first cache line at function entry. The array is a known
  static address — zero guesswork.

### Requires escape analysis (build correctness primitive first)

- [x] **`alloca` substitution for small known-size allocations**
  `alloc(N)` where N is a compile-time constant ≤ 4 KB and the pointer is local-only
  → emit `alloca(N)`, drop the `free`. Zero heap overhead, zero fragmentation,
  automatic cleanup on return. Fires constantly for scratch buffers.

- [x] **Conditional `alloca`/`malloc` for bounded allocations**
  `alloc(n)` where n is a runtime value but is bounded by a known constant → emit
  `n <= 4096 ? alloca(n) : malloc(n)` with a matching conditional `free`.

- [x] **Allocation merging**
  Multiple `alloc` calls of known sizes in the same block scope, all local-only →
  single `alloca`/`malloc`, carved into named offsets. One allocation, one cache
  line, one free (or none if on the stack).

- [x] **Arena allocation batching**
  Multiple `arena_list_new` / `arena_alloc` calls from the same arena in the same
  block → coalesce into a single bump. One pointer advance, zero per-item overhead.
  Sizes are compile-time constants.

### Structural passes — moderate bookkeeping

- [x] **`@cold` inference from function body**
  If every code path in a function terminates in `raise`, `abort()`, or a call to
  another `@cold` function — auto-annotate `__attribute__((cold))`. No annotation
  required from the programmer.

- [x] **`@cold` inference via call-site analysis**
  If a function is *only ever called* from error branches (guard-raise paths,
  `is_err(...)` blocks) — auto-annotate `__attribute__((cold))`. Higher value than
  body inference; catches helper functions that look normal in isolation.

- [x] **Stack variable lifetime narrowing**
  Track first and last statement index for each large local. If it is never
  address-taken and its lifetime doesn't overlap another large local, wrap it in a
  `{ }` scope so the C compiler knows the stack slot can be reused. MicroPy knows
  whether `&var` is ever taken; C compilers must conservatively assume it might be.

- [x] **Linked-list / tree traversal prefetch**
  Detect `while node is not None: ... node = node.next` patterns. Emit
  `MP_PREFETCH(node->next->next, 0, 1)` at the top of each iteration. Pointer-chase
  latency is the dominant cost in tree traversals.

- [x] **Function ordering (topological sort)**
  Emit functions in call-graph order so each callee appears before its callers.
  Removes the need for forward declarations and gives the inliner the best possible
  view. Requires per-function emit buffering and a topological sort of the call graph.

### High complexity — defer until above is stable

- [x] **Non-temporal prefetch for single-pass streaming loops**
  Loops that write every element exactly once and never re-read → `_mm_stream`
  / `__builtin_ia32_movntdq`. Bypasses cache entirely, avoids evicting hot data.
  Requires recognizing the write-only streaming pattern.

- [x] **Struct field sparsity warning**
  At struct definition time, compute the natural layout and warn if field ordering
  would leave gaps larger than a cache line. Suggest a reordered layout.

- [x] **`@soa` Array-of-Structs → Struct-of-Arrays transformation**
  Explicit `@soa` annotation on a struct class. When an `array[T, N]` is declared
  where `T` is `@soa`-annotated, the compiler expands it into one parallel array per
  field instead of a single struct array. All `arr[i].field` accesses rewrite to
  `arr_field[i]`. ~80-120 lines across compiler.py, codegen_stmts.py, codegen_exprs.py.

  ```python
  @soa
  class Particle:
      x: float
      y: float
      z: float
      mass: float

  particles: array[Particle, 1000]
  particles[i].x = 1.0       # reads/writes go through flat arrays
  ```

  Generated C:
  ```c
  double particles_x[1000];
  double particles_y[1000];
  double particles_z[1000];
  double particles_mass[1000];

  particles_x[i] = 1.0;
  ```

  **Compile-time errors** (patterns that defeat SoA):
  - `p = particles[i]` — whole-element read (would need gather)
  - `particles[i] = p` — whole-element write (would need scatter)
  - `particles[i].method()` — method call on element
  - `ref(particles[i])` — pointer to element doesn't exist in SoA layout
  - Passing a SoA array where `ptr[T]` is expected

  **Implementation steps:**
  1. First pass: record `@soa` structs in `self.soa_structs: set` (~5 lines)
  2. Array declaration: expand `array[SoA_T, N]` to per-field arrays (~20 lines)
  3. Field access: rewrite `arr[i].field` → `arr_field[i]` in codegen_exprs (~20 lines)
  4. Field assignment: same rewrite on LHS in codegen_stmts (~15 lines)
  5. Error on unsupported patterns: whole-element access, method calls, `ref()` (~20 lines)

  **Future extensions** (not in v1):
  - Auto gather/scatter for whole-element access
  - SoA-aware method rewriting (method takes field pointers instead of struct pointer)
  - Nested SoA structs

  ### One-pass AST walks — trivial to add

- [x] **`restrict` on non-aliasing pointer parameters**
  If a function takes two or more `ptr[T]` parameters and neither is ever assigned
  from the other or from a common source within the function body, emit `restrict`
  on each. Single AST walk per function — check for aliasing assignments between
  pointer parameters. This is the single highest-value qualifier for loop
  vectorization, and C programmers almost never write it because proving non-aliasing
  manually is tedious. The C compiler cannot insert `restrict` — it's a promise only
  the source author can make.

- [x] **Branch-free select for side-effect-free ternaries**
  `x = a if cond else b` where both `a` and `b` are pure expressions (literals,
  locals, arithmetic — no calls, no pointer derefs with possible side effects) →
  emit as a C ternary `x = cond ? a : b` with a compiler hint, or as
  `x = cond * a + (!cond) * b` for integer types. The C compiler sometimes converts
  `if/else` to `cmov`, but bails when it can't prove both arms are side-effect-free.
  MicroPy knows this from the AST — the purity check is a leaf-node type test.

- [x] **Loop trip-count hints for known bounds**
  When `for i in range(N)` has N known at compile time or traceable to a constant
  call-site argument, emit `#pragma GCC unroll N` (for small N) or
  `__builtin_expect(n, N)` on the loop bound. The C compiler must analyze this
  conservatively; MicroPy can just tell it.

### Requires call-graph or cross-function view

- [x] **Hot call-site constant specialization**
  If a function is called from a hot loop with a constant argument (e.g. a stride,
  a flag, a dimension), emit a specialized copy with that constant folded in. The
  constant enables the C compiler to vectorize and strength-reduce in ways it can't
  with a variable — a matrix multiply with a constant stride, a tree traversal with
  a constant depth limit, a filter with a constant flag. The biggest wins come from
  *larger* functions where constant propagation eliminates branches and unlocks
  vectorization, so no size cap on the callee. MicroPy sees both the call site and the
  callee body; LTO sometimes does this, but only for trivial inlining candidates.

  **Specialization threshold:** specialize freely when ≤ 3 distinct constant values
  are seen across all call sites (one copy per constant, negligible bloat). Above 3
  distinct constants, only specialize if the function is small (≤ 30 statements) to
  bound code size. Functions inside `@hot` or `@unroll` contexts are always eligible.

- [x] **Intra-function hot/cold splitting**
  When an `if` branch contains only error handling, logging, or calls to `@cold`
  functions, extract it into a separate `static __attribute__((cold))` helper and
  replace the branch with a call. Keeps the hot path's instruction footprint tight
  for I-cache. Extension of the existing `@cold` inference — same detection logic,
  but emits an extracted function instead of just an annotation.
## Auto-generated Serialization (`@serializable`)

The compiler has full knowledge of every struct's field types, nesting, and pointer
relationships at compile time. Use this to generate bespoke serialize/deserialize
functions per struct — no runtime reflection, no external schema files, no separate
`.fbs` or `.proto` to maintain. The `.mpy` source is the schema.

### Phase 1 — Byte buffer primitives (`micropy_rt.h`)

- [x] **`MpWriter` / `MpReader` — general-purpose binary I/O**
  Add two small structs to the runtime. `MpWriter` owns a growable `ptr[byte]`
  buffer with a write cursor. `MpReader` holds a `ptr[byte]` and a read cursor.

  Design these as general-purpose binary buffer primitives — not serialization-
  specific. They should be equally useful for network protocols, binary file
  formats, logging, and message packing. Keep the API minimal and composable.

  Primitives to implement:
  - `mp_writer_new(initial_capacity)` / `mp_writer_free(w)`
  - `mp_writer_pos(w)` — return current write offset
  - `mp_write_bytes(w, ptr, len)` — raw memcpy into buffer, grow if needed
  - `mp_write_i8/i16/i32/i64/u8/u16/u32/u64/f32/f64(w, value)`
  - `mp_write_str(w, s)` — write length as `i32` then bytes
  - `mp_write_bool(w, b)` — single byte, doubles as null/present flag
  - `mp_writer_to_bytes(w, out_len)` — return the final buffer
  - `mp_reader_new(buf, len)` / matching `mp_read_*` functions
  - `mp_reader_pos(r)` — return current read offset

  ~100–150 lines of C. No dependencies beyond stdlib. No serialization-specific
  concepts like identity maps or version headers — those belong in the generated
  code, not the runtime.

### Phase 2 — Flat struct serialization *(compiler changes)*

- [x] **`@serializable` on scalar-only structs (memcpy fast path)**
  Handle structs that contain only scalar fields and nested value-type structs
  (no pointers, no strings, no lists).

  - First pass: record `@serializable` structs in a set. For each, check if all
    fields are flat (scalar or another flat `@serializable` struct). If so, mark
    as `flat_serializable`.
  - Codegen: emit `serialize_StructName(MpWriter* w, StructName* v)` and
    `deserialize_StructName(MpReader* r, StructName* v)`. For flat structs the
    body is a single `mp_write_bytes(w, v, sizeof(StructName))` and matching read.

- [x] **Version / hash header**
  Emit a 4-byte struct hash as the first thing written by every `serialize_*`
  function. Compute the hash at compile time from the struct's field names, types,
  and order. On deserialize, compare the hash and abort with a clear error message
  if it doesn't match.

  Optional `@version(N)` decorator for explicit versioning. If present, the
  version number is written instead of the hash. On load with an older version,
  zero-fill fields that were appended after that version. Reordering or removing
  fields without bumping the version is a compile-time error.

### Phase 3 — Strings, pointers, and nested structs

- [x] **Field-type dispatch in codegen**
  Extend the serialization emitter to handle non-flat fields. Walk struct fields
  in declaration order and emit one call per field based on its type:

  | Field type | Serialization |
  |------------|---------------|
  | Scalar (`i32`, `f64`, …) | `mp_write_<type>(w, v->field)` |
  | Nested value struct | `serialize_Inner(w, &v->field)` — inline recursive call |
  | `str` | `mp_write_str(w, v->field)` — length-prefixed bytes |
  | `ptr[T]` (`T` is `@serializable`) | Write 1-byte present flag (0=null, 1=present), then `serialize_T(w, v->field)` if present |
  | `array[T, N]` | Write N elements in order, each serialized by type |
  | `list[T]` | Write `i32` length, then each element |

  Deserialize reads back in the same order and reconstructs. Strings allocate via
  `str_new`, pointers via `alloc`, lists via `list_new`.

  This handles tree-shaped data where nothing is shared. Serialization is inline
  depth-first — no offset management, no deduplication.

### Phase 4 — Shared references and file I/O

- [x] **Compiler-generated graph serialization**
  When a `@serializable` struct contains `ptr[T]` fields pointing to other
  `@serializable` structs, the compiler knows the full type graph at compile time.
  It generates `save_*` / `load_*` functions that handle shared references
  automatically — the user never writes bottom-up ordering by hand.

  **Generated `save_StructName`:**

  1. **Collect phase** — walk the object graph depth-first from the root. For every
     `ptr[T]` to a `@serializable` struct, record the pointer in a seen-set
     (stack-allocated or `alloca`'d flat array). If already seen, skip. This
     produces a deduplicated list of unique objects in depth-first order.

  2. **Topo-sort** — reverse the list so leaves come first, parents come last.
     The compiler knows which struct types can contain pointers to which other
     types — the dependency edges are static. The runtime sort only orders the
     concrete instances within that known structure.

  3. **Write phase** — iterate the sorted list. Serialize each object into the
     `MpWriter`, record its buffer offset in a pointer→offset map (a small flat
     array, indexed by the object's position in the sorted list). When a parent
     writes a `ptr[T]` field, look up the child's offset and write it as an `i32`.

  4. **Write the root** — serialize the root struct last, with all child offsets
     already resolved.

  **Generated `load_StructName`:**

  1. Read objects in the same order they were written (leaves first).
  2. Allocate each object, deserialize its scalar/string fields.
  3. Store each object's pointer in an offset→pointer map (flat array, same size).
  4. When reading a `ptr[T]` field, read the `i32` offset, look up the map, and
     assign the pointer.
  5. Return the root.

  **Seen-set and offset map sizing:** for struct graphs with only fixed `ptr[T]`
  fields (no `list[ptr[T]]`), the compiler knows the maximum object count at
  compile time — the seen-set and offset maps can be stack-allocated flat arrays.
  When `list[ptr[T]]` fields are present (unbounded fan-out), the collect phase
  uses a growable buffer instead — either a realloc'd array or an `MpWriter`
  repurposed as a scratch allocator. The compiler emits the right strategy per
  struct based on whether any `list[ptr[T]]` appears in the type graph.

  ```python
  @serializable
  struct Material:
      color: Vec3
      roughness: f32

  @serializable
  struct Entity:
      name: str
      mesh: ptr[Mesh]
      material: ptr[Material]
      children: list[ptr[Entity]]

  # user just calls:
  save_Entity("scene.bin", root)
  root: ptr[Entity] = load_Entity("scene.bin")
  ```

  The compiler sees that `Entity` contains `ptr[Mesh]`, `ptr[Material]`, and
  `list[ptr[Entity]]`. It generates `save_Entity` that walks the entity tree,
  collects all unique meshes, materials, and child entities, serializes leaves
  first, and writes offsets for shared references. The user never thinks about
  serialization order.

  **Cycle handling:** if the struct graph can contain cycles (e.g. parent
  pointers), fields marked `@backref` are skipped during the collect phase and
  written as null. The deserializer reconstructs backrefs from the tree structure
  after all forward references are resolved.

  **File I/O wrappers:** `save_*` opens the file, creates an `MpWriter`,
  runs the graph serialization, writes the buffer, closes. `load_*` reads the
  file into a buffer, creates an `MpReader`, deserializes, returns a
  `Result[ptr[T]]` so version mismatches and I/O errors propagate cleanly.

### Testing

| Phase | Test |
|-------|------|
| 1 | `MpWriter`/`MpReader` round-trip: write mixed types, read back, verify values |
| 2 | Round-trip a flat struct (write → read → compare all fields) |
| 2 | Version mismatch: change a field, verify load rejects old data with clear error |
| 3 | Round-trip struct with strings and nested pointers, verify content and structure |
| 3 | Round-trip with null `ptr[T]` fields, verify nulls survive |
| 4 | Two entities sharing one material → save/load → verify both resolve to same object |
| 4 | Entity tree with children → save/load → verify tree structure intact |
| 4 | Cyclic parent pointer with `@backref` → verify no infinite loop, parent reconstructed |
| 4 | File I/O round-trip, verify file on disk matches expected size |


## User-Defined Codegen Hook Decorators

> Allow users to define their own decorators (in plain `.py` files) that wrap
> snekc's generated C output with platform-specific boilerplate. The compiler
> doesn't know about the target platform — the user's hook does.

### Motivation

Users integrating snekc with external platforms (Sierra Chart, Unreal Engine,
CoreAudio, Blender C API, etc.) need to wrap the generated C in
platform-specific entry points, includes, and glue code. Rather than adding
per-platform decorators to snekc, let users define their own hooks that
receive the generated C and return the final output.

### How it works

1. User creates a `codegen_hooks.py` (or any `.py` file) next to their `.mpy`
   source. This file contains plain Python functions that return decorator
   callbacks.

2. The `.mpy` file imports and uses the decorator:

   ```python
   from codegen_hooks import sierra_study

   @sierra_study(name="My SMA", subgraphs=["SMA Line"])
   def my_sma(close: ptr[float], count: int, output: ptr[float]) -> void:
       ...
   ```

3. At compile time, snekc:
   - Sees the decorator is imported from a `.py` file (not a built-in)
   - Flags it as a codegen hook
   - Compiles the function body to C as normal
   - Calls the Python hook function, passing it the function name, parameter
     list, return type, and generated C body as strings
   - The hook returns the complete C output (or additional C to prepend/append)
   - Snekc uses the hook's output instead of (or merged with) its normal output

### Hook function interface

The decorator factory returns a callback with this signature:

```python
def hook(func_name: str, params: list[tuple[str, str]], return_type: str, c_body: str) -> str:
    """
    func_name   — the function name (e.g. "my_sma")
    params      — list of (param_name, c_type) tuples
    return_type — C return type string (e.g. "void")
    c_body      — the complete generated C function as a string,
                  including signature and braces
    Returns: full C source string to emit (replaces normal output for
             this function, or wraps it with additional code)
    """
```

### Implementation

**In `compiler.py` first pass (~10 lines):**
- When processing decorators on a function, check if the decorator name was
  imported from a `.py` file (already tracked via `from_imports` or module
  resolution).
- If so, store it in a `codegen_hooks: dict[str, tuple[module_path, func_name, args]]`
  map keyed by the decorated function name.

**In codegen (~20 lines):**
- After emitting a function's C code, check if it has a codegen hook registered.
- If yes, import the `.py` module, call the decorator factory with the stored
  args to get the hook callback, then call the callback with `(func_name,
  params, return_type, c_body)`.
- Replace or augment the emitted C with the hook's return value.
- If the hook returns `None`, emit the function normally (no-op hook).

**Edge cases to handle:**
- Hook `.py` file not found → compile error with clear message
- Hook function raises an exception → compile error showing the traceback
- Multiple hooked functions in one file → each gets its own hook call, results
  are concatenated in function order
- Hook wants to add `#include` lines → it returns them as part of its string,
  snekc deduplicates includes in the final output

### Example: Sierra Chart ACSIL wrapper

```python
# codegen_hooks.py
def sierra_study(name, subgraphs):
    def hook(func_name, params, return_type, c_body):
        sg_setup = ""
        for i, sg in enumerate(subgraphs):
            sg_setup += f'        sc.Subgraph[{i}].Name = "{sg}";\n'
            sg_setup += f'        sc.Subgraph[{i}].DrawStyle = DRAWSTYLE_LINE;\n'

        return f"""
#include "sierrachart.h"
SCDLLName("{name}")

{c_body}

SCSFExport scsf_{func_name}(SCStudyInterfaceRef sc)
{{
    if (sc.SetDefaults)
    {{
        sc.GraphName = "{name}";
{sg_setup}
        sc.AutoLoop = 0;
        return;
    }}

    {func_name}(&sc.Close[0], sc.ArraySize, &sc.Subgraph[0].Data[0]);
}}
"""
    return hook
```

### Estimated size

~30-40 lines of compiler changes total. No new runtime code. No new syntax —
uses existing decorator and import mechanisms.

### Testing

| Test | What |
|------|------|
| 1 | Hook that wraps a simple function with a C preamble/postamble — verify output contains both |
| 2 | Hook that returns `None` — verify function emits normally |
| 3 | Missing hook `.py` file — verify clear compile error |
| 4 | Hook that raises an exception — verify traceback shown in compile error |
| 5 | Two functions in one file with different hooks — verify both wrapped correctly |


# MicroPy Roadmap

## Recent milestones

- **Self-hosting bootstrap.** The compiler's analysis and codegen passes run
  as a native `.dylib` called from Python via ctypes. Binary AST serialization
  hands off the tree; native code returns generated C. Python retains only
  `ast.parse` and the system C compiler invocation.
- **Performance.** Native compile of a 1,000-line `.mpy` module: 0.91 ms
  (vs 102.5 ms in Python). 112× speedup. The compiler is now invisible in
  the pipeline — gcc dominates total build time.
- **Codegen hooks.** Compile-time decorator hooks allow domain-specific
  wrappers (e.g. Sierra Chart ACSIL studies) without polluting `.mpy` source.

Bootstrap test parity with the Python compiler is the immediate priority —
a handful of tests still diverge.

---

## Pythonic built-in types

Strings, lists, and dicts currently use verbose function-call syntax. The goal
is to make them feel like Python while compiling to the same efficient C. This
is the compiler's next major focus.

### Strings

**Current:**
```python
s: str = str_new("hello")
t: str = s + str_new(" world")
u: str = str_format("x=%d", 42)
parts: list = str_new("a,b,c").split(str_new(","))
```

**Target:**
```python
s: str = "hello"
t: str = s + " world"
u: str = f"x={42}"
parts: list[str] = "a,b,c".split(",")
```

Work items:

- **String literal inference.** A bare `"hello"` in a context expecting `str`
  emits `mp_str_new("hello")` automatically. In a context expecting `cstr`,
  it stays as a C string literal. The compiler already knows the expected type
  from annotations — this is a codegen rewrite, not a type system change.
- **Method call syntax on literals.** `"hello".upper()` needs the compiler to
  recognize method calls on string-typed expressions and route them to the
  `mp_str_*` functions. The method dispatch already works for `str` variables;
  extending it to literals means treating a string literal as an implicit
  `str_new` in method-call position.
- **f-string support.** The Python AST already parses f-strings into
  `JoinedStr` / `FormattedValue` nodes (the compiler handles `AstTag.JOINED_STR`).
  Currently these emit `str_format` with positional args. The improvement is
  to support format specs (`:d`, `:.2f`, etc.) and nested expressions cleanly.
- **Automatic `str_free` via defer analysis.** When a string is created from a
  literal and never escapes the function, the compiler can insert
  `defer(str_free(s))` automatically. The escape analysis pass already exists
  for other allocation types — extend it to cover `str`.

### Lists

**Current:**
```python
nums: list[int] = list_new()
nums.append(10)
v: int = nums[0]
```

**Target:**
```python
nums: list[int] = []
nums.append(10)
v: int = nums[0]

# List literals with inference
primes: list[int] = [2, 3, 5, 7, 11]

# Pythonic iteration
for x in nums:
    print(x)
```

Work items:

- **Empty list literal.** `[]` in a `list[T]` context emits `list_new()` with
  the element type inferred from the annotation.
- **Populated list literals.** `[2, 3, 5]` emits `list_new()` followed by
  `list_append` for each element. Element type is inferred from the annotation
  or from the literal types if unambiguous.
- **List comprehension improvements.** Comprehensions already work but require
  explicit `list[T]` annotation. Infer the element type from the expression
  when the annotation is `list[T]` — currently works, but verify coverage for
  nested expressions and filtered comprehensions.
- **`in` operator.** `if x in nums:` emits a linear scan. For `list[T]` this
  is `list_contains(nums, val_int(x))`; the compiler generates the wrapper.
- **Slicing.** `nums[1:3]` returns a new `list[T]`. Lower to
  `list_slice(nums, 1, 3)` with appropriate runtime support.
- **`+` concatenation.** `a + b` on two `list[T]` values emits `list_concat`.
- **`len()` already works** — no changes needed.

### Dicts

**Current:**
```python
d: dict = dict_new()
dict_set(d, "key", val_int(42))
v: int = as_int(dict_get(d, "key"))
```

**Target:**
```python
d: dict[str, int] = {}
d["key"] = 42
v: int = d["key"]

# Dict literals
scores: dict[str, int] = {"alice": 10, "bob": 20}

# Pythonic access
if "alice" in scores:
    print(scores["alice"])

for k, v in scores.items():
    print(k, v)
```

Work items:

- **Typed dict.** `dict[K, V]` as a first-class generic type. The runtime
  `dict` is currently untyped (`val_int`/`as_int` boxing). A typed wrapper
  eliminates boxing overhead and makes subscript access type-safe. Two options:
  monomorphize at compile time (generate `dict_str_int` specializations), or
  keep the current runtime but have the compiler insert box/unbox calls
  automatically based on `K`/`V` types. The second approach is less work and
  matches how `list[T]` works today.
- **Subscript syntax.** `d["key"]` on a `dict[K, V]` emits `dict_get` + unbox
  for reads, `dict_set` + box for writes. The subscript codegen already handles
  `list[T]` — extend the same path to detect dict-typed expressions.
- **Dict literals.** `{"a": 1, "b": 2}` emits `dict_new()` + `dict_set` per
  entry, with types inferred from the annotation.
- **`in` operator.** `if k in d:` emits `dict_has(d, k)`.
- **Iteration.** `for k, v in d.items():` requires a dict iterator in the
  runtime (`dict_iter_init`, `dict_iter_next`). `for k in d:` iterates keys
  only.
- **`.keys()`, `.values()`, `.get(k, default)`.** Method syntax routed to
  runtime functions, same pattern as string methods.

---

## Status

```
 1. String literal inference          ✅
 2. f-string codegen improvements     ✅
 3. List literals and type inference   ✅
 4. Dict subscript syntax             ✅
 5. Typed dict[K, V]                  ✅
 6. Dict literals                     ✅
 7. `in` operator for list and dict   ✅
 8. Dict iteration                    ✅
 9. List slicing and concatenation    ✅
10. Auto-defer for str/list/dict      ✅
```

## Safety checks (`--safe`)

```
 1. Division by zero          ✅  (mp_safe_div_i64 / mp_safe_mod_i64)
 2. Null analysis (static)    ✅  (three-value lattice, compile errors for provably-null — always on)
 3. Null checks (runtime)     ✅  (mp_safe_null_check for `unknown` state under --safe)
 4. Out of bounds             ✅  (mp_safe_bounds_check for array + list)
 5. Integer overflow           ✅  (__builtin_*_overflow via mp_safe_add/sub/mul_i64)
```

Division by zero first to prove the `--safe` flag plumbing end-to-end,
then null analysis in two stages — static analysis (item 2) is always-on
and catches provably-null dereferences as compile errors with zero runtime
cost, then runtime checks (item 3) handle the `unknown` cases under
`--safe`.

Each item is independently testable by comparing generated C output between
the Python and native compiler paths, same strategy used for the bootstrap.

---

## Safety checks (`--safe`)

Runtime safety checks, all gated behind a `--safe` compiler flag. When the
flag is absent, zero overhead — no checks emitted. This follows the existing
three-tier build model: `debug` (safe + assertions), `release` (no checks),
`unsafe` (no checks, no bounds, raw pointers).

The flag controls a compile-time `#define MP_SAFE` that guards every check.
Each check compiles to a single branch that calls a `__attribute__((cold,
noreturn))` handler — the hot path stays branchless and inlineable.

### Division by zero

Every integer division and modulo (`/`, `//`, `%`) is wrapped:

```python
# source
x: int = a / b

# emitted (--safe)
x = mp_safe_div_i64(a, b, __FILE__, __LINE__);

# emitted (release)
x = a / b;
```

The runtime helper is trivial — check `b == 0`, call the cold abort path.
Float division is left unchecked (IEEE 754 produces `inf`/`nan` which is
well-defined and sometimes intentional).

### Null pointer dereference

Static analysis first, runtime checks only where the compiler can't prove
safety. The compiler tracks a nullability state for every `ptr[T]` variable
through the control flow graph using a three-value lattice:

| State | Meaning | Action at dereference |
|-------|---------|----------------------|
| `non-null` | Provably safe | No check emitted |
| `null` | Provably null | **Compile error** |
| `unknown` | Can't prove either way | Runtime check (`--safe` only) |

**Provably non-null** — no check needed:

```python
p: ptr[int] = alloc(8)          # alloc → non-null
v: int = deref(p)               # safe, no check

q: ptr[Node] = addr_of(node)   # addr_of → non-null
r: ptr[Vec2] = Vec2(1.0, 2.0)  # constructor → non-null

if p is not None:
    deref(p)                    # guarded → non-null in this branch
```

Sources of `non-null`: `alloc()`, `addr_of()` / `ref()`, constructor calls,
non-null literal assignment, and control-flow guards (`if p is not None`).

**Provably null** — compile error:

```python
p: ptr[int] = None
deref(p)                        # ERROR: dereference of provably null pointer
```

```
sma_study.mpy:12: error: dereference of provably null pointer 'p'
    note: assigned None at line 11
```

This catches the obvious bugs at compile time — no flag needed, always active.

**Unknown** — runtime check under `--safe`:

```python
def process(p: ptr[Node]) -> void:   # parameter: could be anything
    v: int = p.value                 # unknown → runtime check

# emitted (--safe)
mp_safe_deref_check(p, __FILE__, __LINE__);
v = p->value;
```

Sources of `unknown`: function parameters (public API boundary), return
values from functions that might return `None`, pointer fields loaded from
structs, and variables assigned in only one branch of a conditional.

**Narrowing through control flow:**

```python
def find(head: ptr[Node], key: int) -> ptr[Node]:  # head is unknown
    cur: ptr[Node] = head
    while cur is not None:        # loop guard narrows cur to non-null
        if cur.key == key:        # no check needed — cur is non-null here
            return cur
        cur = cur.next            # next is unknown (struct field load)
    return None                   # cur is null here
```

The analysis propagates through `if`/`elif`/`else`, `while` guards, early
`return`, and `match`/`case`. It joins branches at merge points: `non-null`
+ `null` = `unknown`, `non-null` + `non-null` = `non-null`, etc.

**Whole-program callsite narrowing (optional, later):** If every callsite of
a function passes a provably non-null argument for a parameter, the parameter
can be promoted to `non-null` without a check. This is the same analysis
pattern as the existing cold-function inference — walk all callsites, intersect
the argument states. This is a second-pass optimization; the per-function
local analysis comes first.

**Implementation:** Runs as a dataflow pass after escape analysis (Phase 6),
since it needs the same reaching-definitions information. Conservative by
default — anything unproven is `unknown` and gets a runtime check under
`--safe`, so correctness doesn't depend on the analysis being complete. As
the analysis improves over time, runtime checks silently disappear from the
generated code.

### Out of bounds

Array and list subscript access (`arr[i]`, `lst[i]`) is bounds-checked:

```python
# source — array[int, 64]
v: int = arr[i]

# emitted (--safe)
mp_safe_bounds_check(i, 64, __FILE__, __LINE__);
v = arr[i];

# source — list[int]
v: int = nums[i]

# emitted (--safe)
mp_safe_bounds_check(i, nums->len, __FILE__, __LINE__);
v = ...;
```

For `array[T, N]` the bound is a compile-time constant so the check is a
single comparison. For `list[T]` it reads the length field. Negative indices
are always out of bounds (no Python-style wraparound — this is systems code).

`ptr[T]` raw pointer arithmetic (`p[i]`) is **not** bounds-checked — there is
no length to check against. This is the escape hatch for code that needs raw
access.

### Integer overflow

Arithmetic on `int` (`i64`) and the explicit-width types (`i32`, `u16`, etc.)
is checked for overflow on `+`, `-`, `*`:

```python
# source
c: int = a + b

# emitted (--safe)
c = mp_safe_add_i64(a, b, __FILE__, __LINE__);
```

Implementation uses GCC/Clang `__builtin_add_overflow` /
`__builtin_mul_overflow` — these compile to a single `jo` (jump on overflow)
instruction on x86 and equivalent flag checks on ARM. This is cheaper than
upcasting to 128-bit because:

- The overflow flag is a free byproduct of the ALU operation.
- No widening, no extra registers, no narrowing on the result path.
- The builtins work for all width types (`i8` through `i64`, `u8` through
  `u64`) without needing per-width upcast logic.

The 128-bit upcast approach would only be needed for `i64 * i64` where the
mathematical result exceeds 64 bits and you want the actual wide result.
For overflow *detection* (which is all the safety flag needs), the builtins
are strictly better.

Division overflow (`INT64_MIN / -1`) is caught by the division-by-zero
wrapper — it checks both `b == 0` and the `MIN / -1` edge case.

### Error messages

All safety handlers print the `.mpy` source file and line (via `#line`
directives already emitted by the compiler), not the generated C location:

```
sma_study.mpy:42: division by zero
sma_study.mpy:17: null pointer dereference
sma_study.mpy:31: index 64 out of bounds (size 64)
sma_study.mpy:55: integer overflow in multiplication
```

### CLI

```sh
python3 cli/mpy.py program.mpy --safe              # enable all safety checks
python3 cli/mpy.py program.mpy --safe --run        # safe + run
python3 cli/mpy.py program.mpy                     # release: no checks (default)
```

The `--safe` flag can be combined with `--flags="-O2"` — the checks are
branch-predicted-not-taken and cold-pathed, so the performance cost with
optimization is typically under 2% for compute-heavy code.

---

## Weighted call graph for function ordering

Static PGO-style function layout without needing profile runs. The compiler
already walks every callsite during analysis — this adds edge accumulation
and a layout pass.

### Building the graph

During the existing AST walk, for every `AstTag.CALL` that resolves to a
known function in the same module, record a weighted edge between caller
and callee:

| Context | Weight multiplier |
|---------|-------------------|
| Top-level call | 1× |
| Inside `for`/`while` loop | 10× per nesting level |
| Inside `@hot` function | 5× |
| Inside cold/error path (`@cold`, `raise`, after `if err`) | 0.1× |
| Recursive self-call | 0× (doesn't affect ordering) |

The result is a weighted undirected graph over all functions in the module.
Functions that call each other frequently in hot loops get heavy edges;
error-handling helpers get light ones.

### Layout algorithm

Arrange functions in a linear order that minimizes `Σ weight × distance`
across all edges. This is the minimum linear arrangement problem — NP-hard
in general, but a greedy heuristic works well at function granularity:

1. Seed with the heaviest edge — place those two functions adjacent.
2. For each remaining function (sorted by total edge weight, descending),
   insert it adjacent to its highest-weight already-placed neighbor.
3. Ties broken by source order for stability.

This is essentially what PGO linkers do with basic block reordering (BOLT,
`-forder-file`), just at function granularity and from static analysis
rather than runtime counters.

### Output modes

Two ways to use the result:

**Automatic (default).** The compiler reorders function emissions in
`compile_file` so the generated C has functions laid out in call-graph order.
The linker preserves source order for functions within a translation unit,
so this directly controls the final binary layout without needing a link-time
order file.

**Report.** `--call-graph` flag emits a report showing the suggested ordering
and the heaviest edges, so you can reorganize your `.mpy` source to match:

```
call graph: native_codegen_stmt.mpy
  compile_stmt ↔ compile_expr        weight: 450
  compile_stmt ↔ compile_assign      weight: 120
  compile_expr ↔ compile_call        weight: 380
  compile_call ↔ compile_builtin     weight: 210
  ...
suggested order:
  1. compile_expr
  2. compile_call
  3. compile_builtin
  4. compile_stmt
  5. compile_assign
  ...
```

### What this buys

Functions that call each other land in the same or adjacent cache lines.
The I-cache benefit is most visible in the compiler itself — deep mutual
recursion between `compile_expr`, `compile_call`, `compile_stmt`, and
`compile_binop` means those four functions should be physically adjacent.
At 4ms total compile time the absolute savings are small, but the technique
applies to any micropy project with hot call loops.

---

## Future directions

- **Slice syntax on arrays.** `arr[2:8]` for `array[T, N]` and `ptr[T]` —
  emit pointer arithmetic.
- **Multiple return values.** `a, b = divmod(x, y)` — emit a struct return
  with destructuring.
- **`with` statement generalization.** Currently works for `open`. Extend to
  any type with `__enter__`/`__exit__` or a `defer`-compatible cleanup.
- **Pattern matching on structs.** `case Point(x=0):` — destructure struct
  fields in match arms.
- **Package manager / dependency resolution.** `import` across project
  boundaries with versioned modules.