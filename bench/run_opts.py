#!/usr/bin/env python3
"""
run_opts.py — compare Python, naive C, and micropy-optimized C.

Shows the effect of micropy's automatic optimizations (restrict inference,
constant specialization, alloca substitution for local scratch buffers)
against both a Python baseline and idiomatic C without those annotations.

Usage:
    cd <repo-root>
    python3 bench/run_opts.py
"""

import subprocess
import sys
import os

ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH_MPY = os.path.join(ROOT, "bench", "bench_opts.mpy")
NAIVE_SRC = os.path.join(ROOT, "bench", "bench_opts_naive.c")
MPY_BIN   = os.path.join(ROOT, "bench", "bench_opts")
NAIVE_BIN = os.path.join(ROOT, "bench", "bench_opts_naive")
FLAGS     = ["-O2", "-march=native"]
CC        = os.environ.get("CC", "cc")

NOTES = {
    "saxpy":       "restrict → no aliasing-check prelude",
    "strided_sum": "constant specialisation (stride=4 folded in)",
    "small_alloc": "alloca substitution (no malloc/free per call)",
    "soa_sum":     "@soa → 8B/elem read vs 64B/elem AoS (8-field struct, extract one field)",
}

# Python runs with smaller problem sizes; scale ms up to the C-scale workload
# so all three numbers are directly comparable.
PY_SCALE = {
    "saxpy":       (4_000_000 / 200_000) * (100 / 50),   # N ratio × reps ratio
    "strided_sum": (1_000_000 /  50_000) * (100 / 50),
    "small_alloc": (5_000_000 /  20_000),                 # reps ratio only
    "soa_sum":     (5_000_000 / 100_000) * (20 / 5),      # N ratio × reps ratio
}


def run(cmd, env=None):
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print("FAILED:", " ".join(str(c) for c in cmd), file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def parse_rows(output):
    """Return {name: ms} from benchmark output lines."""
    rows = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and not parts[0].startswith("-") and parts[0] != "benchmark":
            try:
                rows[parts[0]] = int(parts[-1])
            except ValueError:
                pass
    return rows


# ── Build ────────────────────────────────────────────────────────────────────
print("Building micropy version ...")
run(
    [sys.executable, os.path.join(ROOT, "mpy.py"), BENCH_MPY,
     f"--flags={' '.join(FLAGS)}"],
    env={**os.environ, "PYTHONPATH": ROOT},
)

print("Building naive C version ...")
run([CC, *FLAGS, "-o", NAIVE_BIN, NAIVE_SRC])

# ── Run ──────────────────────────────────────────────────────────────────────
print()
print("=== Python ===")
py_out = run([sys.executable, BENCH_MPY], env={**os.environ, "PYTHONPATH": ROOT})
print(py_out)

print()
print("=== Naive C  (no restrict / no specialisation / malloc per call) ===")
naive_out = run([NAIVE_BIN])
print(naive_out)

print()
print("=== Micropy  (auto-optimised) ===")
mpy_out = run([MPY_BIN])
print(mpy_out)

# ── Compare ──────────────────────────────────────────────────────────────────
py_rows    = parse_rows(py_out)
naive_rows = parse_rows(naive_out)
mpy_rows   = parse_rows(mpy_out)

names = list(mpy_rows.keys())

print()
print(f"{'benchmark':<20}  {'python ms':>10}  {'naive C ms':>10}  {'micropy ms':>10}  {'speedup':>8}  optimization")
print(f"{'-'*20}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*8}  {'-'*40}")

for name in names:
    py_ms    = py_rows.get(name, 0)
    naive_ms = naive_rows.get(name, 0)
    mpy_ms   = mpy_rows.get(name, 1)

    py_scaled = int(py_ms * PY_SCALE.get(name, 1.0))
    speedup   = f"{naive_ms / mpy_ms:.1f}x" if mpy_ms > 0 else "—"
    note      = NOTES.get(name, "")

    print(f"{name:<20}  {py_scaled:>10}  {naive_ms:>10}  {mpy_ms:>10}  {speedup:>8}  {note}")

print()
print("Notes:")
print("  python ms  — scaled from smaller problem size to match C workload")
print("  speedup    — naive C ms / micropy ms  (higher = better)")
print("  flags      — both C variants compiled with -O2 -march=native")