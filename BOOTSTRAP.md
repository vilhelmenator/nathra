# Bootstrap Roadmap: Self-Hosting the Micropy Compiler

> Goal: rewrite the compiler's hot path (92ms of 96ms) in micropy, compile it to
> a native shared library, and call it from Python. The Python side keeps only
> `ast.parse` (3.7ms) and the binary AST serializer.

---

## Current state

| Step | Tool | Time |
|------|------|------|
| Parse `.mpy` source | Python `ast.parse` | 3.7 ms |
| Analysis + codegen | Python (compiler.py + codegen_*.py) | 92 ms |
| C compilation | gcc/clang | ~80-200 ms |

The compiler is 6,323 lines across 4 files, 79 methods, ~50 state fields.
It uses 709 f-strings, 200+ dict lookups, 41 distinct AST node types,
28 list comprehensions, and deep mutual recursion between `compile_expr`
and `compile_stmt`.

---

## Architecture

```
                    Python side                  Native side (.dylib)
                ┌──────────────────┐         ┌──────────────────────┐
  source.mpy → │ ast.parse()      │         │                      │
               │ serialize AST    │──buf──→ │ deserialize AST      │
               │ to MpWriter      │         │ analysis passes      │
               └──────────────────┘         │ codegen → C string   │
                                            │ return buf           │
                    Python side              └──────────────────────┘
                ┌──────────────────┐                  │
                │ receive C string │←────────buf──────┘
                │ write .c file    │
                │ invoke gcc       │
                └──────────────────┘
```

Python stays responsible for `ast.parse` (CPython's C parser is fast and
correct — no reason to rewrite it) and for invoking the system C compiler.
Everything between those two steps moves to native code.

---

## Phase 0 — Binary AST format ✅

Define a compact binary encoding for Python AST nodes and write a Python-side
serializer that walks `ast.Module` and writes it to an `MpWriter`-compatible
buffer.

### 0.1 — AST node type enum

Map the 41 AST node types the compiler handles to integer tags:

```python
class AstTag:
    MODULE       = 0
    FUNCTION_DEF = 1
    CLASS_DEF    = 2
    ASSIGN       = 3
    ANN_ASSIGN   = 4
    AUG_ASSIGN   = 5
    RETURN       = 6
    IF           = 7
    WHILE        = 8
    FOR          = 9
    EXPR         = 10
    CALL         = 11
    NAME         = 12
    CONSTANT     = 13
    ATTRIBUTE    = 14
    SUBSCRIPT    = 15
    BIN_OP       = 16
    UNARY_OP     = 17
    COMPARE      = 18
    BOOL_OP      = 19
    LIST         = 20
    TUPLE        = 21
    LAMBDA       = 22
    IF_EXP       = 23
    LIST_COMP    = 24
    JOINED_STR   = 25
    # ... etc
```

### 0.2 — Wire format

Each node is serialized as:

```
[u8]  tag (node type)
[u16] lineno
[u8]  field count
For each field:
  [u8]  field kind (node=0, node_list=1, string=2, int=3, float=4, bool=5, op=6, none=7)
  [...]  value (tag-dispatched)
```

Strings are length-prefixed (`i32` + bytes). Node lists write `i32` count
then each child. Operators are single `u8` tags.

This is a flat depth-first encoding — no pointers, no offsets. The deserializer
on the native side reads sequentially and builds a tree of C structs.

### 0.3 — Python serializer

```python
def serialize_ast(tree: ast.Module, w: MpWriter) -> None:
    """Walk ast.Module depth-first, write binary AST to MpWriter."""
```

One function, ~200 lines. Handles the 41 node types the compiler cares about.
Unknown node types write a SKIP marker so the format is forward-compatible.

### 0.4 — Test: round-trip

Serialize → deserialize (in Python first) → compare with original AST.
Validates the format before any native code is written.

**Estimated size:** ~300 lines Python + ~100 lines for format spec.

---

## Phase 1 — Native AST data structures ✅

Define the AST node structs in micropy. These mirror the Python `ast` module
but use tagged unions and pointer-based children instead of Python objects.

### 1.1 — Core node struct

```python
struct AstNode:
    tag: u8
    lineno: u16
    # Payload is a union selected by tag
```

Two design options:

**Option A — Single struct with union payload:**
```python
@union
struct AstPayload:
    name: AstName
    constant: AstConstant
    call: AstCall
    binop: AstBinOp
    # ... 41 variants
```

Pros: one allocation per node, simple. Cons: every node is as large as the
largest variant (~64 bytes).

**Option B — Tag + ptr[void] to type-specific struct:**
```python
struct AstNode:
    tag: u8
    lineno: u16
    data: ptr[void]   # cast to AstCall*, AstName*, etc. based on tag
```

Pros: nodes are tiny (12 bytes), payload is exact-sized. Cons: two allocations
per node (or arena-allocate both).

**Recommendation:** Option B with arena allocation. All AST nodes and their
payloads are allocated from a single arena that is freed after compilation.
Zero individual frees, zero fragmentation, one `arena_free` at the end.

### 1.2 — Per-node-type structs

~30 payload structs (many AST types share structure):

```python
struct AstName:
    id: str

struct AstConstant:
    kind: u8          # 0=int, 1=float, 2=str, 3=bool
    int_val: i64
    float_val: f64
    str_val: str

struct AstCall:
    func: ptr[AstNode]
    args: ptr[AstNode]       # linked list or array
    arg_count: i32
    keywords: ptr[AstKW]
    kw_count: i32

struct AstBinOp:
    left: ptr[AstNode]
    right: ptr[AstNode]
    op: u8

struct AstFunctionDef:
    name: str
    args: ptr[AstArg]
    arg_count: i32
    defaults: ptr[AstNode]
    default_count: i32
    body: ptr[AstNode]
    body_count: i32
    returns: ptr[AstNode]    # nullable
    decorators: ptr[AstNode]
    decorator_count: i32
```

### 1.3 — Binary AST deserializer (native)

```python
def deserialize_ast(r: ptr[MpReader], arena: ptr[MpArena]) -> ptr[AstNode]:
    """Read binary AST from buffer, allocate all nodes from arena."""
```

Reads the format defined in Phase 0. Returns the root `AstNode*`. All memory
comes from the arena — one free cleans up the entire tree.

**Estimated size:** ~400 lines micropy for structs + deserializer.

---

## Phase 2 — Symbol tables and compiler state ✅

Port the compiler's data structures from Python dicts/sets to micropy structs.
This is the foundation that the analysis and codegen passes build on.

### 2.1 — String-keyed hash map

The compiler does ~200 dict lookups by string key. Micropy needs a hash map:

```python
struct StrMap:
    keys: ptr[str]
    values: ptr[ptr[void]]
    hashes: ptr[u32]
    count: i32
    cap: i32
```

Operations: `strmap_new`, `strmap_get`, `strmap_set`, `strmap_has`, `strmap_free`.
FNV-1a hash, open addressing with linear probe. ~80 lines.

This replaces all of: `local_vars`, `func_args`, `structs`, `enums`,
`constants`, `modules`, `from_imports`, `mutable_globals`, `type_aliases`,
`func_ret_types`, `func_param_types`, etc.

### 2.2 — String set

For membership tests (`_cold_funcs`, `_extern_funcs`, `compiled_files`, etc.):

```python
struct StrSet:
    keys: ptr[str]
    hashes: ptr[u32]
    count: i32
    cap: i32
```

~40 lines. Subset of StrMap without values.

### 2.3 — Compiler state struct

```python
struct CompilerState:
    indent: i32
    lines: ptr[MpWriter]       # output buffer (not a list of strings — write directly)
    header: ptr[MpWriter]
    local_vars: StrMap          # name → ctype
    func_args: StrMap
    structs: StrMap             # name → ptr[FieldList]
    constants: StrMap
    mutable_globals: StrMap
    func_ret_types: StrMap
    cold_funcs: StrSet
    extern_funcs: StrSet
    serializable_structs: StrSet
    # ... ~40 more fields
    arena: ptr[MpArena]         # all temporary allocations
```

**Key design change:** instead of `self.lines = []` (list of strings joined at
the end), use an `MpWriter` and write C code directly into the byte buffer.
`emit()` becomes `mp_write_str(state.lines, line)` + newline. This is faster
and avoids the Python list-of-strings → join overhead.

**Estimated size:** ~200 lines for data structures + state struct.

---

## Phase 3 — Type mapping ✅

Port `type_map.py` (272 lines). This is the simplest module — pure functions
with no mutation, no complex state.

```python
def map_type(node: ptr[AstNode]) -> str:
    """Map an AST annotation node to a C type string."""
```

The `TYPE_MAP` dict becomes a static lookup table (array of `(str, str)` pairs
or a `StrMap` initialized at startup). `map_type` walks `AstNode` trees instead
of `ast.Name`/`ast.Subscript` Python objects.

Also port: `get_array_info`, `get_funcptr_info`, `get_vec_info`, `mangle_type`.

**Estimated size:** ~300 lines micropy.

---

## Phase 4 — Expression codegen

Port `codegen_exprs.py` (1,265 lines). This is `compile_expr` — the recursive
expression compiler that returns a C expression string.

### 4.1 — compile_expr

The core function is a tag-dispatch switch:

```python
def compile_expr(state: ptr[CompilerState], node: ptr[AstNode]) -> str:
    match node.tag:
        case AstTag.CONSTANT:
            return compile_constant(state, node)
        case AstTag.NAME:
            return compile_name(state, node)
        case AstTag.BIN_OP:
            return compile_binop(state, node)
        case AstTag.CALL:
            return compile_call(state, node)
        # ... ~20 cases
```

The Python version uses `isinstance` chains. The micropy version uses
`match` on the tag — cleaner and faster.

### 4.2 — String building

The hardest part of the port. Python does:
```python
return f"{left} {op} {right}"
```

Micropy:
```python
return str_format("%s %s %s", left.data, op.data, right.data)
```

`str_format` already exists and wraps `snprintf`. The verbosity is higher but
the pattern is mechanical.

### 4.3 — Builtin table

The `builtins` dict (~90 entries mapping micropy names to C names) becomes a
static array of `(str, str)` pairs with linear scan, or a pre-built `StrMap`.

**Estimated size:** ~1,400 lines micropy (slightly larger than Python due to
explicit string handling).

---

## Phase 5 — Statement codegen

Port `codegen_stmts.py` (2,127 lines). This is the largest module:
`compile_stmt`, `compile_function`, `compile_struct`, `compile_if`,
`compile_for`, `compile_while`, `compile_match`, etc.

### 5.1 — compile_stmt dispatcher

Same pattern as compile_expr — tag dispatch:

```python
def compile_stmt(state: ptr[CompilerState], node: ptr[AstNode]) -> void:
    match node.tag:
        case AstTag.ANN_ASSIGN:  compile_ann_assign(state, node)
        case AstTag.ASSIGN:      compile_assign(state, node)
        case AstTag.IF:          compile_if(state, node)
        case AstTag.FOR:         compile_for(state, node)
        # ... ~15 cases
```

### 5.2 — compile_function

The most complex single function (~300 lines Python). It:
- Pre-scans for lambdas and extracts them
- Builds the function signature with qualifiers (`const`, `restrict`, `inline`)
- Manages local variable scope (push/pop `local_vars`)
- Handles defer stack
- Runs escape analysis for auto-free

Each of these sub-tasks is a separate function in the native version.

### 5.3 — compile_struct

Emits struct definition, constructor helper, methods, and `@serializable`
functions. Already well-isolated in the Python code.

**Estimated size:** ~2,500 lines micropy.

---

## Phase 6 — Analysis passes

Port the analysis passes from `compiler.py`:

- Escape analysis (`_escape_classify`) — ~60 lines
- Allocation signature tagging (`_build_alloc_tags`) — ~80 lines
- Cold inference (`_infer_cold_from_body`, `_infer_cold_from_callsites`) — ~100 lines
- Static leak detection (`_check_leaks`) — ~150 lines

These are all tree walks over `AstNode` — straightforward to port.

**Estimated size:** ~500 lines micropy.

---

## Phase 7 — Top-level orchestration

Port `compile_file` — the top-level function that:
1. Runs the first pass (collect structs, functions, globals, constants)
2. Processes imports
3. Emits C sections in order (includes, enums, structs, globals, prototypes,
   functions, main, runtime impl)
4. Generates the header file

### 7.1 — Entry point

```python
@export
def compile_ast(ast_buf: ptr[u8], ast_len: i64,
                out_buf: ptr[ptr[u8]], out_len: ptr[i64]) -> i32:
    """Main entry point called from Python via ctypes.

    Takes serialized AST buffer, returns C source string.
    Returns 0 on success, -1 on error.
    """
```

### 7.2 — Python glue

```python
# mpy.py — updated to use native compiler
lib = ctypes.CDLL("./compiler.dylib")
lib.compile_ast.argtypes = [c_char_p, c_int64, POINTER(c_char_p), POINTER(c_int64)]
lib.compile_ast.restype = c_int32

tree = ast.parse(source)
ast_buf = serialize_ast(tree)
out_buf = c_char_p()
out_len = c_int64()
lib.compile_ast(ast_buf, len(ast_buf), byref(out_buf), byref(out_len))
c_source = out_buf.value[:out_len.value].decode()
```

**Estimated size:** ~800 lines micropy + ~50 lines Python glue.

---

## Phase 8 — Bootstrap

The moment of truth: compile the native compiler with itself.

1. **First bootstrap:** Python compiler compiles the `.mpy` compiler to `.c`,
   gcc compiles it to `compiler.dylib`.

2. **Second bootstrap:** `compiler.dylib` compiles the `.mpy` compiler source
   (via serialized AST). Compare the output `.c` against the Python compiler's
   output — they must be identical.

3. **Third bootstrap:** The self-compiled `compiler.dylib` compiles itself
   again. Output must match step 2 exactly (fixed-point).

Once the fixed-point is reached, the Python compiler is only needed as a
fallback. Normal development uses the native compiler.

---

## Estimated sizes

| Phase | What | Est. | Actual |
|-------|------|------|--------|
| 0 | Binary AST format + Python serializer (`ast_serial.py`) | ~400 | 874 |
| 1 | Native AST structs + deserializer (`ast_nodes.mpy`) | ~400 | 806 |
| 2 | Symbol tables + compiler state (`strmap.mpy`) | ~200 | 373 |
| 3 | Type mapping (`native_type_map.mpy`) | ~300 | 295 |
| 4 | Expression codegen | ~1,400 | |
| 5 | Statement codegen | ~2,500 | |
| 6 | Analysis passes | ~500 | |
| 7 | Top-level orchestration + glue | ~850 | |
| **Total** | | **~6,550** | **2,348 so far** |

Roughly 1:1 with the Python version (6,323 lines). The extra lines come from
explicit string handling; the savings come from replacing `isinstance` chains
with `match` and dropping Python-specific patterns (comprehensions, decorators
on methods, dataclass boilerplate).

---

## Ordering and dependencies

```
Phase 0 (AST format)
  │
  ├── Phase 1 (AST structs + deserializer)
  │     │
  │     └── Phase 2 (symbol tables)
  │           │
  │           ├── Phase 3 (type mapping)
  │           │     │
  │           │     ├── Phase 4 (expr codegen)
  │           │     │     │
  │           │     │     └── Phase 5 (stmt codegen)
  │           │     │           │
  │           │     │           └── Phase 6 (analysis passes)
  │           │     │                 │
  │           │     │                 └── Phase 7 (orchestration)
  │           │     │                       │
  │           │     │                       └── Phase 8 (bootstrap)
```

Each phase is independently testable against the Python compiler's output.
The testing strategy is: for each phase, run the same input through both
the Python path and the partial native path, compare results.

---

## What stays in Python

- `ast.parse` — CPython's parser is fast (3.7ms) and correct. No reason to
  rewrite it.
- AST serializer — small (~200 lines), runs once per compile, in Python.
- `mpy.py` CLI — argument parsing, file I/O, invoking gcc. ~170 lines.
- `build.py` — build script interpreter. Could be ported later but low value.
- `snekc.py` — REPL shell. Stays in Python (it drives the compile loop).

---

## Measured performance

Self-compilation benchmark: the native compiler compiling its own 8 source
modules (3,380 lines of .mpy) to C.

| File | Python | Native | Speedup |
|------|--------|--------|---------|
| native_analysis.mpy | 117.9 ms | 0.20 ms | 595x |
| native_compile_file.mpy | 459.1 ms | 0.78 ms | 587x |
| native_infer.mpy | 124.2 ms | 0.26 ms | 478x |
| native_type_map.mpy | 124.0 ms | 0.28 ms | 438x |
| native_codegen_stmt.mpy | 347.6 ms | 1.01 ms | 344x |
| native_codegen_call.mpy | 247.2 ms | 0.85 ms | 290x |
| native_codegen_expr.mpy | 190.5 ms | 0.66 ms | 289x |
| native_compiler_state.mpy | 35.5 ms | 0.14 ms | 253x |
| **Total** | **1,646 ms** | **4.18 ms** | **394x** |

End-to-end compile step breakdown:

| Step | Before | After |
|------|--------|-------|
| `ast.parse` | 3.7 ms | 3.7 ms (unchanged) |
| AST serialize | — | ~0.5 ms |
| Analysis + codegen | 92 ms | ~1-4 ms (native) |
| C compilation | ~100 ms | ~100 ms (unchanged) |
| **Total** | **~200 ms** | **~105 ms** |

The compiler step goes from the bottleneck to negligible. Total compile time
becomes dominated by gcc, which is the correct steady state — your compiler
should never be slower than the C compiler it feeds.

---

## Prerequisite compiler improvements (completed)

The bootstrap work required several improvements to the micropy compiler itself:

- **`cast(T, val)` generic builtin** — `cast(ptr[AstNode], expr)` emits `(AstNode*)(expr)`.
  Replaces the limited `cast_int`/`cast_float` builtins for arbitrary type casts.
- **`mp_arena_str_new_len`** — arena-allocated string from pointer + length (for binary data).
- **`read_file_bin` / `write_file_bin`** — binary file I/O builtins mapped to runtime functions.
- **Cross-module compilation fixes:**
  - Header forward typedefs (`typedef struct X X;`) so structs can reference each other
  - Integer constants exported as `#define` (not `extern const`) for cross-module use
  - Non-main modules skip struct/enum re-emission in `.c` (comes from included `.h`)
  - `main()` skipped in dependency modules
  - Module-local function calls correctly prefixed with `module_name_`
  - `deref(ptr, val)` recognized as a write (prevents false `const` on output parameters)
  - Header prototypes use same `const`/`restrict` inference as `.c` definitions
