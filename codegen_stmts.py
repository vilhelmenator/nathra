import ast
import copy
import os
import sys

from type_map import map_type, _tuple_field_type, get_array_info, get_typed_list_elem, get_funcptr_info, get_vec_info, get_bitfield_info, TUPLE_RET_MAP


_NARROW_INT_TYPES = frozenset({
    "uint8_t", "int8_t", "uint16_t", "int16_t", "uint32_t", "int32_t",
})
_WIDE_INT_TYPES = frozenset({"int64_t", "int", "uint64_t"})


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

    def compile_function(self, node: ast.FunctionDef, module_name: str, prototype_only: bool = False):
        if not prototype_only:
            # Pre-scan body for lambda expressions, emit static helper functions before this function
            self._scan_and_emit_lambdas(node.body)
        ret_type = map_type(node.returns)
        self.current_func_ret_type = ret_type
        args = []
        self.func_args = {}
        self.local_vars = {}
        self.defer_stack = []
        self._array_vars = {}
        self._list_vars = {}
        self._vec_vars = {}

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
            args.append(f"{atype} {arg.arg}")
            self.func_args[arg.arg] = atype

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
        if "cold" in decs:
            attrs.append("cold")
        if "hot" in decs:
            attrs.append("hot")
        self._in_simd_func = "simd" in decs
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
        for stmt in node.body:
            self.compile_stmt(stmt)

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
        self._in_simd_func = False

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
                        if hasattr(self, 'defer_stack'):
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
            val = self.compile_expr(node.value)
            val = self._coerce(val, self.infer_type(node.value), ctype)
            self.emit(f"{ctype} {name} = {val};")
        else:
            self.emit(f"{ctype} {name};")

    def compile_assign(self, node: ast.Assign):
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
                    already_declared = (tgt in self.local_vars or tgt in self.func_args
                                        or tgt in self._array_vars)
                    if already_declared:
                        self.emit(f"{tgt} = {tmp};")
                    else:
                        self.local_vars[tgt] = t
                        self.emit(f"{t} {tgt} = {tmp};")
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

                self.indent += 1
                for stmt in node.body:
                    self.compile_stmt(stmt)
                self.indent -= 1
                self.emit("}")
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

        # Unrolled main loop
        self.emit(f"/* unrolled x{factor} */")
        self.emit(f"for (int64_t {target} = {start}; {target} + {factor - 1} < {stop}; {target} += {factor}) {{")
        self.indent += 1
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

    def _pattern_is_int_const(self, pattern) -> bool:
        """True if pattern can be expressed as a C switch case label."""
        if isinstance(pattern, ast.MatchValue):
            return isinstance(pattern.value, ast.Constant) and isinstance(pattern.value.value, int)
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
                self.emit(f"case {pattern.value.value}: {{")
            elif isinstance(pattern, ast.MatchOr):
                labels = " ".join(f"case {p.value.value}:" for p in pattern.patterns)
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
