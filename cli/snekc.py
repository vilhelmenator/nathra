#!/usr/bin/env python3
"""
snekc — interactive nathra shell.

Compiles Python-syntax input through nathra → C → native shared library,
keeping state alive between evaluations via global variable transfer.

Usage:
    python snekc.py
"""

import ast
import ctypes
import os
import readline
import shutil
import subprocess
import sys
import tempfile

from compiler import Compiler, CompileError
from compiler.type_map import map_type

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# C type → ctypes mapping for state transfer
_CTYPE_MAP = {
    "int64_t": ctypes.c_int64,
    "double": ctypes.c_double,
    "int": ctypes.c_int,
    "int8_t": ctypes.c_int8,
    "int16_t": ctypes.c_int16,
    "int32_t": ctypes.c_int32,
    "uint8_t": ctypes.c_uint8,
    "uint16_t": ctypes.c_uint16,
    "uint32_t": ctypes.c_uint32,
    "uint64_t": ctypes.c_uint64,
    "float": ctypes.c_float,
}

if sys.platform == "darwin":
    _LIB_EXT = ".dylib"
    _SHARED_FLAGS = ["-shared", "-fPIC"]
elif sys.platform == "win32":
    _LIB_EXT = ".dll"
    _SHARED_FLAGS = ["-shared"]
else:
    _LIB_EXT = ".so"
    _SHARED_FLAGS = ["-shared", "-fPIC"]


class ReplState:
    def __init__(self):
        self.structs = []           # [(name, source)]
        self.functions = []         # [(name, source)]
        self.globals = {}           # name → (c_type, mpy_type_str)
        self.global_values = {}     # name → raw bytes
        self.eval_counter = 0
        self.eval_bodies = []       # [source_str, ...]
        self.struct_defs = {}       # name → [(field_name, c_type)]
        self.lib = None
        self.lib_counter = 0
        self.tmpdir = tempfile.mkdtemp(prefix="snekc_")

        # Copy runtime headers to tmpdir
        for hdr in ("nathra_rt.h", "nathra_types.h"):
            src = os.path.join(_HERE, "runtime", hdr)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(self.tmpdir, hdr))

        # Precompile header — avoids re-parsing nathra_rt.h on every eval
        self.pch_path = os.path.join(self.tmpdir, "nathra_rt.h.pch")
        pch_cmd = [
            "gcc", "-x", "c-header",
            os.path.join(self.tmpdir, "nathra_rt.h"),
            "-o", self.pch_path,
        ]
        subprocess.run(pch_cmd, capture_output=True)

    # ------------------------------------------------------------------
    # Input classification
    # ------------------------------------------------------------------

    def _preprocess(self, source):
        """Convert struct/union keywords to class (matching compiler)."""
        lines = source.split("\n")
        out = []
        for line in lines:
            if line.startswith("struct "):
                line = "class " + line[7:]
            elif line.startswith("union "):
                line = "@union\nclass " + line[6:]
            out.append(line)
        return "\n".join(out)

    def classify(self, source):
        """Return (kind, ast_node) for user input.

        kind is one of: 'struct', 'function', 'global', 'statement', 'error', 'empty'.
        """
        pp = self._preprocess(source)
        try:
            tree = ast.parse(pp)
        except SyntaxError as e:
            return "error", str(e)

        if not tree.body:
            return "empty", None

        node = tree.body[0]

        if isinstance(node, ast.ClassDef):
            return "struct", node
        if isinstance(node, ast.FunctionDef):
            return "function", node
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            return "global", node
        return "statement", node

    # ------------------------------------------------------------------
    # Accumulate input
    # ------------------------------------------------------------------

    def add_input(self, source):
        """Process user input and return True if compilation should run."""
        kind, node = self.classify(source)

        if kind == "error":
            print(f"SyntaxError: {node}")
            return False
        if kind == "empty":
            return False

        if kind == "struct":
            # Replace existing struct with same name
            self.structs = [(n, s) for n, s in self.structs if n != node.name]
            self.structs.append((node.name, source))
            # Track fields for ctypes struct building
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    ctype = map_type(item.annotation)
                    fields.append((item.target.id, ctype))
            self.struct_defs[node.name] = fields
            return True

        if kind == "function":
            self.functions = [(n, s) for n, s in self.functions if n != node.name]
            self.functions.append((node.name, source))
            return True

        if kind == "global":
            name = node.target.id
            mpy_type = ast.unparse(node.annotation)
            ctype = map_type(node.annotation)
            self.globals[name] = (ctype, mpy_type)
            # The assignment part becomes a statement in eval_N
            if node.value is not None:
                self.eval_counter += 1
                # Convert `x: int = 42` → `x = 42` for the eval body
                self.eval_bodies.append(f"{name} = {ast.unparse(node.value)}")
            return True

        # statement
        self.eval_counter += 1
        self.eval_bodies.append(source)
        return True

    # ------------------------------------------------------------------
    # Source generation
    # ------------------------------------------------------------------

    def generate_mpy(self):
        """Build the complete .py source from accumulated state."""
        parts = []

        # Struct definitions
        for _, src in self.structs:
            parts.append(src)
            parts.append("")

        # Mutable globals (no initializer — C zero-inits file-scope vars)
        for name, (ctype, mpy_type) in self.globals.items():
            parts.append(f"{name}: {mpy_type}")
        if self.globals:
            parts.append("")

        # Function definitions
        for _, src in self.functions:
            parts.append(src)
            parts.append("")

        # Eval functions
        for i, body in enumerate(self.eval_bodies, 1):
            parts.append(f"def eval_{i}() -> void:")
            for line in body.split("\n"):
                parts.append(f"    {line}")
            parts.append("")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Compile & run
    # ------------------------------------------------------------------

    def compile_and_run(self):
        """Compile everything, load the library, transfer state, call latest eval."""
        if self.eval_counter == 0 and not self.structs and not self.functions:
            return

        mpy_source = self.generate_mpy()
        mpy_path = os.path.join(self.tmpdir, "_repl.py")
        with open(mpy_path, "w") as f:
            f.write(mpy_source)

        # Compile .py → .c
        compiler = Compiler(
            source_dir=self.tmpdir,
            platform="all",
            emit_line_directives=False,
        )

        try:
            c_src, _, _ = compiler.compile_file(mpy_path, "__main__")
        except CompileError as e:
            print(f"CompileError: {e}")
            self._rollback()
            return
        except Exception as e:
            print(f"InternalError: {type(e).__name__}: {e}")
            self._rollback()
            return

        c_path = os.path.join(self.tmpdir, "_repl.c")
        with open(c_path, "w") as f:
            f.write(c_src)

        # Compile .c → shared library
        self.lib_counter += 1
        lib_path = os.path.join(self.tmpdir, f"_repl_{self.lib_counter}{_LIB_EXT}")
        pch_flags = ["-include-pch", self.pch_path] if os.path.exists(self.pch_path) else []
        cmd = (
            ["gcc", "-O0", "-g"]
            + pch_flags
            + _SHARED_FLAGS
            + [c_path, "-o", lib_path]
            + ([] if sys.platform == "win32" else ["-lm"])
        )

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("C compilation failed:")
            for line in (result.stderr or result.stdout or "").strip().split("\n"):
                # Strip temp-dir noise from paths
                print(f"  {line}")
            self._rollback()
            return

        # Save state from old library
        if self.lib is not None:
            self._export_state()

        # Load new library
        self.lib = ctypes.CDLL(lib_path)

        # Restore state into new library
        self._import_state()

        # Call latest eval (if any)
        if self.eval_counter > 0:
            eval_name = f"eval_{self.eval_counter}"
            try:
                fn = getattr(self.lib, eval_name)
                fn.restype = None
                fn.argtypes = []
                fn()
            except Exception as e:
                print(f"RuntimeError: {e}")

            # Capture state after eval
            self._export_state()

    def _rollback(self):
        """Undo the last input on compilation failure."""
        if self.eval_bodies and self.eval_counter > 0:
            self.eval_bodies.pop()
            self.eval_counter -= 1

    # ------------------------------------------------------------------
    # State transfer via ctypes
    # ------------------------------------------------------------------

    def _resolve_ctype(self, c_type_str):
        """Map a C type string to a ctypes type, including struct types."""
        ct = _CTYPE_MAP.get(c_type_str)
        if ct:
            return ct
        # Check if it's a known struct
        if c_type_str in self.struct_defs:
            return self._build_ctypes_struct(c_type_str)
        return None

    def _build_ctypes_struct(self, name):
        """Dynamically build a ctypes.Structure for a nathra struct."""
        fields = self.struct_defs.get(name, [])
        cfields = []
        for fname, ftype in fields:
            ct = _CTYPE_MAP.get(ftype)
            if ct:
                cfields.append((fname, ct))
            elif ftype in self.struct_defs:
                ct = self._build_ctypes_struct(ftype)
                cfields.append((fname, ct))
            else:
                # Unknown field type — skip this struct for state transfer
                return None
        return type(name, (ctypes.Structure,), {"_fields_": cfields})

    def _export_state(self):
        """Copy all globals from the loaded library into raw byte buffers."""
        for name, (c_type_str, _) in self.globals.items():
            ct = self._resolve_ctype(c_type_str)
            if ct is None:
                continue
            try:
                var = ct.in_dll(self.lib, name)
                size = ctypes.sizeof(var)
                buf = (ctypes.c_char * size)()
                ctypes.memmove(buf, ctypes.addressof(var), size)
                self.global_values[name] = bytes(buf)
            except (ValueError, OSError):
                pass

    def _import_state(self):
        """Copy saved byte buffers into the new library's globals."""
        for name, (c_type_str, _) in self.globals.items():
            if name not in self.global_values:
                continue
            ct = self._resolve_ctype(c_type_str)
            if ct is None:
                continue
            try:
                var = ct.in_dll(self.lib, name)
                saved = self.global_values[name]
                ctypes.memmove(ctypes.addressof(var), saved, len(saved))
            except (ValueError, OSError):
                pass

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self):
        """Remove temp directory."""
        try:
            shutil.rmtree(self.tmpdir, ignore_errors=True)
        except Exception:
            pass


# ----------------------------------------------------------------------
# REPL loop
# ----------------------------------------------------------------------

def _needs_continuation(line):
    """Return True if the line looks like the start of a multi-line block."""
    stripped = line.rstrip()
    return stripped.endswith(":")


def main():
    history_path = os.path.expanduser("~/.snekc_history")
    try:
        readline.read_history_file(history_path)
    except (FileNotFoundError, PermissionError, OSError):
        pass
    readline.set_history_length(1000)
    readline.parse_and_bind("tab: complete")

    state = ReplState()
    print("snekc — nathra interactive shell")
    print(f"Type nathra code. Ctrl-D to exit.\n")

    try:
        while True:
            try:
                line = input(">>> ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue

            if not line.strip():
                continue

            # Multi-line input for blocks (struct, def, if, for, while, ...)
            if _needs_continuation(line):
                block = [line]
                while True:
                    try:
                        cont = input("... ")
                    except (EOFError, KeyboardInterrupt):
                        break
                    if cont.strip() == "":
                        break
                    block.append(cont)
                line = "\n".join(block)

            if state.add_input(line):
                state.compile_and_run()
    finally:
        try:
            readline.write_history_file(history_path)
        except (PermissionError, OSError):
            pass
        state.cleanup()


if __name__ == "__main__":
    main()
