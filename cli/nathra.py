# !/usr/bin/env python3

"""
Nathra Compiler — compiles .py files to C.

Usage:
    python nathra.py program.py                  # compile + link executable
    python nathra.py program.py --run            # compile, link, and run
    python nathra.py program.py -o output        # specify output name
    python nathra.py program.py --emit-c         # emit C only, don't link
    python nathra.py program.py --shared         # compile to shared library (.so/.dylib/.dll)
    python nathra.py program.py --platform linux # target platform
    python nathra.py program.py --watch          # rebuild on source change
    python nathra.py program.py --flags="-O2 -march=native"  # extra compiler/linker flags
    python nathra.py program.py --flags="-lssl -lz"          # link extra libraries
    python nathra.py build.py                    # run project build script
"""

import sys
import os
import subprocess
import shlex
import argparse
import time

import shutil
import ctypes
from ctypes import c_int64, c_int32, POINTER, byref, c_uint8

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _HERE)

from compiler import Compiler, CompileError
from lib.build import run_build_file


def _find_native_dylib():
    """Find the native compiler dylib, return path or None."""
    ext = "dylib" if sys.platform == "darwin" else ("dll" if sys.platform == "win32" else "so")
    path = os.path.join(_HERE, "build", f"compiler_native.{ext}")
    if os.path.exists(path):
        return path
    return None


def _compile_native(source: str, dylib_path: str):
    """Compile source using the native compiler. Returns C source string or None on failure."""
    try:
        import ast
        from compiler.ast_serial import serialize_ast

        source_pp = source.replace("\nstruct ", "\nclass ")
        if source_pp.startswith("struct "):
            source_pp = "class " + source_pp[7:]
        source_pp = source_pp.replace("\nunion ", "\n@union\nclass ")

        tree = ast.parse(source_pp)
        ast_buf = serialize_ast(tree)

        lib = ctypes.CDLL(dylib_path)
        func = lib.native_compile
        func.argtypes = [POINTER(c_uint8), c_int64, POINTER(POINTER(c_uint8)), POINTER(c_int64)]
        func.restype = c_int32

        buf = (c_uint8 * len(ast_buf))(*ast_buf)
        out_buf = POINTER(c_uint8)()
        out_len = c_int64(0)

        rc = func(buf, c_int64(len(ast_buf)), byref(out_buf), byref(out_len))
        if rc != 0:
            return None
        return bytes(out_buf[:out_len.value]).decode("utf-8", errors="replace")
    except Exception:
        return None


def _preprocess_source(source: str) -> str:
    """Apply struct/union preprocessing."""
    source = source.replace("\nstruct ", "\nclass ")
    if source.startswith("struct "):
        source = "class " + source[7:]
    source = source.replace("\nunion ", "\n@union\nclass ")
    return source


def _scan_imports(tree, source_dir: str, stdlib_skip: set) -> list:
    """Scan AST for from-imports, return [(mod_name, {used_names})] in order."""
    import ast as _ast
    deps = []
    seen = set()
    for node in _ast.iter_child_nodes(tree):
        if isinstance(node, _ast.ImportFrom):
            mod = node.module
            if mod in stdlib_skip or mod in seen:
                continue
            mpy_path = os.path.join(source_dir, f"{mod}.py")
            if not os.path.exists(mpy_path):
                continue
            used = {alias.name for alias in node.names}
            deps.append((mod, used, mpy_path))
            seen.add(mod)
    return deps


def _compile_native_multi(source: str, source_dir: str, dylib_path: str):
    """Compile source + dependencies using the native compiler's state API.

    Returns dict of {module_name: (c_src, h_src)} or None on failure.
    """
    import ast as _ast
    from compiler.ast_serial import serialize_ast

    _STDLIB_SKIP = {"math", "enum", "nathra", "os", "sys"}

    try:
        lib = ctypes.CDLL(dylib_path)

        # Set up state API functions
        state_new = lib.native_state_new
        state_new.argtypes = []
        state_new.restype = ctypes.c_void_p

        compile_dep = lib.native_compile_dep
        compile_dep.argtypes = [
            ctypes.c_void_p,
            POINTER(c_uint8), c_int64,
            POINTER(c_uint8), c_int64,
            POINTER(POINTER(c_uint8)), POINTER(c_int64),
            POINTER(POINTER(c_uint8)), POINTER(c_int64),
        ]
        compile_dep.restype = c_int32

        compile_main = lib.native_compile_main
        compile_main.argtypes = [
            ctypes.c_void_p,
            POINTER(c_uint8), c_int64,
            POINTER(POINTER(c_uint8)), POINTER(c_int64),
        ]
        compile_main.restype = c_int32

        # Parse main module
        source_pp = _preprocess_source(source)
        main_tree = _ast.parse(source_pp)
        main_ast = serialize_ast(main_tree)

        # Scan imports
        deps = _scan_imports(main_tree, source_dir, _STDLIB_SKIP)

        # Create state
        state = state_new()
        results = {}

        # Compile each dependency
        for mod_name, used_names, mpy_path in deps:
            dep_source = open(mpy_path).read()
            dep_pp = _preprocess_source(dep_source)
            dep_tree = _ast.parse(dep_pp)
            dep_ast = serialize_ast(dep_tree)

            dep_buf = (c_uint8 * len(dep_ast))(*dep_ast)

            # Pack used names as null-separated bytes
            names_bytes = b"\0".join(n.encode() for n in used_names) + b"\0"
            names_buf = (c_uint8 * len(names_bytes))(*names_bytes)

            out_c = POINTER(c_uint8)()
            out_c_len = c_int64(0)
            out_h = POINTER(c_uint8)()
            out_h_len = c_int64(0)

            rc = compile_dep(state,
                             dep_buf, c_int64(len(dep_ast)),
                             names_buf, c_int64(len(names_bytes)),
                             byref(out_c), byref(out_c_len),
                             byref(out_h), byref(out_h_len))
            if rc != 0:
                return None

            c_src = bytes(out_c[:out_c_len.value]).decode("utf-8", errors="replace")
            h_src = bytes(out_h[:out_h_len.value]).decode("utf-8", errors="replace")
            results[mod_name] = (c_src, h_src)

        # Compile main module
        main_buf = (c_uint8 * len(main_ast))(*main_ast)
        out_buf = POINTER(c_uint8)()
        out_len = c_int64(0)

        rc = compile_main(state, main_buf, c_int64(len(main_ast)),
                          byref(out_buf), byref(out_len))
        if rc != 0:
            return None

        main_c = bytes(out_buf[:out_len.value]).decode("utf-8", errors="replace")
        results["__main__"] = (main_c, "")
        return results

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def build_once(args, source_dir) -> bool:
    """Compile and link. Returns True on success, False on failure."""
    for _hdr in ("nathra_rt.h", "nathra_types.h"):
        _dst = os.path.join(source_dir, _hdr)
        _src = os.path.join(_HERE, "runtime", _hdr)
        if not os.path.exists(_dst) or os.path.getmtime(_src) >= os.path.getmtime(_dst):
            shutil.copy2(_src, _dst)

    # Parse --c-module flags: "name=<header1>,<header2>"
    c_modules = {}
    for spec in getattr(args, 'c_module', []):
        if "=" not in spec:
            print(f"Error: --c-module must be NAME=HEADERS, got: {spec}", file=sys.stderr)
            return False
        name, hdrs = spec.split("=", 1)
        c_modules[name.strip()] = [h.strip() for h in hdrs.split(",")]

    compiler = Compiler(
        source_dir=source_dir,
        platform=args.platform,
        emit_line_directives=not getattr(args, 'no_line_directives', False),
        debug_mode=getattr(args, 'debug', False),
        safe_mode=getattr(args, 'safe', False),
        reorder_funcs=getattr(args, 'reorder_funcs', False),
        call_graph_report=getattr(args, 'call_graph', False),
        c_modules=c_modules,
    )
    try:
        c_src, h_src, mod_info = compiler.compile_file(args.source, "__main__")
    except CompileError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        loc = f"{compiler._current_file}:{compiler._current_line}" if compiler._current_line else compiler._current_file
        print(f"Internal error at {loc}: {type(e).__name__}: {e}", file=sys.stderr)
        return False

    # --dump-topology: run topology analysis and exit
    if getattr(args, 'dump_topology', False):
        from compiler.topology import TopologyAnalyzer
        topo = TopologyAnalyzer()
        topo.add_module("__main__", compiler)
        topo.add_call_edges(compiler, "__main__")
        # Add dependency modules
        for dep_name in compiler.compiled_files:
            if dep_name != "__main__" and dep_name in compiler.modules:
                topo.add_module(dep_name, compiler)
        report = topo.analyze()
        report.print(file=sys.stdout)
        return True

    base = os.path.splitext(args.source)[0]
    c_path = base + ".c"
    with open(c_path, "w") as f:
        f.write(c_src)
    print(f"Wrote {c_path}")

    if args.emit_c:
        return True

    c_files = [c_path]
    for mod_name in compiler.compiled_files:
        dep_c = os.path.join(source_dir, f"{mod_name}.c")
        if os.path.exists(dep_c):
            c_files.append(dep_c)

    out_name = args.output or base
    if getattr(args, 'shared', False):
        if sys.platform == "darwin":
            if not out_name.endswith(".dylib"):
                out_name += ".dylib"
        elif sys.platform == "win32":
            if not out_name.endswith(".dll"):
                out_name += ".dll"
        else:
            if not out_name.endswith(".so"):
                out_name += ".so"
    elif sys.platform == "win32" and not out_name.endswith(".exe"):
        out_name += ".exe"

    is_msvc = args.cc in ("cl", "cl.exe")
    extra_flags = shlex.split(getattr(args, 'flags', '') or '')
    if getattr(args, 'debug', False):
        extra_flags = ["-DNATHRA_DEBUG"] + extra_flags
    link_math = [] if sys.platform == "win32" else ["-lm"]
    if getattr(args, 'shared', False):
        if is_msvc:
            cmd = [args.cc] + c_files + [f"/Fe{out_name}", "/nologo", "/Z7", "/LD"] + extra_flags
        else:
            cmd = [args.cc, "-g", "-shared", "-fPIC"] + c_files + ["-o", out_name] + link_math + extra_flags
    elif is_msvc:
        cmd = [args.cc] + c_files + [f"/Fe{out_name}", "/nologo", "/Z7"] + extra_flags
    else:
        cmd = [args.cc, "-g"] + c_files + ["-o", out_name] + link_math + extra_flags
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Compilation failed:")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return False

    print(f"Built {out_name}")

    if args.run:
        print(f"\n--- Running {out_name} ---")
        subprocess.run([os.path.abspath(out_name)])

    return True


def _get_mtime(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="MicroPy compiler")
    parser.add_argument("source", help="Source .py file or build.py")
    parser.add_argument("-o", "--output", help="Output binary name")
    parser.add_argument("--run", action="store_true", help="Compile and run")
    parser.add_argument("--emit-c", action="store_true", help="Only emit C")
    parser.add_argument("--shared", action="store_true",
                        help="Compile to shared library (.so/.dylib/.dll) for hot-reloading")
    parser.add_argument("--cc", default="gcc", help="C compiler (default: gcc)")
    parser.add_argument("--platform", default="all",
                        choices=["all", "windows", "linux", "macos"],
                        help="Target platform for @platform decorators")
    parser.add_argument("--watch", action="store_true",
                        help="Watch source file and rebuild on change")
    parser.add_argument("--flags", default="",
                        metavar="FLAGS",
                        help='Extra flags passed to the C compiler/linker, quoted: --flags="-O2 -lssl"')
    parser.add_argument("--no-line-directives", action="store_true",
                        help="Omit #line directives from emitted C (cleaner output for diffing)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable allocation tracking: wraps alloc/free with counters, "
                             "asserts zero live allocations at exit")
    parser.add_argument("--safe", action="store_true",
                        help="Enable runtime safety checks: division by zero, bounds, overflow")
    parser.add_argument("--reorder-funcs", action="store_true",
                        help="Reorder functions by call-graph weight for I-cache locality")
    parser.add_argument("--call-graph", action="store_true",
                        help="Print weighted call graph report (no reordering)")
    parser.add_argument("--c-module", action="append", default=[],
                        metavar="NAME=HEADER",
                        help='Map import name to C header(s): --c-module "glut=<GLUT/glut.h>,<OpenGL/gl.h>"')
    parser.add_argument("--dump-topology", action="store_true",
                        help="Analyze and print build topology report")
    args = parser.parse_args()

    # Route build.py to the build system
    if os.path.basename(args.source) == "build.py":
        run_build_file(args.source, cc=args.cc, platform=args.platform)
        return

    source_dir = os.path.dirname(os.path.abspath(args.source))

    if not args.watch:
        ok = build_once(args, source_dir)
        sys.exit(0 if ok else 1)

    # --watch mode: rebuild whenever .py source changes
    print(f"Watching {args.source} (Ctrl-C to stop) ...")
    last_mtime = 0.0
    while True:
        mtime = _get_mtime(args.source)
        if mtime != last_mtime:
            last_mtime = mtime
            print(f"\n[{time.strftime('%H:%M:%S')}] Change detected — rebuilding ...")
            build_once(args, source_dir)
        time.sleep(0.5)


if __name__ == "__main__":
    main()