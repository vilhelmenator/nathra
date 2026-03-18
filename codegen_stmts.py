import ast
import copy
import os
import sys

from type_map import map_type, _tuple_field_type, get_array_info, get_typed_list_elem, get_funcptr_info, get_vec_info, get_bitfield_info, TUPLE_RET_MAP


_NARROW_INT_TYPES = frozenset({
    "uint8_t", "int8_t", "uint16_t", "int16_t", "uint32_t", "int32_t",
})
_WIDE_INT_TYPES = frozenset({"int64_t", "int", "uint64_t"})

# Allocation primitives shared with the ownership analysis in compiler.py
_ALLOC_FUNCS = frozenset({"alloc", "alloc_safe", "mp_alloc"})
_FREE_FUNCS  = frozenset({"free",  "mp_free"})

# Scalar/small types that should NOT be lifetime-scoped (stack slot reuse is
# already handled by the C compiler's register allocator for these).
_SMALL_CTYPES = frozenset({
    "int64_t", "int32_t", "uint32_t", "int16_t", "uint16_t",
    "int8_t",  "uint8_t", "double",   "float",   "bool",
    "char",    "void",    "int",      "uint64_t", "size_t",
    "ptrdiff_t", "MpVal",
})

# ── Struct field layout helpers (used by sparsity warning) ──────────────────

_SCALAR_ALIGN_SIZE = {
    "double":    (8, 8), "int64_t":  (8, 8), "uint64_t":  (8, 8),
    "ptrdiff_t": (8, 8), "size_t":   (8, 8), "MpVal":     (8, 8),
    "int32_t":   (4, 4), "uint32_t": (4, 4), "float":     (4, 4), "int": (4, 4),
    "int16_t":   (2, 2), "uint16_t": (2, 2),
    "int8_t":    (1, 1), "uint8_t":  (1, 1), "bool":      (1, 1), "char": (1, 1),
}

def _field_align_size(ctype: str, structs: dict):
    """Return (alignment, size) in bytes for ctype, or None if unknown."""
    if not ctype or ctype in ("__array__", "__funcptr__", "__vec__", "__typed_list__"):
        return None
    if ctype.endswith("*"):
        return (8, 8)
    if ctype in _SCALAR_ALIGN_SIZE:
        return _SCALAR_ALIGN_SIZE[ctype]
    if ctype in structs:
        return _struct_align_size(structs[ctype], structs)
    return None

def _struct_align_size(fields: list, structs: dict):
    """Return (alignment, total_size) for a struct with fields in the given order, or None."""
    offset    = 0
    max_align = 1
    for _fn, ctype in fields:
        info = _field_align_size(ctype, structs)
        if info is None:
            return None
        align, size = info
        max_align = max(max_align, align)
        offset = (offset + align - 1) & ~(align - 1)   # pad to alignment
        offset += size
    if max_align > 1:
        offset = (offset + max_align - 1) & ~(max_align - 1)  # trailing pad
    return (max_align, offset)


def _ptr_is_written(body, param_name: str, func_param_types: dict = None) -> bool:
    """Return True if param_name is ever written through in body.

    A write-through is any assignment whose LHS root is param_name and
    whose immediate LHS is a Subscript or Attribute node, e.g.:
      param[i] = v        (Subscript write)
      param.field = v     (Attribute write)
      param[i] += v       (AugAssign Subscript)

    When func_param_types is provided, also checks whether param_name is
    passed as argument i to a callee whose i-th param is a non-const pointer
    (the callee may mutate through the pointer, e.g. struct method self args).
    """
    def _root(target) -> str:
        while isinstance(target, (ast.Subscript, ast.Attribute)):
            target = target.value
        return target.id if isinstance(target, ast.Name) else ""

    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, (ast.Subscript, ast.Attribute))
                            and _root(target) == param_name):
                        return True
            elif isinstance(node, ast.AugAssign):
                if (isinstance(node.target, (ast.Subscript, ast.Attribute))
                        and _root(node.target) == param_name):
                    return True
            elif isinstance(node, ast.Call) and func_param_types is not None:
                if isinstance(node.func, ast.Attribute):
                    # Method call: param.method(...) — param is the receiver (self).
                    # Look up StructType_method; if its first param (self) is a
                    # non-const pointer, param_name is mutated.
                    if (isinstance(node.func.value, ast.Name)
                            and node.func.value.id == param_name):
                        method = node.func.attr
                        # Search for any StructType_method entry whose self is non-const
                        for key, ptypes in func_param_types.items():
                            if (key.endswith(f"_{method}")
                                    and ptypes
                                    and ptypes[0].endswith("*")
                                    and not ptypes[0].startswith("const ")):
                                return True
                elif isinstance(node.func, ast.Name):
                    # Free-function call: SomeFunc(param, ...) — check by position.
                    callee = node.func.id
                    ptypes = func_param_types.get(callee)
                    if ptypes:
                        for i, call_arg in enumerate(node.args):
                            if (isinstance(call_arg, ast.Name)
                                    and call_arg.id == param_name
                                    and i < len(ptypes)):
                                ptype = ptypes[i]
                                if ptype.endswith("*") and not ptype.startswith("const "):
                                    return True
    return False


def _aliasing_ptr_params(body, ptr_param_names: set) -> set:
    """Return the subset of ptr_param_names that may alias another ptr param.

    A param is marked aliasing if it is ever directly assigned from another
    ptr param (or if another ptr param is assigned from it) anywhere in the
    function body.  Conservative: any Name node from ptr_param_names appearing
    in the RHS of an assignment whose LHS is also in ptr_param_names taints
    both the source and the destination.
    """
    aliased: set = set()
    for stmt in body:
        for node in ast.walk(stmt):
            lhs_name: str = ""
            rhs_node = None
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in ptr_param_names:
                        lhs_name = target.id
                        rhs_node = node.value
            elif isinstance(node, ast.AnnAssign) and node.value:
                if isinstance(node.target, ast.Name) and node.target.id in ptr_param_names:
                    lhs_name = node.target.id
                    rhs_node = node.value
            if lhs_name and rhs_node is not None:
                for rhs in ast.walk(rhs_node):
                    if (isinstance(rhs, ast.Name)
                            and rhs.id in ptr_param_names
                            and rhs.id != lhs_name):
                        aliased.add(lhs_name)
                        aliased.add(rhs.id)
    return aliased


def _is_pure_expr(node) -> bool:
    """Return True if node contains no function calls, subscripts, or attribute accesses.

    Pure expressions are literals, names, and arithmetic/logical/compare
    operations on those — safe to evaluate without side effects so we can
    hoist them into a ternary that the C compiler can convert to cmov.
    """
    for n in ast.walk(node):
        if isinstance(n, (ast.Call, ast.Subscript, ast.Attribute)):
            return False
    return True


class StmtMixin:
    # -------------------------------------------------------------------
    # Enum detection
    # -------------------------------------------------------------------

    def _is_enum_class(self, node: ast.ClassDef) -> bool:
        """A class is an enum if it has plain assignments and NO type annotations."""
        has_assignments = False
        for item in node.body:
            if isinstance(item, ast.Pass):
                continue
            if isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant):
                continue  # docstring
            if isinstance(item, ast.AnnAssign):
                return False  # has type annotations → it's a struct
            if isinstance(item, ast.FunctionDef):
                return False  # has methods → it's a struct
            if isinstance(item, ast.Assign) and len(item.targets) == 1:
                if isinstance(item.targets[0], ast.Name) and isinstance(item.value, ast.Constant):
                    has_assignments = True
                    continue
            return False
        return has_assignments

    # -------------------------------------------------------------------
    # Structs & Enums
    # -------------------------------------------------------------------

    def compile_struct(self, node: ast.ClassDef):
        # Struct-level C attributes from decorators
        decs = self.get_decorators(node)
        is_union = "union" in decs
        struct_keyword = "union" if is_union else "struct"
        struct_attrs = []
        if "packed" in decs:
            struct_attrs.append("packed")
        if "hot" in decs:
            struct_attrs.append("aligned(64)")
        if "align" in decs:
            align_info = decs["align"]
            n = align_info["args"][0] if isinstance(align_info, dict) and align_info.get("args") else 64
            struct_attrs.append(f"aligned({n})")
        attr_str = f" __attribute__(({', '.join(struct_attrs)}))" if struct_attrs else ""

        # Use tagged form so forward declaration and definition agree
        self.emit(f"typedef {struct_keyword} {node.name} {{")
        self.indent += 1
        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fname = item.target.id
                # Bit field: bitfield[T, N]
                bf = get_bitfield_info(item.annotation)
                if bf:
                    ctype, width = bf
                    self.emit(f"{ctype} {fname} : {width};")
                    fields.append((fname, ctype))
                else:
                    ctype = map_type(item.annotation)
                    if ctype == "__array__":
                        elem_type, size = get_array_info(item.annotation)
                        self.emit(f"{elem_type} {fname}[{size}];")
                        fields.append((fname, None))  # arrays not passable as ctor args
                    elif ctype == "__funcptr__":
                        info = get_funcptr_info(item.annotation)
                        # Resolve funcptr type aliases
                        if info is None and isinstance(item.annotation, ast.Name):
                            info = self.funcptr_alias_infos.get(item.annotation.id)
                        if info:
                            ret, fp_args = info
                            fp_arg_str = ", ".join(fp_args) if fp_args else "void"
                            self.emit(f"{ret} (*{fname})({fp_arg_str});")
                        else:
                            self.emit(f"void *{fname};")
                        fields.append((fname, None))  # funcptrs need special ctor handling
                    else:
                        self.emit(f"{ctype} {fname};")
                        fields.append((fname, ctype))
        self.indent -= 1
        self.emit(f"}}{attr_str} {node.name};")
        self.emit("")

        # Struct field sparsity warning — skip packed structs, unions, and
        # structs whose fields include bitfields, arrays, or funcptrs (layout
        # is either intentional or non-trivial to compute).
        if not is_union and "packed" not in decs:
            _warnfields = [(fn, ct) for fn, ct in fields
                           if ct is not None
                           and ct not in ("__array__", "__funcptr__", "__vec__")]
            if len(_warnfields) >= 2:
                _src_info = _struct_align_size(_warnfields, self.structs)
                if _src_info is not None:
                    _, _src_sz = _src_info
                    # Optimal order: largest alignment first, then largest size
                    _opt = sorted(_warnfields,
                                  key=lambda fc: _field_align_size(fc[1], self.structs) or (0, 0),
                                  reverse=True)
                    _opt_info = _struct_align_size(_opt, self.structs)
                    if _opt_info is not None:
                        _, _opt_sz = _opt_info
                        _wasted = _src_sz - _opt_sz
                        if _wasted > 0:
                            import sys
                            _loc = f"{self._current_file or '?'}:{node.lineno}"
                            _sugg = ", ".join(f"{fn}: {ct}" for fn, ct in _opt)
                            print(
                                f"{_loc}: warning: struct '{node.name}' wastes "
                                f"{_wasted} bytes of padding. "
                                f"Suggested field order ({_opt_sz} vs {_src_sz} bytes): "
                                f"{_sugg}",
                                file=sys.stderr,
                            )

        # Emit constructor helper for MSVC compatibility
        # Skip array/funcptr fields (ct==None) — they can't be passed by value
        simple_fields = [(fn, ct) for fn, ct in fields if ct is not None]
        arg_list = ", ".join(f"{ct} {fn}" for fn, ct in simple_fields)
        self.emit(f"static inline {node.name} _mp_make_{node.name}({arg_list or 'void'}) {{")
        self.indent += 1
        self.emit(f"{node.name} _s = {{0}};")
        for fn, ct in simple_fields:
            self.emit(f"_s.{fn} = {fn};")
        self.emit(f"return _s;")
        self.indent -= 1
        self.emit(f"}}")
        self.emit("")

        # Emit class methods as ClassName_method(ClassName* self, ...)
        # __init__ goes first so the factory can follow immediately after it
        methods = [item for item in node.body if isinstance(item, ast.FunctionDef)]
        methods.sort(key=lambda m: (0 if m.name == "__init__" else 1, m.name))

        ptr_annotation = ast.Subscript(
            value=ast.Name(id="ptr", ctx=ast.Load()),
            slice=ast.Name(id=node.name, ctx=ast.Load()),
            ctx=ast.Load())

        # Emit forward declarations so methods can call each other regardless of order
        for item in methods:
            synth = copy.deepcopy(item)
            synth.name = f"{node.name}_{item.name}"
            method_decs = self.get_decorators(item)
            is_static = "staticmethod" in method_decs
            if not is_static:
                if synth.args.args and synth.args.args[0].arg == "self":
                    synth.args.args[0].annotation = copy.deepcopy(ptr_annotation)
                else:
                    fwd_self = ast.arg(arg="self", annotation=copy.deepcopy(ptr_annotation))
                    synth.args.args.insert(0, fwd_self)
            self.compile_function(synth, self.current_module, prototype_only=True)
        self.emit("")

        for item in methods:
            synth = copy.deepcopy(item)
            synth.name = f"{node.name}_{item.name}"
            method_decs = self.get_decorators(item)
            is_static = "staticmethod" in method_decs
            if not is_static:
                if synth.args.args and synth.args.args[0].arg == "self":
                    synth.args.args[0].annotation = copy.deepcopy(ptr_annotation)
                else:
                    self_arg = ast.arg(arg="self", annotation=copy.deepcopy(ptr_annotation))
                    synth.args.args.insert(0, self_arg)
            self.compile_function(synth, self.current_module)

            # After __init__, emit a ClassName_new(...) factory
            if item.name == "__init__":
                factory_args = [(map_type(a.annotation) if a.annotation else "int64_t", a.arg)
                                for a in item.args.args if a.arg != "self"]
                arg_decl = ", ".join(f"{t} {n}" for t, n in factory_args)
                arg_call = ", ".join(n for _, n in factory_args)
                self.emit(f"static inline {node.name} {node.name}_new({arg_decl or 'void'}) {{")
                self.indent += 1
                self.emit(f"{node.name} _self;")
                self.emit(f"{node.name}___init__(&_self{', ' + arg_call if arg_call else ''});")
                self.emit(f"return _self;")
                self.indent -= 1
                self.emit(f"}}")
                self.emit("")

    def compile_enum(self, node: ast.ClassDef):
        members = self.enums[node.name]
        self.emit(f"typedef enum {{")
        self.indent += 1
        for i, (mname, mval) in enumerate(members):
            suffix = "," if i < len(members) - 1 else ""
            if mval is not None:
                self.emit(f"{node.name}_{mname} = {mval}{suffix}")
            else:
                self.emit(f"{node.name}_{mname}{suffix}")
        self.indent -= 1
        self.emit(f"}} {node.name};")
        self.emit("")

    # -------------------------------------------------------------------
    # Functions
    # -------------------------------------------------------------------

    def _scan_and_emit_lambdas(self, stmts):
        """Pre-scan statements for lambda expressions, emit static functions before enclosing function."""
        from type_map import get_funcptr_info
        import ast as _ast

        def walk_stmts(nodes):
            for node in nodes:
                # Look for: name: func[...] = lambda ...: ...
                if isinstance(node, _ast.AnnAssign) and isinstance(node.value, _ast.Lambda):
                    lam = node.value
                    info = get_funcptr_info(node.annotation)
                    if info:
                        ret_type, arg_types = info
                        params = [a.arg for a in lam.args.args]
                        # Pair params with types (pad with int64_t if mismatch)
                        while len(params) < len(arg_types):
                            params.append(f"_arg{len(params)}")
                        while len(arg_types) < len(params):
                            arg_types.append("int64_t")
                        lname = f"_lam_{self._lambda_counter}"
                        self._lambda_counter += 1
                        self._lambda_table[id(lam)] = lname
                        # Emit static function
                        typed_params = list(zip(params, arg_types))
                        param_str = ", ".join(f"{t} {p}" for p, t in typed_params) if typed_params else "void"
                        self.emit(f"static {ret_type} {lname}({param_str}) {{")
                        self.indent += 1
                        # Compile lambda body — set up func_args temporarily
                        saved_func_args = self.func_args.copy()
                        saved_local = self.local_vars.copy()
                        saved_ret = self.current_func_ret_type
                        self.func_args = {p: t for p, t in typed_params}
                        self.local_vars = {p: t for p, t in typed_params}
                        self.current_func_ret_type = ret_type
                        body_expr = self.compile_expr(lam.body)
                        self.emit(f"return {body_expr};")
                        self.func_args = saved_func_args
                        self.local_vars = saved_local
                        self.current_func_ret_type = saved_ret
                        self.indent -= 1
                        self.emit("}")
                        self.emit("")
                # Recurse into compound statements
                for child_attr in ('body', 'orelse', 'handlers', 'finalbody'):
                    child = getattr(node, child_attr, None)
                    if child and isinstance(child, list):
                        walk_stmts(child)

        walk_stmts(stmts)

    # -------------------------------------------------------------------
    # Hot/cold branch splitting
    # -------------------------------------------------------------------

    def _is_cold_stmts(self, stmts) -> bool:
        """True if every statement qualifies as cold: raise, @cold call, or nested cold if."""
        if not stmts:
            return False
        for stmt in stmts:
            if isinstance(stmt, ast.Raise):
                continue
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                name = (call.func.id if isinstance(call.func, ast.Name) else
                        call.func.attr if isinstance(call.func, ast.Attribute) else None)
                if name and name in self._cold_funcs:
                    continue
            if isinstance(stmt, ast.If):
                if (self._is_cold_stmts(stmt.body)
                        and (not stmt.orelse or self._is_cold_stmts(stmt.orelse))):
                    continue
            return False
        return True

    def _cold_free_vars(self, stmts, local_types: dict) -> list:
        """Collect all Name references in stmts that are known locals or parameters."""
        found = set()
        for stmt in stmts:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Name) and n.id in local_types:
                    found.add(n.id)
        return sorted(found)

    def _cold_all_raise(self, stmts) -> bool:
        """True if every exit path of stmts ends in a raise (helper is noreturn)."""
        if not stmts:
            return False
        last = stmts[-1]
        if isinstance(last, ast.Raise):
            return True
        if isinstance(last, ast.If):
            return (self._cold_all_raise(last.body)
                    and self._cold_all_raise(last.orelse or []))
        return False

    def _scan_and_emit_cold_branches(self, node: ast.FunctionDef, module_name: str):
        """Pre-scan function body; extract cold if-arms into static __attribute__((cold)) helpers."""
        self._cold_splits = {}
        if not hasattr(self, '_cold_helper_counter'):
            self._cold_helper_counter = 0

        # Build local type map: parameters + top-level AnnAssign declarations
        local_types: dict = {}
        for arg in node.args.args:
            ctype = map_type(arg.annotation)
            if ctype not in ("__funcptr__", "__array__", "__vec__"):
                local_types[arg.arg] = ctype
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                ctype = map_type(stmt.annotation)
                if ctype not in ("__funcptr__", "__array__", "__vec__"):
                    local_types[stmt.target.id] = ctype

        prefix = f"{module_name}_" if module_name != "__main__" else ""

        for stmt in node.body:
            if not isinstance(stmt, ast.If):
                continue
            for arm_name, arm_stmts in (('body', stmt.body), ('orelse', stmt.orelse)):
                if not arm_stmts:
                    continue
                # Skip elif chains
                if (arm_name == 'orelse'
                        and len(arm_stmts) == 1
                        and isinstance(arm_stmts[0], ast.If)):
                    continue
                if not self._is_cold_stmts(arm_stmts):
                    continue

                free_vars = self._cold_free_vars(arm_stmts, local_types)
                helper_name = f"_ch_{prefix}{node.name}_{self._cold_helper_counter}"
                self._cold_helper_counter += 1

                param_pairs = [(local_types[v], v) for v in free_vars if v in local_types]
                param_str = ", ".join(f"{ct} {vn}" for ct, vn in param_pairs) or "void"
                attrs = "cold, noreturn" if self._cold_all_raise(arm_stmts) else "cold"

                self.emit(f"static void __attribute__(({attrs})) {helper_name}({param_str}) {{")
                self.indent += 1

                # Compile arm body with a temporary scope
                saved = {
                    'func_args': self.func_args.copy(),
                    'local_vars': self.local_vars.copy(),
                    'current_func_ret_type': self.current_func_ret_type,
                    'defer_stack': getattr(self, 'defer_stack', [])[:]
                }
                self.func_args = {vn: ct for ct, vn in param_pairs}
                self.local_vars = {vn: ct for ct, vn in param_pairs}
                self.current_func_ret_type = "void"
                self.defer_stack = []
                for s in arm_stmts:
                    self.compile_stmt(s)
                for k, v in saved.items():
                    setattr(self, k, v)

                self.indent -= 1
                self.emit("}")
                self.emit("")

                self._cold_splits[id(stmt)] = {
                    'arm': arm_name,
                    'name': helper_name,
                    'free_vars': free_vars,
                }
                break  # one arm per if-statement

    # -------------------------------------------------------------------
    # Hot call-site constant specialization
    # -------------------------------------------------------------------

    def _scan_and_emit_specializations(self, node: ast.FunctionDef, module_name: str):
        """For @hot functions: emit specialized callees for constant-arg call sites.

        Threshold:
          ≤ 3 distinct constant combinations per callee → specialize freely (no size limit).
          > 3 distinct combinations              → only if callee body has ≤ 30 statements.
        The biggest wins come from *large* functions where constants eliminate branches
        and unlock vectorization — so there is no hard size cap by default.
        """
        if "hot" not in self.get_decorators(node):
            return
        if not hasattr(self, '_spec_cache'):
            self._spec_cache = {}
        if not hasattr(self, '_call_spec_map'):
            self._call_spec_map = {}
        if not hasattr(self, '_spec_counter'):
            self._spec_counter = 0

        all_func_defs = getattr(self, '_all_func_defs', {})
        prefix = f"{module_name}_" if module_name != "__main__" else ""

        # ---- First pass: collect all constant-arg sites, grouped by callee ----
        # callee_name → list of (call_node, const_args dict, spec_key)
        callee_sites: dict = {}
        for stmt in node.body:
            for n in ast.walk(stmt):
                if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name):
                    continue
                callee_name = n.func.id
                callee_def = all_func_defs.get(callee_name)
                if callee_def is None:
                    continue
                callee_params = callee_def.args.args
                const_args = {}
                for idx, arg in enumerate(n.args):
                    if isinstance(arg, ast.Constant) and idx < len(callee_params):
                        const_args[idx] = (callee_params[idx].arg, arg.value)
                if not const_args:
                    continue
                spec_key = (callee_name,
                            frozenset((pn, pv) for pn, pv in const_args.values()))
                callee_sites.setdefault(callee_name, []).append((n, const_args, spec_key))

        # ---- Second pass: decide and emit ----
        import copy as _copy
        for callee_name, sites in callee_sites.items():
            callee_def = all_func_defs[callee_name]
            distinct_keys = {sk for _, _, sk in sites}
            n_distinct = len(distinct_keys)

            # Size gating: only applies when > 3 distinct constants
            if n_distinct > 3:
                stmt_count = sum(1 for s in callee_def.body
                                 for n in ast.walk(s) if isinstance(n, ast.stmt))
                if stmt_count > 30:
                    continue  # too many variants of a large function → skip

            for call_node, const_args, spec_key in sites:
                if spec_key not in self._spec_cache:
                    spec_name = f"_spec_{prefix}{callee_name}_{self._spec_counter}"
                    self._spec_counter += 1
                    cloned = _copy.deepcopy(callee_def)
                    subs = {pn: pv for pn, pv in const_args.values()}
                    class _Subst(ast.NodeTransformer):
                        def visit_Name(self, nd):
                            if nd.id in subs:
                                return ast.Constant(value=subs[nd.id])
                            return nd
                    cloned = _Subst().visit(cloned)
                    ast.fix_missing_locations(cloned)
                    cloned.args.args = [p for i, p in enumerate(callee_def.args.args)
                                        if i not in const_args]
                    cloned.args.defaults = []
                    cloned.decorator_list = [
                        d for d in cloned.decorator_list
                        if not (isinstance(d, ast.Name) and d.id in ('hot', 'test'))
                    ]
                    cloned.name = spec_name
                    self.emit("// specialization: " + callee_name + " with "
                              + ", ".join(f"{pn}={pv}" for pn, pv in subs.items()))
                    self.compile_function(cloned, module_name)
                    self.emit("")
                    self._spec_cache[spec_key] = (spec_name, const_args)
                else:
                    spec_name, _ = self._spec_cache[spec_key]
                non_const_indices = [i for i in range(len(call_node.args))
                                     if i not in const_args]
                self._call_spec_map[id(call_node)] = (spec_name, non_const_indices)

    def compile_function(self, node: ast.FunctionDef, module_name: str, prototype_only: bool = False):
        if not prototype_only:
            # Pre-scan body for lambda expressions, emit static helper functions before this function
            self._scan_and_emit_lambdas(node.body)
            self._scan_and_emit_cold_branches(node, module_name)
            self._scan_and_emit_specializations(node, module_name)
        ret_type = map_type(node.returns)
        self.current_func_ret_type = ret_type
        args = []
        self.func_args = {}
        self.local_vars = {}
        self.defer_stack = []
        self._array_vars = {}
        self._list_vars = {}
        self._vec_vars = {}

        # Restrict inference: collect ptr params (≥2 required), then check aliasing.
        _all_ptr_params = {
            a.arg for a in node.args.args
            if map_type(a.annotation).endswith("*")
            and map_type(a.annotation) not in ("void*", "const void*")
            and a.arg != "self"
        }
        _restrict_params: set = set()
        if len(_all_ptr_params) >= 2:
            _aliased = _aliasing_ptr_params(node.body, _all_ptr_params)
            _restrict_params = _all_ptr_params - _aliased

        for arg in node.args.args:
            atype = map_type(arg.annotation)
            if atype == "__funcptr__":
                info = get_funcptr_info(arg.annotation)
                # Resolve funcptr type aliases (e.g., SupportFunc = func[...])
                if info is None and isinstance(arg.annotation, ast.Name):
                    info = self.funcptr_alias_infos.get(arg.annotation.id)
                if info:
                    ret, fp_args = info
                    fp_arg_str = ", ".join(fp_args) if fp_args else "void"
                    args.append(f"{ret} (*{arg.arg})({fp_arg_str})")
                    self.func_args[arg.arg] = "__funcptr__"
                    if hasattr(self, '_funcptr_rettypes'):
                        self._funcptr_rettypes[arg.arg] = ret
                    continue
            # Read-only inference: ptr param never written through → const T*
            # Applied to both prototype and definition so they stay in sync.
            const_prefix = ""
            if (atype.endswith("*")
                    and not atype.startswith("const ")
                    and atype != "void*"
                    and arg.arg != "self"
                    and not _ptr_is_written(node.body, arg.arg, self.func_param_types)):
                const_prefix = "const "
            restrict_kw = " restrict" if arg.arg in _restrict_params else ""
            args.append(f"{const_prefix}{atype}{restrict_kw} {arg.arg}")
            self.func_args[arg.arg] = atype  # store without const for type inference

        arg_str = ", ".join(args) if args else "void"
        if node.args.vararg is not None:
            arg_str = (arg_str + ", ..." if args else "...")
        prefix = f"{module_name}_" if module_name != "__main__" else ""
        fname = node.name

        # Record parameter types for use at call sites (auto-deref pointer args)
        _param_ctypes = [map_type(a.annotation) for a in node.args.args]
        self.func_param_types[f"{prefix}{fname}"] = _param_ctypes

        # C qualifiers and attributes from decorators
        decs = self.get_decorators(node)
        qualifiers = []
        attrs = []
        if "export" in decs:
            # Exported symbols must be globally visible — no static
            pass
        elif "inline" in decs:
            qualifiers.append("static inline")
        if "noinline" in decs:
            attrs.append("noinline")
        if "noreturn" in decs:
            attrs.append("noreturn")
        if "cold" in decs or fname in self._cold_funcs:
            attrs.append("cold")
        if "hot" in decs:
            attrs.append("hot")
        self._in_simd_func   = "simd"   in decs
        self._in_stream_func = "stream" in decs
        qual_str = " ".join(qualifiers) + (" " if qualifiers else "")
        attr_str = f" __attribute__(({', '.join(attrs)}))" if attrs else ""

        if fname == "main":
            if prototype_only:
                return
            self.emit(f"int main(void) {{")
        else:
            sig = f"{qual_str}{ret_type}{attr_str} {prefix}{fname}({arg_str})"
            if prototype_only:
                self.emit(f"{sig};")
                return
            self.emit(f"{sig} {{")

        self.indent += 1
        # Pre-classify alloc'd locals so compile_ann_assign can auto-defer free()
        self._auto_free_vars = {
            var for var, status in self._escape_classify(node).items()
            if status == "local_only"
        }
        # Alloca substitution for explicitly-freed locals: vars classified as
        # "consumed" (programmer wrote free(var)) that are ONLY ever passed to
        # free() and have a compile-time constant ≤4 KB alloc size.  These are
        # semantically identical to auto-free vars for stack-substitution
        # purposes — the explicit free() call will be suppressed at emit time.
        _escape_status = self._escape_classify(node)
        _consumed_vars = {v for v, s in _escape_status.items() if s == "consumed"}
        self._alloca_consumed_vars: set = set()
        for _stmt in node.body:
            if (isinstance(_stmt, ast.AnnAssign)
                    and isinstance(_stmt.target, ast.Name)
                    and _stmt.value
                    and isinstance(_stmt.value, ast.Call)
                    and isinstance(_stmt.value.func, ast.Name)
                    and _stmt.value.func.id in _ALLOC_FUNCS
                    and len(_stmt.value.args) == 1
                    and isinstance(_stmt.value.args[0], ast.Constant)
                    and isinstance(_stmt.value.args[0].value, int)
                    and 0 < _stmt.value.args[0].value <= 4096
                    and _stmt.target.id in _consumed_vars):
                _vname = _stmt.target.id
                _free_only = True
                for _n in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                    if (isinstance(_n, ast.Call)
                            and isinstance(_n.func, ast.Name)
                            and _n.func.id not in _FREE_FUNCS):
                        for _a in _n.args:
                            if isinstance(_a, ast.Name) and _a.id == _vname:
                                _free_only = False
                                break
                    if not _free_only:
                        break
                if _free_only:
                    self._alloca_consumed_vars.add(_vname)
        # Allocation merging: collect top-level constant-size local-only allocs.
        # If ≥ 2 found, emit one stack buffer and carve named offsets from it.
        _merge_candidates = []
        for _stmt in node.body:
            if (isinstance(_stmt, ast.AnnAssign)
                    and isinstance(_stmt.target, ast.Name)
                    and _stmt.value
                    and isinstance(_stmt.value, ast.Call)
                    and isinstance(_stmt.value.func, ast.Name)
                    and _stmt.value.func.id in _ALLOC_FUNCS
                    and len(_stmt.value.args) == 1
                    and isinstance(_stmt.value.args[0], ast.Constant)
                    and isinstance(_stmt.value.args[0].value, int)
                    and 0 < _stmt.value.args[0].value <= 4096
                    and _stmt.target.id in self._auto_free_vars):
                _merge_candidates.append((
                    _stmt.target.id,
                    map_type(_stmt.annotation),
                    _stmt.value.args[0].value,
                ))
        if len(_merge_candidates) >= 2:
            _total = 0
            self._merged_alloc_offsets = {}
            for _vname, _vctype, _vsize in _merge_candidates:
                _total = (_total + 7) & ~7  # 8-byte align each slot
                self._merged_alloc_offsets[_vname] = (_vctype, _total)
                _total += _vsize
            _total = (_total + 7) & ~7
            self._merged_buf_name = f"_mrgd_{id(node) & 0xFFFF:04x}"
            self.emit(f"char {self._merged_buf_name}[{_total}];")
        else:
            self._merged_alloc_offsets = {}
            self._merged_buf_name = ""
        # Arena allocation batching: group same-arena top-level calls into one bump.
        # arena_alloc(a, N) × ≥2 same-arena → single mp_arena_alloc + offset slices.
        # arena_list_new(a) × ≥2 same-arena → single bump + inline MpList init.
        _arena_alloc_groups = {}   # arena_name → [(varname, ctype, size_int)]
        _arena_list_groups  = {}   # arena_name → [varname]
        for _stmt in node.body:
            if (isinstance(_stmt, ast.AnnAssign)
                    and isinstance(_stmt.target, ast.Name)
                    and _stmt.value
                    and isinstance(_stmt.value, ast.Call)
                    and isinstance(_stmt.value.func, ast.Name)):
                _fn   = _stmt.value.func.id
                _vn   = _stmt.target.id
                _vct  = map_type(_stmt.annotation)
                if (_fn == "arena_alloc"
                        and len(_stmt.value.args) == 2
                        and isinstance(_stmt.value.args[0], ast.Name)
                        and isinstance(_stmt.value.args[1], ast.Constant)
                        and isinstance(_stmt.value.args[1].value, int)):
                    _an = _stmt.value.args[0].id
                    _sz = _stmt.value.args[1].value
                    _arena_alloc_groups.setdefault(_an, []).append((_vn, _vct, _sz))
                elif (_fn == "arena_list_new"
                        and len(_stmt.value.args) == 1
                        and isinstance(_stmt.value.args[0], ast.Name)):
                    _an = _stmt.value.args[0].id
                    _arena_list_groups.setdefault(_an, []).append(_vn)
        self._arena_batched_vars = {}
        self._arena_batch_meta   = {}
        for _an, _entries in _arena_alloc_groups.items():
            if len(_entries) < 2 or _an in self._arena_batch_meta:
                continue
            _bvar  = f"_ab_{_an}"
            _total = 0
            _offs  = {}
            for _vn, _vct, _vsz in _entries:
                _total = (_total + 7) & ~7
                _offs[_vn] = _total
                _total += _vsz
            _total = (_total + 7) & ~7
            self._arena_batch_meta[_an] = {
                "kind": "alloc", "base_var": _bvar,
                "total": _total, "emitted": False,
            }
            for _vn, _vct, _vsz in _entries:
                self._arena_batched_vars[_vn] = {
                    "kind": "alloc", "arena": _an,
                    "ctype": _vct, "offset": _offs[_vn],
                }
        for _an, _names in _arena_list_groups.items():
            if len(_names) < 2 or _an in self._arena_batch_meta:
                continue
            _bvar  = f"_ab_{_an}"
            _svar  = f"_aslot_{_an}"
            self._arena_batch_meta[_an] = {
                "kind": "list_new", "base_var": _bvar, "slot_var": _svar,
                "count": len(_names), "emitted": False,
            }
            for _i, _vn in enumerate(_names):
                self._arena_batched_vars[_vn] = {
                    "kind": "list_new", "arena": _an, "index": _i,
                }
        # Stack variable lifetime narrowing:
        # Wrap large struct-value locals that are never address-taken in { } scopes
        # so the C compiler knows the stack slot ends and can be reused.
        # Only applies to user-defined struct values (not pointers, not primitives).
        _lv_decls = {}  # varname → stmt_index
        for _i, _stmt in enumerate(node.body):
            if (isinstance(_stmt, ast.AnnAssign)
                    and isinstance(_stmt.target, ast.Name)):
                _vn  = _stmt.target.id
                _vct = map_type(_stmt.annotation)
                # Candidate: a user struct value — in self.structs, not a pointer
                if (_vct in self.structs
                        and not _vct.endswith("*")
                        and _vct not in _SMALL_CTYPES):
                    _lv_decls[_vn] = _i
        # Remove address-taken vars: ref(var) anywhere in body
        _addr_taken = set()
        for _stmt in node.body:
            for _nd in ast.walk(_stmt):
                if (isinstance(_nd, ast.Call)
                        and isinstance(_nd.func, ast.Name)
                        and _nd.func.id == "ref"
                        and _nd.args
                        and isinstance(_nd.args[0], ast.Name)):
                    _addr_taken.add(_nd.args[0].id)
        # Find last-use index for each candidate, then filter out partial overlaps.
        # Two lifetimes [d1,l1] and [d2,l2] partially overlap when they intersect
        # but neither fully contains the other — this would produce non-nested { }
        # that the C compiler rejects.  Only wrap variables whose lifetimes are
        # either fully disjoint from, or fully contained within, every other candidate.
        _cands = {}  # varname → (decl_idx, last_use_idx)
        for _vn, _di in _lv_decls.items():
            if _vn in _addr_taken:
                continue
            _last = _di
            for _i, _stmt in enumerate(node.body):
                if _i < _di:
                    continue
                for _nd in ast.walk(_stmt):
                    if isinstance(_nd, ast.Name) and _nd.id == _vn:
                        _last = _i
                        break
            _cands[_vn] = (_di, _last)
        # Build last-use map for ALL locals so we can detect scope-escape.
        # A variable declared inside a proposed scope that is used outside it
        # would go out of scope too early — that wrapping must be suppressed.
        _all_local_decls = {}  # varname → decl_idx (all AnnAssign, not just structs)
        for _i, _stmt in enumerate(node.body):
            if isinstance(_stmt, ast.AnnAssign) and isinstance(_stmt.target, ast.Name):
                _all_local_decls[_stmt.target.id] = _i
        _all_last_use = {}
        for _ovn, _odi in _all_local_decls.items():
            _olast = _odi
            for _i, _stmt in enumerate(node.body):
                if _i < _odi:
                    continue
                for _nd in ast.walk(_stmt):
                    if isinstance(_nd, ast.Name) and _nd.id == _ovn:
                        _olast = _i
                        break
            _all_last_use[_ovn] = _olast
        # Exclude any candidate that partially overlaps another candidate
        _excl = set()
        _clist = list(_cands.items())
        for _ia, (_vna, (_d1, _l1)) in enumerate(_clist):
            for _ib, (_vnb, (_d2, _l2)) in enumerate(_clist):
                if _ia >= _ib:
                    continue
                _overlaps     = _d1 <= _l2 and _d2 <= _l1
                _a_contains_b = _d1 <= _d2 and _l2 <= _l1
                _b_contains_a = _d2 <= _d1 and _l1 <= _l2
                if _overlaps and not _a_contains_b and not _b_contains_a:
                    _excl.add(_vna)
                    _excl.add(_vnb)
        # Exclude any candidate whose scope would trap another local variable:
        # if local X is declared inside [_di, _last] but used after _last,
        # closing the scope at _last would make X inaccessible.
        for _vn, (_di, _last) in _cands.items():
            if _vn in _excl:
                continue
            for _ovn, _odi in _all_local_decls.items():
                if _ovn == _vn:
                    continue
                if _di <= _odi <= _last and _all_last_use.get(_ovn, _odi) > _last:
                    _excl.add(_vn)
                    break
        _scope_open  = {}  # stmt_idx → [varname]  — emit "{" before this stmt
        _scope_close = {}  # stmt_idx → [varname]  — emit "}" after this stmt
        for _vn, (_di, _last) in _cands.items():
            if _vn in _excl:
                continue
            _scope_open.setdefault(_di, []).append(_vn)
            _scope_close.setdefault(_last, []).append(_vn)
        # Prewarm @compile_time static arrays referenced in this function body
        if self._compile_time_arrays:
            _prewarmed = set()
            for _stmt in node.body:
                for _n in ast.walk(_stmt):
                    if (isinstance(_n, ast.Name)
                            and _n.id in self._compile_time_arrays
                            and _n.id not in _prewarmed):
                        self.emit(f"MP_PREFETCH(&{_n.id}[0], 0, 1);")
                        _prewarmed.add(_n.id)
        for _i, stmt in enumerate(node.body):
            # Open { for struct-value locals declared at this statement
            for _sv in _scope_open.get(_i, []):
                self.emit("{")
                self.indent += 1
            self.compile_stmt(stmt)
            # Close } in reverse-open order (last opened, first closed)
            _closers = sorted(_scope_close.get(_i, []),
                               key=lambda v: _lv_decls.get(v, 0), reverse=True)
            for _sv in _closers:
                self.indent -= 1
                self.emit("}")

        # Emit deferred calls at end of function (reverse order)
        if self.defer_stack:
            self.emit("/* deferred cleanup */")
            for call in reversed(self.defer_stack):
                self.emit(f"{call};")

        self.indent -= 1
        self.emit("}")
        self.emit("")
        self.func_args = {}
        self.local_vars = {}
        self.defer_stack = []
        self._array_vars = {}
        self._list_vars = {}
        self._vec_vars = {}
        self._auto_free_vars = set()
        self._str_literal_vars = set()
        self._merged_alloc_offsets = {}
        self._merged_buf_name = ""
        self._arena_batched_vars = {}
        self._arena_batch_meta = {}
        self._in_simd_func   = False
        self._in_stream_func = False
        self._stream_loop_active = False

    # -------------------------------------------------------------------
    # Statements
    # -------------------------------------------------------------------

    def compile_stmt(self, node):
        if hasattr(node, 'lineno'):
            self._current_line = node.lineno
            if self._current_file and self.emit_line_directives:
                # Emit #line directive so C compiler errors point to .mpy source
                self.lines.append(f'#line {node.lineno} "{self._current_file}"')
        if isinstance(node, ast.AnnAssign):
            self.compile_ann_assign(node)
        elif isinstance(node, ast.Assign):
            self.compile_assign(node)
        elif isinstance(node, ast.AugAssign):
            self.compile_aug_assign(node)
        elif isinstance(node, ast.Return):
            self.compile_return(node)
        elif isinstance(node, ast.If):
            self.compile_if(node)
        elif isinstance(node, ast.While):
            self.compile_while(node)
        elif isinstance(node, ast.For):
            self.compile_for(node)
        elif isinstance(node, ast.Expr):
            # free(var) where var was alloca-substituted — suppress the call
            if (isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in _FREE_FUNCS
                    and len(node.value.args) == 1
                    and isinstance(node.value.args[0], ast.Name)
                    and node.value.args[0].id in getattr(self, '_alloca_consumed_vars', set())):
                return
            # c_code() inline C passthrough
            if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                if node.value.func.id == "c_code":
                    if node.value.args and isinstance(node.value.args[0], ast.Constant):
                        for line in node.value.args[0].value.strip().split("\n"):
                            self.emit(line.strip())
                        return
                # defer func(args) — register for cleanup
                if node.value.func.id == "defer":
                    if node.value.args and isinstance(node.value.args[0], ast.Call):
                        inner = self.compile_expr(node.value.args[0])
                        if inner != "((void)0)" and hasattr(self, 'defer_stack'):
                            self.defer_stack.append(inner)
                            self.emit(f"/* defer: {inner} */")
                        return
            # defer as a bare name calling a function: defer(list_free(nums))
            # already handled above. Also handle: defer(expr)
            expr = self.compile_expr(node.value)
            self.emit(f"{expr};")
        elif isinstance(node, ast.Assert):
            self.compile_assert(node)
        elif isinstance(node, ast.Raise):
            self.compile_raise(node)
        elif isinstance(node, ast.Break):
            self.emit("break;")
        elif isinstance(node, ast.Continue):
            self.emit("continue;")
        elif isinstance(node, ast.Pass):
            self.emit("/* pass */")
        elif isinstance(node, ast.With):
            self.compile_with(node)
        elif hasattr(ast, "Match") and isinstance(node, ast.Match):
            self.compile_match(node)
        else:
            lineno = getattr(node, 'lineno', '?')
            self.emit(f"/* TODO: unsupported statement '{type(node).__name__}' at line {lineno} */")

    def _dest_type(self, target) -> str:
        """Return the C type of an assignment target, or '' if unknown."""
        if isinstance(target, ast.Name):
            return self.local_vars.get(target.id) or self.mutable_globals.get(target.id, "")
        if isinstance(target, ast.Attribute):
            obj_type = self.infer_type(target.value)
            base = obj_type.rstrip("*").strip()
            for fn, ft in self.structs.get(base, []):
                if fn == target.attr:
                    return ft
        if isinstance(target, ast.Subscript):
            if isinstance(target.value, ast.Name):
                info = self._array_vars.get(target.value.id)
                if info:
                    return info[0]
        return ""

    @staticmethod
    def _coerce(val_expr: str, src_type: str, dest_type: str) -> str:
        """Insert a C cast when assigning a wide int to a narrow int type."""
        if dest_type in _NARROW_INT_TYPES and src_type not in _NARROW_INT_TYPES:
            return f"({dest_type})({val_expr})"
        return val_expr

    def compile_ann_assign(self, node: ast.AnnAssign):
        name = self.compile_expr(node.target)
        annotation = node.annotation
        ctype = map_type(annotation)

        if ctype == "__funcptr__":
            info = get_funcptr_info(annotation)
            if info:
                ret, fp_args = info
                fp_arg_str = ", ".join(fp_args) if fp_args else "void"
                self.local_vars[name] = "__funcptr__"
                if hasattr(self, '_funcptr_rettypes'):
                    self._funcptr_rettypes[name] = ret
                if node.value:
                    val = self.compile_expr(node.value)
                    self.emit(f"{ret} (*{name})({fp_arg_str}) = {val};")
                else:
                    self.emit(f"{ret} (*{name})({fp_arg_str}) = NULL;")
            return

        if ctype == "__array__":
            elem_type, size = get_array_info(annotation)
            # @soa expansion: array[SoAStruct, N] → one flat array per field
            if elem_type in self.soa_structs:
                _soa_fields = [(fn, ft) for fn, ft in self.structs.get(elem_type, [])
                               if ft and ft not in ("__array__", "__funcptr__", "__vec__")]
                for _fn, _ft in _soa_fields:
                    self.emit(f"{_ft} {name}_{_fn}[{size}];")
                self._soa_vars[name] = (elem_type, str(size), _soa_fields)
                return
            self._array_vars[name] = (elem_type, str(size))
            if node.value:
                # Check if this is a compile_time call (already emitted by _emit_compile_time)
                if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                    called = node.value.func.id
                    if called in self._compile_time_funcs:
                        return
                val = self.compile_expr(node.value)
                self.emit(f"{elem_type} {name}[{size}] = {val};")
            else:
                self.emit(f"{elem_type} {name}[{size}] = {{0}};")
            return

        if ctype == "__vec__":
            info = get_vec_info(annotation)
            if info:
                elem_ctype, count, vec_bytes = info
                vec_ctype = f"{elem_ctype} __attribute__((vector_size({vec_bytes})))"
                self.local_vars[name] = vec_ctype
                self._vec_vars[name] = (elem_ctype, count)
                if node.value:
                    val = self.compile_expr(node.value)
                    self.emit(f"{vec_ctype} {name} = {val};")
                else:
                    self.emit(f"{vec_ctype} {name};")
            return

        if ctype == "__typed_list__":
            elem_t = get_typed_list_elem(annotation)
            list_name = self.typed_lists.get(elem_t, "MpList")
            ctype = f"{list_name}*"
            self.local_vars[name] = ctype
            self._list_vars[name] = elem_t
            if node.value:
                val = self.compile_expr(node.value)
                self.emit(f"{ctype} {name} = {val};")
            else:
                self.emit(f"{ctype} {name} = NULL;")
            return

        self.local_vars[name] = ctype

        # thread_local[T] inside a function requires static storage duration in C
        if ctype.startswith("MP_TLS "):
            if node.value:
                val = self.compile_expr(node.value)
                self.emit(f"static {ctype} {name} = {val};")
            else:
                self.emit(f"static {ctype} {name};")
            return

        # static[T] — static local variable (persists across calls, shared by all threads)
        if ctype.startswith("__static__ "):
            real_ctype = ctype[len("__static__ "):]
            self.local_vars[name] = real_ctype
            if node.value:
                val = self.compile_expr(node.value)
                self.emit(f"static {real_ctype} {name} = {val};")
            else:
                self.emit(f"static {real_ctype} {name};")
            return

        if node.value:
            # Literal string optimization: s: str = "hello" → stack MpStr, no malloc
            if (ctype == "MpStr*"
                    and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                s = node.value.value
                escaped = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                self.emit(f'MpStr _lit_{name} = {{.data=(char*)"{escaped}",.len={len(s)}}};')
                self.emit(f"MpStr* {name} = &_lit_{name};")
                self._str_literal_vars.add(name)
                return
            # Arena allocation batching — coalesce same-arena bump allocs
            if (name in self._arena_batched_vars
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in ("arena_alloc", "arena_list_new")):
                _bi   = self._arena_batched_vars[name]
                _an   = _bi["arena"]
                _meta = self._arena_batch_meta[_an]
                if not _meta["emitted"]:
                    _meta["emitted"] = True
                    _bv = _meta["base_var"]
                    if _meta["kind"] == "alloc":
                        self.emit(f"char* {_bv} = (char*)mp_arena_alloc({_an}, {_meta['total']});")
                    else:
                        _sv = _meta["slot_var"]
                        self.emit(f"const int64_t {_sv} = (int64_t)"
                                  f"(((sizeof(MpList)+7)&~7) + ((sizeof(MpVal)*8+7)&~7));")
                        self.emit(f"char* {_bv} = (char*)mp_arena_alloc({_an}, {_meta['count']} * {_sv});")
                _bv = _meta["base_var"]
                if _bi["kind"] == "alloc":
                    self.emit(f"{_bi['ctype']} {name} = ({_bi['ctype']})({_bv} + {_bi['offset']});")
                else:
                    _i  = _bi["index"]
                    _sv = _meta["slot_var"]
                    self.emit(f"MpList* {name} = (MpList*)({_bv} + {_i} * {_sv});")
                    self.emit(f"{name}->cap = 8; {name}->len = 0;")
                    self.emit(f"{name}->data = (MpVal*)({_bv} + {_i} * {_sv}"
                              f" + (int64_t)((sizeof(MpList)+7)&~7));")
                return
            # Escape-analysis alloc optimizations (local-only pointer, no escape)
            if ((name in self._auto_free_vars
                    or name in getattr(self, '_alloca_consumed_vars', set()))
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in _ALLOC_FUNCS
                    and len(node.value.args) == 1):
                _arg = node.value.args[0]
                # Item 3: allocation merging — part of a merged stack buffer
                if name in self._merged_alloc_offsets:
                    _vctype, _off = self._merged_alloc_offsets[name]
                    self.emit(f"{_vctype} {name} = ({_vctype})({self._merged_buf_name} + {_off});")
                    return
                # Item 1: alloca for compile-time constant size ≤ 4 KB
                if (isinstance(_arg, ast.Constant)
                        and isinstance(_arg.value, int)
                        and 0 < _arg.value <= 4096):
                    self.emit(f"{ctype} {name} = alloca({_arg.value});")
                    return
                # Item 2: conditional alloca/malloc for runtime-bounded size
                _sz = f"_sz_{name}"
                _compiled_sz = self.compile_expr(_arg)
                self.emit(f"int64_t {_sz} = {_compiled_sz};")
                self.emit(f"{ctype} {name} = {_sz} <= 4096 ? ({ctype})alloca({_sz}) : ({ctype})malloc({_sz});")
                self.defer_stack.append(f"if ({_sz} > 4096) free({name})")
                return
            val = self.compile_expr(node.value)
            val = self._coerce(val, self.infer_type(node.value), ctype)
            self.emit(f"{ctype} {name} = {val};")
            # Scope-based auto-free: non-alloc producer calls (e.g. malloc wrappers)
            if (name in self._auto_free_vars
                    and isinstance(node.value, ast.Call)
                    and isinstance(node.value.func, ast.Name)
                    and node.value.func.id in _ALLOC_FUNCS):
                self.defer_stack.append(f"free({name})")
        else:
            self.emit(f"{ctype} {name};")

    def compile_assign(self, node: ast.Assign):
        # @stream non-temporal store: arr[idx] = val → __builtin_nontemporal_store
        if (getattr(self, '_stream_loop_active', False)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Subscript)):
            _tgt = node.targets[0]
            _arr = self.compile_expr(_tgt.value)
            _idx = self.compile_expr(_tgt.slice)
            _val = self.compile_expr(node.value)
            self.emit(f"__builtin_nontemporal_store(({_val}), &({_arr})[{_idx}]);")
            return
        # Tuple unpacking: a, b = func()  or  a, b = (x, y)
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Tuple):
            elts = node.targets[0].elts
            # RHS is a tuple literal — emit individual assignments
            if isinstance(node.value, ast.Tuple) and len(node.value.elts) == len(elts):
                # Evaluate all RHS values first into temps, then assign to LHS.
                # This correctly handles swaps like a, b = b, a.
                temps = []
                for i, val_node in enumerate(node.value.elts):
                    t = self.infer_type(val_node)
                    tmp = f"_mp_swap_{i}_{id(node) & 0xFFFF:04x}"
                    val = self.compile_expr(val_node)
                    self.emit(f"{t} {tmp} = {val};")
                    temps.append((tmp, t))
                for tgt_node, (tmp, t) in zip(elts, temps):
                    tgt = self.compile_expr(tgt_node)
                    if isinstance(tgt_node, ast.Name):
                        already_declared = (tgt in self.local_vars or tgt in self.func_args
                                            or tgt in self._array_vars)
                        if already_declared:
                            self.emit(f"{tgt} = {tmp};")
                        else:
                            self.local_vars[tgt] = t
                            self.emit(f"{t} {tgt} = {tmp};")
                    else:
                        # Subscript or attribute target — always an assignment
                        self.emit(f"{tgt} = {tmp};")
                return
            # RHS is a struct-returning call — unpack by field position
            ret_type = self.infer_type(node.value)
            base = ret_type.rstrip("*").strip()
            val = self.compile_expr(node.value)
            if base in self.structs:
                tmp = f"_mp_unpack_{base}"
                self.emit(f"{base} {tmp} = {val};")
                for i, tgt_node in enumerate(elts):
                    tgt = self.compile_expr(tgt_node)
                    if i < len(self.structs[base]):
                        fname, ftype = self.structs[base][i]
                        already_declared = tgt in self.local_vars or tgt in self.func_args
                        if already_declared:
                            self.emit(f"{tgt} = {tmp}.{fname};")
                        else:
                            self.local_vars[tgt] = ftype
                            self.emit(f"{ftype} {tgt} = {tmp}.{fname};")
            elif ret_type.startswith("_TupleRet_"):
                # Tuple return struct — unpack by field position
                # Find the field key from TUPLE_RET_MAP
                _fkey = None
                for _k, _v in TUPLE_RET_MAP.items():
                    if _v == ret_type:
                        _fkey = _k
                        break
                tmp = f"_mp_unpack"
                self.emit(f"{ret_type} {tmp} = {val};")
                if _fkey:
                    for i, tgt_node in enumerate(elts):
                        if i >= len(_fkey):
                            break
                        tgt = self.compile_expr(tgt_node)
                        _ft = _fkey[i]
                        already_declared = (tgt in self.local_vars or tgt in self.func_args
                                            or tgt in self._array_vars)
                        if "[" in _ft:
                            # Array field: only declare if not already in scope
                            bracket = _ft.index("[")
                            _elem = _ft[:bracket]
                            _size_str = _ft[bracket:]  # "[N]"
                            _size_n = _size_str.strip("[]")
                            if not already_declared:
                                self.emit(f"{_elem} {tgt}{_size_str};")
                                self._array_vars[tgt] = (_elem, _size_n)
                            self.emit(f"memcpy({tgt}, {tmp}.v{i}, {_size_n} * sizeof({_elem}));")
                        else:
                            if already_declared:
                                self.emit(f"{tgt} = {tmp}.v{i};")
                            else:
                                self.local_vars[tgt] = _ft
                                self.emit(f"{_ft} {tgt} = {tmp}.v{i};")
            else:
                self.emit(f"/* unpack */ __auto_type _mp_unpack = {val};")
            return
        val_node = node.value
        for target in node.targets:
            if isinstance(target, ast.Subscript):
                # @soa: whole-element write is not supported
                if (isinstance(target.value, ast.Name)
                        and target.value.id in self._soa_vars):
                    import sys
                    _arr = target.value.id
                    print(f"{self._current_file or '?'}:{getattr(node, 'lineno', '?')}: error: "
                          f"cannot assign whole element to @soa array '{_arr}' "
                          f"— use '{_arr}[i].field = val'", file=sys.stderr)
                    continue
                # Generated typed list: XList_set, no boxing
                if isinstance(target.value, ast.Name):
                    _et = self._list_vars.get(target.value.id)
                    if _et and _et in self.typed_lists:
                        _lname = self.typed_lists[_et]
                        lst = self.compile_expr(target.value)
                        idx = self.compile_expr(target.slice)
                        v = self.compile_expr(val_node)
                        self.emit(f"{_lname}_set({lst}, {idx}, {v});")
                        continue
                # MpList* → mp_list_set with auto-boxing
                if self.infer_type(target.value) == "MpList*":
                    lst = self.compile_expr(target.value)
                    idx = self.compile_expr(target.slice)
                    v = self.compile_expr(val_node)
                    vt = self.infer_type(val_node)
                    if vt == "double":   boxed = f"mp_val_float({v})"
                    elif vt == "MpStr*": boxed = f"mp_val_str({v})"
                    else:                boxed = f"mp_val_int((int64_t)({v}))"
                    self.emit(f"mp_list_set({lst}, {idx}, {boxed});")
                    continue
            # Array literal assigned to an existing array variable: emit element-by-element
            if isinstance(val_node, ast.List) and isinstance(target, ast.Name):
                arr_info = self._array_vars.get(target.id)
                if arr_info:
                    tgt = target.id
                    for i, elt in enumerate(val_node.elts):
                        elt_val = self.compile_expr(elt)
                        self.emit(f"{tgt}[{i}] = {elt_val};")
                    continue
            val = self.compile_expr(val_node)
            tgt = self.compile_expr(target)
            val = self._coerce(val, self.infer_type(val_node), self._dest_type(target))
            self.emit(f"{tgt} = {val};")

    def compile_aug_assign(self, node: ast.AugAssign):
        tgt_type = self.infer_type(node.target)
        tgt_base = tgt_type.rstrip("*").strip()
        # Struct operator overload: expand a += b  →  a = a.__iadd__(b) → a = a + b
        if tgt_base in self.structs:
            _iop_map = {
                ast.Add: "__add__", ast.Sub: "__sub__", ast.Mult: "__mul__",
                ast.Div: "__truediv__", ast.Mod: "__mod__",
            }
            _op_name = _iop_map.get(type(node.op))
            _method = f"{tgt_base}_{_op_name}" if _op_name else None
            if _method and _method in self.func_ret_types:
                tgt = self.compile_expr(node.target)
                rhs = self.compile_expr(node.value)
                if tgt_type.endswith("*"):
                    self_arg = tgt
                else:
                    self_arg = f"&({tgt})"
                self.emit(f"{tgt} = {_method}({self_arg}, {rhs});")
                return
        tgt = self.compile_expr(node.target)
        val = self.compile_expr(node.value)
        op = self.compile_op(node.op)
        self.emit(f"{tgt} {op}= {val};")

    def compile_return(self, node: ast.Return):
        if node.value:
            val = self.compile_expr(node.value)
            if isinstance(node.value, ast.Tuple):
                ret_struct = self._current_ret_type()
                # Check if any field in the tuple struct is an array (needs memcpy)
                _tkey = TUPLE_RET_MAP.get(tuple(
                    _tuple_field_type(e_ann) if hasattr(e_ann, 'elts') else "int64_t"
                    for e_ann in []  # placeholder
                ))
                # Build field info from TUPLE_RET_MAP reverse lookup
                _field_key = None
                for _k, _v in TUPLE_RET_MAP.items():
                    if _v == ret_struct:
                        _field_key = _k
                        break
                has_array_field = _field_key and any("[" in ft for ft in _field_key)
                if has_array_field and _field_key:
                    # Emit field-by-field with memcpy for array fields
                    self.emit(f"{ret_struct} _tret = {{0}};")
                    for _fi, (_ft, _fnode) in enumerate(zip(_field_key, node.value.elts)):
                        _fval = self.compile_expr(_fnode)
                        if "[" in _ft:
                            bracket = _ft.index("[")
                            _size_str = _ft[bracket:]  # "[2]"
                            _elem = _ft[:bracket]
                            _size_n = _size_str.strip("[]")
                            self.emit(f"memcpy(_tret.v{_fi}, {_fval}, {_size_n} * sizeof({_elem}));")
                        else:
                            self.emit(f"_tret.v{_fi} = {_fval};")
                    if hasattr(self, 'defer_stack') and self.defer_stack:
                        for call in reversed(self.defer_stack):
                            self.emit(f"{call};")
                    self.emit(f"return _tret;")
                else:
                    elts = [self.compile_expr(e) for e in node.value.elts]
                    val = "{" + ", ".join(elts) + "}"
                    if hasattr(self, 'defer_stack') and self.defer_stack:
                        self.emit(f"/* deferred cleanup (early return) */")
                        for call in reversed(self.defer_stack):
                            self.emit(f"{call};")
                    self.emit(f"return ({ret_struct}){val};")
            else:
                if hasattr(self, 'defer_stack') and self.defer_stack:
                    # Capture return value before running cleanup
                    self.emit(f"{self.current_func_ret_type} _ret = {val};")
                    self.emit(f"/* deferred cleanup (early return) */")
                    for call in reversed(self.defer_stack):
                        self.emit(f"{call};")
                    self.emit(f"return _ret;")
                else:
                    self.emit(f"return {val};")
        else:
            if hasattr(self, 'defer_stack') and self.defer_stack:
                self.emit(f"/* deferred cleanup (early return) */")
                for call in reversed(self.defer_stack):
                    self.emit(f"{call};")
            self.emit("return;")

    def _current_ret_type(self) -> str:
        return self.current_func_ret_type

    def compile_if(self, node: ast.If):
        # Hot/cold splitting: arm was extracted → emit a call to the static cold helper
        _split = getattr(self, '_cold_splits', {}).get(id(node))
        if _split:
            _cond = self.compile_expr(node.test)
            _call_args = ', '.join(_split['free_vars'])
            _call = f"{_split['name']}({_call_args})"
            if _split['arm'] == 'body':
                self.emit(f"if (MP_UNLIKELY({_cond})) {{")
                self.indent += 1
                self.emit(f"{_call};")
                self.indent -= 1
                if node.orelse:
                    self.emit("} else {")
                    self.indent += 1
                    for s in node.orelse:
                        self.compile_stmt(s)
                    self.indent -= 1
                self.emit("}")
            else:  # cold arm is the else
                self.emit(f"if ({_cond}) {{")
                self.indent += 1
                for s in node.body:
                    self.compile_stmt(s)
                self.indent -= 1
                self.emit("} else {")
                self.indent += 1
                self.emit(f"{_call};")
                self.indent -= 1
                self.emit("}")
            return

        # Branch-free select: if cond: x = a \n else: x = b with pure a, b
        # → x = (cond) ? (a) : (b)  — lets the C compiler emit cmov
        if (len(node.body) == 1
                and len(node.orelse) == 1
                and isinstance(node.body[0], ast.Assign)
                and isinstance(node.orelse[0], ast.Assign)
                and len(node.body[0].targets) == 1
                and len(node.orelse[0].targets) == 1
                and isinstance(node.body[0].targets[0], ast.Name)
                and isinstance(node.orelse[0].targets[0], ast.Name)
                and node.body[0].targets[0].id == node.orelse[0].targets[0].id
                and _is_pure_expr(node.body[0].value)
                and _is_pure_expr(node.orelse[0].value)
                and _is_pure_expr(node.test)):
            _lhs = self.compile_expr(node.body[0].targets[0])
            _cond = self.compile_expr(node.test)
            _val_a = self.compile_expr(node.body[0].value)
            _val_b = self.compile_expr(node.orelse[0].value)
            self.emit(f"{_lhs} = (({_cond}) ? ({_val_a}) : ({_val_b}));")
            return

        cond = self.compile_expr(node.test)
        # __bool__ dispatch: if a struct has a __bool__ method, call it
        test_type = self.infer_type(node.test)
        test_base = test_type.rstrip("*").strip()
        if test_base in self.structs and f"{test_base}___bool__" in self.func_ret_types:
            deref = "->" if test_type.endswith("*") else "."
            obj = self.compile_expr(node.test)
            if test_type.endswith("*"):
                cond = f"{test_base}___bool__({obj})"
            else:
                cond = f"{test_base}___bool__(&({obj}))"
        # Guard pattern: if cond: raise/abort — the error branch is cold
        _is_guard = (
            not node.orelse
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Raise)
        )
        if _is_guard:
            self.emit(f"if (MP_UNLIKELY({cond})) {{")
        else:
            self.emit(f"if ({cond}) {{")
        self.indent += 1
        for stmt in node.body:
            self.compile_stmt(stmt)
        self.indent -= 1
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                self.emit(f"}} else ")
                self.compile_if(node.orelse[0])
                return
            else:
                self.emit("} else {")
                self.indent += 1
                for stmt in node.orelse:
                    self.compile_stmt(stmt)
                self.indent -= 1
        self.emit("}")

    def compile_while(self, node: ast.While):
        cond = self.compile_expr(node.test)
        test_type = self.infer_type(node.test)
        test_base = test_type.rstrip("*").strip()
        if test_base in self.structs and f"{test_base}___bool__" in self.func_ret_types:
            if test_type.endswith("*"):
                cond = f"{test_base}___bool__({self.compile_expr(node.test)})"
            else:
                cond = f"{test_base}___bool__(&({self.compile_expr(node.test)}))"
        self.emit(f"while ({cond}) {{")
        self.indent += 1
        # Linked-list / tree traversal prefetch:
        # Pattern: while node is not None: ... node = node.field
        # Emit MP_PREFETCH(node->field->field) at the top of each iteration.
        _ll_var = None
        _ll_field = None
        if (isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1
                and isinstance(node.test.ops[0], ast.IsNot)
                and len(node.test.comparators) == 1
                and isinstance(node.test.comparators[0], ast.Constant)
                and node.test.comparators[0].value is None
                and isinstance(node.test.left, ast.Name)):
            _lv = node.test.left.id
            for _bstmt in node.body:
                if (isinstance(_bstmt, ast.Assign)
                        and len(_bstmt.targets) == 1
                        and isinstance(_bstmt.targets[0], ast.Name)
                        and _bstmt.targets[0].id == _lv
                        and isinstance(_bstmt.value, ast.Attribute)
                        and isinstance(_bstmt.value.value, ast.Name)
                        and _bstmt.value.value.id == _lv):
                    _ll_var   = _lv
                    _ll_field = _bstmt.value.attr
                    break
        if _ll_var is not None:
            self.emit(f"if ({_ll_var}->{_ll_field}) "
                      f"MP_PREFETCH({_ll_var}->{_ll_field}->{_ll_field}, 0, 1);")
        for stmt in node.body:
            self.compile_stmt(stmt)
        self.indent -= 1
        self.emit("}")

    def compile_assert(self, node: ast.Assert):
        cond = self.compile_expr(node.test)
        if node.msg:
            msg = self.compile_expr(node.msg)
            self.emit(f'if (!({cond})) {{ fprintf(stderr, "AssertionError: %s\\n  at {self._current_file}:{node.lineno}\\n", {msg}); abort(); }}')
        else:
            # Stringify the condition for the error message
            try:
                cond_src = ast.unparse(node.test)
            except Exception:
                cond_src = "assertion"
            cond_src = cond_src.replace('"', '\\"')
            self.emit(f'if (!({cond})) {{ fprintf(stderr, "AssertionError: {cond_src}\\n  at {self._current_file}:{node.lineno}\\n"); abort(); }}')

    def compile_raise(self, node: ast.Raise):
        ret = self.current_func_ret_type
        if node.exc:
            msg = self.compile_expr(node.exc)
            if ret.startswith("Result_") and ret in self.result_types:
                self.emit(f"return {ret}_err({msg});")
            else:
                # Fallback: panic
                self.emit(f'fprintf(stderr, "Error: %s\\n  at {self._current_file}:{node.lineno}\\n", {msg}); abort();')
        else:
            # bare raise — re-raise last error (only valid in Result functions)
            self.emit(f'fprintf(stderr, "raise with no argument\\n"); abort();')

    def _infer_cleanup(self, open_func: str):
        """Infer cleanup function from open/create function name."""
        if open_func == "open":
            return "file_close"
        for suffix, close_suffix in [("_open", "_close"), ("_new", "_free"),
                                      ("_create", "_destroy"), ("_init", "_deinit")]:
            if open_func.endswith(suffix):
                return open_func[:-len(suffix)] + close_suffix
        return None

    def compile_with(self, node: ast.With):
        """with expr as var: body  →  scoped block with inferred cleanup."""
        for item in node.items:
            ctx = item.context_expr
            var = item.optional_vars

            enter_expr = self.compile_expr(ctx)

            # Infer cleanup function from call name
            cleanup_fn = None
            if isinstance(ctx, ast.Call) and isinstance(ctx.func, ast.Name):
                cleanup_fn = self._infer_cleanup(ctx.func.id)

            self.emit("{")
            self.indent += 1

            varname = None
            if var and isinstance(var, ast.Name):
                varname = var.id
                ret_type = self.infer_call_type(ctx) if isinstance(ctx, ast.Call) else None
                if ret_type and ret_type != "void":
                    self.emit(f"{ret_type} {varname} = {enter_expr};")
                    self.local_vars[varname] = ret_type
                    if ret_type.endswith("]"):
                        pass  # array type, skip _array_vars tracking
                else:
                    self.emit(f"__auto_type {varname} = {enter_expr};")
                    self.local_vars[varname] = "__auto_type"
            else:
                self.emit(f"{enter_expr};")

            for stmt in node.body:
                self.compile_stmt(stmt)

            if cleanup_fn:
                arg_name = varname if varname else "_ctx"
                cleanup_node = ast.Call(
                    func=ast.Name(id=cleanup_fn, ctx=ast.Load()),
                    args=[ast.Name(id=arg_name, ctx=ast.Load())],
                    keywords=[],
                )
                cleanup_code = self.compile_expr(cleanup_node)
                self.emit(f"{cleanup_code};")

            self.indent -= 1
            self.emit("}")

    def _emit_simd_pragma(self):
        if getattr(self, '_in_simd_func', False):
            self.emit("#pragma GCC ivdep")
            self.emit("#pragma clang loop vectorize(enable)")

    def _for_iter_info(self, src_node):
        """Return (kind, name, elem_type, bound_expr) for an array/list source, or None."""
        if not isinstance(src_node, ast.Name):
            return None
        name = src_node.id
        if name in self._array_vars:
            elem_type, size = self._array_vars[name]
            return ("array", name, elem_type, str(size))
        if name in self._list_vars:
            elem_type = self._list_vars[name]
            return ("list", name, elem_type, f"{name}->len")
        return None

    def _for_elem(self, kind, name, elem_type, idx):
        if kind == "array":
            return f"{name}[{idx}]"
        return f"{name}->data[{idx}]"

    def compile_for(self, node: ast.For):
        # enumerate: for i, v in enumerate(arr):
        if (isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "enumerate"):
            if not (isinstance(node.target, ast.Tuple) and len(node.target.elts) == 2):
                self.emit("/* ERROR: enumerate() requires (idx, val) target */")
                return
            enum_args = node.iter.args
            if len(enum_args) != 1:
                self.emit("/* ERROR: enumerate() takes exactly 1 argument */")
                return
            info = self._for_iter_info(enum_args[0])
            if info is None:
                self.emit("/* ERROR: enumerate() source must be a known array or list */")
                return
            kind, src, elem_type, bound = info
            idx_var = self.compile_expr(node.target.elts[0])
            elem_var = self.compile_expr(node.target.elts[1])
            self.emit(f"for (int64_t {idx_var} = 0; {idx_var} < {bound}; {idx_var}++) {{")
            self.indent += 1
            self.emit(f"{elem_type} {elem_var} = {self._for_elem(kind, src, elem_type, idx_var)};")
            for stmt in node.body:
                self.compile_stmt(stmt)
            self.indent -= 1
            self.emit("}")
            return

        # zip: for a, b in zip(arr1, arr2):
        if (isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "zip"):
            zip_args = node.iter.args
            if not (isinstance(node.target, ast.Tuple)
                    and len(node.target.elts) == len(zip_args)
                    and len(zip_args) >= 2):
                self.emit("/* ERROR: zip() target count must match argument count (>=2) */")
                return
            sources = []
            for arg in zip_args:
                info = self._for_iter_info(arg)
                if info is None:
                    self.emit("/* ERROR: zip() source must be a known array or list */")
                    return
                sources.append(info)
            idx = "_zip_i"
            bound = sources[0][3]
            self.emit(f"for (int64_t {idx} = 0; {idx} < {bound}; {idx}++) {{")
            self.indent += 1
            for i, (kind, src, elem_type, _) in enumerate(sources):
                elem_var = self.compile_expr(node.target.elts[i])
                self.emit(f"{elem_type} {elem_var} = {self._for_elem(kind, src, elem_type, idx)};")
            for stmt in node.body:
                self.compile_stmt(stmt)
            self.indent -= 1
            self.emit("}")
            return

        target = self.compile_expr(node.target)
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
            if node.iter.func.id == "range":
                args = node.iter.args
                if len(args) == 1:
                    stop = self.compile_expr(args[0])
                    self._emit_simd_pragma()
                    # Trip-count hint: known small bound → unroll pragma
                    if (isinstance(args[0], ast.Constant)
                            and isinstance(args[0].value, int)
                            and 2 <= args[0].value <= 8):
                        self.emit(f"#pragma GCC unroll {args[0].value}")
                    self.emit(f"for (int64_t {target} = 0; {target} < {stop}; {target}++) {{")
                elif len(args) == 2:
                    start = self.compile_expr(args[0])
                    stop = self.compile_expr(args[1])
                    self._emit_simd_pragma()
                    self.emit(f"for (int64_t {target} = {start}; {target} < {stop}; {target}++) {{")
                elif len(args) == 3:
                    start = self.compile_expr(args[0])
                    stop = self.compile_expr(args[1])
                    step_node = args[2]
                    step = self.compile_expr(step_node)
                    # Detect negative step at compile time
                    _neg = (isinstance(step_node, ast.UnaryOp) and isinstance(step_node.op, ast.USub)) or \
                           (isinstance(step_node, ast.Constant) and step_node.value < 0)
                    cmp = ">" if _neg else "<"
                    self._emit_simd_pragma()
                    self.emit(f"for (int64_t {target} = {start}; {target} {cmp} {stop}; {target} += {step}) {{")
                else:
                    self.emit(f"/* ERROR: unsupported range() */")
                    return

                # Detect arrays subscripted by the loop variable — emit prefetch
                _target_id = node.target.id if isinstance(node.target, ast.Name) else None
                _prefetch_arrs = []
                if _target_id:
                    for _stmt in node.body:
                        for _n in ast.walk(_stmt):
                            if (isinstance(_n, ast.Subscript)
                                    and isinstance(_n.slice, ast.Name)
                                    and _n.slice.id == _target_id
                                    and isinstance(_n.value, ast.Name)
                                    and _n.value.id not in _prefetch_arrs):
                                _prefetch_arrs.append(_n.value.id)
                _prefetch_arrs = _prefetch_arrs[:2]  # cap at 2 streams

                self.indent += 1
                if _prefetch_arrs:
                    for _arr in _prefetch_arrs:
                        if _arr in self._array_vars:
                            try:
                                if int(self._array_vars[_arr][1]) <= 8:
                                    continue
                            except (ValueError, TypeError):
                                pass
                        self.emit(f"MP_PREFETCH(&{_arr}[{_target_id} + 8], 0, 1);")
                # @stream: subscript writes inside this loop become non-temporal stores
                if self._in_stream_func:
                    self._stream_loop_active = True
                for stmt in node.body:
                    self.compile_stmt(stmt)
                if self._in_stream_func:
                    self._stream_loop_active = False
                self.indent -= 1
                self.emit("}")
                # Flush non-temporal write buffer after streaming loop
                if self._in_stream_func:
                    self.emit("#if defined(__x86_64__) || defined(__i386__)")
                    self.emit("__builtin_ia32_sfence();")
                    self.emit("#endif")
                return

        # Array/typed_list iteration: for x in arr:
        iter_name = None
        if isinstance(node.iter, ast.Name):
            iter_name = node.iter.id

        if iter_name and iter_name in self._array_vars:
            elem_type, size = self._array_vars[iter_name]
            idx = f"_fi_{iter_name}"
            self._emit_simd_pragma()
            self.emit(f"for (int64_t {idx} = 0; {idx} < {size}; {idx}++) {{")
            self.indent += 1
            self.emit(f"{elem_type} {target} = {iter_name}[{idx}];")
            for stmt in node.body:
                self.compile_stmt(stmt)
            self.indent -= 1
            self.emit("}")
            return

        if iter_name and iter_name in self._list_vars:
            elem_type = self._list_vars[iter_name]
            idx = f"_fi_{iter_name}"
            self.emit(f"for (int64_t {idx} = 0; {idx} < {iter_name}->len; {idx}++) {{")
            self.indent += 1
            self.emit(f"{elem_type} {target} = {iter_name}->data[{idx}];")
            for stmt in node.body:
                self.compile_stmt(stmt)
            self.indent -= 1
            self.emit("}")
            return

        self.emit(f"/* TODO: unsupported for loop */")

    def _emit_unrolled_for(self, node: ast.For, factor: int):
        target = self.compile_expr(node.target)
        if not (isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"):
            self.compile_for(node)
            return

        args = node.iter.args
        if len(args) == 2:
            start = self.compile_expr(args[0])
            stop = self.compile_expr(args[1])
        elif len(args) == 1:
            start = "0"
            stop = self.compile_expr(args[0])
        else:
            self.compile_for(node)
            return

        # Detect arrays subscripted by the loop variable — prefetch them ahead
        _arrays_to_prefetch = []
        for _stmt in node.body:
            for _n in ast.walk(_stmt):
                if (isinstance(_n, ast.Subscript) and
                        isinstance(_n.slice, ast.Name) and _n.slice.id == target and
                        isinstance(_n.value, ast.Name) and
                        _n.value.id not in _arrays_to_prefetch):
                    _arrays_to_prefetch.append(_n.value.id)
        # Cap at 2 arrays to avoid evicting useful lines from cache
        _arrays_to_prefetch = _arrays_to_prefetch[:2]
        # Distance: 2 cache lines worth of elements (128 bytes / element size).
        # Default to 16 (covers 128 B for 8-byte types, 64 B for 4-byte types).
        _prefetch_dist = max(factor * 4, 16)

        # Unrolled main loop
        self.emit(f"/* unrolled x{factor} */")
        self.emit(f"for (int64_t {target} = {start}; {target} + {factor - 1} < {stop}; {target} += {factor}) {{")
        self.indent += 1
        if _arrays_to_prefetch:
            for _arr in _arrays_to_prefetch:
                if _arr in self._array_vars:
                    try:
                        if int(self._array_vars[_arr][1]) <= _prefetch_dist:
                            continue
                    except (ValueError, TypeError):
                        pass
                self.emit(f"MP_PREFETCH(&{_arr}[{target} + {_prefetch_dist}], 0, 1);")
        for offset in range(factor):
            self.emit(f"/* iteration +{offset} */")
            self.emit(f"{{")
            self.indent += 1
            self.emit(f"int64_t {target}_u = {target} + {offset};")
            for stmt in node.body:
                # Replace references to the loop variable with the offset version
                code = self.compile_stmt_to_str(stmt, target, f"{target}_u")
                if code:
                    self.emit(code)
                else:
                    self.compile_stmt(stmt)
            self.indent -= 1
            self.emit(f"}}")
        self.indent -= 1
        self.emit("}")

        # Remainder loop
        self.emit(f"for (int64_t {target} = (({stop} - {start}) / {factor}) * {factor} + {start}; "
                  f"{target} < {stop}; {target}++) {{")
        self.indent += 1
        for stmt in node.body:
            self.compile_stmt(stmt)
        self.indent -= 1
        self.emit("}")

    # -------------------------------------------------------------------
    # Match statement
    # -------------------------------------------------------------------

    def _arm_is_cold(self, case) -> bool:
        """True if this match arm is a cold path (single raise or call to @cold func)."""
        body = case.body
        if len(body) != 1:
            return False
        stmt = body[0]
        if isinstance(stmt, ast.Raise):
            return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if isinstance(call.func, ast.Name):
                return call.func.id in self._cold_funcs
            if isinstance(call.func, ast.Attribute):
                return call.func.attr in self._cold_funcs
        return False

    def _pattern_is_int_const(self, pattern) -> bool:
        """True if pattern can be expressed as a C switch case label."""
        if isinstance(pattern, ast.MatchValue):
            val = pattern.value
            if isinstance(val, ast.Constant) and isinstance(val.value, int):
                return True
            # Enum member access: GJKStatus.VALID
            if isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name):
                return val.value.id in self.enums
            return False
        if isinstance(pattern, ast.MatchOr):
            return all(self._pattern_is_int_const(p) for p in pattern.patterns)
        # Wildcard _ → default:
        if isinstance(pattern, ast.MatchAs) and pattern.pattern is None and pattern.name is None:
            return True
        return False

    def _match_can_use_switch(self, cases: list) -> bool:
        return all(
            case.guard is None and self._pattern_is_int_const(case.pattern)
            for case in cases
        )

    def _pattern_to_cond(self, subject: str, pattern) -> str | None:
        """Return a C condition string, or None for wildcard/capture (→ else)."""
        if isinstance(pattern, ast.MatchAs):
            return None  # wildcard _ or named capture x
        if isinstance(pattern, ast.MatchValue):
            val = pattern.value
            if isinstance(val, ast.Constant):
                if isinstance(val.value, str):
                    return f'strcmp({subject}, {repr(val.value)}) == 0'
                return f"{subject} == {val.value}"
            # Enum member or other named constant
            return f"{subject} == {self.compile_expr(val)}"
        if isinstance(pattern, ast.MatchOr):
            parts = [self._pattern_to_cond(subject, p) for p in pattern.patterns]
            return " || ".join(f"({p})" for p in parts if p is not None)
        return None

    def compile_match(self, node: ast.Match):
        subject = self.compile_expr(node.subject)
        if self._match_can_use_switch(node.cases):
            self._compile_match_switch(subject, node.cases)
        else:
            self._compile_match_ifelse(subject, node.cases)

    def _compile_match_switch(self, subject: str, cases: list):
        self.emit(f"switch ({subject}) {{")
        self.indent += 1
        for case in cases:
            pattern = case.pattern
            if isinstance(pattern, ast.MatchAs) and pattern.pattern is None and pattern.name is None:
                self.emit("default: {")
            elif isinstance(pattern, ast.MatchValue):
                label = self.compile_expr(pattern.value)
                self.emit(f"case {label}: {{")
            elif isinstance(pattern, ast.MatchOr):
                labels = " ".join(f"case {self.compile_expr(p.value)}:" for p in pattern.patterns)
                self.emit(f"{labels} {{")
            self.indent += 1
            for stmt in case.body:
                self.compile_stmt(stmt)
            self.emit("break;")
            self.indent -= 1
            self.emit("}")
        self.indent -= 1
        self.emit("}")

    def _compile_match_ifelse(self, subject: str, cases: list):
        # Reorder: cold arms (single raise / @cold call) go last, before any wildcard
        def _is_unconditional(c):
            p = c.pattern
            return isinstance(p, ast.MatchAs) and c.guard is None
        _unconditional = [c for c in cases if _is_unconditional(c)]
        _conditional   = [c for c in cases if not _is_unconditional(c)]
        _cold_arms     = [c for c in _conditional if self._arm_is_cold(c)]
        _warm_arms     = [c for c in _conditional if not self._arm_is_cold(c)]
        cases = _warm_arms + _cold_arms + _unconditional

        # Hoist capture variables so they're available in guards and bodies
        hoisted: set = set()
        for case in cases:
            p = case.pattern
            if isinstance(p, ast.MatchAs) and p.name and p.name not in hoisted:
                self.emit(f"__typeof__({subject}) {p.name} = {subject};")
                hoisted.add(p.name)

        for i, case in enumerate(cases):
            pattern = case.pattern
            cond = self._pattern_to_cond(subject, pattern)

            if cond is None and case.guard is not None:
                # named capture with guard: use the guard as the condition
                cond = self.compile_expr(case.guard)
                guard_suffix = ""
            else:
                guard_suffix = f" && ({self.compile_expr(case.guard)})" if case.guard else ""

            if cond is None:
                # unconditional wildcard → else (or bare body if first)
                if i == 0:
                    for stmt in case.body:
                        self.compile_stmt(stmt)
                    return
                self.emit("} else {")
            elif i == 0:
                self.emit(f"if ({cond}{guard_suffix}) {{")
            else:
                self.emit(f"}} else if ({cond}{guard_suffix}) {{")

            self.indent += 1
            for stmt in case.body:
                self.compile_stmt(stmt)
            self.indent -= 1

        self.emit("}")

    def compile_stmt_to_str(self, node, old_var, new_var):
        """Try to compile a statement with variable substitution. Returns None if too complex."""
        # Simple case: expression statement with subscript using loop var
        if isinstance(node, ast.Assign) or isinstance(node, ast.AugAssign) or isinstance(node, ast.Expr):
            # Quick and dirty: compile normally, then substitute
            saved = self.lines
            self.lines = []
            saved_indent = self.indent
            self.indent = 0
            self.compile_stmt(node)
            result = "\n".join(self.lines).strip()
            self.lines = saved
            self.indent = saved_indent

            # Only substitute the variable when it appears as an index
            # This is simple but effective for common patterns like data[i]
            if f"[{old_var}]" in result:
                return result.replace(f"[{old_var}]", f"[{new_var}]")
        return None
