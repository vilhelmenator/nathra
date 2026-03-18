import ast
import sys
import os
import copy
import shutil
from dataclasses import dataclass, field
from typing import Optional

from type_map import TYPE_MAP, ALIAS_MAP, TUPLE_RET_MAP, map_type, mangle_type, get_array_info, get_typed_list_elem, gen_typed_list, get_funcptr_info
import type_map as _type_map_mod
from codegen_stmts import StmtMixin, _ALLOC_FUNCS, _FREE_FUNCS, _ptr_is_written
from codegen_exprs import ExprMixin

_HERE = os.path.dirname(os.path.abspath(__file__))


def _body_is_all_cold(stmts: list, cold_funcs: set) -> bool:
    """Return True if every code path through stmts terminates coldly.

    A cold terminal is: raise, a call to abort(), or a bare call to a @cold function.
    An if/else where BOTH branches are all-cold is also a cold terminal.
    Any return statement → not all-cold.
    """
    if not stmts:
        return False
    for stmt in stmts:
        if isinstance(stmt, ast.Return):
            return False
        if isinstance(stmt, ast.Raise):
            return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            fname = (call.func.id if isinstance(call.func, ast.Name) else
                     call.func.attr if isinstance(call.func, ast.Attribute) else None)
            if fname in cold_funcs or fname == "abort":
                return True
        if isinstance(stmt, ast.If):
            then_cold = _body_is_all_cold(stmt.body, cold_funcs)
            else_cold = (_body_is_all_cold(stmt.orelse, cold_funcs)
                         if stmt.orelse else False)
            if then_cold and else_cold:
                return True
    return False


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class CompileError(Exception):
    pass


# ---------------------------------------------------------------------------
# Compiler state
# ---------------------------------------------------------------------------

@dataclass
class ModuleInfo:
    name: str
    functions: dict = field(default_factory=dict)
    structs: dict = field(default_factory=dict)
    enums: dict = field(default_factory=dict)
    constants: list = field(default_factory=list)
    globals: list = field(default_factory=list)  # (name, ctype, annotation, value_node)
    traits: dict = field(default_factory=dict)


@dataclass
class Compiler(StmtMixin, ExprMixin):
    indent: int = 0
    lines: list = field(default_factory=list)
    header_lines: list = field(default_factory=list)
    current_module: str = ""
    modules: dict = field(default_factory=dict)
    compiled_files: set = field(default_factory=set)
    imports: list = field(default_factory=list)
    from_imports: dict = field(default_factory=dict)
    structs: dict = field(default_factory=dict)
    enums: dict = field(default_factory=dict)
    constants: dict = field(default_factory=dict)
    local_vars: dict = field(default_factory=dict)
    func_args: dict = field(default_factory=dict)
    func_ret_types: dict = field(default_factory=dict)
    traits: dict = field(default_factory=dict)  # trait_name → [(method_name, ret_type, args)]
    trait_impls: dict = field(default_factory=dict)  # struct_name → [trait_name, ...]
    typed_lists: dict = field(default_factory=dict)  # elem_type → list_name
    platform: str = "all"  # "windows", "linux", "macos", "all"
    source_dir: str = ""
    _compile_time_funcs: set = field(default_factory=set)  # names of @compile_time functions
    _compile_time_arrays: set = field(default_factory=set) # names of @compile_time static arrays
    _cold_funcs: set = field(default_factory=set)          # names of @cold-decorated functions

    thread_wrappers_emitted: set = field(default_factory=set)
    current_func_ret_type: str = "void"
    thread_spawn_counter: int = 0
    test_funcs: list = field(default_factory=list)   # names of @test functions
    c_includes: list = field(default_factory=list)    # c_include() calls at module level
    _extern_funcs: set = field(default_factory=set)   # names of @extern functions
    _variadic_funcs: set = field(default_factory=set)  # names of variadic functions (have *args)
    _fstr_counter: int = 0                            # unique suffix for f-string buffers
    _lc_counter: int = 0                              # unique suffix for list comprehension temps
    _funcptr_rettypes: dict = field(default_factory=dict)  # varname → ret ctype for func ptrs
    _current_file: str = ""                           # file being compiled (for errors)
    _current_line: int = 0                            # line being compiled (for errors)
    _array_vars: dict = field(default_factory=dict)   # varname → (elem_type, size_str)
    _list_vars: dict = field(default_factory=dict)    # varname → elem_type
    mutable_globals: dict = field(default_factory=dict)  # name → ctype for top-level vars
    func_defaults: dict = field(default_factory=dict)    # fname → [ast_node|None, ...] per param
    func_param_order: dict = field(default_factory=dict) # fname → [param_name, ...] in declared order
    func_param_types: dict = field(default_factory=dict)  # fname → [ctype, ...] for all params (incl. self)
    struct_array_fields: dict = field(default_factory=dict)  # (struct_name, field_name) → elem_ctype
    funcptr_alias_infos: dict = field(default_factory=dict)  # alias_name → (ret_ctype, [arg_ctypes])
    type_aliases: dict = field(default_factory=dict)     # alias_name → resolved ctype
    result_types: dict = field(default_factory=dict)     # "Result_T" → inner_ctype
    _export_funcs: list = field(default_factory=list)    # (name, ret, [(arg,type)]) for @export
    struct_properties: dict = field(default_factory=dict) # struct_name → {prop_name → ret_type}
    _lambda_counter: int = 0
    emit_line_directives: bool = True  # set False with --no-line-directives
    _lambda_table: dict = field(default_factory=dict)  # id(ast.Lambda) → name
    func_alloc_tags: dict = field(default_factory=dict)  # fname → frozenset of "producer"|"consumer"|"borrows"|"stores"
    _auto_free_vars: set = field(default_factory=set)    # locals auto-deferred for free() in current function
    _str_literal_vars: set = field(default_factory=set)  # locals init'd from string literal (stack MpStr, no malloc)
    _arena_batched_vars: dict = field(default_factory=dict)  # varname → arena batch info for current function
    _arena_batch_meta: dict = field(default_factory=dict)    # arena_name → batch metadata for current function
    _in_stream_func: bool = False     # current function has @stream — subscript writes → non-temporal stores
    _stream_loop_active: bool = False # inside a @stream for-range loop body right now
    debug_mode: bool = False                             # emit allocation tracking (--debug)

    def emit(self, line=""):
        prefix = "    " * self.indent
        self.lines.append(f"{prefix}{line}")

    def emit_header(self, line=""):
        self.header_lines.append(line)

    # -------------------------------------------------------------------
    # Decorator helpers
    # -------------------------------------------------------------------

    def get_decorators(self, node) -> dict:
        """Extract decorator info from a function or class node."""
        result = {}
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                result[dec.id] = True
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    name = dec.func.id
                    args = []
                    kwargs = {}
                    for a in dec.args:
                        if isinstance(a, ast.Constant):
                            args.append(a.value)
                        elif isinstance(a, ast.Name):
                            args.append(a.id)
                        elif isinstance(a, ast.List):
                            args.append([self._extract_const(e) for e in a.elts])
                    for kw in dec.keywords:
                        if isinstance(kw.value, ast.List):
                            kwargs[kw.arg] = [self._extract_const(e) for e in kw.value.elts]
                        elif isinstance(kw.value, ast.Constant):
                            kwargs[kw.arg] = kw.value.value
                        elif isinstance(kw.value, ast.Name):
                            kwargs[kw.arg] = kw.value.id
                    result[name] = {"args": args, "kwargs": kwargs}
        return result

    def _extract_const(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.List):
            return [self._extract_const(e) for e in node.elts]
        return str(ast.dump(node))

    # -------------------------------------------------------------------
    # Escape analysis + allocation signature tagging
    # -------------------------------------------------------------------

    def _escape_classify(self, func_node: ast.FunctionDef) -> dict:
        """Return {var_name: status} for every local assigned from alloc().

        Status values:
          "local_only" — never freed, never escapes → auto-free candidate
          "consumed"   — passed to free() or a Consumer-tagged function
          "escaping"   — returned, stored in struct, or passed to a
                         Stores-tagged or unknown function
        """
        alloc_vars: dict = {}
        for node in ast.walk(func_node):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if (node.value and isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id in _ALLOC_FUNCS):
                    alloc_vars[node.target.id] = "local_only"
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        if (isinstance(node.value, ast.Call)
                                and isinstance(node.value.func, ast.Name)
                                and node.value.func.id in _ALLOC_FUNCS):
                            alloc_vars[t.id] = "local_only"

        if not alloc_vars:
            return {}

        for node in ast.walk(func_node):
            # Returned — definitely escapes
            if isinstance(node, ast.Return) and node.value:
                if isinstance(node.value, ast.Name) and node.value.id in alloc_vars:
                    alloc_vars[node.value.id] = "escaping"

            # Stored into struct field — escapes
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        if isinstance(node.value, ast.Name) and node.value.id in alloc_vars:
                            alloc_vars[node.value.id] = "escaping"

            # Passed to a call — classify by callee tag
            elif isinstance(node, ast.Call):
                fname = node.func.id if isinstance(node.func, ast.Name) else None
                for arg in node.args:
                    if not (isinstance(arg, ast.Name) and arg.id in alloc_vars):
                        continue
                    cur = alloc_vars[arg.id]
                    if cur == "escaping":
                        continue  # already worst case
                    if fname in _FREE_FUNCS:
                        alloc_vars[arg.id] = "consumed"
                    else:
                        tags = self.func_alloc_tags.get(fname, frozenset())
                        if "consumer" in tags:
                            alloc_vars[arg.id] = "consumed"
                        elif "stores" in tags:
                            alloc_vars[arg.id] = "escaping"
                        elif tags and "borrows" in tags and "stores" not in tags:
                            pass  # caller retains ownership — no change
                        else:
                            # unknown / extern → conservative
                            alloc_vars[arg.id] = "escaping"

        return alloc_vars

    def _build_alloc_tags(self, tree) -> None:
        """Populate self.func_alloc_tags[fname] = frozenset of allocation roles.

        Tags:
          "producer" — returns a pointer that came from alloc()
          "consumer" — frees a pointer parameter via free()
          "stores"   — writes a pointer parameter into a struct field or global
          "borrows"  — takes pointer params but neither frees nor stores them

        Handles top-level functions and struct methods (tagged as ClassName_method).
        For extern/compile_time/trait/generic functions no tags are emitted.
        """
        skip_decs = frozenset({"extern", "compile_time", "trait", "generic"})

        def _tag_func(node: ast.FunctionDef, prefix: str = "") -> None:
            decs = self.get_decorators(node)
            if any(d in decs for d in skip_decs):
                return

            # Pointer-typed parameters (excludes self)
            ptr_params: set = set()
            for arg in node.args.args:
                if arg.arg == "self":
                    continue
                if arg.annotation:
                    ctype = map_type(arg.annotation)
                    if ctype.endswith("*"):
                        ptr_params.add(arg.arg)

            # alloc'd locals — needed for Producer detection
            alloc_locals: set = set()
            for child in ast.walk(node):
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    if (child.value and isinstance(child.value, ast.Call)
                            and isinstance(child.value.func, ast.Name)
                            and child.value.func.id in _ALLOC_FUNCS):
                        alloc_locals.add(child.target.id)
                elif isinstance(child, ast.Assign):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            if (isinstance(child.value, ast.Call)
                                    and isinstance(child.value.func, ast.Name)
                                    and child.value.func.id in _ALLOC_FUNCS):
                                alloc_locals.add(t.id)

            tags: set = set()
            consumed: set = set()
            stored: set = set()

            for child in ast.walk(node):
                # Producer: return alloc(...) or return alloc'd local
                if isinstance(child, ast.Return) and child.value:
                    if (isinstance(child.value, ast.Call)
                            and isinstance(child.value.func, ast.Name)
                            and child.value.func.id in _ALLOC_FUNCS):
                        tags.add("producer")
                    elif isinstance(child.value, ast.Name) and child.value.id in alloc_locals:
                        tags.add("producer")

                # Consumer: free(param)
                elif isinstance(child, ast.Call):
                    if (isinstance(child.func, ast.Name)
                            and child.func.id in _FREE_FUNCS
                            and child.args
                            and isinstance(child.args[0], ast.Name)
                            and child.args[0].id in ptr_params):
                        consumed.add(child.args[0].id)

                # Stores: x.field = param
                elif isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Attribute):
                            if (isinstance(child.value, ast.Name)
                                    and child.value.id in ptr_params):
                                stored.add(child.value.id)

            if consumed:
                tags.add("consumer")
            if stored:
                tags.add("stores")
            # Borrows: pointer params that are neither consumed nor stored
            if ptr_params - consumed - stored:
                tags.add("borrows")

            fname = f"{prefix}{node.name}" if prefix else node.name
            self.func_alloc_tags[fname] = frozenset(tags)

        # Top-level functions — pass 1: tag based on direct alloc() / free()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                _tag_func(node)
            elif isinstance(node, ast.ClassDef):
                decs = self.get_decorators(node)
                if "trait" not in decs and not self._is_enum_class(node):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            _tag_func(item, prefix=f"{node.name}_")

        # Pass 2: propagate Producer one more hop (depth-2 cap).
        # A function that returns a value from a Producer-tagged call is also a Producer.
        def _propagate_producer_tag(node: ast.FunctionDef, prefix: str = "") -> None:
            fname = f"{prefix}{node.name}" if prefix else node.name
            if "producer" in self.func_alloc_tags.get(fname, frozenset()):
                return  # already tagged — nothing to propagate
            # Locals assigned from Producer-tagged calls in this body
            producer_locals: set = set()
            for child in ast.walk(node):
                if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    if (child.value and isinstance(child.value, ast.Call)
                            and isinstance(child.value.func, ast.Name)
                            and "producer" in self.func_alloc_tags.get(
                                child.value.func.id, frozenset())):
                        producer_locals.add(child.target.id)
                elif isinstance(child, ast.Assign):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            if (isinstance(child.value, ast.Call)
                                    and isinstance(child.value.func, ast.Name)
                                    and "producer" in self.func_alloc_tags.get(
                                        child.value.func.id, frozenset())):
                                producer_locals.add(t.id)
            # If any return gives back a Producer-call result or a Producer local, tag self
            for child in ast.walk(node):
                if isinstance(child, ast.Return) and child.value:
                    ret = child.value
                    if (isinstance(ret, ast.Call) and isinstance(ret.func, ast.Name)
                            and "producer" in self.func_alloc_tags.get(
                                ret.func.id, frozenset())):
                        tags = set(self.func_alloc_tags.get(fname, frozenset()))
                        tags.add("producer")
                        self.func_alloc_tags[fname] = frozenset(tags)
                        return
                    if isinstance(ret, ast.Name) and ret.id in producer_locals:
                        tags = set(self.func_alloc_tags.get(fname, frozenset()))
                        tags.add("producer")
                        self.func_alloc_tags[fname] = frozenset(tags)
                        return

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                _propagate_producer_tag(node)
            elif isinstance(node, ast.ClassDef):
                decs = self.get_decorators(node)
                if "trait" not in decs and not self._is_enum_class(node):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            _propagate_producer_tag(item, prefix=f"{node.name}_")

    # -------------------------------------------------------------------
    # @cold inference
    # -------------------------------------------------------------------

    def _infer_cold_from_body(self, tree) -> None:
        """Auto-tag @cold: functions whose every code path terminates coldly.

        Fixpoint loop — a newly inferred cold function may unlock further
        inference in callers. Stops when no new functions are added.
        """
        skip_decs = frozenset({"extern", "compile_time", "trait", "generic"})
        changed = True
        while changed:
            changed = False
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    if any(d in self.get_decorators(node) for d in skip_decs):
                        continue
                    fname = node.name
                    if fname not in self._cold_funcs and _body_is_all_cold(node.body, self._cold_funcs):
                        self._cold_funcs.add(fname)
                        changed = True
                elif isinstance(node, ast.ClassDef):
                    decs = self.get_decorators(node)
                    if "trait" in decs or self._is_enum_class(node):
                        continue
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            fname = f"{node.name}_{item.name}"
                            if fname not in self._cold_funcs and _body_is_all_cold(item.body, self._cold_funcs):
                                self._cold_funcs.add(fname)
                                changed = True

    def _infer_cold_from_callsites(self, tree) -> None:
        """Auto-tag @cold: functions only ever called from error branches.

        Error branches: guard-raise bodies (if cond: raise / abort / @cold call)
        and is_err()/not is_ok() conditional blocks.
        """
        skip_decs = frozenset({"extern", "compile_time", "trait", "generic"})
        warm_calls: set = set()   # called from at least one non-error context
        all_calls: set = set()    # called at least once anywhere

        def _is_err_cond(test) -> bool:
            if isinstance(test, ast.Call) and isinstance(test.func, ast.Name):
                return test.func.id == "is_err"
            if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
                op = test.operand
                if isinstance(op, ast.Call) and isinstance(op.func, ast.Name):
                    return op.func.id == "is_ok"
            return False

        def _record_call(call_node, is_cold_ctx: bool) -> None:
            if isinstance(call_node.func, ast.Name):
                fname = call_node.func.id
            elif isinstance(call_node.func, ast.Attribute):
                fname = call_node.func.attr
            else:
                return
            if fname in self._cold_funcs:
                return
            all_calls.add(fname)
            if not is_cold_ctx:
                warm_calls.add(fname)

        def walk_expr(expr, is_cold_ctx: bool) -> None:
            for node in ast.walk(expr):
                if isinstance(node, ast.Call):
                    _record_call(node, is_cold_ctx)

        def walk_stmts(stmts, is_cold_ctx: bool) -> None:
            for stmt in stmts:
                if isinstance(stmt, ast.If):
                    walk_expr(stmt.test, is_cold_ctx)
                    body_cold = is_cold_ctx or _body_is_all_cold(stmt.body, self._cold_funcs)
                    walk_stmts(stmt.body, body_cold)
                    orelse_cold = is_cold_ctx or _is_err_cond(stmt.test)
                    if stmt.orelse:
                        walk_stmts(stmt.orelse, orelse_cold)
                elif isinstance(stmt, (ast.While, ast.For)):
                    if hasattr(stmt, "test"):
                        walk_expr(stmt.test, is_cold_ctx)
                    walk_stmts(stmt.body, is_cold_ctx)
                elif isinstance(stmt, ast.With):
                    walk_stmts(stmt.body, is_cold_ctx)
                elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                    _record_call(stmt.value, is_cold_ctx)
                    for arg in stmt.value.args:
                        walk_expr(arg, is_cold_ctx)
                elif isinstance(stmt, (ast.AnnAssign, ast.Assign)):
                    val = getattr(stmt, "value", None)
                    if val:
                        walk_expr(val, is_cold_ctx)
                elif isinstance(stmt, ast.Return) and stmt.value:
                    walk_expr(stmt.value, is_cold_ctx)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                if not any(d in self.get_decorators(node) for d in skip_decs):
                    walk_stmts(node.body, False)
            elif isinstance(node, ast.ClassDef):
                decs = self.get_decorators(node)
                if "trait" not in decs and not self._is_enum_class(node):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            walk_stmts(item.body, False)

        for fname in all_calls - warm_calls:
            self._cold_funcs.add(fname)

    # -------------------------------------------------------------------
    # Static leak detection
    # -------------------------------------------------------------------

    def _check_leaks(self, tree, filepath: str) -> None:
        """Entry point: run leak detection over every non-trivial function."""
        skip_decs = frozenset({"extern", "compile_time", "trait", "generic", "test"})
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                if not any(d in self.get_decorators(node) for d in skip_decs):
                    self._check_leaks_func(node, filepath)
            elif isinstance(node, ast.ClassDef):
                decs = self.get_decorators(node)
                if "trait" not in decs and not self._is_enum_class(node):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            self._check_leaks_func(item, filepath)

    def _check_leaks_func(self, func_node: ast.FunctionDef, filepath: str) -> None:
        """Path-sensitive leak/double-free/use-after-free analysis for one function."""
        # Skip vars the compiler already auto-frees or that legitimately escape
        classify = self._escape_classify(func_node)
        skip_vars = {v for v, st in classify.items() if st in ("local_only", "escaping")}

        def warn_leak(lineno: int, var: str, alloc_info) -> None:
            alloc_line, producer = alloc_info
            if producer:
                origin = f"returned by '{producer}' at line {alloc_line}"
            else:
                origin = f"allocated at line {alloc_line}"
            print(
                f"{filepath}:{lineno}: warning: '{var}' {origin}"
                f" may not be freed on this path",
                file=sys.stderr,
            )

        def error_double_free(lineno: int, var: str, free_line: int) -> None:
            print(
                f"{filepath}:{lineno}: error: '{var}' already freed at line {free_line}",
                file=sys.stderr,
            )

        def warn_uaf(lineno: int, var: str, free_line: int) -> None:
            print(
                f"{filepath}:{lineno}: warning: '{var}' used after free at line {free_line}",
                file=sys.stderr,
            )

        def producer_of(call_node):
            """If call transfers ownership to caller, return (True, producer_fname).
            producer_fname is None for direct alloc(), or the function name for Producer calls.
            Returns (False, None) if the call does not transfer ownership."""
            if not (isinstance(call_node, ast.Call)
                    and isinstance(call_node.func, ast.Name)):
                return False, None
            fname = call_node.func.id
            if fname in _ALLOC_FUNCS:
                return True, None
            if "producer" in self.func_alloc_tags.get(fname, frozenset()):
                return True, fname
            return False, None

        def check_expr_for_uaf(expr, freed: dict, lineno: int) -> None:
            """Warn if any freed variable appears in an expression."""
            for node in ast.walk(expr):
                if isinstance(node, ast.Name) and node.id in freed:
                    warn_uaf(lineno, node.id, freed[node.id])

        def discharge(call_node, live: dict, freed: dict) -> None:
            """Discharge ownership at a call site; detect double-free and UAF."""
            lineno = getattr(call_node, "lineno", 0)
            if not isinstance(call_node.func, ast.Name):
                # Method call — still check args for UAF
                for arg in call_node.args:
                    if isinstance(arg, ast.Name) and arg.id in freed:
                        warn_uaf(lineno, arg.id, freed[arg.id])
                return
            fname = call_node.func.id
            tags = self.func_alloc_tags.get(fname, frozenset())
            if fname in _FREE_FUNCS:
                for arg in call_node.args:
                    if isinstance(arg, ast.Name):
                        var = arg.id
                        if var in freed:
                            error_double_free(lineno, var, freed[var])
                        else:
                            live.pop(var, None)
                            freed[var] = lineno
            elif "consumer" in tags or "stores" in tags:
                for arg in call_node.args:
                    if isinstance(arg, ast.Name):
                        var = arg.id
                        if var in freed:
                            warn_uaf(lineno, var, freed[var])
                        else:
                            live.pop(var, None)
            else:
                # Regular borrows / unknown call — check args for UAF
                for arg in call_node.args:
                    if isinstance(arg, ast.Name) and arg.id in freed:
                        warn_uaf(lineno, arg.id, freed[arg.id])

        def analyze_body(stmts, live: dict, freed: dict):
            """Process a statement list. Returns (live, freed), or None if every
            path through these statements exits (return/raise)."""
            live = dict(live)
            freed = dict(freed)
            for stmt in stmts:
                result = analyze_stmt(stmt, live, freed)
                if result is None:
                    return None
                live, freed = result
            return live, freed

        def analyze_stmt(stmt, live: dict, freed: dict):
            """Returns (live, freed), or None if this statement always exits."""
            lineno = getattr(stmt, "lineno", 0)

            # x: ptr[T] = alloc(...) or x: ptr[T] = producer()
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                name = stmt.target.id
                if stmt.value:
                    if isinstance(stmt.value, ast.Call):
                        discharge(stmt.value, live, freed)
                    else:
                        check_expr_for_uaf(stmt.value, freed, lineno)
                    owned, pname = producer_of(stmt.value)
                    if name not in skip_vars and owned:
                        live[name] = (lineno, pname)
                return live, freed

            # x = alloc(...) or x = producer()
            if isinstance(stmt, ast.Assign):
                if isinstance(stmt.value, ast.Call):
                    discharge(stmt.value, live, freed)
                else:
                    check_expr_for_uaf(stmt.value, freed, lineno)
                for t in stmt.targets:
                    owned, pname = producer_of(stmt.value)
                    if isinstance(t, ast.Name) and t.id not in skip_vars and owned:
                        live[t.id] = (lineno, pname)
                return live, freed

            # Bare call expression: free(x), consume(x)
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                discharge(stmt.value, live, freed)
                return live, freed

            # return — warn about live vars that aren't the returned value
            if isinstance(stmt, ast.Return):
                returned = (stmt.value.id
                            if stmt.value and isinstance(stmt.value, ast.Name)
                            else None)
                if stmt.value:
                    check_expr_for_uaf(stmt.value, freed, lineno)
                for var, alloc_info in live.items():
                    if var != returned:
                        warn_leak(lineno, var, alloc_info)
                return None  # path exits

            # raise — warn about all live vars
            if isinstance(stmt, ast.Raise):
                for var, alloc_info in live.items():
                    warn_leak(lineno, var, alloc_info)
                return None  # path exits

            # if / else — fork, recurse, merge surviving sets
            if isinstance(stmt, ast.If):
                check_expr_for_uaf(stmt.test, freed, lineno)
                for n in ast.walk(stmt.test):
                    if isinstance(n, ast.Call):
                        discharge(n, live, freed)
                result_then = analyze_body(stmt.body, live, freed)
                result_else = (analyze_body(stmt.orelse, live, freed)
                               if stmt.orelse else (dict(live), dict(freed)))
                if result_then is None and result_else is None:
                    return None
                if result_then is None:
                    return result_else
                if result_else is None:
                    return result_then
                live_then, freed_then = result_then
                live_else, freed_else = result_else
                merged_live = dict(live_then)
                for var, loc in live_else.items():
                    if var not in merged_live:
                        merged_live[var] = loc
                merged_freed = dict(freed_then)
                merged_freed.update(freed_else)
                return merged_live, merged_freed

            # while / for — analyze body once (conservative: don't model iterations)
            if isinstance(stmt, (ast.While, ast.For)):
                if isinstance(stmt, ast.While):
                    check_expr_for_uaf(stmt.test, freed, lineno)
                analyze_body(stmt.body, dict(live), dict(freed))
                return live, freed

            # with — analyze body
            if isinstance(stmt, ast.With):
                result = analyze_body(stmt.body, live, freed)
                return (live, freed) if result is None else result

            return live, freed

        final = analyze_body(func_node.body, {}, {})
        if final:
            live, _freed = final
            end_line = getattr(func_node, "end_lineno", func_node.lineno)
            for var, alloc_info in live.items():
                warn_leak(end_line, var, alloc_info)

    # -------------------------------------------------------------------
    # Type inference
    # -------------------------------------------------------------------

    def infer_type(self, node) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "int"
            if isinstance(node.value, int):
                return "int64_t"
            if isinstance(node.value, float):
                return "double"
            if isinstance(node.value, str):
                return "MpStr*"
            return "int64_t"

        if isinstance(node, ast.Name):
            name = node.id
            if name in ("True", "False"):
                return "int"
            if name in self.local_vars:
                return self.local_vars[name]
            if name in self.func_args:
                return self.func_args[name]
            if name in self.constants:
                return self.constants[name]
            return "int64_t"

        if isinstance(node, ast.BinOp):
            lt = self.infer_type(node.left)
            rt = self.infer_type(node.right)
            lb = lt.rstrip("*").strip()
            if lb in self.structs:
                _op_map = {
                    ast.Add: "__add__", ast.Sub: "__sub__", ast.Mult: "__mul__",
                    ast.Div: "__truediv__", ast.Mod: "__mod__",
                }
                _op_name = _op_map.get(type(node.op))
                if _op_name:
                    _method = f"{lb}_{_op_name}"
                    if _method in self.func_ret_types:
                        return self.func_ret_types[_method]
            if lt == "double" or rt == "double":
                return "double"
            return "int64_t"

        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.Not):
                return "int"
            return self.infer_type(node.operand)

        if isinstance(node, ast.BoolOp):
            return "int"

        if isinstance(node, ast.Compare):
            return "int"

        if isinstance(node, ast.Call):
            return self.infer_call_type(node)

        if isinstance(node, ast.Attribute):
            obj_type = self.infer_type(node.value)
            base = obj_type.rstrip("*").strip()
            if base in self.structs:
                for fname, ftype in self.structs[base]:
                    if fname == node.attr:
                        if ftype == "__array__":
                            # Return elem type for array fields
                            et = self.struct_array_fields.get((base, node.attr))
                            return et if et else "int64_t"
                        return ftype
            return "int64_t"

        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                vname = node.value.id
                # Named array variable
                arr_info = self._array_vars.get(vname)
                if arr_info:
                    return arr_info[0]  # elem_type
                et = self._list_vars.get(vname)
                if et:
                    return et
            # Attribute subscript: s.field[i] where field is an array or ptr[T]
            if isinstance(node.value, ast.Attribute):
                obj_type = self.infer_type(node.value.value)
                base = obj_type.rstrip("*").strip()
                et = self.struct_array_fields.get((base, node.value.attr))
                if et:
                    return et
                # ptr[T] field: T* → T
                for _fn, _ft in self.structs.get(base, []):
                    if _fn == node.value.attr and _ft.endswith("*"):
                        return _ft[:-1].strip()
            # Plain pointer subscript: T*[i] → T
            val_type = self.infer_type(node.value)
            if val_type.endswith("*"):
                return val_type[:-1].strip()
            return "int64_t"

        if isinstance(node, ast.IfExp):
            return self.infer_type(node.body)

        if isinstance(node, ast.ListComp):
            return "MpList*"

        return "int64_t"

    def infer_call_type(self, node) -> str:
        if isinstance(node.func, ast.Name):
            fname = node.func.id

            # Function pointer variable call
            if fname in self._funcptr_rettypes:
                return self._funcptr_rettypes[fname]

            cast_types = {"cast_int": "int64_t", "cast_float": "double",
                          "cast_byte": "uint8_t", "cast_bool": "int"}
            if fname in cast_types:
                return cast_types[fname]

            if fname in self.structs:
                return fname

            # Result helpers
            if fname == "Ok" and len(node.args) == 1:
                from type_map import mangle_type as _mangle
                inner = self.infer_type(node.args[0])
                return f"Result_{_mangle(inner)}"
            if fname in ("Err",):
                return self.current_func_ret_type
            if fname in ("is_ok", "is_err"):
                return "int"
            if fname == "unwrap" and len(node.args) == 1:
                t = self.infer_type(node.args[0])
                if t in self.result_types:
                    return self.result_types[t]
                return t
            if fname == "err_msg":
                return "char*"
            if fname == "try_unwrap" and len(node.args) == 1:
                t = self.infer_type(node.args[0])
                if t in self.result_types:
                    return self.result_types[t]
                return "int64_t"

            _math_ret = {f: "double" for f in (
                "sqrt", "cbrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
                "sinh", "cosh", "tanh", "exp", "exp2", "log", "log2", "log10",
                "pow", "floor", "ceil", "round", "trunc", "fabs", "hypot", "fmod",
            )}
            _math_ret.update({"isnan": "int", "isinf": "int"})
            if fname in _math_ret:
                return _math_ret[fname]

            if fname == "input":
                return "MpStr*"
            if fname == "exit":
                return "void"

            rt_types = {
                "list_new": "MpList*", "list_get": "MpVal", "list_len": "int64_t",
                "list_pop": "MpVal", "dict_new": "MpDict*", "dict_get": "MpVal",
                "dict_len": "int64_t", "dict_has": "int",
                "str_new": "MpStr*", "str_concat": "MpStr*", "str_len": "int64_t",
                "str_eq": "int", "str_from_int": "MpStr*", "str_from_float": "MpStr*",
                "str_upper": "MpStr*", "str_lower": "MpStr*", "str_slice": "MpStr*",
                "str_repeat": "MpStr*", "str_find": "int64_t",
                "str_contains": "int", "str_starts_with": "int", "str_ends_with": "int",
                "str_strip": "MpStr*", "str_lstrip": "MpStr*", "str_rstrip": "MpStr*",
                "str_split": "MpList*", "str_format": "MpStr*",
                "str": "MpStr*",
                "rand_int": "int64_t", "rand_float": "double",
                "time_now": "int64_t", "time_ms": "int64_t",
                "getenv": "MpStr*",
                "val_int": "MpVal", "val_float": "MpVal",
                "val_str": "MpVal", "as_int": "int64_t", "as_float": "double",
                "open": "MpFile",
                "file_open": "MpFile", "file_open_safe": "MpFile",
                "file_read_all": "MpStr*", "file_read_line": "MpStr*",
                "file_eof": "int", "file_exists": "int", "file_size": "int64_t",
                "dir_exists": "int", "dir_create": "int", "dir_remove": "int",
                "dir_cwd": "MpStr*", "dir_chdir": "int", "dir_list": "MpList*",
                "path_join": "MpStr*", "path_ext": "MpStr*",
                "path_basename": "MpStr*", "path_dirname": "MpStr*",
                "remove_file": "int", "rename_file": "int",
                "thread_spawn": "MpThread", "mutex_new": "MpMutex*",
                "cond_new": "MpCond*",
                "channel_new": "MpChannel*", "channel_send": "int",
                "channel_recv": "int",
                "channel_recv_val": "MpVal", "channel_drain": "MpList*",
                "channel_has_data": "int",
                "atomic_add": "int64_t", "atomic_sub": "int64_t",
                "atomic_load": "int64_t", "atomic_store": "void",
                "atomic_cas": "int64_t",
                "pool_new": "MpThreadPool*",
            }
            if fname in rt_types:
                return rt_types[fname]

            # Typed list constructors
            for elem_t, list_name in self.typed_lists.items():
                if fname == f"{list_name}_new":
                    return f"{list_name}*"
                if fname == f"{list_name}_get" or fname == f"{list_name}_pop":
                    return elem_t
                if fname == f"{list_name}_len":
                    return "int64_t"

            if fname in self.from_imports:
                mod, real_name = self.from_imports[fname]
                if mod in self.modules and real_name in self.modules[mod].functions:
                    return self.modules[mod].functions[real_name][0]

            cur = self.modules.get(self.current_module)
            if cur and fname in cur.functions:
                return cur.functions[fname][0]

            for mn, mi in self.modules.items():
                if fname in mi.functions:
                    return mi.functions[fname][0]

        if isinstance(node.func, ast.Attribute):
            obj = node.func.value
            attr = node.func.attr
            # math.sqrt(x) etc.
            _math_names = {
                "sqrt", "cbrt", "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
                "sinh", "cosh", "tanh", "exp", "exp2", "log", "log2", "log10",
                "pow", "floor", "ceil", "round", "trunc", "fabs", "hypot", "fmod",
            }
            if isinstance(obj, ast.Name) and obj.id == "math":
                return "double" if attr in _math_names else "int"
            if isinstance(obj, ast.Name) and obj.id in self.modules:
                mi = self.modules[obj.id]
                if attr in mi.functions:
                    return mi.functions[attr][0]
            # Method calls on known types
            obj_type = self.infer_type(obj)
            if obj_type == "MpStr*":
                _str_ret = {
                    "concat": "MpStr*", "upper": "MpStr*", "lower": "MpStr*",
                    "slice": "MpStr*", "repeat": "MpStr*",
                    "strip": "MpStr*", "lstrip": "MpStr*", "rstrip": "MpStr*",
                    "split": "MpList*", "format": "MpStr*",
                    "len": "int64_t", "find": "int64_t",
                    "eq": "int", "contains": "int",
                    "starts_with": "int", "ends_with": "int",
                }
                if attr in _str_ret:
                    return _str_ret[attr]
            base = obj_type.rstrip("*").strip()
            if base in self.structs:
                method_cname = f"{base}_{attr}"
                if method_cname in self.func_ret_types:
                    return self.func_ret_types[method_cname]

        return "int64_t"

    # -------------------------------------------------------------------
    # Top-level compilation
    # -------------------------------------------------------------------

    def compile_file(self, filepath: str, module_name: str = "") -> tuple:
        with open(filepath, "r") as f:
            source = f.read()

        if not module_name:
            module_name = os.path.splitext(os.path.basename(filepath))[0]

        self._current_file = filepath
        self._current_line = 0
        self.source_dir = os.path.dirname(os.path.abspath(filepath))
        self.current_module = module_name
        self.lines = []
        self.header_lines = []
        self.imports = []
        self.from_imports = {}
        self.local_vars = {}
        self.func_args = {}
        # Clear module-level alias maps for this compile run
        _type_map_mod.ALIAS_MAP.clear()
        _type_map_mod.TUPLE_RET_MAP.clear()

        # Preprocess: struct/union keywords → class (with @union decorator for unions)
        source = source.replace("\nstruct ", "\nclass ")
        if source.startswith("struct "):
            source = "class " + source[7:]
        source = source.replace("\nunion ", "\n@union\nclass ")
        if source.startswith("union "):
            source = "@union\nclass " + source[6:]

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            raise CompileError(
                f"{filepath}:{e.lineno}: syntax error: {e.msg}"
            ) from e
        mod_info = ModuleInfo(name=module_name)

        # ---- First pass: collect everything ----
        for node in ast.iter_child_nodes(tree):
            # c_include("header.h") at module level
            if isinstance(node, ast.Expr):
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    if node.value.func.id == "c_include":
                        if node.value.args and isinstance(node.value.args[0], ast.Constant):
                            self.c_includes.append(node.value.args[0].value)
                continue

            if isinstance(node, ast.FunctionDef):
                decs = self.get_decorators(node)

                # @extern: register signature, emit no definition
                if "extern" in decs:
                    ret_type = map_type(node.returns)
                    args = []
                    for arg in node.args.args:
                        atype = map_type(arg.annotation)
                        args.append((arg.arg, atype))
                    mod_info.functions[node.name] = (ret_type, args)
                    self.func_ret_types[node.name] = ret_type
                    self._extern_funcs.add(node.name)
                    continue

                # @export: register for vtable emission; function is compiled normally
                if "export" in decs:
                    ret_type = map_type(node.returns)
                    args = []
                    for arg in node.args.args:
                        atype = map_type(arg.annotation)
                        args.append((arg.arg, atype))
                    self._export_funcs.append((node.name, ret_type, args))

                # Track variadic functions (have *args parameter)
                if node.args.vararg is not None:
                    self._variadic_funcs.add(node.name)

                # Skip @compile_time functions in first pass (handled separately)
                if "compile_time" in decs:
                    self._compile_time_funcs.add(node.name)
                    continue

                # @test: register for test runner generation
                if "test" in decs:
                    self.test_funcs.append(node.name)

                # Skip @trait methods (they're just declarations)
                if "trait" in decs:
                    methods = []
                    for item in node.body:
                        pass  # traits are on classes, not functions
                    continue

                # @generic: register all specializations
                if "generic" in decs:
                    gen_info = decs["generic"]
                    type_params = gen_info.get("kwargs", {})
                    # e.g. @generic(T=[int, float, Vec2])
                    for param_name, type_list in type_params.items():
                        for t in type_list:
                            ct = TYPE_MAP.get(t, t)
                            suffix = t.replace("*", "ptr")
                            spec_name = f"{node.name}_{suffix}"
                            ret_type = map_type(node.returns)
                            if ret_type == param_name:
                                ret_type = ct
                            args = []
                            for arg in node.args.args:
                                atype = map_type(arg.annotation)
                                if atype == param_name:
                                    atype = ct
                                args.append((arg.arg, atype))
                            mod_info.functions[spec_name] = (ret_type, args)
                    continue

                # @platform: only register if matches
                if "platform" in decs:
                    plat_info = decs["platform"]
                    plat = plat_info["args"][0] if plat_info.get("args") else "all"
                    if self.platform != "all" and plat != self.platform:
                        continue

                ret_type = map_type(node.returns)
                args = []
                for arg in node.args.args:
                    atype = map_type(arg.annotation)
                    args.append((arg.arg, atype))
                mod_info.functions[node.name] = (ret_type, args)
                self.func_ret_types[node.name] = ret_type
                self.func_param_order[node.name] = [a.arg for a in node.args.args]
                self.func_param_types[node.name] = [map_type(a.annotation) for a in node.args.args]
                if "cold" in decs:
                    self._cold_funcs.add(node.name)

                # Collect default parameter values (right-aligned in ast.arguments.defaults)
                n_args = len(node.args.args)
                n_defs = len(node.args.defaults)
                defaults = [None] * n_args
                for i, d in enumerate(node.args.defaults):
                    defaults[n_args - n_defs + i] = d
                self.func_defaults[node.name] = defaults

            elif isinstance(node, ast.ClassDef):
                decs = self.get_decorators(node)

                if "trait" in decs:
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            ret = map_type(item.returns)
                            margs = []
                            for a in item.args.args:
                                if a.arg == "self":
                                    continue
                                margs.append((a.arg, map_type(a.annotation)))
                            methods.append((item.name, ret, margs))
                    self.traits[node.name] = methods
                    mod_info.traits[node.name] = methods
                    continue

                # Check for @impl(TraitName)
                impl_traits = []
                if "impl" in decs:
                    impl_info = decs["impl"]
                    impl_traits = impl_info.get("args", [])

                is_enum = self._is_enum_class(node)
                if is_enum:
                    members = []
                    for item in node.body:
                        if isinstance(item, ast.Assign) and len(item.targets) == 1:
                            if isinstance(item.targets[0], ast.Name):
                                nm = item.targets[0].id
                                val = item.value.value if isinstance(item.value, ast.Constant) else None
                                members.append((nm, val))
                    mod_info.enums[node.name] = members
                    self.enums[node.name] = members
                else:
                    fields = []
                    for item in node.body:
                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            _ctype = map_type(item.annotation)
                            fields.append((item.target.id, _ctype))
                            if _ctype == "__array__":
                                _et, _ = get_array_info(item.annotation)
                                self.struct_array_fields[(node.name, item.target.id)] = _et
                    mod_info.structs[node.name] = fields
                    self.structs[node.name] = fields

                    # Register class methods as ClassName_methodname
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            ret_type = map_type(item.returns) if item.returns else "void"
                            # @property: record for attribute-access rewriting
                            _is_property = any(
                                (isinstance(d, ast.Name) and d.id == "property")
                                for d in item.decorator_list
                            )
                            if _is_property:
                                self.struct_properties.setdefault(node.name, {})[item.name] = ret_type
                            _is_static = any(
                                (isinstance(d, ast.Name) and d.id == "staticmethod") or
                                (isinstance(d, ast.Attribute) and d.attr == "staticmethod")
                                for d in item.decorator_list
                            )
                            method_args = [] if _is_static else [("self", f"{node.name}*")]
                            for arg in item.args.args:
                                if arg.arg == "self":
                                    continue
                                atype = map_type(arg.annotation) if arg.annotation else "int64_t"
                                method_args.append((arg.arg, atype))
                            method_cname = f"{node.name}_{item.name}"
                            mod_info.functions[method_cname] = (ret_type, method_args)
                            self.func_ret_types[method_cname] = ret_type
                            self.func_param_order[method_cname] = [a.arg for a in item.args.args]
                            self.func_param_types[method_cname] = [t for _, t in method_args]

                    if impl_traits:
                        self.trait_impls[node.name] = impl_traits

            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                if name.isupper() or name.startswith("CONST_"):
                    # Don't treat compile_time results as regular constants
                    is_ct_call = False
                    if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                        if node.value.func.id in self._compile_time_funcs:
                            is_ct_call = True
                    if not is_ct_call:
                        ctype = map_type(node.annotation)
                        mod_info.constants.append((name, ctype, node.value))
                        self.constants[name] = ctype
                else:
                    # Mutable global variable
                    ctype = map_type(node.annotation)
                    mod_info.globals.append((name, ctype, node.annotation, node.value))
                    self.mutable_globals[name] = ctype

                # Detect typed_list declarations to know which types to generate
                if isinstance(node.annotation, ast.Subscript):
                    base = node.annotation.value
                    if isinstance(base, ast.Name) and base.id == "typed_list":
                        elem_t = get_typed_list_elem(node.annotation)
                        if elem_t not in self.typed_lists:
                            # Generate name: int64_t → IntList, double → FloatList, Vec2 → Vec2List
                            nice = {"int64_t": "Int", "double": "Float", "uint8_t": "Byte",
                                    "int": "Bool"}
                            prefix = nice.get(elem_t, elem_t.replace("*", "Ptr"))
                            self.typed_lists[elem_t] = f"{prefix}List"

            # Type aliases: MyInt = int  or  MyVec = ptr[float]
            elif isinstance(node, ast.Assign):
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    alias_name = node.targets[0].id
                    # Only treat as type alias if RHS looks like a type expression
                    val = node.value
                    if isinstance(val, (ast.Name, ast.Subscript)):
                        resolved = map_type(val)
                        if resolved != alias_name:  # avoid trivial self-aliases
                            self.type_aliases[alias_name] = resolved
                            _type_map_mod.ALIAS_MAP[alias_name] = resolved
                            if resolved == "__funcptr__":
                                fp_info = get_funcptr_info(val)
                                if fp_info:
                                    self.funcptr_alias_infos[alias_name] = fp_info

            # Python 3.12+ `type MyInt = int` statement
            elif hasattr(ast, "TypeAlias") and isinstance(node, ast.TypeAlias):
                alias_name = node.name.id if isinstance(node.name, ast.Name) else str(node.name)
                resolved = map_type(node.value)
                self.type_aliases[alias_name] = resolved
                _type_map_mod.ALIAS_MAP[alias_name] = resolved

        self.modules[module_name] = mod_info

        # Scan entire tree for typed_list / Result annotations
        self._scan_typed_lists(tree)
        self._scan_result_types(tree)
        self._scan_tuple_returns(tree)

        # Build allocation signature tags for every function in this module
        self._build_alloc_tags(tree)

        # @cold inference: body analysis (fixpoint), then call-site analysis
        self._infer_cold_from_body(tree)
        self._infer_cold_from_callsites(tree)

        # Static leak detection — warns to stderr, no effect on codegen
        self._check_leaks(tree, self._current_file or filepath)

        # ---- Process imports ----
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                self.compile_import(node)
            elif isinstance(node, ast.ImportFrom):
                self.compile_import_from(node)

        # ---- Emit C file ----
        # micropy_rt.h brings in stdint, stdio, stdlib, string, math — no need to repeat them.
        self.emit('#include "micropy_rt.h"')
        if self._variadic_funcs:
            self.emit('#include <stdarg.h>')
        for inc in self.c_includes:
            if inc.startswith("<") and inc.endswith(">"):
                self.emit(f"#include {inc}")
            else:
                self.emit(f'#include "{inc}"')
        if self.test_funcs:
            self._ensure_test_header()
            self.emit('#include "micropy_test.h"')
        if module_name != "__main__":
            self.emit(f'#include "{module_name}.h"')
        else:
            for imp in self.imports:
                self.emit(f'#include "{imp}.h"')
        self.emit("")

        # Debug mode: define the shared alloc counter and register exit check
        if self.debug_mode and module_name == "__main__":
            self.emit("#ifdef MICROPY_DEBUG")
            self.emit("volatile long long _mp_alloc_count = 0;")
            self.emit("__attribute__((constructor)) static void _mp_debug_init(void) {")
            self.emit("    atexit(_mp_alloc_assert_zero);")
            self.emit("}")
            self.emit("#endif")
            self.emit("")

        # Emit scalar typed list implementations (before structs)
        for elem_t, list_name in self.typed_lists.items():
            if elem_t not in self.structs:
                self.emit(gen_typed_list(elem_t, list_name))

        # Emit enums
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name in self.enums:
                self.compile_enum(node)

        # Emit Result[T] types
        if self.result_types:
            self._emit_result_types()

        # Emit tuple return structs
        if TUPLE_RET_MAP:
            self._emit_tuple_ret_structs()

        # Emit constants — before structs so struct methods can reference them
        for name, ctype, value_node in mod_info.constants:
            if value_node:
                val = self.compile_expr(value_node)
                # If annotation was bare `const`, infer C type from value
                if ctype == "const":
                    ctype = self.infer_type(value_node)
                self.emit(f"const {ctype} {name} = {val};")
        if mod_info.constants:
            self.emit("")

        # Emit mutable globals — before structs for same reason
        for name, ctype, annotation, value_node in mod_info.globals:
            if ctype == "__array__":
                elem_type, size = get_array_info(annotation)
                if value_node:
                    val = self.compile_expr(value_node)
                    self.emit(f"{elem_type} {name}[{size}] = {val};")
                else:
                    self.emit(f"{elem_type} {name}[{size}] = {{0}};")
            elif ctype == "__funcptr__":
                info = get_funcptr_info(annotation)
                if info:
                    ret, fp_args = info
                    fp_arg_str = ", ".join(fp_args) if fp_args else "void"
                    if value_node:
                        val = self.compile_expr(value_node)
                        self.emit(f"{ret} (*{name})({fp_arg_str}) = {val};")
                    else:
                        self.emit(f"{ret} (*{name})({fp_arg_str}) = NULL;")
            else:
                if value_node:
                    val = self.compile_expr(value_node)
                    self.emit(f"{ctype} {name} = {val};")
                else:
                    self.emit(f"{ctype} {name};")
        if mod_info.globals:
            self.emit("")

        # Emit @compile_time evaluated constants
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                decs = self.get_decorators(node)
                if "compile_time" in decs:
                    self._emit_compile_time(node, tree)

        # Forward-declare all structs/unions so function prototypes can reference them
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name in self.structs:
                decs = self.get_decorators(node)
                kw = "union" if "union" in decs else "struct"
                self.emit(f"typedef {kw} {node.name} {node.name};")
        if self.structs:
            self.emit("")

        # Emit function prototypes (forward declarations) — before structs so struct
        # methods can call free functions defined later in the file
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                decs = self.get_decorators(node)
                if any(d in decs for d in ("extern", "compile_time", "trait", "generic", "test")):
                    continue
                if "platform" in decs:
                    plat_info = decs["platform"]
                    plat = plat_info["args"][0] if plat_info.get("args") else "all"
                    if self.platform != "all" and plat != self.platform:
                        continue
                proto = self._make_prototype(node, module_name)
                if proto:
                    self.emit(f"{proto};")
        self.emit("")

        # Emit structs
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name in self.structs:
                self.compile_struct(node)

        # Emit struct-element typed list implementations (after structs are defined)
        for elem_t, list_name in self.typed_lists.items():
            if elem_t in self.structs:
                self.emit(gen_typed_list(elem_t, list_name))

        # Verify trait implementations
        for sname, trait_names in self.trait_impls.items():
            for tname in trait_names:
                self._verify_trait(sname, tname, tree)

        # Emit functions — in topological order (callees before callers).
        # Prototypes already emitted above handle mutual recursion.
        _emit_funcs = []
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                decs = self.get_decorators(node)
                if any(d in decs for d in ("extern", "compile_time", "trait")):
                    continue
                _emit_funcs.append(node)

        # Build call graph: fname → set of module-function names it calls
        _mod_names = {n.name for n in _emit_funcs}
        _call_graph = {}
        for _fn in _emit_funcs:
            _edges = set()
            for _stmt in _fn.body:
                for _nd in ast.walk(_stmt):
                    if (isinstance(_nd, ast.Call)
                            and isinstance(_nd.func, ast.Name)
                            and _nd.func.id in _mod_names
                            and _nd.func.id != _fn.name):
                        _edges.add(_nd.func.id)
            _call_graph[_fn.name] = _edges

        # Topological sort via DFS post-order: callee before caller
        _topo_visited: set = set()
        _topo_result: list = []
        def _topo_dfs(name: str) -> None:
            if name in _topo_visited:
                return
            _topo_visited.add(name)
            for dep in _call_graph.get(name, ()):
                _topo_dfs(dep)
            _topo_result.append(name)
        for _fn in _emit_funcs:
            _topo_dfs(_fn.name)

        _fn_map = {n.name: n for n in _emit_funcs}
        for _fname in _topo_result:
            node = _fn_map[_fname]
            decs = self.get_decorators(node)

            if "generic" in decs:
                self._emit_generic(node, decs, module_name)
                continue

            if "platform" in decs:
                plat_info = decs["platform"]
                plat = plat_info["args"][0] if plat_info.get("args") else "all"
                if self.platform != "all" and plat != self.platform:
                    continue
                self._emit_platform_func(node, plat, module_name)
                continue

            if "unroll" in decs:
                self.compile_function_with_unroll(node, module_name, decs["unroll"])
                continue

            if "parallel" in decs:
                self._emit_parallel(node, decs["parallel"], module_name)
                continue

            if "test" in decs:
                self.compile_function(node, module_name)
                self._emit_test_wrapper(node.name)
                continue

            self.compile_function(node, module_name)

        # Emit test main() if we have @test functions and no explicit main
        if self.test_funcs and "main" not in mod_info.functions:
            self._emit_test_main()

        # Emit @export vtable if any functions are exported
        if self._export_funcs:
            self._emit_export_vtable()

        # Top-level statements → main()
        top_stmts = []
        for n in ast.iter_child_nodes(tree):
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                nm = n.target.id
                if nm.isupper() or nm.startswith("CONST_"):
                    continue
                if nm in self.mutable_globals:
                    continue  # already emitted as C global
                top_stmts.append(n)
            elif not isinstance(n, (ast.FunctionDef, ast.Import,
                                    ast.ImportFrom, ast.ClassDef)):
                # Skip c_include() at top level — already emitted in header block
                if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
                    if isinstance(n.value.func, ast.Name) and n.value.func.id == "c_include":
                        continue
                # Skip type alias assignments (already handled in first pass)
                if isinstance(n, ast.Assign):
                    if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                        alias_name = n.targets[0].id
                        if alias_name in self.type_aliases:
                            continue
                # Skip Python 3.12+ type aliases
                if hasattr(ast, "TypeAlias") and isinstance(n, ast.TypeAlias):
                    continue
                top_stmts.append(n)

        has_main_func = "main" in mod_info.functions

        if top_stmts and not has_main_func:
            self.emit("int main(void) {")
            self.indent += 1
            for node in top_stmts:
                self.compile_stmt(node)
            self.emit("return 0;")
            self.indent -= 1
            self.emit("}")

        # Emit directory implementation at the very end (isolates windows.h)
        if module_name == "__main__":
            self.emit("")
            self.emit("/* Platform directory implementations */")
            self.emit("#define MICROPY_RT_IMPL")
            self.emit('#include "micropy_rt.h"')

        # ---- Generate header ----
        guard = f"{module_name.upper()}_H"
        self.emit_header(f"#ifndef {guard}")
        self.emit_header(f"#define {guard}")
        self.emit_header('#include "micropy_types.h"')
        for imp in self.imports:
            self.emit_header(f'#include "{imp}.h"')

        for ename, members in mod_info.enums.items():
            self.emit_header(f"typedef enum {{")
            for i, (mname, mval) in enumerate(members):
                suffix = "," if i < len(members) - 1 else ""
                if mval is not None:
                    self.emit_header(f"    {ename}_{mname} = {mval}{suffix}")
                else:
                    self.emit_header(f"    {ename}_{mname}{suffix}")
            self.emit_header(f"}} {ename};")
            self.emit_header("")

        for sname, sfields in mod_info.structs.items():
            self.emit_header(f"typedef struct {{")
            for fname, ftype in sfields:
                self.emit_header(f"    {ftype} {fname};")
            self.emit_header(f"}} {sname};")
            self.emit_header("")

        prefix = f"{module_name}_" if module_name != "__main__" else ""
        for fname, (ret, args) in mod_info.functions.items():
            if fname in self._extern_funcs:
                continue  # declared by the C header, not ours to re-declare
            arg_str = ", ".join(f"{t} {n}" for n, t in args) if args else "void"
            self.emit_header(f"{ret} {prefix}{fname}({arg_str});")

        for name, ctype, value_node in mod_info.constants:
            if ctype == "const":
                ctype = self.infer_type(value_node) if value_node else "int64_t"
            self.emit_header(f"extern const {ctype} {name};")

        for name, ctype, annotation, value_node in mod_info.globals:
            if ctype == "__array__":
                elem_type, size = get_array_info(annotation)
                self.emit_header(f"extern {elem_type} {name}[{size}];")
            elif ctype != "__funcptr__":
                self.emit_header(f"extern {ctype} {name};")

        self.emit_header(f"#endif /* {guard} */")

        c_source = "\n".join(self.lines)
        h_source = "\n".join(self.header_lines)

        # Embed source mtime stamp for incremental build tracking
        import os as _os
        _src_mtime = _os.path.getmtime(filepath)
        for _mod_name in self.compiled_files:
            _dep = _os.path.join(self.source_dir, _mod_name + ".mpy")
            if _os.path.exists(_dep):
                _src_mtime = max(_src_mtime, _os.path.getmtime(_dep))
        c_source = f"/* mpy_stamp: {_src_mtime:.6f} */\n" + c_source

        return c_source, h_source, mod_info

    def _emit_export_vtable(self):
        """Emit a vtable struct + get_api() for all @export-decorated functions."""
        self.emit("/* ---- Hot-reload export table ---- */")
        self.emit("typedef struct {")
        self.indent += 1
        for name, ret, args in self._export_funcs:
            arg_str = ", ".join(t for _, t in args) if args else "void"
            self.emit(f"{ret} (*{name})({arg_str});")
        self.indent -= 1
        self.emit("} MpApi;")
        self.emit("")
        self.emit("MpApi* get_api(void) {")
        self.indent += 1
        self.emit("static MpApi _api;")
        for name, _, _ in self._export_funcs:
            self.emit(f"_api.{name} = {name};")
        self.emit("return &_api;")
        self.indent -= 1
        self.emit("}")
        self.emit("")

    def _scan_result_types(self, tree):
        """Walk entire AST to find all Result[T] annotations and register them."""
        for node in ast.walk(tree):
            ann = None
            if isinstance(node, ast.AnnAssign):
                ann = node.annotation
            elif isinstance(node, ast.FunctionDef) and node.returns:
                ann = node.returns
            elif isinstance(node, ast.arg) and node.annotation:
                ann = node.annotation
            if ann is not None and isinstance(ann, ast.Subscript):
                base = ann.value
                if isinstance(base, ast.Name) and base.id == "Result":
                    inner = map_type(ann.slice)
                    mangled = mangle_type(inner)
                    result_name = f"Result_{mangled}"
                    if result_name not in self.result_types:
                        self.result_types[result_name] = inner
                        self.func_ret_types[f"{result_name}_ok"] = result_name
                        self.func_ret_types[f"{result_name}_err"] = result_name

    def _emit_result_types(self):
        """Emit C struct + helpers for each Result[T] type discovered."""
        for result_name, inner in self.result_types.items():
            self.emit(f"typedef struct {{")
            self.indent += 1
            self.emit(f"int _ok;")
            self.emit(f"union {{ {inner} _val; const char* _err; }};")
            self.indent -= 1
            self.emit(f"}} {result_name};")
            self.emit(f"static inline {result_name} {result_name}_ok({inner} v) "
                      f"{{ {result_name} r; r._ok=1; r._val=v; return r; }}")
            self.emit(f"static inline {result_name} {result_name}_err(const char* msg) "
                      f"{{ {result_name} r; r._ok=0; r._err=msg; return r; }}")
            self.emit(f"static inline {inner} {result_name}_unwrap({result_name} r) "
                      f'{{ if (!r._ok) {{ fprintf(stderr, "unwrap: %s\\n", r._err); abort(); }} '
                      f"return r._val; }}")
            self.emit("")

    def _scan_tuple_returns(self, tree):
        """Scan for functions with tuple return types and populate TUPLE_RET_MAP."""
        import type_map as _tm
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.returns:
                if isinstance(node.returns, ast.Tuple):
                    # map_type will register the struct name in TUPLE_RET_MAP
                    map_type(node.returns)

    def _emit_tuple_ret_structs(self):
        """Emit C structs for all tuple return types found during scan."""
        import type_map as _tm
        for key, struct_name in _tm.TUPLE_RET_MAP.items():
            self.emit(f"typedef struct {{")
            self.indent += 1
            for i, ctype in enumerate(key):
                if ctype == "__array__":
                    # Shouldn't normally reach here; arrays handled per-field below
                    self.emit(f"void* v{i};")
                elif "[" in ctype:
                    # e.g. "double[2]" — parse as elem_type[N]
                    bracket = ctype.index("[")
                    elem = ctype[:bracket]
                    rest = ctype[bracket:]  # "[2]" etc
                    self.emit(f"{elem} v{i}{rest};")
                else:
                    self.emit(f"{ctype} v{i};")
            self.indent -= 1
            self.emit(f"}} {struct_name};")
            self.emit("")

    def _scan_typed_lists(self, tree):
        """Walk entire AST to find all typed_list[X] / list[StructType] annotations."""
        nice = {"int64_t": "Int", "double": "Float", "uint8_t": "Byte", "int": "Bool"}
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and node.annotation is not None:
                if isinstance(node.annotation, ast.Subscript):
                    base = node.annotation.value
                    if isinstance(base, ast.Name) and base.id in ("typed_list", "list"):
                        elem_t = get_typed_list_elem(node.annotation)
                        # typed_list[T] always generates; list[T] only for struct types
                        if base.id == "list" and elem_t not in self.structs:
                            continue
                        if elem_t not in self.typed_lists:
                            prefix = nice.get(elem_t, elem_t.replace("*", "Ptr"))
                            self.typed_lists[elem_t] = f"{prefix}List"

    # -------------------------------------------------------------------
    # Trait verification
    # -------------------------------------------------------------------

    def _verify_trait(self, struct_name: str, trait_name: str, tree):
        if trait_name not in self.traits:
            print(f"Warning: trait '{trait_name}' not found for struct '{struct_name}'",
                  file=sys.stderr)
            return

        required = self.traits[trait_name]
        # Find the struct's class node and its methods
        implemented = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == struct_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        implemented.add(item.name)

        # Also check top-level functions named structname_methodname
        cur_mod = self.modules.get(self.current_module)
        if cur_mod:
            for fname in cur_mod.functions:
                if fname.startswith(f"{struct_name}_"):
                    method = fname[len(struct_name) + 1:]
                    implemented.add(method)

        for method_name, ret, margs in required:
            if method_name not in implemented:
                print(f"Error: struct '{struct_name}' missing method '{method_name}' "
                      f"required by trait '{trait_name}'", file=sys.stderr)

    # -------------------------------------------------------------------
    # @compile_time — execute Python at compile time, embed result
    # -------------------------------------------------------------------

    def _emit_compile_time(self, node: ast.FunctionDef, tree):
        """Execute a @compile_time function in Python and embed the result."""
        # Strip decorators so Python doesn't try to evaluate them
        clean_node = copy.deepcopy(node)
        clean_node.decorator_list = []
        func_code = ast.Module(body=[clean_node], type_ignores=[])
        ast.fix_missing_locations(func_code)
        ns = {"__builtins__": __builtins__}
        try:
            exec(compile(func_code, "<compile_time>", "exec"), ns)
            result = ns[node.name]()
        except Exception as e:
            print(f"Error in @compile_time function '{node.name}': {e}",
                  file=sys.stderr)
            return

        # Find any top-level assignment that calls this function and emit it
        for other in ast.iter_child_nodes(tree):
            if isinstance(other, ast.AnnAssign) and isinstance(other.target, ast.Name):
                if isinstance(other.value, ast.Call) and isinstance(other.value.func, ast.Name):
                    if other.value.func.id == node.name:
                        name = other.target.id
                        ctype = map_type(other.annotation)

                        if isinstance(result, list):
                            # Emit as static array
                            if ctype == "__array__":
                                elem_t, size = get_array_info(other.annotation)
                                vals = ", ".join(str(v) for v in result)
                                self.emit(f"const {elem_t} {name}[{len(result)}] = {{{vals}}};")
                            else:
                                vals = ", ".join(str(v) for v in result)
                                self.emit(f"const int64_t {name}[] = {{{vals}}};")
                                self.emit(f"const int64_t {name}_len = {len(result)};")
                            self._compile_time_arrays.add(name)
                        elif isinstance(result, (int, float)):
                            self.emit(f"const {ctype} {name} = {result};")
                        self.emit("")

    # -------------------------------------------------------------------
    # @generic — stamp out specialized versions
    # -------------------------------------------------------------------

    def _emit_generic(self, node: ast.FunctionDef, decs: dict, module_name: str):
        gen_info = decs["generic"]
        type_params = gen_info.get("kwargs", {})

        for param_name, type_list in type_params.items():
            for t in type_list:
                ct = TYPE_MAP.get(t, t)
                suffix = t.replace("*", "ptr")

                # Build a type map for this specialization
                local_type_map = dict(TYPE_MAP)
                local_type_map[param_name] = ct

                # Emit the specialized function
                ret_type = map_type(node.returns, local_type_map)
                args = []
                self.func_args = {}
                self.local_vars = {}

                for arg in node.args.args:
                    atype = map_type(arg.annotation, local_type_map)
                    args.append(f"{atype} {arg.arg}")
                    self.func_args[arg.arg] = atype

                arg_str = ", ".join(args) if args else "void"
                prefix = f"{module_name}_" if module_name != "__main__" else ""
                fname = f"{node.name}_{suffix}"

                self.emit(f"{ret_type} {prefix}{fname}({arg_str}) {{")
                self.indent += 1

                # Compile body with type substitution active
                TYPE_MAP[param_name] = ct
                for stmt in node.body:
                    self.compile_stmt(stmt)
                TYPE_MAP.pop(param_name, None)

                self.indent -= 1
                self.emit("}")
                self.emit("")

                self.func_args = {}
                self.local_vars = {}

    # -------------------------------------------------------------------
    # @platform — conditional compilation
    # -------------------------------------------------------------------

    def _emit_platform_func(self, node: ast.FunctionDef, plat: str, module_name: str):
        plat_map = {
            "windows": "_WIN32",
            "linux": "__linux__",
            "macos": "__APPLE__",
        }
        guard = plat_map.get(plat)
        if guard:
            self.emit(f"#ifdef {guard}")
        self.compile_function(node, module_name)
        if guard:
            self.emit(f"#endif /* {guard} */")
            self.emit("")

    # -------------------------------------------------------------------
    # @unroll — loop unrolling
    # -------------------------------------------------------------------

    def compile_function_with_unroll(self, node: ast.FunctionDef, module_name: str, unroll_info):
        """Compile a function, applying unroll to for-range loops."""
        factor = unroll_info["args"][0] if isinstance(unroll_info, dict) and unroll_info.get("args") else 4

        ret_type = map_type(node.returns)
        args = []
        self.func_args = {}
        self.local_vars = {}

        for arg in node.args.args:
            atype = map_type(arg.annotation)
            const_prefix = ""
            if (atype.endswith("*")
                    and not atype.startswith("const ")
                    and atype != "void*"
                    and arg.arg != "self"
                    and not _ptr_is_written(node.body, arg.arg)):
                const_prefix = "const "
            args.append(f"{const_prefix}{atype} {arg.arg}")
            self.func_args[arg.arg] = atype

        arg_str = ", ".join(args) if args else "void"
        prefix = f"{module_name}_" if module_name != "__main__" else ""
        fname = node.name
        if fname == "main":
            self.emit(f"int main(void) {{")
        else:
            self.emit(f"{ret_type} {prefix}{fname}({arg_str}) {{")

        self.indent += 1
        for stmt in node.body:
            if isinstance(stmt, ast.For):
                self._emit_unrolled_for(stmt, factor)
            else:
                self.compile_stmt(stmt)
        self.indent -= 1
        self.emit("}")
        self.emit("")
        self.func_args = {}
        self.local_vars = {}

    # -------------------------------------------------------------------
    # @parallel — auto-parallelized loops
    # -------------------------------------------------------------------

    def _emit_parallel(self, node: ast.FunctionDef, par_info, module_name: str):
        num_threads = 4
        if isinstance(par_info, dict):
            kw = par_info.get("kwargs", {})
            if "threads" in kw:
                num_threads = kw["threads"]
            elif par_info.get("args"):
                num_threads = par_info["args"][0]

        fname = node.name
        prefix = f"{module_name}_" if module_name != "__main__" else ""
        full_name = f"{prefix}{fname}"

        args = []
        self.func_args = {}
        self.local_vars = {}
        for arg in node.args.args:
            atype = map_type(arg.annotation)
            args.append((arg.arg, atype))
            self.func_args[arg.arg] = atype

        ret_type = map_type(node.returns)

        for_node = None
        pre_stmts = []
        post_stmts = []
        found_for = False
        for stmt in node.body:
            if not found_for and isinstance(stmt, ast.For):
                if (isinstance(stmt.iter, ast.Call) and
                        isinstance(stmt.iter.func, ast.Name) and
                        stmt.iter.func.id == "range"):
                    for_node = stmt
                    found_for = True
                    continue
            if not found_for:
                pre_stmts.append(stmt)
            else:
                post_stmts.append(stmt)

        if for_node is None:
            self.compile_function(node, module_name)
            return

        loop_var = self.compile_expr(for_node.target)
        range_args = for_node.iter.args
        if len(range_args) == 2:
            range_start = self.compile_expr(range_args[0])
            range_end = self.compile_expr(range_args[1])
        elif len(range_args) == 1:
            range_start = "0"
            range_end = self.compile_expr(range_args[0])
        else:
            self.compile_function(node, module_name)
            return

        chunk_name = f"_Mp_{fname}_Chunk"
        self.emit(f"typedef struct {{")
        self.indent += 1
        for aname, atype in args:
            self.emit(f"{atype} {aname};")
        self.emit(f"int64_t _start;")
        self.emit(f"int64_t _end;")
        self.indent -= 1
        self.emit(f"}} {chunk_name};")
        self.emit("")

        self.emit(f"static void* _mp_{fname}_worker(void* _arg) {{")
        self.indent += 1
        self.emit(f"{chunk_name}* _chunk = ({chunk_name}*)_arg;")
        for aname, atype in args:
            self.emit(f"{atype} {aname} = _chunk->{aname};")
        for stmt in pre_stmts:
            self.compile_stmt(stmt)
        self.emit(f"for (int64_t {loop_var} = _chunk->_start; {loop_var} < _chunk->_end; {loop_var}++) {{")
        self.indent += 1
        for stmt in for_node.body:
            self.compile_stmt(stmt)
        self.indent -= 1
        self.emit(f"}}")
        self.emit(f"return NULL;")
        self.indent -= 1
        self.emit(f"}}")
        self.emit("")

        def _const_arg(aname, atype):
            if (atype.endswith("*") and not atype.startswith("const ")
                    and atype != "void*" and aname != "self"
                    and not _ptr_is_written(node.body, aname)):
                return f"const {atype} {aname}"
            return f"{atype} {aname}"
        arg_str = ", ".join(_const_arg(n, t) for n, t in args) if args else "void"
        self.emit(f"{ret_type} {full_name}({arg_str}) {{")
        self.indent += 1
        self.emit(f"int64_t _total = {range_end} - {range_start};")
        self.emit(f"int64_t _nthreads = {num_threads};")
        self.emit(f"if (_total <= 0) return;")
        self.emit(f"if (_nthreads > _total) _nthreads = _total;")
        self.emit(f"int64_t _chunk_size = (_total + _nthreads - 1) / _nthreads;")
        self.emit(f"")
        self.emit(f"{chunk_name} _chunks[{num_threads}];")
        self.emit(f"MpThread _threads[{num_threads}];")
        self.emit(f"int64_t _actual = 0;")
        self.emit(f"")
        self.emit(f"for (int64_t _t = 0; _t < _nthreads; _t++) {{")
        self.indent += 1
        self.emit(f"int64_t _s = {range_start} + _t * _chunk_size;")
        self.emit(f"int64_t _e = _s + _chunk_size;")
        self.emit(f"if (_s >= {range_end}) break;")
        self.emit(f"if (_e > {range_end}) _e = {range_end};")
        for aname, atype in args:
            self.emit(f"_chunks[_t].{aname} = {aname};")
        self.emit(f"_chunks[_t]._start = _s;")
        self.emit(f"_chunks[_t]._end = _e;")
        self.emit(f"_threads[_t] = mp_thread_spawn(_mp_{fname}_worker, &_chunks[_t]);")
        self.emit(f"_actual++;")
        self.indent -= 1
        self.emit(f"}}")
        self.emit(f"")
        self.emit(f"for (int64_t _t = 0; _t < _actual; _t++) {{")
        self.indent += 1
        self.emit(f"mp_thread_join(_threads[_t]);")
        self.indent -= 1
        self.emit(f"}}")
        for stmt in post_stmts:
            self.compile_stmt(stmt)
        self.indent -= 1
        self.emit(f"}}")
        self.emit("")
        self.func_args = {}
        self.local_vars = {}

    # -------------------------------------------------------------------
    # Imports
    # -------------------------------------------------------------------

    # Python stdlib modules we silently skip (they map to C via math.h, stdio.h, etc.)
    _STDLIB_SKIP = frozenset({
        "math", "sys", "os", "os.path", "time", "random", "re",
        "json", "collections", "itertools", "functools", "typing",
        "io", "pathlib", "struct", "array", "ctypes",
        "enum",     # Python enum stdlib; Micropy emits C typedef enum instead
        "micropy",  # stub-only import for IDE type checking; not compiled
    })

    def compile_import(self, node: ast.Import):
        for alias in node.names:
            mod_name = alias.name
            if mod_name in self._STDLIB_SKIP:
                continue
            if mod_name not in self.compiled_files:
                self.compile_dependency(mod_name)
            self.imports.append(mod_name)

    def compile_import_from(self, node: ast.ImportFrom):
        mod_name = node.module
        if mod_name in self._STDLIB_SKIP:
            # Register individual names into from_imports so they resolve at call site
            for alias in node.names:
                local_name = alias.asname if alias.asname else alias.name
                # math functions resolve directly; just skip the module import
            return
        if mod_name not in self.compiled_files:
            self.compile_dependency(mod_name)
        self.imports.append(mod_name)
        for alias in node.names:
            local_name = alias.asname if alias.asname else alias.name
            self.from_imports[local_name] = (mod_name, alias.name)

    def compile_dependency(self, mod_name: str):
        dep_path = os.path.join(self.source_dir, f"{mod_name}.mpy")
        if not os.path.exists(dep_path):
            print(f"Warning: cannot find {dep_path}", file=sys.stderr)
            return
        dep_compiler = Compiler(
            compiled_files=self.compiled_files,
            modules=self.modules,
            source_dir=self.source_dir,
            platform=self.platform,
        )
        c_src, h_src, mod_info = dep_compiler.compile_file(dep_path, mod_name)
        self.modules[mod_name] = mod_info
        self.compiled_files.add(mod_name)
        for sname, sfields in mod_info.structs.items():
            self.structs[sname] = sfields
        for ename, members in mod_info.enums.items():
            self.enums[ename] = members
        # Propagate function return types so call-site codegen can resolve them
        for fname, (ret_type, _args) in mod_info.functions.items():
            self.func_ret_types[fname] = ret_type

        out_dir = self.source_dir or "."
        with open(os.path.join(out_dir, f"{mod_name}.c"), "w") as f:
            f.write(c_src)
        with open(os.path.join(out_dir, f"{mod_name}.h"), "w") as f:
            f.write(h_src)

    def _make_prototype(self, node: ast.FunctionDef, module_name: str) -> str | None:
        """Build a C function prototype string (without trailing semicolon)."""
        from type_map import get_funcptr_info as _gfp
        ret_type = map_type(node.returns)
        args = []
        for arg in node.args.args:
            atype = map_type(arg.annotation)
            if atype == "__funcptr__":
                info = _gfp(arg.annotation)
                # If annotation is a Name alias, resolve via funcptr_alias_infos
                if info is None and isinstance(arg.annotation, ast.Name):
                    info = self.funcptr_alias_infos.get(arg.annotation.id)
                if info:
                    r, fp_args = info
                    fp_arg_str = ", ".join(fp_args) if fp_args else "void"
                    args.append(f"{r} (*{arg.arg})({fp_arg_str})")
                    continue
            const_prefix = ""
            if (atype.endswith("*")
                    and not atype.startswith("const ")
                    and atype != "void*"
                    and arg.arg != "self"
                    and not _ptr_is_written(node.body, arg.arg, self.func_param_types)):
                const_prefix = "const "
            args.append(f"{const_prefix}{atype} {arg.arg}")
        arg_str = ", ".join(args) if args else "void"
        if node.args.vararg is not None:
            arg_str = (arg_str + ", ..." if args else "...")
        prefix = f"{module_name}_" if module_name != "__main__" else ""
        fname = node.name
        decs = self.get_decorators(node)
        qualifiers = []
        attrs = []
        if "inline" in decs:
            qualifiers.append("static inline")
        if "noinline" in decs:
            attrs.append("noinline")
        if "noreturn" in decs:
            attrs.append("noreturn")
        if "cold" in decs or fname in self._cold_funcs:
            attrs.append("cold")
        qual_str = " ".join(qualifiers) + (" " if qualifiers else "")
        attr_str = f" __attribute__(({', '.join(attrs)}))" if attrs else ""
        if fname == "main":
            return "int main(void)"
        return f"{qual_str}{ret_type}{attr_str} {prefix}{fname}({arg_str})"

    # -------------------------------------------------------------------
    # @test — unit test wrapper + runner generation
    # -------------------------------------------------------------------

    def _ensure_test_header(self):
        """Copy micropy_test.h next to the source if missing or stale."""
        out_dir = self.source_dir or "."
        src = os.path.join(_HERE, "micropy_test.h")
        dst = os.path.join(out_dir, "micropy_test.h")
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)

    def _emit_test_wrapper(self, func_name: str):
        """Emit a _mp_run_test_NAME() wrapper with timing and pass/fail reporting."""
        self._ensure_test_header()
        self.emit(f"static void _mp_run_test_{func_name}(void) {{")
        self.indent += 1
        self.emit(f"_mp_test_total++;")
        self.emit(f"_mp_test_failures = 0;")
        self.emit(f'_mp_cprint(_MP_GREEN, "[ RUN      ] {func_name}\\n");')
        self.emit(f"uint64_t _t1 = _mp_time_ns();")
        self.emit(f"{func_name}();")
        self.emit(f"uint64_t _t2 = _mp_time_ns();")
        self.emit(f"char _tbuf[64]; _mp_fmt_time(_t2 - _t1, _tbuf, sizeof(_tbuf));")
        self.emit(f"if (_mp_test_failures == 0) {{")
        self.indent += 1
        self.emit(f'_mp_cprint(_MP_GREEN, "[       OK ] {func_name} %s\\n", _tbuf);')
        self.indent -= 1
        self.emit(f"}} else {{")
        self.indent += 1
        self.emit(f"_mp_test_fail_total++;")
        self.emit(f'_mp_cprint(_MP_RED, "[  FAILED  ] {func_name} (%d failures)\\n", _mp_test_failures);')
        self.indent -= 1
        self.emit(f"}}")
        self.indent -= 1
        self.emit(f"}}")
        self.emit("")

    def _emit_test_main(self):
        """Emit a main() that runs all @test functions and prints a summary."""
        self.emit("int main(void) {")
        self.indent += 1
        self.emit("_mp_time_init();")
        for name in self.test_funcs:
            self.emit(f"_mp_run_test_{name}();")
        self.emit('printf("[==========] %d tests, %d failures\\n", _mp_test_total, _mp_test_fail_total);')
        self.emit("return _mp_test_fail_total ? 1 : 0;")
        self.indent -= 1
        self.emit("}")
