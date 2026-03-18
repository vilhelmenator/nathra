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

- [ ] **Cross-function ownership chain analysis**
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

- [ ] **Match/case cold-arm ordering**
  When emitting the `if/else if` chain for a `match`, sort arms so any arm whose
  body is a single `raise` or calls a `@cold` function goes last. Direct extension
  of the guard-raise logic.

- [ ] **String literal stack optimization**
  `str_new("literal")` where the variable never appears as the target of a mutating
  `str_*` call → emit `const char*` directly. No heap allocation for temporary strings.

- [ ] **`@compile_time` array prewarm**
  When a `@compile_time`-generated array is referenced in a function body, emit
  `MP_PREFETCH` for its first cache line at function entry. The array is a known
  static address — zero guesswork.

### Requires escape analysis (build correctness primitive first)

- [ ] **`alloca` substitution for small known-size allocations**
  `alloc(N)` where N is a compile-time constant ≤ 4 KB and the pointer is local-only
  → emit `alloca(N)`, drop the `free`. Zero heap overhead, zero fragmentation,
  automatic cleanup on return. Fires constantly for scratch buffers.

- [ ] **Conditional `alloca`/`malloc` for bounded allocations**
  `alloc(n)` where n is a runtime value but is bounded by a known constant → emit
  `n <= 4096 ? alloca(n) : malloc(n)` with a matching conditional `free`.

- [ ] **Allocation merging**
  Multiple `alloc` calls of known sizes in the same block scope, all local-only →
  single `alloca`/`malloc`, carved into named offsets. One allocation, one cache
  line, one free (or none if on the stack).

- [ ] **Arena allocation batching**
  Multiple `arena_list_new` / `arena_alloc` calls from the same arena in the same
  block → coalesce into a single bump. One pointer advance, zero per-item overhead.
  Sizes are compile-time constants.

### Structural passes — moderate bookkeeping

- [ ] **`@cold` inference from function body**
  If every code path in a function terminates in `raise`, `abort()`, or a call to
  another `@cold` function — auto-annotate `__attribute__((cold))`. No annotation
  required from the programmer.

- [ ] **`@cold` inference via call-site analysis**
  If a function is *only ever called* from error branches (guard-raise paths,
  `is_err(...)` blocks) — auto-annotate `__attribute__((cold))`. Higher value than
  body inference; catches helper functions that look normal in isolation.

- [ ] **Stack variable lifetime narrowing**
  Track first and last statement index for each large local. If it is never
  address-taken and its lifetime doesn't overlap another large local, wrap it in a
  `{ }` scope so the C compiler knows the stack slot can be reused. MicroPy knows
  whether `&var` is ever taken; C compilers must conservatively assume it might be.

- [ ] **Linked-list / tree traversal prefetch**
  Detect `while node is not None: ... node = node.next` patterns. Emit
  `MP_PREFETCH(node->next->next, 0, 1)` at the top of each iteration. Pointer-chase
  latency is the dominant cost in tree traversals.

- [ ] **Function ordering (topological sort)**
  Emit functions in call-graph order so each callee appears before its callers.
  Removes the need for forward declarations and gives the inliner the best possible
  view. Requires per-function emit buffering and a topological sort of the call graph.

### High complexity — defer until above is stable

- [ ] **Non-temporal prefetch for single-pass streaming loops**
  Loops that write every element exactly once and never re-read → `_mm_stream`
  / `__builtin_ia32_movntdq`. Bypasses cache entirely, avoids evicting hot data.
  Requires recognizing the write-only streaming pattern.

- [ ] **Loop-invariant hoist hints**
  Hoist method calls on structs that don't change within the loop into locals before
  the loop. Requires alias analysis: confirming no pointer write in the body can
  reach the struct. More conservative analysis needed than a simple scan.

- [ ] **Explicit NRVO (return-value placement)**
  Detect allocate-fill-return-pointer pattern. Rewrite callee to accept an output
  pointer; rewrite call sites to pass a stack slot. Eliminates the heap allocation
  entirely. Cross-function transformation — only item here that mutates function
  signatures and requires coordinated changes across modules.

- [ ] **Struct field sparsity warning**
  At struct definition time, compute the natural layout and warn if field ordering
  would leave gaps larger than a cache line. Suggest a reordered layout.