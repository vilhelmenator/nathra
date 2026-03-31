import os
import sys
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List

from compiler import Compiler, CompileError

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _detect_platform() -> str:
    """Detect the current platform as 'macos', 'linux', or 'windows'."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform == "win32":
        return "windows"
    return "linux"


def _resolve_platform(value, platform: str):
    """Resolve a platform-keyed dict or return value as-is.

    Accepts:
      - A plain list/str: returned unchanged
      - A dict with platform keys: resolves to the matching entry
        e.g. {"macos": [...], "linux": [...]} → [...]
    """
    if isinstance(value, dict):
        # Check for platform keys (not c_module names like "glut")
        if platform in value:
            return value[platform]
        if "all" in value:
            return value["all"]
        return []
    return value


def _resolve_c_modules(c_modules: dict, platform: str) -> dict:
    """Resolve platform-keyed c_modules entries.

    Input:  {"glut": {"macos": ["<GLUT/glut.h>"], "linux": ["<GL/glut.h>"]},
             "sdl": ["<SDL2/SDL.h>"]}
    Output: {"glut": ["<GLUT/glut.h>"], "sdl": ["<SDL2/SDL.h>"]}
    """
    resolved = {}
    for name, headers in c_modules.items():
        resolved[name] = _resolve_platform(headers, platform)
    return resolved


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
    c_modules: dict = field(default_factory=dict)  # module_name → [header_paths]


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
        self._topology_pins: list = []    # [(name, name, ...), ...]
        self._topology_keeps: set = set() # module names to keep_alive

    # -- DSL surface ---------------------------------------------------------

    def exe(self, name: str, sources: List[str],
            flags: List[str] = None, libs: List[str] = None,
            deps: List[str] = None, run: bool = False,
            c_modules: dict = None):
        self.targets.append(BuildTarget(
            name=name, sources=sources, kind="exe",
            flags=flags or [], libs=libs or [], deps=deps or [],
            run=run, c_modules=c_modules or {},
        ))

    def lib(self, name: str, sources: List[str], kind: str = "static",
            flags: List[str] = None, libs: List[str] = None,
            c_modules: dict = None):
        if kind not in ("static", "shared"):
            print(f"Error: lib kind must be 'static' or 'shared', got '{kind}'", file=sys.stderr)
            sys.exit(1)
        self.targets.append(BuildTarget(
            name=name, sources=sources, kind=kind,
            flags=flags or [], libs=libs or [],
            c_modules=c_modules or {},
        ))

    def pin_together(self, *names: str):
        """Force modules/functions into the same shared library cluster."""
        self._topology_pins.append(names)

    def keep_alive(self, name: str):
        """Mark a module as non-swappable (pinned into the host)."""
        self._topology_keeps.add(name)

    # -- Execution -----------------------------------------------------------

    def run(self):
        run_results = []  # (name, passed) for targets with run=True
        _plat = _detect_platform()
        for target in self.targets:
            # Resolve platform-keyed flags
            if isinstance(target.flags, dict):
                target.flags = _resolve_platform(target.flags, _plat)
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
        """Read the nth_stamp from the first line of a generated C file."""
        try:
            with open(c_path) as f:
                first = f.readline()
            if first.startswith("/* nth_stamp:"):
                return float(first[13:].strip().rstrip(" */"))
        except Exception:
            pass
        return 0.0

    def _compile_sources(self, target: BuildTarget):
        """Compile all .py sources for a target. Returns (c_files, any_recompiled)."""
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

            # Resolve platform-keyed c_modules
            _plat = _detect_platform()
            _resolved_mods = _resolve_c_modules(target.c_modules, _plat)

            compiler = Compiler(
                compiled_files=compiled_files,
                source_dir=self.build_dir,
                platform=self.platform,
                c_modules=_resolved_mods,
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

    # -- Topology-aware build ------------------------------------------------

    def build_with_topology(self, target: BuildTarget,
                             mode: str = "dev"):
        """Build a target using topology-driven .so partitioning.

        Args:
            target: Build target to compile
            mode: "dev" (hot-swap), "release" (static LTO), or "service"
        """
        from compiler.topology import TopologyAnalyzer, BuildMode

        build_mode = BuildMode(mode)

        print(f"\n==> topology build: {target.name}")

        # Step 1: Compile all sources, keep compiler instances
        compilers = {}  # module_name → compiler
        c_files_by_module = {}  # module_name → c_path
        _plat = _detect_platform()
        _resolved_mods = _resolve_c_modules(target.c_modules, _plat)
        compiled_files = set()

        for src in target.sources:
            src_path = os.path.join(self.build_dir, src)
            base = os.path.splitext(src_path)[0]
            c_path = base + ".c"
            module_name = (
                "__main__" if target.kind == "exe" and src == target.sources[0]
                else os.path.splitext(os.path.basename(src))[0]
            )

            compiler = Compiler(
                compiled_files=compiled_files,
                source_dir=self.build_dir,
                platform=self.platform,
                c_modules=_resolved_mods,
            )
            try:
                c_src, h_src, mod_info = compiler.compile_file(src_path, module_name)
            except Exception as e:
                print(f"Error compiling {src}: {e}", file=sys.stderr)
                sys.exit(1)

            compiled_files = compiler.compiled_files
            compilers[module_name] = compiler
            c_files_by_module[module_name] = c_path

            with open(c_path, "w") as f:
                f.write(c_src)
            if module_name != "__main__":
                h_path = base + ".h"
                with open(h_path, "w") as f:
                    f.write(h_src)

            # Collect dependency .c files
            for dep in compiler.compiled_files:
                dep_c = os.path.join(self.build_dir, f"{dep}.c")
                if os.path.exists(dep_c) and dep not in c_files_by_module:
                    c_files_by_module[dep] = dep_c

            print(f"  Compiled {src} -> {os.path.basename(c_path)}")

        # Step 2: Run topology analysis
        topo = TopologyAnalyzer()
        for mod_name, comp in compilers.items():
            topo.add_module(mod_name, comp)
            topo.add_call_edges(comp, mod_name)

        # Step 3: Apply overrides
        for names in self._topology_pins:
            topo.pin_together(*names)
        for name in self._topology_keeps:
            topo.keep_alive(name)

        report = topo.analyze()
        plan = topo.generate_build_plan(
            report,
            source_dir=self.build_dir,
            host_name=target.name,
            mode=build_mode,
        )

        # Print reports
        report.print(file=sys.stdout)
        plan.print(file=sys.stdout)

        # Step 4: Generate dispatch header if needed
        dispatch_h = plan.generate_dispatch_header()
        if dispatch_h:
            dispatch_path = os.path.join(self.build_dir, "nathra_dispatch.h")
            with open(dispatch_path, "w") as f:
                f.write(dispatch_h)
            print(f"  Generated {dispatch_path}")

            dispatch_c = plan.generate_dispatch_impl()
            dispatch_c_path = os.path.join(self.build_dir, "nathra_dispatch.c")
            with open(dispatch_c_path, "w") as f:
                f.write(dispatch_c)

        from compiler.topology import BuildMode, Reloadability

        # ── RELEASE MODE: single static binary with LTO ──
        if build_mode == BuildMode.RELEASE:
            all_c = [c_files_by_module[m] for m in c_files_by_module]
            out = os.path.join(self.build_dir, target.name)
            lto_flags = ["-flto", "-O2"]
            cmd = [self.cc] + all_c + ["-o", out, "-lm"] + \
                  lto_flags + target.flags
            self._run_cmd(cmd, f"Link release {target.name}")
            print(f"  => {out}  (static, LTO)")
            return

        # ── DEV / SERVICE MODE: .so per cluster with hot-swap ──

        # Step 5: Generate reload init
        reload_init = plan.generate_reload_init()
        if reload_init:
            init_path = os.path.join(self.build_dir, "nathra_reload_init.c")
            with open(init_path, "w") as f:
                f.write(reload_init)
            print(f"  Generated {init_path}")

        # Step 6: Generate state migration stubs (service mode)
        if build_mode == BuildMode.SERVICE:
            stubs = plan.generate_state_migration_stubs()
            if stubs:
                stubs_path = os.path.join(self.build_dir,
                                           "nathra_state_migration.c")
                with open(stubs_path, "w") as f:
                    f.write(stubs)
                print(f"  Generated {stubs_path}")

        # Step 7: Link each cluster as a .so
        ext = "dylib" if sys.platform == "darwin" else (
            "dll" if sys.platform == "win32" else "so")

        # Stricter flags for swappable modules
        _strict_flags = ["-DNR_SAFE", "-Wall", "-Werror",
                         "-Wno-unused-variable", "-Wno-unused-function"]

        for lib in plan.shared_libs:
            if lib.cluster_id == plan.pinned_cluster:
                continue  # pinned cluster goes into the host exe

            existing_c = [c_files_by_module[m]
                          for m in lib.modules
                          if m in c_files_by_module]
            if not existing_c:
                continue

            out = os.path.join(self.build_dir, f"lib{lib.name}.{ext}")
            swappable = lib.reloadability in (Reloadability.PURE,
                                               Reloadability.PROCESS_LOCAL)
            extra = _strict_flags if swappable else []

            # Service mode: embed ABI hash in abi-anchor .so's
            if build_mode == BuildMode.SERVICE and lib.abi_hash:
                extra += [f"-DNR_ABI_HASH=0x{lib.abi_hash:08x}"]

            cmd = [self.cc, "-shared", "-fPIC"] + existing_c + \
                  ["-o", out, "-lm"] + extra + target.flags
            self._run_cmd(cmd, f"Link shared {lib.name}")
            swap_str = "(swappable)" if swappable else "(pinned)"
            print(f"  => {out}  {swap_str}")

        # Step 8: Link host exe
        host_c = []
        if plan.pinned_cluster >= 0:
            pinned_lib = plan.shared_libs[plan.pinned_cluster]
            host_c = [c_files_by_module[m]
                      for m in pinned_lib.modules
                      if m in c_files_by_module]
        else:
            if "__main__" in c_files_by_module:
                host_c = [c_files_by_module["__main__"]]

        if dispatch_h:
            dispatch_c_path = os.path.join(self.build_dir, "nathra_dispatch.c")
            if os.path.exists(dispatch_c_path):
                host_c.append(dispatch_c_path)
        if reload_init:
            host_c.append(init_path)

        if host_c:
            out = os.path.join(self.build_dir, target.name)
            lib_flags = []
            for lib in plan.shared_libs:
                if lib.cluster_id != plan.pinned_cluster:
                    lib_flags += [f"-L{self.build_dir}", f"-l{lib.name}"]
            dl_flag = [] if sys.platform == "win32" else ["-ldl"]
            cmd = [self.cc] + host_c + ["-o", out, "-lm"] + \
                  dl_flag + target.flags + lib_flags
            self._run_cmd(cmd, f"Link host {target.name}")
            print(f"  => {out}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_build_file(build_path: str, cc: str = "gcc", platform: str = "all"):
    """Execute a build.py file with the build DSL injected."""
    build_dir = os.path.dirname(os.path.abspath(build_path))

    rt_path = os.path.join(build_dir, "nathra_rt.h")
    src_rt = os.path.join(_HERE, "runtime", "nathra_rt.h")
    if not os.path.exists(rt_path) or os.path.getmtime(src_rt) > os.path.getmtime(rt_path):
        shutil.copy2(src_rt, rt_path)

    runner = BuildRunner(build_dir=build_dir, cc=cc, platform=platform)

    ns = {
        "exe": runner.exe,
        "lib": runner.lib,
        "pin_together": runner.pin_together,
        "keep_alive": runner.keep_alive,
    }

    with open(build_path) as f:
        source = f.read()

    exec(compile(source, build_path, "exec"), ns)
    runner.run()
