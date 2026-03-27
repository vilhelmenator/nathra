#!/usr/bin/env python3
"""Benchmark: Python compiler vs native compiler on the native compiler's own source.

Usage:
    python3 scripts/benchmark.py
"""

import ast
import ctypes
import glob
import io
import os
import sys
import time
from ctypes import c_int64, c_int32, POINTER, byref, c_uint8

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from compiler import Compiler
from compiler.ast_serial import serialize_ast

SRC_DIR = os.path.join(_ROOT, "native", "src")
DYLIB_EXT = "dylib" if sys.platform == "darwin" else ("dll" if sys.platform == "win32" else "so")
DYLIB_PATH = os.path.join(_ROOT, "build", f"compiler_native.{DYLIB_EXT}")


def main():
    if not os.path.exists(DYLIB_PATH):
        print(f"Error: {DYLIB_PATH} not found. Run 'make' first.")
        sys.exit(1)

    lib = ctypes.CDLL(DYLIB_PATH)
    func = lib.native_compile
    func.argtypes = [POINTER(c_uint8), c_int64, POINTER(POINTER(c_uint8)), POINTER(c_int64)]
    func.restype = c_int32

    files = sorted(glob.glob(os.path.join(SRC_DIR, "native_*.mpy")))
    if not files:
        print("No native_*.mpy files found.")
        sys.exit(1)

    print(f"{'File':<35} {'Python':>10} {'Native':>10} {'Speedup':>10}")
    print("-" * 70)

    total_py = 0.0
    total_native = 0.0
    total_lines = 0
    generated = []

    for f in files:
        name = os.path.basename(f)
        src = open(f).read()
        total_lines += src.count("\n") + 1

        # Python compiler (suppress DCE info messages)
        t0 = time.perf_counter()
        _old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        c = Compiler(source_dir=SRC_DIR, emit_line_directives=False)
        c.compile_file(f, name.replace(".mpy", ""))
        sys.stderr = _old_stderr
        t1 = time.perf_counter()
        py_ms = (t1 - t0) * 1000

        # Clean up any .c/.h files the Python compiler wrote into SRC_DIR
        for ext in (".c", ".h"):
            dep_files = glob.glob(os.path.join(SRC_DIR, f"*{ext}"))
            for df in dep_files:
                generated.append(df)

        # Native compiler
        src_pp = src.replace("\nstruct ", "\nclass ")
        if src_pp.startswith("struct "):
            src_pp = "class " + src_pp[7:]
        tree = ast.parse(src_pp)
        ast_buf = serialize_ast(tree)
        buf = (c_uint8 * len(ast_buf))(*ast_buf)
        out_buf = POINTER(c_uint8)()
        out_len = c_int64(0)

        t0 = time.perf_counter()
        rc = func(buf, c_int64(len(ast_buf)), byref(out_buf), byref(out_len))
        t1 = time.perf_counter()
        native_ms = (t1 - t0) * 1000

        speedup = py_ms / native_ms if native_ms > 0 else 0
        total_py += py_ms
        total_native += native_ms

        status = "" if rc == 0 else "  ERR"
        print(f"{name:<35} {py_ms:>8.1f}ms {native_ms:>8.2f}ms {speedup:>8.0f}x{status}")

    print("-" * 70)
    overall = total_py / total_native if total_native > 0 else 0
    print(f"{'TOTAL':<35} {total_py:>8.1f}ms {total_native:>8.2f}ms {overall:>8.0f}x")
    print(f"\n{total_lines} lines compiled in {total_native:.2f}ms (native)")

    # Clean up generated files
    cleaned = 0
    for path in set(generated):
        if os.path.exists(path):
            os.remove(path)
            cleaned += 1
    if cleaned:
        print(f"Cleaned {cleaned} temp file(s) from {SRC_DIR}")


if __name__ == "__main__":
    main()
