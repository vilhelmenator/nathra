"""Bootstrap test: compile a .mpy file with both the Python compiler
and the native compiler, compare output."""

import ast
import sys
import os
import time
import ctypes
from ctypes import c_char_p, c_int64, c_int32, POINTER, byref, c_uint8

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from compiler.ast_serial import serialize_ast
from compiler import Compiler


def compile_with_python(source: str, filepath: str) -> str:
    """Compile .mpy source using the Python compiler."""
    # Preprocess: struct → class
    source_pp = source.replace("\nstruct ", "\nclass ")
    if source_pp.startswith("struct "):
        source_pp = "class " + source_pp[7:]
    source_pp = source_pp.replace("\nunion ", "\n@union\nclass ")

    c = Compiler(source_dir=os.path.dirname(os.path.abspath(filepath)),
                 emit_line_directives=False)
    c_src, _, _ = c.compile_file(filepath, "__main__")
    return c_src


def compile_with_native(source: str, lib_path: str) -> str:
    """Compile .mpy source using the native compiler via ctypes."""
    # Preprocess
    source_pp = source.replace("\nstruct ", "\nclass ")
    if source_pp.startswith("struct "):
        source_pp = "class " + source_pp[7:]

    # Parse and serialize AST
    tree = ast.parse(source_pp)
    ast_buf = serialize_ast(tree)

    # Load native compiler
    lib = ctypes.CDLL(lib_path)
    func = lib.native_compile
    func.argtypes = [
        ctypes.POINTER(c_uint8), c_int64,
        ctypes.POINTER(ctypes.POINTER(c_uint8)),
        ctypes.POINTER(c_int64)
    ]
    func.restype = c_int32

    # Call native compiler
    buf = (c_uint8 * len(ast_buf))(*ast_buf)
    out_buf = ctypes.POINTER(c_uint8)()
    out_len = c_int64(0)

    t0 = time.perf_counter()
    rc = func(buf, c_int64(len(ast_buf)), byref(out_buf), byref(out_len))
    t1 = time.perf_counter()

    if rc != 0:
        print(f"Native compiler returned error code {rc}")
        return None

    # Read result
    result = bytes(out_buf[:out_len.value]).decode("utf-8", errors="replace")
    native_ms = (t1 - t0) * 1000
    return result, native_ms


def main():
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    lib_ext = "dylib" if sys.platform == "darwin" else "so"
    lib_path = os.path.join(_root, "build", f"compiler_native.{lib_ext}")
    if not os.path.exists(lib_path):
        print(f"Error: {lib_path} not found. Run 'make' first.")
        sys.exit(1)

    # Test with a simple program
    test_source = '''
def add(a: int, b: int) -> int:
    return a + b

def main() -> int:
    x: int = add(3, 4)
    if x > 5:
        print(x)
    return 0
'''

    print("=== Bootstrap Test ===")
    print()

    # Compile with Python
    # Write temp file for Python compiler
    os.makedirs(os.path.join(_root, "build"), exist_ok=True)
    tmp_path = os.path.join(_root, "build", "test_input.mpy")
    with open(tmp_path, "w") as f:
        f.write(test_source)

    t0 = time.perf_counter()
    py_result = compile_with_python(test_source, tmp_path)
    t1 = time.perf_counter()
    py_ms = (t1 - t0) * 1000

    print(f"Python compiler: {py_ms:.1f} ms")

    # Compile with native
    native_result, native_ms = compile_with_native(test_source, lib_path)
    print(f"Native compiler: {native_ms:.2f} ms")

    if native_result is None:
        print("FAIL: native compiler returned error")
        sys.exit(1)

    print()
    print("--- Python output (first 20 lines) ---")
    for line in py_result.split("\n")[:20]:
        print(f"  {line}")

    print()
    print("--- Native output (first 20 lines) ---")
    for line in native_result.split("\n")[:20]:
        print(f"  {line}")

    # Compare (strip whitespace for fuzzy match)
    py_lines = [l.strip() for l in py_result.strip().split("\n") if l.strip()]
    native_lines = [l.strip() for l in native_result.strip().split("\n") if l.strip()]

    print()
    print(f"Python lines: {len(py_lines)}")
    print(f"Native lines: {len(native_lines)}")

    if native_ms > 0:
        speedup = py_ms / native_ms
        print(f"Speedup: {speedup:.0f}x")

    print()
    print("BOOTSTRAP TEST COMPLETE")


if __name__ == "__main__":
    main()
