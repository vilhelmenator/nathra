import os
import sys
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List

from compiler import Compiler, CompileError

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Build target definitions
# ---------------------------------------------------------------------------

@dataclass
class BuildTarget:
    name: str
    sources: List[str]
    kind: str          # "exe", "static", "shared"
    flags: List[str] = field(default_factory=list)
    libs: List[str] = field(default_factory=list)
    deps: List[str] = field(default_factory=list)  # other lib target names
    run: bool = False  # run after linking (useful for test binaries)


# ---------------------------------------------------------------------------
# Build runner
# ---------------------------------------------------------------------------

class BuildRunner:
    def __init__(self, build_dir: str, cc: str = "gcc", platform: str = "all"):
        self.build_dir = build_dir
        self.cc = cc
        self.platform = platform
        self.targets: List[BuildTarget] = []
        self.is_msvc = cc in ("cl", "cl.exe")

    # -- DSL surface ---------------------------------------------------------

    def exe(self, name: str, sources: List[str],
            flags: List[str] = None, libs: List[str] = None,
            deps: List[str] = None, run: bool = False):
        self.targets.append(BuildTarget(
            name=name, sources=sources, kind="exe",
            flags=flags or [], libs=libs or [], deps=deps or [],
            run=run,
        ))

    def lib(self, name: str, sources: List[str], kind: str = "static",
            flags: List[str] = None, libs: List[str] = None):
        if kind not in ("static", "shared"):
            print(f"Error: lib kind must be 'static' or 'shared', got '{kind}'", file=sys.stderr)
            sys.exit(1)
        self.targets.append(BuildTarget(
            name=name, sources=sources, kind=kind,
            flags=flags or [], libs=libs or [],
        ))

    # -- Execution -----------------------------------------------------------

    def run(self):
        run_results = []  # (name, passed) for targets with run=True
        for target in self.targets:
            print(f"\n==> {target.kind}: {target.name}")
            c_files, any_recompiled = self._compile_sources(target)
            if target.kind == "exe":
                out = self._link_exe(target, c_files, force=any_recompiled)
                if target.run and out:
                    passed = self._run_binary(out)
                    run_results.append((target.name, passed))
            elif target.kind == "static":
                self._link_static(target, c_files)
            elif target.kind == "shared":
                self._link_shared(target, c_files)  # type: ignore

        if run_results:
            print(f"\n{'='*50}")
            passed = sum(1 for _, ok in run_results if ok)
            failed = len(run_results) - passed
            for name, ok in run_results:
                status = "PASS" if ok else "FAIL"
                print(f"  [{status}] {name}")
            print(f"{'='*50}")
            print(f"  {passed}/{len(run_results)} passed")
            if failed:
                sys.exit(1)

    @staticmethod
    def _mtime(path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0

    @staticmethod
    def _read_stamp(c_path: str) -> float:
        """Read the mpy_stamp from the first line of a generated C file."""
        try:
            with open(c_path) as f:
                first = f.readline()
            if first.startswith("/* mpy_stamp:"):
                return float(first[13:].strip().rstrip(" */"))
        except Exception:
            pass
        return 0.0

    def _compile_sources(self, target: BuildTarget):
        """Compile all .mpy sources for a target. Returns (c_files, any_recompiled)."""
        c_files = []
        compiled_files: set = set()
        any_recompiled = False

        for src in target.sources:
            src_path = os.path.join(self.build_dir, src)
            if not os.path.exists(src_path):
                print(f"Error: source not found: {src_path}", file=sys.stderr)
                sys.exit(1)

            base = os.path.splitext(src_path)[0]
            c_path = base + ".c"

            # Skip if embedded stamp matches or exceeds source mtime
            if os.path.exists(c_path) and self._read_stamp(c_path) >= self._mtime(src_path):
                print(f"  [skip] {src} (up to date)")
                c_files.append(c_path)
                for mod_name in list(compiled_files):
                    dep_c = os.path.join(self.build_dir, f"{mod_name}.c")
                    if os.path.exists(dep_c) and dep_c not in c_files:
                        c_files.append(dep_c)
                continue

            module_name = "__main__" if target.kind == "exe" and src == target.sources[0] else \
                          os.path.splitext(os.path.basename(src))[0]

            compiler = Compiler(
                compiled_files=compiled_files,
                source_dir=self.build_dir,
                platform=self.platform,
            )
            try:
                c_src, h_src, mod_info = compiler.compile_file(src_path, module_name)
            except CompileError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                loc = f"{compiler._current_file}:{compiler._current_line}" if compiler._current_line else compiler._current_file
                print(f"Internal error at {loc}: {type(e).__name__}: {e}", file=sys.stderr)
                sys.exit(1)

            compiled_files = compiler.compiled_files
            any_recompiled = True

            with open(c_path, "w") as f:
                f.write(c_src)

            if module_name != "__main__":
                h_path = base + ".h"
                with open(h_path, "w") as f:
                    f.write(h_src)

            print(f"  Compiled {src} -> {os.path.basename(c_path)}")
            c_files.append(c_path)

            for mod_name in compiler.compiled_files:
                dep_c = os.path.join(self.build_dir, f"{mod_name}.c")
                if os.path.exists(dep_c) and dep_c not in c_files:
                    c_files.append(dep_c)

        return c_files, any_recompiled

    def _run_cmd(self, cmd: List[str], label: str):
        print(f"  {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"{label} failed:")
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr)
            sys.exit(1)

    def _lib_flags(self, target: BuildTarget) -> List[str]:
        flags = [f"-l{l}" for l in target.libs]
        for dep in target.deps:
            flags += [f"-L{self.build_dir}", f"-l{dep}"]
        return flags

    def _link_exe(self, target: BuildTarget, c_files: List[str], force: bool = False) -> str:
        out = os.path.join(self.build_dir, target.name)
        if sys.platform == "win32" and not out.endswith(".exe"):
            out += ".exe"
        # Skip linking if exe is newer than all inputs and not forced
        if not force and os.path.exists(out):
            exe_mtime = self._mtime(out)
            if all(self._mtime(c) <= exe_mtime for c in c_files):
                print(f"  [skip] {target.name} (up to date)")
                return out
        if self.is_msvc:
            cmd = [self.cc] + c_files + [f"/Fe{out}", "/nologo"] + target.flags
        else:
            cmd = [self.cc] + c_files + ["-o", out, "-lm"] + target.flags + self._lib_flags(target)
        self._run_cmd(cmd, f"Link {target.name}")
        print(f"  => {out}")
        return out

    def _run_binary(self, path: str) -> bool:
        """Run a binary, return True if it exits with code 0."""
        result = subprocess.run([os.path.abspath(path)], capture_output=False)
        return result.returncode == 0

    def _link_static(self, target: BuildTarget, c_files: List[str]):
        # Compile to .o first
        o_files = []
        for c_file in c_files:
            o_file = c_file.replace(".c", ".o")
            if self.is_msvc:
                cmd = [self.cc, "/c", c_file, f"/Fo{o_file}", "/nologo"] + target.flags
            else:
                cmd = [self.cc, "-c", c_file, "-o", o_file] + target.flags
            self._run_cmd(cmd, f"Compile {os.path.basename(c_file)}")
            o_files.append(o_file)

        out = os.path.join(self.build_dir, f"lib{target.name}.a")
        if self.is_msvc:
            out = os.path.join(self.build_dir, f"{target.name}.lib")
            cmd = ["lib", f"/OUT:{out}"] + o_files
        else:
            cmd = ["ar", "rcs", out] + o_files
        self._run_cmd(cmd, f"Archive {target.name}")
        print(f"  => {out}")

    def _link_shared(self, target: BuildTarget, c_files: List[str]):
        if sys.platform == "win32":
            out = os.path.join(self.build_dir, f"{target.name}.dll")
        elif sys.platform == "darwin":
            out = os.path.join(self.build_dir, f"lib{target.name}.dylib")
        else:
            out = os.path.join(self.build_dir, f"lib{target.name}.so")

        if self.is_msvc:
            cmd = [self.cc] + c_files + [f"/Fe{out}", "/LD", "/nologo"] + target.flags
        else:
            cmd = [self.cc, "-shared", "-fPIC"] + c_files + \
                  ["-o", out, "-lm"] + target.flags + self._lib_flags(target)
        self._run_cmd(cmd, f"Link shared {target.name}")
        print(f"  => {out}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_build_file(build_path: str, cc: str = "gcc", platform: str = "all"):
    """Execute a build.mpy file with the build DSL injected."""
    build_dir = os.path.dirname(os.path.abspath(build_path))

    rt_path = os.path.join(build_dir, "micropy_rt.h")
    src_rt = os.path.join(_HERE, "runtime", "micropy_rt.h")
    if not os.path.exists(rt_path) or os.path.getmtime(src_rt) > os.path.getmtime(rt_path):
        shutil.copy2(src_rt, rt_path)

    runner = BuildRunner(build_dir=build_dir, cc=cc, platform=platform)

    ns = {
        "exe": runner.exe,
        "lib": runner.lib,
    }

    with open(build_path) as f:
        source = f.read()

    exec(compile(source, build_path, "exec"), ns)
    runner.run()
