import ast
import sys

from type_map import TYPE_MAP, mangle_type


class ExprMixin:
    # -------------------------------------------------------------------
    # Expressions
    # -------------------------------------------------------------------

    def compile_expr(self, node) -> str:
        if isinstance(node, ast.Constant):
            if node.value is None:
                return "NULL"
            if isinstance(node.value, bool):
                return "1" if node.value else "0"
            if isinstance(node.value, str):
                escaped = node.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                return f'"{escaped}"'
            if isinstance(node.value, float):
                return repr(node.value)
            return str(node.value)

        if isinstance(node, ast.Name):
            name = node.id
            if name in self.from_imports:
                mod, func = self.from_imports[name]
                return f"{mod}_{func}"
            if name == "True":
                return "1"
            if name == "False":
                return "0"
            if name == "None":
                return "NULL"
            return name

        if isinstance(node, ast.BinOp):
            # String + concatenation
            if isinstance(node.op, ast.Add):
                left_type = self.infer_type(node.left)
                if left_type == "MpStr*":
                    left = self.compile_expr(node.left)
                    right = self.compile_expr(node.right)
                    return f"mp_str_concat({left}, {right})"
            # Operator overloading via __add__, __sub__, etc.
            left_type = self.infer_type(node.left)
            left_base = left_type.rstrip("*").strip()
            if left_base in self.structs:
                _op_map = {
                    ast.Add: "__add__", ast.Sub: "__sub__", ast.Mult: "__mul__",
                    ast.Div: "__truediv__", ast.Mod: "__mod__",
                }
                _op_name = _op_map.get(type(node.op))
                _method = f"{left_base}_{_op_name}" if _op_name else None
                if _method and _method in self.func_ret_types:
                    left = self.compile_expr(node.left)
                    right = self.compile_expr(node.right)
                    if left_type.endswith("*"):
                        left_self = left
                    else:
                        # If left is not an lvalue (e.g. another Call/BinOp), spill to temp
                        _left_is_lval = isinstance(node.left, (ast.Name, ast.Attribute, ast.Subscript))
                        if not _left_is_lval:
                            _tmp = f"_tmp_{left_base.lower()}_{id(node) & 0xFFFF:04x}"
                            self.emit(f"{left_base} {_tmp} = {left};")
                            left = _tmp
                        left_self = f"&({left})"
                    return f"{_method}({left_self}, {right})"
            left = self.compile_expr(node.left)
            right = self.compile_expr(node.right)
            if isinstance(node.op, ast.Pow):
                return f"pow({left}, {right})"
            if isinstance(node.op, ast.FloorDiv):
                return f"(({left}) / ({right}))"
            op = self.compile_op(node.op)
            return f"({left} {op} {right})"

        if isinstance(node, ast.UnaryOp):
            # __neg__ overloading
            if isinstance(node.op, ast.USub):
                op_type = self.infer_type(node.operand)
                op_base = op_type.rstrip("*").strip()
                _method = f"{op_base}___neg__"
                if op_base in self.structs and _method in self.func_ret_types:
                    operand = self.compile_expr(node.operand)
                    op_self = operand if op_type.endswith("*") else f"&({operand})"
                    return f"{_method}({op_self})"
            operand = self.compile_expr(node.operand)
            if isinstance(node.op, ast.USub):
                return f"(-{operand})"
            if isinstance(node.op, ast.UAdd):
                return f"(+{operand})"
            if isinstance(node.op, ast.Not):
                return f"(!{operand})"
            if isinstance(node.op, ast.Invert):
                return f"(~{operand})"

        if isinstance(node, ast.BoolOp):
            op = " && " if isinstance(node.op, ast.And) else " || "
            parts = [self.compile_expr(v) for v in node.values]
            return f"({op.join(parts)})"

        if isinstance(node, ast.Compare):
            # String == / != comparison
            if len(node.ops) == 1 and len(node.comparators) == 1:
                left_type = self.infer_type(node.left)
                if left_type == "MpStr*":
                    left = self.compile_expr(node.left)
                    right = self.compile_expr(node.comparators[0])
                    if isinstance(node.ops[0], ast.Eq):
                        return f"mp_str_eq({left}, {right})"
                    if isinstance(node.ops[0], ast.NotEq):
                        return f"(!mp_str_eq({left}, {right}))"
            # Comparison operator overloading (__eq__, __lt__, etc.) for single comparisons
            if len(node.ops) == 1 and len(node.comparators) == 1:
                left_type = self.infer_type(node.left)
                left_base = left_type.rstrip("*").strip()
                if left_base in self.structs:
                    _cmp_map = {
                        ast.Eq: "__eq__", ast.NotEq: "__ne__",
                        ast.Lt: "__lt__", ast.LtE: "__le__",
                        ast.Gt: "__gt__", ast.GtE: "__ge__",
                    }
                    _op_name = _cmp_map.get(type(node.ops[0]))
                    _method = f"{left_base}_{_op_name}" if _op_name else None
                    if _method and _method in self.func_ret_types:
                        left = self.compile_expr(node.left)
                        right = self.compile_expr(node.comparators[0])
                        return f"{_method}(&({left}), {right})"
            left = self.compile_expr(node.left)
            parts = []
            prev = left
            for op, comp in zip(node.ops, node.comparators):
                right = self.compile_expr(comp)
                cop = self.compile_cmpop(op)
                parts.append(f"({prev} {cop} {right})")
                prev = right
            return " && ".join(parts)

        if isinstance(node, ast.Call):
            return self.compile_call(node)

        if isinstance(node, ast.Subscript):
            if isinstance(node.value, ast.Name):
                vname = node.value.id
                et = self._list_vars.get(vname)
                if et and et in self.typed_lists:
                    list_name = self.typed_lists[et]
                    lst = self.compile_expr(node.value)
                    idx = self.compile_expr(node.slice)
                    return f"{list_name}_get({lst}, {idx})"
            if self.infer_type(node.value) == "MpList*":
                lst = self.compile_expr(node.value)
                idx = self.compile_expr(node.slice)
                raw = f"mp_list_get({lst}, {idx})"
                if isinstance(node.value, ast.Name):
                    et = self._list_vars.get(node.value.id)
                    if et == "double":
                        return f"mp_as_float({raw})"
                    elif et == "MpStr*":
                        return f"(MpStr*)(uintptr_t)mp_as_int({raw})"
                    elif et:
                        return f"(({et})mp_as_int({raw}))"
                return raw
            val = self.compile_expr(node.value)
            sl = self.compile_expr(node.slice)
            return f"{val}[{sl}]"

        if isinstance(node, ast.Attribute):
            val = self.compile_expr(node.value)
            attr = node.attr
            if isinstance(node.value, ast.Name) and node.value.id in self.enums:
                return f"{node.value.id}_{attr}"
            # Module-qualified names: mod.name → name (C has no namespaces; struct/func
            # names are already prefixed at definition time)
            if isinstance(node.value, ast.Name) and node.value.id in self.modules:
                return attr
            # Use -> for pointer types; dispatch @property getters
            obj_type = self.infer_type(node.value)
            obj_base = obj_type.rstrip("*").strip()
            props = self.struct_properties.get(obj_base, {})
            if attr in props:
                if obj_type.endswith("*"):
                    return f"{obj_base}_{attr}({val})"
                else:
                    return f"{obj_base}_{attr}(&({val}))"
            if obj_type.endswith("*"):
                return f"{val}->{attr}"
            return f"{val}.{attr}"

        if isinstance(node, ast.Index):
            return self.compile_expr(node.value)

        if isinstance(node, ast.IfExp):
            test = self.compile_expr(node.test)
            body = self.compile_expr(node.body)
            orelse = self.compile_expr(node.orelse)
            return f"(({test}) ? ({body}) : ({orelse}))"

        if isinstance(node, ast.Tuple):
            elts = [self.compile_expr(e) for e in node.elts]
            return "{" + ", ".join(elts) + "}"

        if isinstance(node, ast.Set):
            elts = [self.compile_expr(e) for e in node.elts]
            return "{" + ", ".join(elts) + "}"

        if isinstance(node, ast.JoinedStr):
            fmt, args = self._fstr_to_printf(node)
            self._fstr_counter += 1
            buf = f"_fstr_{self._fstr_counter}"
            arg_str = f', {", ".join(args)}' if args else ""
            self.emit(f'char {buf}[512]; snprintf({buf}, 512, "{fmt}"{arg_str});')
            return buf

        if isinstance(node, ast.ListComp):
            return self._compile_listcomp(node)

        if isinstance(node, ast.Lambda):
            lname = self._lambda_table.get(id(node))
            if lname:
                return lname
            # Unregistered lambda — try to generate inline (no type info, use int64_t for all)
            lname = f"_lam_{self._lambda_counter}"
            self._lambda_counter += 1
            params = [a.arg for a in node.args.args]
            param_str = ", ".join(f"int64_t {p}" for p in params) if params else "void"
            # Save/restore state
            saved_func_args = self.func_args.copy()
            saved_local = self.local_vars.copy()
            saved_ret = self.current_func_ret_type
            self.func_args = {p: "int64_t" for p in params}
            self.local_vars = {p: "int64_t" for p in params}
            self.current_func_ret_type = "int64_t"
            body_expr = self.compile_expr(node.body)
            self.func_args = saved_func_args
            self.local_vars = saved_local
            self.current_func_ret_type = saved_ret
            self.emit(f"static int64_t {lname}({param_str}) {{ return {body_expr}; }}")
            return lname

        return f"/* UNKNOWN: {ast.dump(node)} */"

    # Math functions that map directly to C math.h
    _MATH_FUNCS = {
        "sqrt": "sqrt", "cbrt": "cbrt",
        "sin": "sin", "cos": "cos", "tan": "tan",
        "asin": "asin", "acos": "acos", "atan": "atan", "atan2": "atan2",
        "sinh": "sinh", "cosh": "cosh", "tanh": "tanh",
        "exp": "exp", "exp2": "exp2",
        "log": "log", "log2": "log2", "log10": "log10",
        "pow": "pow",
        "floor": "floor", "ceil": "ceil", "round": "round", "trunc": "trunc",
        "fabs": "fabs", "hypot": "hypot", "fmod": "fmod",
        "isnan": "isnan", "isinf": "isinf",
    }

    def compile_call(self, node: ast.Call) -> str:
        # Fill in default arguments for user-defined functions before compiling
        if isinstance(node.func, ast.Name):
            fname = node.func.id
            if fname in self.func_defaults:
                defaults = self.func_defaults[fname]
                n_provided = len(node.args)
                if n_provided < len(defaults):
                    import copy
                    node = copy.copy(node)
                    node.args = list(node.args)
                    for i in range(n_provided, len(defaults)):
                        if defaults[i] is not None:
                            node.args.append(defaults[i])

        args = [self.compile_expr(a) for a in node.args]
        arg_str = ", ".join(args)

        if isinstance(node.func, ast.Name):
            fname = node.func.id

            if fname in self.from_imports:
                mod, real_name = self.from_imports[fname]
                return f"{mod}_{real_name}({arg_str})"

            # Struct constructors — use ClassName_new() if __init__ is defined
            if fname in self.structs:
                if node.keywords:
                    # Named initialization
                    kwargs = {kw.arg: kw.value for kw in node.keywords}
                    init_key = f"{fname}___init__"
                    if init_key in self.func_ret_types:
                        # Reorder by __init__ param order (skip 'self')
                        params = [p for p in self.func_param_order.get(init_key, []) if p != "self"]
                        ordered = []
                        for i, p in enumerate(params):
                            if p in kwargs:
                                ordered.append(self.compile_expr(kwargs[p]))
                            elif i < len(node.args):
                                ordered.append(self.compile_expr(node.args[i]))
                        return f"{fname}_new({', '.join(ordered)})"
                    else:
                        # Designated initializers — no __init__, use field names
                        parts = [f".{kw.arg}={self.compile_expr(kw.value)}" for kw in node.keywords]
                        return f"({fname}){{{', '.join(parts)}}}"
                if f"{fname}___init__" in self.func_ret_types:
                    return f"{fname}_new({arg_str})"
                # No __init__: zero-init if no args, else designated init
                if not arg_str:
                    return f"({fname}){{0}}"
                return f"({fname}){{{arg_str}}}"

            # Typed list constructors: IntList_new() etc.
            for elem_t, list_name in self.typed_lists.items():
                if fname == f"{list_name}_new":
                    return f"{list_name}_new()"
                for op in ["append", "get", "set", "len", "pop", "free"]:
                    if fname == f"{list_name}_{op}":
                        return f"{list_name}_{op}({arg_str})"

            # test_assert(cond) or test_assert(cond, msg)
            if fname == "test_assert":
                if len(node.args) == 2:
                    cond = self.compile_expr(node.args[0])
                    msg  = self.compile_expr(node.args[1])
                    return f"mp_test_assert_msg({cond}, {msg})"
                return f"mp_test_assert({arg_str})"

            if fname == "test_assert_eq":
                return f"mp_test_assert_eq({arg_str})"

            # sizeof with type name mapping
            if fname == "sizeof" and len(node.args) == 1:
                arg = node.args[0]
                if isinstance(arg, ast.Name):
                    from type_map import TYPE_MAP
                    mapped = TYPE_MAP.get(arg.id, arg.id)
                    return f"sizeof({mapped})"
                return f"sizeof({self.compile_expr(arg)})"

            # abs / min / max
            if fname == "abs" and len(node.args) == 1:
                t = self.infer_type(node.args[0])
                expr = self.compile_expr(node.args[0])
                return f"fabs({expr})" if t == "double" else f"llabs((long long)({expr}))"

            if fname in ("min", "max") and len(node.args) == 2:
                t = self.infer_type(node.args[0])
                a = self.compile_expr(node.args[0])
                b = self.compile_expr(node.args[1])
                if t == "double":
                    return f"fmin({a}, {b})" if fname == "min" else f"fmax({a}, {b})"
                op = "<" if fname == "min" else ">"
                return f"(({a}) {op} ({b}) ? ({a}) : ({b}))"

            # int(x) / float(x) casts
            if fname == "int" and len(node.args) == 1:
                return f"((int64_t)({self.compile_expr(node.args[0])}))"
            if fname == "float" and len(node.args) == 1:
                return f"((double)({self.compile_expr(node.args[0])}))"

            # str(x) — convert value to MpStr*
            if fname == "str" and len(node.args) == 1:
                arg = node.args[0]
                t = self.infer_type(arg)
                expr = self.compile_expr(arg)
                if t == "MpStr*":
                    return expr
                if t == "double":
                    return f"mp_str_from_float({expr})"
                if t in ("char*", "cstr"):
                    return f"mp_str_new({expr})"
                return f"mp_str_from_int((int64_t)({expr}))"

            # Cast builtins
            cast_map = {"cast_int": "int64_t", "cast_float": "double",
                        "cast_byte": "uint8_t", "cast_bool": "int"}
            if fname in cast_map:
                return f"(({cast_map[fname]})({arg_str}))"

            # addr_of(x) → &x
            if fname == "addr_of":
                return f"(&{arg_str})"

            # deref(p) → *p
            if fname == "deref":
                if len(node.args) == 2:
                    # deref(ptr, val) → *ptr = val  (write form)
                    ptr_expr = self.compile_expr(node.args[0])
                    val_expr = self.compile_expr(node.args[1])
                    self.emit(f"*({ptr_expr}) = {val_expr};")
                    return "(void)0"
                return f"(*({arg_str}))"

            # deref_set(p, val) → *p = val  (kept for back-compat)
            if fname == "deref_set":
                ptr_expr = self.compile_expr(node.args[0])
                val_expr = self.compile_expr(node.args[1])
                return f"(*({ptr_expr}) = {val_expr})"

            # cast_ptr(x) → (void*)x  or cast_ptr_Type(x) → (Type*)x
            if fname == "cast_ptr":
                return f"((void*)({arg_str}))"
            if fname.startswith("cast_ptr_"):
                target_type = fname[9:]  # after "cast_ptr_"
                return f"(({target_type}*)({arg_str}))"

            # Result[T] helpers
            if fname == "Ok" and len(node.args) == 1:
                inner_type = self.infer_type(node.args[0])
                result_name = f"Result_{mangle_type(inner_type)}"
                val = self.compile_expr(node.args[0])
                return f"{result_name}_ok({val})"

            if fname == "Err" and len(node.args) == 1:
                msg = self.compile_expr(node.args[0])
                ret = self.current_func_ret_type
                if ret.startswith("Result_"):
                    return f"{ret}_err({msg})"
                return f'({{ fprintf(stderr, "%s\\n", {msg}); abort(); 0; }})'

            if fname == "is_ok" and len(node.args) == 1:
                expr = self.compile_expr(node.args[0])
                return f"({expr})._ok"

            if fname == "is_err" and len(node.args) == 1:
                expr = self.compile_expr(node.args[0])
                return f"(!({expr})._ok)"

            if fname == "unwrap" and len(node.args) == 1:
                t = self.infer_type(node.args[0])
                expr = self.compile_expr(node.args[0])
                if t.startswith("Result_"):
                    return f"{t}_unwrap({expr})"
                return expr

            if fname == "err_msg" and len(node.args) == 1:
                expr = self.compile_expr(node.args[0])
                return f"({expr})._err"

            if fname == "try_unwrap" and len(node.args) == 1:
                result_expr = self.compile_expr(node.args[0])
                result_type = self.infer_type(node.args[0])
                self._try_counter = getattr(self, '_try_counter', 0) + 1
                tmp = f"_mp_try_{self._try_counter}"
                self.emit(f"{result_type} {tmp} = {result_expr};")
                ret = self.current_func_ret_type
                if ret.startswith("Result_"):
                    self.emit(f"if (!{tmp}._ok) return {ret}_err({tmp}._err);")
                else:
                    self.emit(f"if (!{tmp}._ok) {{ fprintf(stderr, \"%s\\n\", {tmp}._err); abort(); }}")
                return f"{tmp}._val"

            # sort(arr, cmp_fn) — qsort wrapper for typed arrays
            if fname == "sort" and len(node.args) == 2:
                arr_node = node.args[0]
                cmp_node = node.args[1]
                cmp_expr = self.compile_expr(cmp_node)
                if isinstance(arr_node, ast.Name) and arr_node.id in self._array_vars:
                    arr_name = arr_node.id
                    elem_type, size = self._array_vars[arr_name]
                    return (f"qsort({arr_name}, {size}, sizeof({elem_type}), "
                            f"(int(*)(const void*, const void*)){cmp_expr})")
                arr_expr = self.compile_expr(arr_node)
                return f"qsort({arr_expr}, 0, 0, (int(*)(const void*, const void*)){cmp_expr})"

            # exit(n)
            if fname == "exit":
                code = arg_str if arg_str else "0"
                return f"exit({code})"

            # va_start / va_end / va_arg
            if fname == "va_start":
                ap = self.compile_expr(node.args[0])
                last = self.compile_expr(node.args[1])
                return f"va_start({ap}, {last})"
            if fname == "va_end":
                ap = self.compile_expr(node.args[0])
                return f"va_end({ap})"
            if fname == "va_arg":
                from type_map import map_type as _map_type
                ap = self.compile_expr(node.args[0])
                T = _map_type(node.args[1])
                return f"va_arg({ap}, {T})"

            # input(prompt?) — read a line from stdin
            if fname == "input":
                prompt = arg_str if arg_str else "NULL"
                return f"mp_input({prompt})"

            # getenv(name) — get environment variable, returns ptr[str] (NULL if not set)
            if fname == "getenv" and len(node.args) == 1:
                arg = node.args[0]
                expr = self.compile_expr(arg)
                # MpStr* variable → extract .data; string literals and cstr → pass directly
                if not isinstance(arg, ast.Constant) and self.infer_type(arg) == "MpStr*":
                    return f"mp_getenv(({expr})->data)"
                return f"mp_getenv({expr})"

            # Math functions (direct or via 'math' import)
            if fname in self._MATH_FUNCS:
                return f"{self._MATH_FUNCS[fname]}({arg_str})"

            # len(x) — type-dispatched length
            if fname == "len" and len(node.args) == 1:
                arg = node.args[0]
                arg_expr = self.compile_expr(arg)
                if isinstance(arg, ast.Name):
                    aname = arg.id
                    if aname in self._array_vars:
                        _, size = self._array_vars[aname]
                        return size
                    if aname in self._list_vars:
                        return f"{arg_expr}->len"
                    # mutable global arrays
                    if aname in self.mutable_globals:
                        # check if it's an array global - look up size from globals
                        pass
                # Fallback by inferred type
                t = self.infer_type(arg)
                t_base = t.rstrip("*").strip()
                # __len__ special method
                if t_base in self.structs and f"{t_base}___len__" in self.func_ret_types:
                    return f"{t_base}___len__(&({arg_expr}))"
                if t == "MpStr*":
                    return f"mp_str_len({arg_expr})"
                if t == "MpList*":
                    return f"mp_list_len({arg_expr})"
                if t.endswith("*"):
                    return f"{arg_expr}->len"
                return f"mp_list_len({arg_expr})"

            # Universal print()
            if fname == "print":
                return self._compile_print(node.args)

            # thread_spawn with auto-wrapping
            if fname == "thread_spawn" and len(node.args) >= 2:
                return self._compile_thread_spawn(node)

            # Built-in mappings
            builtins = {
                "print_int": "mp_print_int", "print_float": "mp_print_float",
                "print_str": "mp_print_str", "print_bool": "mp_print_bool",
                "print_val": "mp_print_val",
                "list_new": "mp_list_new", "list_append": "mp_list_append",
                "list_get": "mp_list_get", "list_set": "mp_list_set",
                "list_len": "mp_list_len", "list_pop": "mp_list_pop",
                "list_free": "mp_list_free",
                "dict_new": "mp_dict_new", "dict_set": "mp_dict_set",
                "dict_get": "mp_dict_get", "dict_has": "mp_dict_has",
                "dict_del": "mp_dict_del", "dict_len": "mp_dict_len",
                "dict_free": "mp_dict_free",
                "str_new": "mp_str_new", "str_len": "mp_str_len",
                "str_concat": "mp_str_concat", "str_eq": "mp_str_eq",
                "str_print": "mp_str_print", "str_free": "mp_str_free",
                "str_from_int": "mp_str_from_int", "str_from_float": "mp_str_from_float",
                "str_contains": "mp_str_contains", "str_starts_with": "mp_str_starts_with",
                "str_ends_with": "mp_str_ends_with", "str_slice": "mp_str_slice",
                "str_find": "mp_str_find", "str_upper": "mp_str_upper",
                "str_lower": "mp_str_lower", "str_repeat": "mp_str_repeat",
                "to_int": "mp_val_to_int", "to_float": "mp_val_to_float",
                "as_int": "mp_as_int", "as_float": "mp_as_float",
                "val_int": "mp_val_int", "val_float": "mp_val_float",
                "val_str": "mp_val_str",
                "alloc": "malloc", "free": "free", "sizeof": "sizeof",
                "arena_new": "mp_arena_new", "arena_free": "mp_arena_free",
                "arena_reset": "mp_arena_reset", "arena_alloc": "mp_arena_alloc",
                "arena_list_new": "mp_arena_list_new",
                "arena_str_new": "mp_arena_str_new",
                "file_open": "mp_file_open", "file_open_safe": "mp_file_open_safe",
                "file_close": "mp_file_close",
                "file_write": "mp_file_write", "file_write_str": "mp_file_write_str",
                "file_write_line": "mp_file_write_line",
                "file_write_int": "mp_file_write_int",
                "file_write_float": "mp_file_write_float",
                "file_read_all": "mp_file_read_all",
                "file_read_line": "mp_file_read_line",
                "file_eof": "mp_file_eof",
                "file_exists": "mp_file_exists", "file_size": "mp_file_size",
                "dir_create": "mp_dir_create", "dir_remove": "mp_dir_remove",
                "dir_exists": "mp_dir_exists", "dir_list": "mp_dir_list",
                "dir_cwd": "mp_dir_cwd", "dir_chdir": "mp_dir_chdir",
                "path_join": "mp_path_join", "path_ext": "mp_path_ext",
                "path_basename": "mp_path_basename", "path_dirname": "mp_path_dirname",
                "remove_file": "mp_remove", "rename_file": "mp_rename",
                "thread_spawn": "mp_thread_spawn", "thread_join": "mp_thread_join",
                "mutex_new": "mp_mutex_new", "mutex_lock": "mp_mutex_lock",
                "mutex_unlock": "mp_mutex_unlock", "mutex_free": "mp_mutex_free",
                "cond_new": "mp_cond_new", "cond_wait": "mp_cond_wait",
                "cond_signal": "mp_cond_signal", "cond_broadcast": "mp_cond_broadcast",
                "cond_free": "mp_cond_free",
                "sleep_ms": "mp_sleep_ms",
                "atomic_add": "mp_atomic_add", "atomic_load": "mp_atomic_load",
                "atomic_store": "mp_atomic_store",
                "channel_new": "mp_channel_new", "channel_send": "mp_channel_send",
                "channel_recv": "mp_channel_recv", "channel_close": "mp_channel_close",
                "channel_free": "mp_channel_free",
                "channel_recv_val": "mp_channel_recv_val",
                "channel_drain": "mp_channel_drain",
                "channel_has_data": "mp_channel_has_data",
                "pool_new": "mp_pool_new", "pool_submit": "mp_pool_submit",
                "pool_shutdown": "mp_pool_shutdown",
                "parallel_for": "mp_parallel_for",
                "rand_seed": "mp_rand_seed", "rand_int": "mp_rand_int",
                "rand_float": "mp_rand_float",
                "time_now": "mp_time_now", "time_ms": "mp_time_ms",
                "str_format": "mp_str_format",
                "str_strip": "mp_str_strip", "str_lstrip": "mp_str_lstrip",
                "str_rstrip": "mp_str_rstrip", "str_split": "mp_str_split",
            }
            if fname in builtins:
                return f"{builtins[fname]}({arg_str})"

            for mod_name, mod_info in self.modules.items():
                if mod_name == self.current_module:
                    continue
                if fname in mod_info.functions:
                    return f"{mod_name}_{fname}({arg_str})"

            return f"{fname}({arg_str})"

        if isinstance(node.func, ast.Attribute):
            obj = node.func.value
            attr = node.func.attr
            # math.sqrt(x) etc.
            if isinstance(obj, ast.Name) and obj.id == "math" and attr in self._MATH_FUNCS:
                return f"{self._MATH_FUNCS[attr]}({arg_str})"
            if isinstance(obj, ast.Name) and obj.id in self.modules:
                mi = self.modules[obj.id]
                # Struct constructor: mod.StructName(args) → StructName_new(args)
                if attr in mi.structs:
                    if f"{attr}___init__" in self.func_ret_types:
                        return f"{attr}_new({arg_str})"
                    return f"({attr}){{{arg_str}}}"
                return f"{attr}({arg_str})"
            # Static method call: ClassName.method(args) — no self injection
            if isinstance(obj, ast.Name) and obj.id in self.structs:
                return f"{obj.id}_{attr}({arg_str})"
            obj_str = self.compile_expr(obj)
            # Resolve TypeName_method via type inference
            obj_type = self.infer_type(obj)

            # Generated typed list dispatch (struct element types, no boxing)
            if isinstance(obj, ast.Name):
                _et = self._list_vars.get(obj.id)
                if _et and _et in self.typed_lists:
                    _lname = self.typed_lists[_et]
                    if attr == "append" and len(node.args) == 1:
                        v = self.compile_expr(node.args[0])
                        return f"{_lname}_append({obj_str}, {v})"
                    if attr == "pop" and not node.args:
                        return f"{_lname}_pop({obj_str})"
                    if attr == "len" and not node.args:
                        return f"{_lname}_len({obj_str})"

            # MpList* method dispatch with auto-boxing/unboxing
            if obj_type == "MpList*":
                def _box(a_node):
                    e = self.compile_expr(a_node)
                    t = self.infer_type(a_node)
                    if t == "double": return f"mp_val_float({e})"
                    if t == "MpStr*": return f"mp_val_str({e})"
                    return f"mp_val_int((int64_t)({e}))"
                elem_type = self._list_vars.get(obj.id) if isinstance(obj, ast.Name) else None
                if attr == "append" and len(node.args) == 1:
                    return f"mp_list_append({obj_str}, {_box(node.args[0])})"
                if attr == "pop" and not node.args:
                    raw = f"mp_list_pop({obj_str})"
                    if elem_type == "double": return f"mp_as_float({raw})"
                    if elem_type == "MpStr*": return f"(MpStr*)(uintptr_t)mp_as_int({raw})"
                    if elem_type: return f"(({elem_type})mp_as_int({raw}))"
                    return raw
                if attr == "len" and not node.args:
                    return f"mp_list_len({obj_str})"

            base = obj_type.rstrip("*").strip()
            if obj_type.endswith("*") or base in self.structs:
                # Check if attr is a funcptr field — call it as a function pointer
                _struct_field_types = dict(self.structs.get(base, []))
                if _struct_field_types.get(attr) == "__funcptr__":
                    sep = "->" if obj_type.endswith("*") else "."
                    return f"{obj_str}{sep}{attr}({arg_str})"

                if base.startswith("Mp") and len(base) > 2:
                    prefix = "mp_" + base[2:].lower()
                else:
                    prefix = base
                # Value-type structs: pass &obj as self (pointer self).
                # If obj is an rvalue (Call, BinOp, …), spill to a temp so we
                # can take its address — C does not allow &(rvalue).
                if base in self.structs:
                    if obj_type.endswith("*"):
                        # Already a pointer — pass directly, no & needed
                        self_arg = obj_str
                    else:
                        _is_lval = isinstance(obj, (ast.Name, ast.Attribute, ast.Subscript))
                        if not _is_lval:
                            _tmp = f"_tmp_{base.lower()}_{id(node) & 0xFFFF:04x}"
                            self.emit(f"{base} {_tmp} = {obj_str};")
                            obj_str = _tmp
                        self_arg = f"&({obj_str})"
                    # Auto-deref args: if a T* is passed where T is expected, emit (*arg)
                    _cfunc = f"{prefix}_{attr}"
                    _ptypes = self.func_param_types.get(_cfunc, [])
                    if _ptypes and node.args:
                        _coerced = []
                        for _i, (_aexpr, _anode) in enumerate(zip(args, node.args)):
                            _pidx = _i + 1  # skip self param
                            if _pidx < len(_ptypes):
                                _exp = _ptypes[_pidx]
                                _inf = self.infer_type(_anode)
                                if _inf.endswith("*") and _exp == _inf[:-1].strip():
                                    _aexpr = f"(*({_aexpr}))"
                            _coerced.append(_aexpr)
                        arg_str = ", ".join(_coerced)
                else:
                    self_arg = obj_str
                all_args = f"{self_arg}, {arg_str}" if arg_str else self_arg
                return f"{prefix}_{attr}({all_args})"
            all_args = f"{obj_str}, {arg_str}" if arg_str else obj_str
            return f"{attr}({all_args})"

        func_str = self.compile_expr(node.func)
        return f"{func_str}({arg_str})"

    def _fstr_to_printf(self, node: ast.JoinedStr):
        """Convert an f-string to (fmt_string, [c_args]) for use with printf/snprintf."""
        fmt_parts = []
        c_args = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                s = (str(part.value)
                     .replace("\\", "\\\\")
                     .replace('"', '\\"')
                     .replace("\n", "\\n")
                     .replace("\t", "\\t")
                     .replace("%", "%%"))
                fmt_parts.append(s)
            elif isinstance(part, ast.FormattedValue):
                expr = self.compile_expr(part.value)
                t = self.infer_type(part.value)

                # Extract user format spec (e.g. ".2f", "x", "08d")
                spec = ""
                if part.format_spec and isinstance(part.format_spec, ast.JoinedStr):
                    for sp in part.format_spec.values:
                        if isinstance(sp, ast.Constant):
                            spec += str(sp.value)

                if spec:
                    # Map spec suffix to printf, widening ints to long long
                    if spec[-1] in ("d", "i") and t in ("int64_t", "int", "uint8_t"):
                        fmt_parts.append(f"%{spec[:-1]}lld")
                        c_args.append(f"(long long)({expr})")
                    elif spec[-1] in ("x", "X") and t in ("int64_t", "int", "uint8_t"):
                        fmt_parts.append(f"%{spec[:-1]}ll{spec[-1]}")
                        c_args.append(f"(long long)({expr})")
                    elif spec[-1] == "f" and t == "double":
                        fmt_parts.append(f"%{spec}")
                        c_args.append(expr)
                    else:
                        fmt_parts.append(f"%{spec}")
                        c_args.append(expr)
                elif t == "double":
                    fmt_parts.append("%g")
                    c_args.append(expr)
                elif t == "int64_t":
                    fmt_parts.append("%lld")
                    c_args.append(f"(long long)({expr})")
                elif t == "uint8_t":
                    fmt_parts.append("%u")
                    c_args.append(f"(unsigned)({expr})")
                elif t == "int":
                    fmt_parts.append("%d")
                    c_args.append(f"(int)({expr})")
                elif t == "MpStr*":
                    fmt_parts.append("%.*s")
                    c_args.append(f"(int)(({expr})->len)")
                    c_args.append(f"(({expr})->data)")
                elif t in self.structs and f"{t}___str__" in self.func_ret_types:
                    str_ret = self.func_ret_types[f"{t}___str__"]
                    str_call = f"{t}___str__(&({expr}))"
                    if str_ret == "MpStr*":
                        fmt_parts.append("%.*s")
                        c_args.append(f"(int)(({str_call})->len)")
                        c_args.append(f"(({str_call})->data)")
                    else:
                        fmt_parts.append("%s")
                        c_args.append(str_call)
                else:
                    fmt_parts.append("%lld")
                    c_args.append(f"(long long)({expr})")
        return "".join(fmt_parts), c_args

    def _print_list_arg(self, arg) -> None:
        """Emit statements to print a list arg in [elem, ...] format."""
        self._lc_counter += 1
        idx = f"_pi_{self._lc_counter}"
        expr = self.compile_expr(arg)
        t = self.infer_type(arg)

        # Determine element type and format
        elem_t = None
        list_name = None
        if isinstance(arg, ast.Name):
            elem_t = self._list_vars.get(arg.id)
            if elem_t and elem_t in self.typed_lists:
                list_name = self.typed_lists[elem_t]

        self.emit('printf("[");')
        if list_name:
            # Generated typed list (e.g. Vec2List*)
            self.emit(f"for (int64_t {idx} = 0; {idx} < {expr}->len; {idx}++) {{")
            self.indent += 1
            self.emit(f"if ({idx} > 0) printf(\", \");")
            elem_expr = f"{expr}->data[{idx}]"
            if elem_t in self.structs:
                fields = self.structs[elem_t]
                parts = []
                fargs = []
                for fn, ft in fields:
                    if ft == "double":
                        parts.append(f"{fn}=%.6g")
                        fargs.append(f"{elem_expr}.{fn}")
                    else:
                        parts.append(f"{fn}=%lld")
                        fargs.append(f"(long long){elem_expr}.{fn}")
                fmt = f"{elem_t}({', '.join(parts)})"
                farg_str = ", ".join(fargs)
                self.emit(f'printf("{fmt}", {farg_str});')
            else:
                self.emit(f'printf("%lld", (long long){elem_expr});')
        else:
            # MpList* with MpVal elements
            self.emit(f"for (int64_t {idx} = 0; {idx} < {expr}->len; {idx}++) {{")
            self.indent += 1
            self.emit(f"if ({idx} > 0) printf(\", \");")
            raw = f"{expr}->data[{idx}]"
            if elem_t == "double":
                self.emit(f"printf(\"%.6g\", mp_as_float({raw}));")
            elif elem_t == "MpStr*":
                self.emit(f"{{ MpStr* _ps = (MpStr*)(uintptr_t)mp_as_int({raw}); printf(\"%.*s\", (int)_ps->len, _ps->data); }}")
            else:
                self.emit(f"printf(\"%lld\", (long long)mp_as_int({raw}));")
        self.indent -= 1
        self.emit("}")
        self.emit('printf("]\\n");')

    def _compile_print(self, args) -> str:
        if not args:
            return 'printf("\\n")'
        # If any arg is a list type, emit loop-based printing and return a no-op
        for arg in args:
            t = self.infer_type(arg)
            is_list = (t == "MpList*") or (
                isinstance(arg, ast.Name)
                and self._list_vars.get(arg.id) in self.typed_lists
            )
            if is_list:
                # Emit each arg: non-list ones via printf, list ones via loop
                for a in args:
                    ta = self.infer_type(a)
                    ia = (ta == "MpList*") or (
                        isinstance(a, ast.Name)
                        and self._list_vars.get(a.id) in self.typed_lists
                    )
                    if ia:
                        self._print_list_arg(a)
                    else:
                        ea = self.compile_expr(a)
                        if ta == "double":
                            self.emit(f'printf("%.6g\\n", {ea});')
                        elif ta == "MpStr*":
                            self.emit(f'printf("%.*s\\n", (int)(({ea})->len), ({ea})->data);')
                        else:
                            self.emit(f'printf("%lld\\n", (long long)({ea}));')
                return "(void)0"
        fmt_parts = []
        c_args = []
        for arg in args:
            # f-strings inline directly into the printf format string
            if isinstance(arg, ast.JoinedStr):
                f_fmt, f_args = self._fstr_to_printf(arg)
                fmt_parts.append(f_fmt)
                c_args.extend(f_args)
                continue
            t = self.infer_type(arg)
            expr = self.compile_expr(arg)
            if t == "double":
                fmt_parts.append("%.6f")
                c_args.append(expr)
            elif t in ("int64_t",):
                fmt_parts.append("%lld")
                c_args.append(f"(long long)({expr})")
            elif t == "uint8_t":
                fmt_parts.append("%u")
                c_args.append(f"(unsigned)({expr})")
            elif t == "int":
                fmt_parts.append("%s")
                c_args.append(f"(({expr}) ? \"True\" : \"False\")")
            elif t == "MpStr*":
                fmt_parts.append("%.*s")
                c_args.append(f"(int)(({expr})->len)")
                c_args.append(f"(({expr})->data)")
            elif t in self.enums:
                fmt_parts.append("%d")
                c_args.append(f"(int)({expr})")
            elif t in self.structs and f"{t}___str__" in self.func_ret_types:
                # __str__ special method
                str_ret = self.func_ret_types[f"{t}___str__"]
                str_call = f"{t}___str__(&({expr}))"
                if str_ret == "MpStr*":
                    fmt_parts.append("%.*s")
                    c_args.append(f"(int)(({str_call})->len)")
                    c_args.append(f"(({str_call})->data)")
                else:
                    fmt_parts.append("%s")
                    c_args.append(str_call)
            elif t in self.structs:
                # Print struct fields
                fields = self.structs[t]
                inner_fmt = []
                for fn, ft in fields:
                    if ft == "double":
                        inner_fmt.append(f"{fn}=%.6f")
                        c_args.append(f"({expr}).{fn}")
                    elif ft in ("int64_t",):
                        inner_fmt.append(f"{fn}=%lld")
                        c_args.append(f"(long long)({expr}).{fn}")
                    else:
                        inner_fmt.append(f"{fn}=%lld")
                        c_args.append(f"(long long)({expr}).{fn}")
                fmt_parts.append(f"{t}({', '.join(inner_fmt)})")
            else:
                fmt_parts.append("%lld")
                c_args.append(f"(long long)({expr})")

        fmt = " ".join(fmt_parts) + "\\n"
        if c_args:
            return f'printf("{fmt}", {", ".join(c_args)})'
        return f'printf("{fmt}")'

    def _compile_thread_spawn(self, node: ast.Call) -> str:
        """
        Handle thread_spawn with automatic argument wrapping.

        thread_spawn(func, arg)             → raw spawn (1 void* arg)
        thread_spawn(func, a, b, c)         → auto-generate wrapper struct + trampoline
        """
        func_node = node.args[0]
        spawn_args = node.args[1:]

        # Get the target function name
        if isinstance(func_node, ast.Name):
            target_name = func_node.id
        else:
            # Complex expression, fall back to raw spawn
            func_expr = self.compile_expr(func_node)
            arg_expr = self.compile_expr(spawn_args[0]) if spawn_args else "NULL"
            return f"mp_thread_spawn({func_expr}, {arg_expr})"

        # Check if target function is known and takes typed args
        target_info = None
        cur = self.modules.get(self.current_module)
        if cur and target_name in cur.functions:
            target_info = cur.functions[target_name]
        for mn, mi in self.modules.items():
            if target_name in mi.functions:
                target_info = mi.functions[target_name]

        # If only 1 spawn arg, or target takes (void*), use raw spawn
        if len(spawn_args) <= 1:
            arg_expr = self.compile_expr(spawn_args[0]) if spawn_args else "NULL"
            return f"mp_thread_spawn({target_name}, {arg_expr})"

        # If target function is known, use its arg types
        # Otherwise infer from the spawn call arguments
        if target_info:
            ret_type, func_args = target_info
            # func_args is [(name, type), ...]
            arg_types = [(name, atype) for name, atype in func_args]
        else:
            # Infer types from the expressions being passed
            arg_types = []
            for i, a in enumerate(spawn_args):
                t = self.infer_type(a)
                arg_types.append((f"_a{i}", t))

        wrapper_name = f"_MpArgs_{target_name}"
        trampoline_name = f"_mp_trampoline_{target_name}"

        # Emit wrapper struct and trampoline (only once per target function)
        if target_name not in self.thread_wrappers_emitted:
            self.thread_wrappers_emitted.add(target_name)

            # We need to insert these BEFORE the current function.
            # Save current lines, emit the wrapper, then restore.
            insert_lines = []

            # Struct
            insert_lines.append(f"typedef struct {{")
            for aname, atype in arg_types:
                insert_lines.append(f"    {atype} {aname};")
            insert_lines.append(f"}} {wrapper_name};")
            insert_lines.append("")

            # Trampoline
            insert_lines.append(f"static void* {trampoline_name}(void* _raw) {{")
            insert_lines.append(f"    {wrapper_name}* _a = ({wrapper_name}*)_raw;")

            # Build the call with unpacked args
            call_args = ", ".join(f"_a->{aname}" for aname, atype in arg_types)
            insert_lines.append(f"    {target_name}({call_args});")
            insert_lines.append(f"    free(_raw);")
            insert_lines.append(f"    return NULL;")
            insert_lines.append(f"}}")
            insert_lines.append("")

            # Find insertion point — before the current function
            # We look for the last function definition start
            insert_idx = 0
            for i, line in enumerate(self.lines):
                stripped = line.strip()
                if stripped.startswith("void ") or stripped.startswith("int64_t ") or stripped.startswith(
                        "double ") or stripped.startswith("int main"):
                    if stripped.endswith("{"):
                        insert_idx = i
            # Insert before the current function
            for j, il in enumerate(insert_lines):
                self.lines.insert(insert_idx + j, il)

        # At the spawn site: allocate struct, fill it, spawn
        compiled_args = [self.compile_expr(a) for a in spawn_args]
        self.thread_spawn_counter += 1
        alloc_var = f"_targ_{target_name}_{self.thread_spawn_counter}"

        # Build a multi-statement expression using comma operator
        # Actually, we need to emit statements before this expression.
        # Use a block expression pattern:
        stmts = []
        stmts.append(f"{wrapper_name}* {alloc_var} = ({wrapper_name}*)malloc(sizeof({wrapper_name}))")
        for i, (aname, atype) in enumerate(arg_types):
            stmts.append(f"{alloc_var}->{aname} = {compiled_args[i]}")

        # Emit the setup as separate statements
        for s in stmts:
            self.emit(f"{s};")

        return f"mp_thread_spawn({trampoline_name}, {alloc_var})"

    def _compile_listcomp(self, node: ast.ListComp) -> str:
        """Compile [elt for target in iter if cond ...] into a typed or MpList* temp."""
        self._lc_counter += 1
        lc_var = f"_lc_{self._lc_counter}"
        # Determine element type before emitting so we can pick the right list type
        _elt_type_early = self.infer_type(node.elt)
        _gen_list = self.typed_lists.get(_elt_type_early)
        if _gen_list:
            self.emit(f"{_gen_list}* {lc_var} = {_gen_list}_new();")
        else:
            self.emit(f"MpList* {lc_var} = mp_list_new();")

        # Only handle single generator
        gen = node.generators[0]
        target_name = gen.target.id if isinstance(gen.target, ast.Name) else "_lc_x"
        iter_node = gen.iter

        saved_locals = self.local_vars.copy()
        elem_type = "int64_t"
        opened_blocks = 1  # the for loop block

        # --- Emit the for loop ---
        if (isinstance(iter_node, ast.Call)
                and isinstance(iter_node.func, ast.Name)
                and iter_node.func.id == "range"):
            args = iter_node.args
            if len(args) == 1:
                stop = self.compile_expr(args[0])
                self.emit(f"for (int64_t {target_name} = 0; {target_name} < {stop}; {target_name}++) {{")
            elif len(args) >= 2:
                start = self.compile_expr(args[0])
                stop = self.compile_expr(args[1])
                step = self.compile_expr(args[2]) if len(args) == 3 else "1"
                self.emit(f"for (int64_t {target_name} = {start}; {target_name} < {stop}; {target_name} += {step}) {{")
            self.indent += 1
            self.local_vars[target_name] = "int64_t"
            elem_type = "int64_t"

        elif isinstance(iter_node, ast.Name) and iter_node.id in self._array_vars:
            et, size = self._array_vars[iter_node.id]
            idx = f"_lci_{self._lc_counter}"
            self.emit(f"for (int64_t {idx} = 0; {idx} < {size}; {idx}++) {{")
            self.indent += 1
            self.emit(f"{et} {target_name} = {iter_node.id}[{idx}];")
            self.local_vars[target_name] = et
            elem_type = et

        elif isinstance(iter_node, ast.Name) and iter_node.id in self._list_vars:
            et = self._list_vars[iter_node.id]
            idx = f"_lci_{self._lc_counter}"
            self.emit(f"for (int64_t {idx} = 0; {idx} < {iter_node.id}->len; {idx}++) {{")
            self.indent += 1
            self.emit(f"{et} {target_name} = ({et})mp_as_int({iter_node.id}->data[{idx}]);")
            self.local_vars[target_name] = et
            elem_type = et

        else:
            self.emit(f"/* ERROR: unsupported list comprehension iterable */")
            return lc_var

        # --- Emit if guards ---
        for if_node in gen.ifs:
            cond = self.compile_expr(if_node)
            self.emit(f"if ({cond}) {{")
            self.indent += 1
            opened_blocks += 1

        # --- Emit the element append ---
        elt_expr = self.compile_expr(node.elt)
        elt_type = self.infer_type(node.elt)
        if _gen_list:
            self.emit(f"{_gen_list}_append({lc_var}, {elt_expr});")
        elif elt_type == "double":
            self.emit(f"mp_list_append({lc_var}, mp_val_float({elt_expr}));")
        elif elt_type == "MpStr*":
            self.emit(f"mp_list_append({lc_var}, mp_val_str({elt_expr}));")
        else:
            self.emit(f"mp_list_append({lc_var}, mp_val_int((int64_t)({elt_expr})));")

        # --- Close all opened blocks ---
        for _ in range(opened_blocks):
            self.indent -= 1
            self.emit("}")

        self.local_vars = saved_locals
        return lc_var

    def compile_op(self, op) -> str:
        ops = {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
            ast.Mod: "%", ast.LShift: "<<", ast.RShift: ">>",
            ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^",
            ast.FloorDiv: "/",
        }
        return ops.get(type(op), "?")

    def compile_cmpop(self, op) -> str:
        ops = {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
            ast.Gt: ">", ast.GtE: ">=",
            ast.Is: "==", ast.IsNot: "!=",
        }
        return ops.get(type(op), "?")
