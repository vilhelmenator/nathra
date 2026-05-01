#!/usr/bin/env python3
"""Run the nathra benchmark against CPython and print a comparison table."""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCH = os.path.join(ROOT, "bench", "bench.nth")

def run(cmd, env=None):
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()

print("Building nathra binary...")
run([sys.executable, os.path.join(ROOT, "mpy.py"), BENCH,
     "--mode=release", "--flags=-O2"],
    env={**os.environ, "PYTHONPATH": ROOT})

print()
print("=== CPython ===")
py_out = run([sys.executable, BENCH], env={**os.environ, "PYTHONPATH": ROOT})
print(py_out)

print("=== Nathra (O2) ===")
mp_out = run([os.path.join(ROOT, "bench", "bench")])
print(mp_out)

# Parse and print speedup column
print()
py_lines  = [l for l in py_out.splitlines()  if l and not l.startswith("-")]
mp_lines  = [l for l in mp_out.splitlines()  if l and not l.startswith("-")]
header    = py_lines[0]

print(f"{'benchmark':<20}  {'python ms':>10}  {'nathra ms':>10}  {'speedup':>8}")
print(f"{'-'*20}  {'-'*10}  {'-'*10}  {'-'*8}")
for py_row, mp_row in zip(py_lines[1:], mp_lines[1:]):
    py_cols = py_row.split()
    mp_cols = mp_row.split()
    name     = py_cols[0]
    py_ms    = int(py_cols[-1])
    mp_ms    = int(mp_cols[-1])
    speedup  = f"{py_ms / max(mp_ms, 1):.0f}x" if mp_ms > 0 else "—"
    print(f"{name:<20}  {py_ms:>10}  {mp_ms:>10}  {speedup:>8}")