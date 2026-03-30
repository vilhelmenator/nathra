"nathra"
"""
bench_opts.nth — optimization contrast benchmark.

Run as Python:   python3 bench/bench_opts.nth
Run as nathra:  python3 nathra.py bench/bench_opts.nth --run

Demonstrates four automatic nathra optimizations vs plain C:
  1. restrict inference  — SAXPY with 3 ptr params → restrict enables SIMD
  2. constant specializ. — strided sum called from @hot with stride=4 constant
  3. alloca substitution — local alloc(≤4KB) replaced with stack allocation
  4. @soa layout         — Struct-of-Arrays for sequential field access
"""
from __future__ import annotations
from nathra_stubs import *

# ---------------------------------------------------------------------------
# Module-level constants — used by main() when compiled
# ---------------------------------------------------------------------------
N:           const = 4_000_000    # elements per array (3 arrays = 96 MB)
REPS:        const = 100
STRIDED_N:   const = 1_000_000    # N/4 — stride-4 accesses stay in bounds
ALLOC_N:     const = 64           # int64 elements per scratch buffer
ALLOC_BYTES: const = 512          # ALLOC_N * 8
ALLOC_REPS:  const = 5_000_000    # calls to the scratch-buffer function
SOA_N:       const = 5_000_000    # particles; 4 fields × 8B × 5M = 160 MB AoS, 40 MB SoA
SOA_REPS:    const = 20

# ---------------------------------------------------------------------------
# 1. SAXPY  (out = a*x + y)
#    Three ptr[float] params, none assigned from another → all get restrict.
#    restrict removes the runtime aliasing-check prelude the C compiler must
#    emit without it, and unlocks full SIMD vectorisation.
# ---------------------------------------------------------------------------
def saxpy(out: ptr[float], x: ptr[float], y: ptr[float], a: float, n: int) -> void:
    i: int = 0
    while i < n:
        out[i] = a * x[i] + y[i]
        i += 1

# ---------------------------------------------------------------------------
# 2. Strided reduction
#    Called from a @hot context with the compile-time constant stride=4.
#    nathra emits a specialised copy with stride folded in — the index
#    multiply disappears and the loop body becomes more vectorisable.
# ---------------------------------------------------------------------------
def strided_sum(arr: ptr[float], n: int, stride: int) -> float:
    total: float = 0.0
    i: int = 0
    while i < n:
        total = total + arr[i * stride]
        i += 1
    return total

@hot
def bench_strided(arr: ptr[float], n: int) -> float:
    return strided_sum(arr, n, 4)   # stride=4 is a compile-time constant here

# ---------------------------------------------------------------------------
# 3. Alloca substitution
#    alloc(ALLOC_BYTES) is a compile-time constant ≤ 4 KB, and scratch is
#    local-only (never returned or stored into a struct field).
#    nathra replaces it with alloca(ALLOC_BYTES) and drops the free() call.
#    Stack allocation costs ~1 ns (a single sub instruction on the stack
#    pointer); malloc/free costs ~30–100 ns per call on most allocators.
# ---------------------------------------------------------------------------
def process_with_scratch(data: ptr[int], n: int) -> int:
    scratch: ptr[int] = alloc(512)           # → alloca(512) in nathra
    i: int = 0
    while i < n:
        scratch[i] = data[i] * 2 + 1
        i += 1
    total: int = 0
    i = 0
    while i < n:
        total = total + scratch[i]
        i += 1
    free(scratch)                            # dropped by nathra (alloca)
    return total

# ---------------------------------------------------------------------------
# 4. Struct-of-Arrays (@soa)
#    AoS layout: Particle[i].x is at byte offset i*32 — every cache line holds
#    2 structs but only 1/4 of it is the x field → 75% wasted bandwidth.
#    SoA layout: particles_x[i] is sequential — every byte fetched is useful,
#    and the hardware prefetcher and SIMD can operate at full width.
#    With 500K particles (16 MB AoS vs 4 MB SoA for x), the benchmark is
#    L3-bound for SoA but DRAM-bound for AoS → ~3-4× speedup.
# ---------------------------------------------------------------------------
@soa
class Particle:
    x: float
    y: float
    z: float
    vx: float
    vy: float
    vz: float
    mass: float
    charge: float

particles: array[Particle, 5000000]    # → 4 flat double arrays in C

@noinline
def extract_x(out: ptr[float], n: int) -> void:
    i: int = 0
    while i < n:
        out[i] = particles[i].x    # rewritten: particles_x[i]
        i += 1

# ---------------------------------------------------------------------------
# 5. Restrict with short arrays
#    4 ptr[float] params, N=64, called 50M times.
#    Without restrict the compiler emits a runtime overlap-check preamble on
#    every call. With restrict (all 4 params non-aliasing) it goes straight
#    into the vectorised body — preamble cost is a large fraction of per-call
#    work at N=64.
# ---------------------------------------------------------------------------
RESTRICT_N:    const = 64
RESTRICT_REPS: const = 50_000_000

@noinline
def fused_mad(out: ptr[float], a: ptr[float], b: ptr[float], c: ptr[float], n: int) -> void:
    i: int = 0
    while i < n:
        out[i] = a[i] * b[i] + c[i]
        i += 1

# ---------------------------------------------------------------------------
# 6. Hot/cold splitting
#    Three validation raises → three __attribute__((cold,noreturn)) helpers.
#    The hot path contains only the useful loop; cold error-handling code is
#    moved out of the instruction stream, shrinking the hot-path footprint and
#    reducing I-cache pressure when called from a tight loop.
# ---------------------------------------------------------------------------
HOT_N:    const = 256
HOT_REPS: const = 5_000_000

@noinline
def validated_sum(data: ptr[int], n: int) -> int:
    if data is None:
        raise "validated_sum: data pointer is NULL — caller must supply a non-null array"
    if n <= 0:
        raise "validated_sum: n must be positive — received a zero or negative length"
    if n > 10_000_000:
        raise "validated_sum: n exceeds maximum allowed size — possible buffer overflow"
    total: int = 0
    i: int = 0
    while i < n:
        total = total + data[i]
        i += 1
    return total

# ---------------------------------------------------------------------------
# 7. Linked-list pointer-chase with prefetch
#    Nodes linked in a stride-permutation (stride=1,999,993 is coprime to 2M)
#    so every hop skips ~16 MB of address space → L3 miss on every node.
#    nathra inserts NR_PREFETCH(head->next->next, 0, 1) before the load,
#    overlapping the next fetch with processing of the current node.
# ---------------------------------------------------------------------------
LIST_N:    const = 1_500_007   # prime → any step gives full cycle
LIST_STEP: const = 750_013     # ~ N/2, prime → jumps of ~12 MB defeat hardware prefetcher
LIST_REPS: const = 20

class Node:
    value: int
    next: ptr[Node]

list_nodes: array[Node, 1500007]

@noinline
def walk_list(head: ptr[Node]) -> int:
    total: int = 0
    while head is not None:
        total = total + head.value
        head = head.next
    return total

# ---------------------------------------------------------------------------
# Micropy entry point (compiled only)
# ---------------------------------------------------------------------------
def main() -> int:
    out: ptr[float] = alloc(N * 8)
    x:   ptr[float] = alloc(N * 8)
    y:   ptr[float] = alloc(N * 8)
    data: ptr[int]  = alloc(ALLOC_N * 8)

    i: int = 0
    while i < N:
        x[i] = float(i) * 0.001
        y[i] = float(i) * 0.002
        i += 1
    i = 0
    while i < ALLOC_N:
        data[i] = i + 1
        i += 1

    printf("%-20s  %12s  %8s\n", "benchmark", "result", "ms")
    printf("%-20s  %12s  %8s\n", "--------------------", "------------", "--------")

    t0: int = time_ms()
    r: int = 0
    while r < REPS:
        saxpy(out, x, y, 2.5, N)
        r += 1
    t1: int = time_ms()
    printf("%-20s  %12.6f  %8d\n", "saxpy", out[N / 2], t1 - t0)

    result: float = 0.0
    t2: int = time_ms()
    r = 0
    while r < REPS:
        result = bench_strided(x, STRIDED_N)
        r += 1
    t3: int = time_ms()
    printf("%-20s  %12.6f  %8d\n", "strided_sum", result, t3 - t2)

    total: int = 0
    t4: int = time_ms()
    r = 0
    while r < ALLOC_REPS:
        data[0] = r            # vary input to prevent loop-invariant hoisting
        total = total + process_with_scratch(data, ALLOC_N)
        r += 1
    t5: int = time_ms()
    printf("%-20s  %12d  %8d\n", "small_alloc", total % 1_000_000, t5 - t4)

    i = 0
    while i < SOA_N:
        particles[i].x      = float(i) * 0.001
        particles[i].y      = float(i) * 0.002
        particles[i].z      = float(i) * 0.003
        particles[i].vx     = 0.0
        particles[i].vy     = 0.0
        particles[i].vz     = 0.0
        particles[i].mass   = 1.0
        particles[i].charge = 0.0
        i += 1

    soa_out: ptr[float] = alloc(SOA_N * 8)
    t6: int = time_ms()
    r = 0
    while r < SOA_REPS:
        extract_x(soa_out, SOA_N)
        r += 1
    t7: int = time_ms()
    printf("%-20s  %12.6f  %8d\n", "soa_sum", soa_out[SOA_N / 2], t7 - t6)
    free(soa_out)

    # ---------- restrict_short -----------------------------------------------
    rm_out: ptr[float] = alloc(RESTRICT_N * 8)
    rm_a:   ptr[float] = alloc(RESTRICT_N * 8)
    rm_b:   ptr[float] = alloc(RESTRICT_N * 8)
    rm_c:   ptr[float] = alloc(RESTRICT_N * 8)
    i = 0
    while i < RESTRICT_N:
        rm_a[i] = float(i) * 0.1
        rm_b[i] = float(i) * 0.2
        rm_c[i] = float(i) * 0.05
        i += 1
    t8: int = time_ms()
    r = 0
    while r < RESTRICT_REPS:
        fused_mad(rm_out, rm_a, rm_b, rm_c, RESTRICT_N)
        r += 1
    t9: int = time_ms()
    printf("%-20s  %12.6f  %8d\n", "restrict_short", rm_out[RESTRICT_N / 2], t9 - t8)
    free(rm_out)
    free(rm_a)
    free(rm_b)
    free(rm_c)

    # ---------- hot_cold ------------------------------------------------------
    hc_data: ptr[int] = alloc(HOT_N * 8)
    i = 0
    while i < HOT_N:
        hc_data[i] = i + 1
        i += 1
    hc_total: int = 0
    t10: int = time_ms()
    r = 0
    while r < HOT_REPS:
        hc_data[0] = r % 127 + 1   # vary input to prevent loop-invariant hoisting
        hc_total = hc_total + validated_sum(hc_data, HOT_N)
        r += 1
    t11: int = time_ms()
    printf("%-20s  %12d  %8d\n", "hot_cold", hc_total % 1_000_000, t11 - t10)
    free(hc_data)

    # ---------- linked_list ---------------------------------------------------
    ll_idx: int = 0
    i = 0
    while i < LIST_N - 1:
        ll_next: int = (ll_idx + LIST_STEP) % LIST_N
        list_nodes[ll_idx].value = ll_idx % 100
        list_nodes[ll_idx].next = addr_of(list_nodes[ll_next])
        ll_idx = ll_next
        i += 1
    list_nodes[ll_idx].value = ll_idx % 100
    list_nodes[ll_idx].next = None
    ll_result: int = 0
    t12: int = time_ms()
    r = 0
    while r < LIST_REPS:
        list_nodes[0].value = r    # vary input to prevent loop-invariant hoisting
        ll_result = walk_list(addr_of(list_nodes[0]))
        r += 1
    t13: int = time_ms()
    printf("%-20s  %12d  %8d\n", "linked_list", ll_result % 1_000_000, t13 - t12)

    free(out)
    free(x)
    free(y)
    free(data)
    return 0


# ---------------------------------------------------------------------------
# Python fallback — smaller counts so the run completes in ~5 seconds.
# The alloca substitution does not apply to Python (which uses its own
# object allocator), but the timing still shows how far Python lags.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _N        = 200_000
    _REPS     = 50
    _STRD_N   = 50_000     # _N / 4
    _ALLOC_N  = 64
    _ALLOC_R  = 20_000     # scale × 250 → effective 5M
    _SOA_N    = 100_000    # scale × 50 → effective 5M
    _SOA_REPS = 20          # scale × 4  → effective 20

    _x   = [float(i) * 0.001 for i in range(_N)]
    _y   = [float(i) * 0.002 for i in range(_N)]
    _out = [0.0] * _N
    _data = list(range(1, _ALLOC_N + 1))
    _px  = [float(i) * 0.001 for i in range(_SOA_N)]  # SoA x-field equivalent

    printf("%-20s  %12s  %8s\n", "benchmark", "result", "ms")
    printf("%-20s  %12s  %8s\n", "--------------------", "------------", "--------")

    _t0 = time_ms()
    for _ in range(_REPS):
        saxpy(_out, _x, _y, 2.5, _N)
    _t1 = time_ms()
    printf("%-20s  %12.6f  %8d\n", "saxpy", _out[_N // 2], _t1 - _t0)

    _result = 0.0
    _t2 = time_ms()
    for _ in range(_REPS):
        _result = strided_sum(_x, _STRD_N, 4)
    _t3 = time_ms()
    printf("%-20s  %12.6f  %8d\n", "strided_sum", _result, _t3 - _t2)

    _total = 0
    _t4 = time_ms()
    for _r in range(_ALLOC_R):
        _data[0] = _r
        _scratch = [0] * _ALLOC_N
        for i in range(_ALLOC_N):
            _scratch[i] = _data[i] * 2 + 1
        for i in range(_ALLOC_N):
            _total += _scratch[i]
    _t5 = time_ms()
    printf("%-20s  %12d  %8d\n", "small_alloc", _total % 1000000, _t5 - _t4)

    _soa_out = [0.0] * _SOA_N
    _t6 = time_ms()
    for _ in range(_SOA_REPS):
        for _i in range(_SOA_N):
            _soa_out[_i] = _px[_i]
    _t7 = time_ms()
    printf("%-20s  %12.6f  %8d\n", "soa_sum", _soa_out[_SOA_N // 2], _t7 - _t6)