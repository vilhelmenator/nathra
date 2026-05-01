# Nathra Compiler Roadmap

Roadmap — LLM Ergonomics

## 1. Local type inference

Drop required annotations on locals; infer from initializer. Function
signatures and struct fields stay annotated. Annotation always wins over
inference, so existing code keeps working. Biggest visible reduction in
surface noise. Low risk.

```python
# before
total: f32 = 0.0
count: i32 = 0
name: str = "output"
items: list[int] = [1, 2, 3]

# after
total = 0.0
count = 0
name = "output"
items = [1, 2, 3]
```

---

## 2. `.value` for scalar pointers

`p: ptr[int]` gets `p.value` for read and `p.value = x` for write. Applies
to pointers where there's no field access alternative — scalars,
`ptr[ptr[T]]` chains end in `.value`. Struct pointers are unchanged. Small
targeted addition that fills a real syntactic gap. Skip `.addr` entirely.

```python
# before
v: int = deref(p)
deref_set(p, 42)

# after
v = p.value
p.value = 42
```

---

## 3. Implicit `addr_of` at call sites

When a function takes `ptr[T]` and the caller passes a `T`, insert the
address-of automatically. Generalizes the `@property` behavior already
present. Removes the most common remaining `addr_of` use. Low risk if
you lint for the surprise case (passing a value to a function that mutates
through a non-`const[T]` parameter).

```python
# before
modify(addr_of(x))

# after
modify(x)
```

---

## 4. Better error messages with actionable fixes

Every error gets a `help:` suggestion pointing at the specific fix —
`defer(...)`, `own[T]`, change return type, etc. High leverage for LLM
use specifically because LLMs are excellent at applying suggested fixes.
Compounding payoff: every error improved helps every user forever.

```
sma_study.py:25: error: list 'nums' may leak — not freed on all paths
    note: 'nums' is allocated at line 20, not freed when returning at line 23
    help: add defer(list_free(nums)) after allocation
```

---

## 5. `--safe` defaults tied to build topology

Drop `--safe` as a primary user-facing flag. `dev` and `service` topologies
get safety on; `release` gets it off. Keep `--safe`/`--unsafe` as overrides
for the unusual cases (benchmarking with safety on, profiling release with
it off). Static null analysis stays always-on regardless. Trivial to
implement, just a default change.

| Topology | Safety | Optimization |
|----------|--------|--------------|
| `dev` (default) | on | `-O0 -g` |
| `service` | on | `-O2` |
| `release` | off | `-O2` |

---

## 6. Inferred performance decorators

Extend the existing auto-cold inference. Functions called only from cold
contexts → cold. Small functions called in tight loops → inline candidate.
Constant args in hot contexts → already specialized per docs. The
decorators become overrides for the rare case where inference is wrong,
not requirements. Medium effort, the call graph is already built.

---

## 7. Optimization explanation flag

`--explain-optimizations` prints what the compiler did: which pointers got
`restrict`, which functions got outlined cold paths, which calls got
specialized constants. Optionally extend to `--explain-loads` showing
pointer-chase chains. Doesn't change the language; teaches users (and LLMs)
what patterns trigger the wins. Strictly additive.

```sh
python3 nathra.py program.py --explain-optimizations
```

```
optimizations applied:
  process()
    restrict: dst, src (no pointer aliasing detected)
    cold-split: error path at line 12 → process_cold_1()
  sma()
    unroll: loop at line 8 (trip count 4, constant)
    const-specialize: scaled_sum(arr, n, 4) → scaled_sum_stride4(arr, n)
```

---

## Summary

Items 1, 2, 3 are surface-noise reductions. Item 4 is the feedback-loop
improvement. Item 5 is a default change. Items 6 and 7 are the
compiler-tells-you-what-it-did pair. None of these change the language's
underlying model — typed C with Python syntax, explicit memory,
source-aware optimization. They reduce friction at the surface and improve
the feedback loop. Each is independently shippable, none breaks existing
code.
