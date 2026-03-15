# !/usr/bin/env python3

"""
MicroPy Compiler — compiles .mpy files to C.

Usage:
    python mpy.py program.mpy                  # compile + link executable
    python mpy.py program.mpy --run            # compile, link, and run
    python mpy.py program.mpy -o output        # specify output name
    python mpy.py program.mpy --emit-c         # emit C only, don't link
    python mpy.py program.mpy --shared         # compile to shared library (.so/.dylib/.dll)
    python mpy.py program.mpy --platform linux # target platform
    python mpy.py program.mpy --watch          # rebuild on source change
    python mpy.py program.mpy --flags="-O2 -march=native"  # extra compiler/linker flags
    python mpy.py program.mpy --flags="-lssl -lz"          # link extra libraries
    python mpy.py build.mpy                    # run project build script
"""

import sys
import os
import subprocess
import shlex
import argparse
import time

import shutil
from compiler import Compiler, CompileError
from build import run_build_file

_HERE = os.path.dirname(os.path.abspath(__file__))


def build_once(args, source_dir) -> bool:
    """Compile and link. Returns True on success, False on failure."""
    rt_path = os.path.join(source_dir, "micropy_rt.h")
    src_rt = os.path.join(_HERE, "micropy_rt.h")
    if not os.path.exists(rt_path) or os.path.getmtime(src_rt) > os.path.getmtime(rt_path):
        shutil.copy2(src_rt, rt_path)

    compiler = Compiler(source_dir=source_dir, platform=args.platform)
    try:
        c_src, h_src, mod_info = compiler.compile_file(args.source, "__main__")
    except CompileError as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        loc = f"{compiler._current_file}:{compiler._current_line}" if compiler._current_line else compiler._current_file
        print(f"Internal error at {loc}: {type(e).__name__}: {e}", file=sys.stderr)
        return False

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
    if getattr(args, 'shared', False):
        if is_msvc:
            cmd = [args.cc] + c_files + [f"/Fe{out_name}", "/nologo", "/LD"] + extra_flags
        else:
            cmd = [args.cc, "-shared", "-fPIC"] + c_files + ["-o", out_name, "-lm"] + extra_flags
    elif is_msvc:
        cmd = [args.cc] + c_files + [f"/Fe{out_name}", "/nologo"] + extra_flags
    else:
        cmd = [args.cc] + c_files + ["-o", out_name, "-lm"] + extra_flags
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
    parser.add_argument("source", help="Source .mpy file or build.mpy")
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
    args = parser.parse_args()

    # Route build.mpy to the build system
    if os.path.basename(args.source) == "build.mpy":
        run_build_file(args.source, cc=args.cc, platform=args.platform)
        return

    source_dir = os.path.dirname(os.path.abspath(args.source))

    if not args.watch:
        ok = build_once(args, source_dir)
        sys.exit(0 if ok else 1)

    # --watch mode: rebuild whenever .mpy source changes
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