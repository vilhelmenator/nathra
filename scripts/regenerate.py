#!/usr/bin/env python3
"""Regenerate native/generated/ .c and .h files from native/src/ .mpy sources.

Uses the Python compiler to compile each .mpy file. The output is checked
into version control so that users can build the native dylib without needing
the Python compiler.

Usage:
    python3 scripts/regenerate.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from compiler import Compiler

SRC_DIR = os.path.join(_ROOT, "native", "src")
GEN_DIR = os.path.join(_ROOT, "native", "generated")

# rt_impl.c is a tiny shim that #define's MICROPY_RT_IMPL and #include's the
# runtime header so the implementation gets compiled into the dylib.
RT_IMPL = """\
#define MICROPY_RT_IMPL
#include "micropy_rt.h"

/* Public entry point -- short alias for ctypes callers */
int32_t native_compile_file_native_compile(const uint8_t*, int64_t, uint8_t**, int64_t*);
int32_t native_compile(const uint8_t* buf, int64_t len, uint8_t** out, int64_t* out_len) {
    return native_compile_file_native_compile(buf, len, out, out_len);
}
"""

# Compile order — dependencies before dependents.
MODULES = [
    "strmap",
    "ast_nodes",
    "native_compiler_state",
    "native_type_map",
    "native_infer",
    "native_analysis",
    "native_codegen_expr",
    "native_codegen_call",
    "native_codegen_stmt",
    "native_compile_file",
]


def main():
    os.makedirs(GEN_DIR, exist_ok=True)

    for mod in MODULES:
        mpy_path = os.path.join(SRC_DIR, f"{mod}.mpy")
        if not os.path.exists(mpy_path):
            print(f"  SKIP {mod}.mpy (not found)")
            continue

        c = Compiler(source_dir=SRC_DIR, emit_line_directives=False)
        c_src, header, _ = c.compile_file(mpy_path, mod)

        c_path = os.path.join(GEN_DIR, f"{mod}.c")
        h_path = os.path.join(GEN_DIR, f"{mod}.h")

        with open(c_path, "w") as f:
            f.write(c_src)
        if header:
            with open(h_path, "w") as f:
                f.write(header)

        print(f"  {mod}.c + .h")

    # Write rt_impl.c
    rt_path = os.path.join(GEN_DIR, "rt_impl.c")
    with open(rt_path, "w") as f:
        f.write(RT_IMPL)
    print(f"  rt_impl.c")

    print(f"\nRegenerated {len(MODULES)} modules into {GEN_DIR}")


if __name__ == "__main__":
    main()
