# Compiler Optimizations & Safety

## Compiler optimizations

The compiler performs a set of automatic analyses and rewrites at compile time. All are zero-cost in the sense that nothing is added at runtime that wasn't already implied by the source.

### `restrict` inference

When a function takes two or more `ptr[T]` parameters and none of them is ever assigned from another within the function body, the compiler emits `restrict` on each parameter. This is the single highest-value qualifier for loop vectorization — the C compiler cannot insert it on its own.

```python
def copy_bytes(dst: ptr[byte], src: ptr[byte], n: int) -> void:
    ...
# emits: void copy_bytes(uint8_t * restrict dst, uint8_t * restrict src, int64_t n)
```

If any pointer is assigned from another (`a = b`), neither receives `restrict`.

### Branch-free select

An `if/else` that assigns the same variable in both arms using only pure expressions (literals, locals, arithmetic — no calls, no pointer derefs with side effects) is emitted as a C ternary `?:`. The C compiler sometimes converts `if/else` to a `cmov` instruction but only when it can prove both arms are side-effect-free; nathra knows this from the AST.

```python
result: int = 0
if x < 0:
    result = -x
else:
    result = x
# emits: result = ((x < 0) ? (-x) : (x));
```

### Loop unroll hints

`for i in range(N)` where `N` is a small compile-time constant (≤ 8) emits `#pragma GCC unroll N` immediately before the loop, giving the C compiler a reliable unroll hint without manual `@unroll` annotation.

```python
for i in range(4):
    total = total + arr[i]
# emits: #pragma GCC unroll 4
#        for (int64_t i = 0; i < 4; i++) { ... }
```

### Stack variable lifetime narrowing

Large local variables are wrapped in a `{ }` block scope sized to their actual first/last use, so the C compiler knows the stack slot can be reused for a non-overlapping local. nathra can guarantee this safely because it tracks whether `&var` is ever taken; C compilers must conservatively assume it might be.

### Hot/cold splitting

When an `if` arm contains only error handling (a `raise`, a call to a `@cold` function, or another cold `if`) the arm is extracted into a separate `static __attribute__((cold))` helper and the branch is wrapped in `NR_UNLIKELY(...)`. This keeps the hot path's instruction footprint tight for I-cache utilisation.

```python
def safe_divide(a: int, b: int) -> int:
    if b == 0:
        raise "division by zero"
    return a / b
# The raise arm becomes a separate cold helper; the hot path is just the division.
```

Functions whose every code path ends in `raise` or `abort()` are automatically annotated `__attribute__((cold, noreturn))` — no annotation required.

### Constant specialization for `@hot` functions

When a `@hot` function calls a callee with a compile-time constant argument, the compiler emits a specialized copy of the callee with that constant folded in. The constant enables the C compiler to vectorize, strength-reduce, and eliminate branches in ways it cannot with a variable argument.

```python
@hot
def process(arr: ptr[int], n: int) -> int:
    return scaled_sum(arr, n, 4)   # stride=4 is constant → specialized copy emitted
```

**Threshold:** up to 3 distinct constant combinations per callee are specialized freely (one copy each, negligible code size). Beyond 3 distinct combinations, specialization proceeds only for callees with ≤ 30 statements. Functions inside `@hot` or `@unroll` contexts are always eligible.

## Safety checks

`--safe` enables runtime safety checks. All checks are gated behind `#ifdef NR_SAFE` so there is zero overhead when compiling without the flag.

```sh
python3 cli/nathra.py program.py --safe          # compile with safety checks
python3 cli/nathra.py program.py --safe --run     # compile and run
```

### Division by zero

Integer `/` and `%` are wrapped with a check that aborts with file and line info instead of triggering undefined behavior:

```python
x: int = a / b   # aborts with "division by zero at file.py:3" if b == 0
```

### Integer overflow

`+`, `-`, `*` on integers use `__builtin_*_overflow` to detect wrapping:

```python
big: int = 9223372036854775807
result: int = big + 1   # aborts with "integer overflow at file.py:2"
```

### Out-of-bounds access

Array subscripts are bounds-checked at runtime:

```python
arr: array[int, 4] = {1, 2, 3, 4}
x: int = arr[10]   # aborts with "index 10 out of bounds [0, 4) at file.py:2"
```

### Null pointer dereference

**Static analysis (always on):** The compiler tracks null/non-null/unknown state for every `ptr[T]` variable through assignments and `if`/`while` guards. Provably-null dereferences are compile errors — no flag needed.

**Runtime checks (under `--safe`):** Where the compiler cannot prove a pointer is non-null (state is `unknown`), it emits a null check before the dereference:

```python
p: ptr[int] = find_item(key)
# compiler doesn't know if find_item returns null
x: int = deref(p)   # under --safe: aborts if p is NULL

if p is not None:
    x = deref(p)     # no check — compiler proved non-null in this branch
```

