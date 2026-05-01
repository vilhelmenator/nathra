"nathra"
"""Native port of compile_call — function call code generation.

Substages 4.5-4.6: simple call dispatch (casts, pointer ops, sizeof,
builtins table) and complex call dispatch (struct ctors, len, sort,
Result helpers, method calls).

Substages 4.7-4.8 (print/f-strings, lambda/listcomp/thread_spawn)
are deferred — they require statement emission which couples to
compile_stmt. For now those fall through to a TODO marker.
"""

from nathra_stubs import alloc, free
from ast_nodes import AstNode, AstNodeList, AstName, AstConstant, AstCall
from ast_nodes import AstAttribute, AstSubscript
from ast_nodes import TAG_NAME, TAG_ATTRIBUTE, TAG_CONSTANT, TAG_SUBSCRIPT, CONST_STR, AstConstant
from strmap import StrMap, strmap_get, strmap_has
from native_compiler_state import CompilerState, FieldList, field_list_find, ArrayInfo
from native_compiler_state import ParamTypeList
from native_infer import native_infer_type, _strip_ptr, _ends_with_star
from native_codegen_expr import native_compile_expr

# ── Address-taken predicate (for auto addr_of) ─────────────────────────

def _is_addressable_lvalue(s: ptr[CompilerState], node: ptr[AstNode]) -> int:
    """True if `node` is an addressable value expression — Name in scope,
    Attribute on an addressable base, or Subscript of a known array."""
    if node is None:
        return 0
    if node.tag == TAG_NAME:
        n: ptr[AstName] = node.data
        if strmap_has(addr_of(s.local_vars), n.id):
            return 1
        if strmap_has(addr_of(s.func_args), n.id):
            return 1
        if strmap_has(addr_of(s.mutable_globals), n.id):
            return 1
        if strmap_has(addr_of(s.constants), n.id):
            return 1
        if strmap_has(addr_of(s.array_vars), n.id):
            return 1
        return 0
    if node.tag == TAG_ATTRIBUTE:
        a: ptr[AstAttribute] = node.data
        return _is_addressable_lvalue(s, a.value)
    if node.tag == TAG_SUBSCRIPT:
        sb: ptr[AstSubscript] = node.data
        if sb.value is not None and sb.value.tag == TAG_NAME:
            sn: ptr[AstName] = sb.value.data
            if strmap_has(addr_of(s.array_vars), sn.id):
                return 1
        return 0
    return 0

# ── Builtins table ──────────────────────────────────────────────────────

class BuiltinEntry:
    key: cstr
    value: cstr

builtin_map: array[BuiltinEntry] = [
    BuiltinEntry("print_int", "nr_print_int"), BuiltinEntry("print_float", "nr_print_float"),
    BuiltinEntry("print_str", "nr_print_str"), BuiltinEntry("print_bool", "nr_print_bool"),
    BuiltinEntry("print_val", "nr_print_val"),
    BuiltinEntry("list_new", "nr_list_new"), BuiltinEntry("list_append", "nr_list_append"),
    BuiltinEntry("list_get", "nr_list_get"), BuiltinEntry("list_set", "nr_list_set"),
    BuiltinEntry("list_len", "nr_list_len"), BuiltinEntry("list_pop", "nr_list_pop"),
    BuiltinEntry("list_free", "nr_list_free"),
    BuiltinEntry("dict_new", "nr_dict_new"), BuiltinEntry("dict_set", "nr_dict_set"),
    BuiltinEntry("dict_get", "nr_dict_get"), BuiltinEntry("dict_has", "nr_dict_has"),
    BuiltinEntry("dict_del", "nr_dict_del"), BuiltinEntry("dict_len", "nr_dict_len"),
    BuiltinEntry("dict_free", "nr_dict_free"),
    BuiltinEntry("str_new", "nr_str_new"), BuiltinEntry("str_len", "nr_str_len"),
    BuiltinEntry("str_concat", "nr_str_concat"), BuiltinEntry("str_eq", "nr_str_eq"),
    BuiltinEntry("str_print", "nr_str_print"), BuiltinEntry("str_free", "nr_str_free"),
    BuiltinEntry("str_from_int", "nr_str_from_int"), BuiltinEntry("str_from_float", "nr_str_from_float"),
    BuiltinEntry("str_contains", "nr_str_contains"), BuiltinEntry("str_starts_with", "nr_str_starts_with"),
    BuiltinEntry("str_ends_with", "nr_str_ends_with"), BuiltinEntry("str_slice", "nr_str_slice"),
    BuiltinEntry("str_find", "nr_str_find"), BuiltinEntry("str_upper", "nr_str_upper"),
    BuiltinEntry("str_lower", "nr_str_lower"), BuiltinEntry("str_repeat", "nr_str_repeat"),
    BuiltinEntry("to_int", "nr_val_to_int"), BuiltinEntry("to_float", "nr_val_to_float"),
    BuiltinEntry("as_int", "nr_as_int"), BuiltinEntry("as_float", "nr_as_float"),
    BuiltinEntry("val_int", "nr_val_int"), BuiltinEntry("val_float", "nr_val_float"),
    BuiltinEntry("val_str", "nr_val_str"),
    BuiltinEntry("alloc", "malloc"), BuiltinEntry("free", "free"),
    BuiltinEntry("arena_new", "nr_arena_new"), BuiltinEntry("arena_free", "nr_arena_free"),
    BuiltinEntry("arena_reset", "nr_arena_reset"), BuiltinEntry("arena_alloc", "nr_arena_alloc"),
    BuiltinEntry("arena_list_new", "nr_arena_list_new"),
    BuiltinEntry("arena_str_new", "nr_arena_str_new"),
    BuiltinEntry("arena_str_new_len", "nr_arena_str_new_len"),
    BuiltinEntry("read_file_bin", "nr_read_file_bin"),
    BuiltinEntry("write_file_bin", "nr_write_file_bin"),
    BuiltinEntry("open", "nr_file_open"),
    BuiltinEntry("file_open", "nr_file_open"), BuiltinEntry("file_open_safe", "nr_file_open_safe"),
    BuiltinEntry("file_close", "nr_file_close"),
    BuiltinEntry("file_write", "nr_file_write"), BuiltinEntry("file_write_str", "nr_file_write_str"),
    BuiltinEntry("file_write_line", "nr_file_write_line"),
    BuiltinEntry("file_write_int", "nr_file_write_int"),
    BuiltinEntry("file_write_float", "nr_file_write_float"),
    BuiltinEntry("file_read_all", "nr_file_read_all"),
    BuiltinEntry("file_read_line", "nr_file_read_line"),
    BuiltinEntry("file_eof", "nr_file_eof"),
    BuiltinEntry("file_exists", "nr_file_exists"), BuiltinEntry("file_size", "nr_file_size"),
    BuiltinEntry("dir_create", "nr_dir_create"), BuiltinEntry("dir_remove", "nr_dir_remove"),
    BuiltinEntry("dir_exists", "nr_dir_exists"), BuiltinEntry("dir_list", "nr_dir_list"),
    BuiltinEntry("dir_cwd", "nr_dir_cwd"), BuiltinEntry("dir_chdir", "nr_dir_chdir"),
    BuiltinEntry("path_join", "nr_path_join"), BuiltinEntry("path_ext", "nr_path_ext"),
    BuiltinEntry("path_basename", "nr_path_basename"), BuiltinEntry("path_dirname", "nr_path_dirname"),
    BuiltinEntry("remove_file", "nr_remove"), BuiltinEntry("rename_file", "nr_rename"),
    BuiltinEntry("thread_spawn", "nr_thread_spawn"), BuiltinEntry("thread_join", "nr_thread_join"),
    BuiltinEntry("mutex_new", "nr_mutex_new"), BuiltinEntry("mutex_lock", "nr_mutex_lock"),
    BuiltinEntry("mutex_unlock", "nr_mutex_unlock"), BuiltinEntry("mutex_free", "nr_mutex_free"),
    BuiltinEntry("cond_new", "nr_cond_new"), BuiltinEntry("cond_wait", "nr_cond_wait"),
    BuiltinEntry("cond_signal", "nr_cond_signal"), BuiltinEntry("cond_broadcast", "nr_cond_broadcast"),
    BuiltinEntry("cond_free", "nr_cond_free"),
    BuiltinEntry("sleep_ms", "nr_sleep_ms"),
    BuiltinEntry("atomic_add", "nr_atomic_add"), BuiltinEntry("atomic_sub", "nr_atomic_sub"),
    BuiltinEntry("atomic_load", "nr_atomic_load"), BuiltinEntry("atomic_store", "nr_atomic_store"),
    BuiltinEntry("atomic_cas", "nr_atomic_cas"),
    BuiltinEntry("channel_new", "nr_channel_new"), BuiltinEntry("channel_send", "nr_channel_send"),
    BuiltinEntry("channel_recv", "nr_channel_recv"), BuiltinEntry("channel_close", "nr_channel_close"),
    BuiltinEntry("channel_free", "nr_channel_free"),
    BuiltinEntry("channel_recv_val", "nr_channel_recv_val"),
    BuiltinEntry("channel_drain", "nr_channel_drain"),
    BuiltinEntry("channel_has_data", "nr_channel_has_data"),
    BuiltinEntry("pool_new", "nr_pool_new"), BuiltinEntry("pool_submit", "nr_pool_submit"),
    BuiltinEntry("pool_shutdown", "nr_pool_shutdown"),
    BuiltinEntry("parallel_for", "nr_parallel_for"),
    BuiltinEntry("rand_seed", "nr_rand_seed"), BuiltinEntry("rand_int", "nr_rand_int"),
    BuiltinEntry("rand_float", "nr_rand_float"),
    BuiltinEntry("time_now", "nr_time_now"), BuiltinEntry("time_ms", "nr_time_ms"),
    BuiltinEntry("str_format", "nr_str_format"),
    BuiltinEntry("str_strip", "nr_str_strip"), BuiltinEntry("str_lstrip", "nr_str_lstrip"),
    BuiltinEntry("str_rstrip", "nr_str_rstrip"), BuiltinEntry("str_split", "nr_str_split"),
    BuiltinEntry("writer_new", "nr_writer_new"), BuiltinEntry("writer_free", "nr_writer_free"),
    BuiltinEntry("writer_pos", "nr_writer_pos"),
    BuiltinEntry("write_bytes", "nr_write_bytes"),
    BuiltinEntry("write_i8", "nr_write_i8"), BuiltinEntry("write_i16", "nr_write_i16"),
    BuiltinEntry("write_i32", "nr_write_i32"), BuiltinEntry("write_i64", "nr_write_i64"),
    BuiltinEntry("write_u8", "nr_write_u8"), BuiltinEntry("write_u16", "nr_write_u16"),
    BuiltinEntry("write_u32", "nr_write_u32"), BuiltinEntry("write_u64", "nr_write_u64"),
    BuiltinEntry("write_f32", "nr_write_f32"), BuiltinEntry("write_f64", "nr_write_f64"),
    BuiltinEntry("write_bool", "nr_write_bool"), BuiltinEntry("write_str", "nr_write_str"),
    BuiltinEntry("writer_to_bytes", "nr_writer_to_bytes"),
    BuiltinEntry("reader_new", "nr_reader_new"), BuiltinEntry("reader_free", "nr_reader_free"),
    BuiltinEntry("reader_pos", "nr_reader_pos"),
    BuiltinEntry("read_bytes", "nr_read_bytes"),
    BuiltinEntry("read_i8", "nr_read_i8"), BuiltinEntry("read_i16", "nr_read_i16"),
    BuiltinEntry("read_i32", "nr_read_i32"), BuiltinEntry("read_i64", "nr_read_i64"),
    BuiltinEntry("read_u8", "nr_read_u8"), BuiltinEntry("read_u16", "nr_read_u16"),
    BuiltinEntry("read_u32", "nr_read_u32"), BuiltinEntry("read_u64", "nr_read_u64"),
    BuiltinEntry("read_f32", "nr_read_f32"), BuiltinEntry("read_f64", "nr_read_f64"),
    BuiltinEntry("read_bool", "nr_read_bool"), BuiltinEntry("read_str", "nr_read_str"),
    BuiltinEntry("", "")
]

def lookup_builtin(name: str) -> cstr:
    """Look up a builtin function name. Returns C name or NULL."""
    if name is None:
        return None
    if name.data is None:
        return None
    i: i32 = 0
    while builtin_map[i].key[0] != 0:
        if strcmp(name.data, builtin_map[i].key) == 0:
            return builtin_map[i].value
        i = i + 1
    return None

# ── 4.5: Type cast handlers ────────────────────────────────────────────

def native_call_type_cast(s: ptr[CompilerState], fname: str, node: ptr[AstCall], arg_str: str) -> str:
    """Handle int(), float(), str(), cast(), cast_int, etc. Returns NULL if not a cast."""
    if fname == "int" and node.args.count == 1:
        e: str = native_compile_expr(s, node.args.items[0])
        return str_format("((int64_t)(%s))", e.data)
    if fname == "float" and node.args.count == 1:
        e2: str = native_compile_expr(s, node.args.items[0])
        return str_format("((double)(%s))", e2.data)
    if fname == "cast_int":
        return str_format("((int64_t)(%s))", arg_str.data)
    if fname == "cast_float":
        return str_format("((double)(%s))", arg_str.data)
    if fname == "cast_byte":
        return str_format("((uint8_t)(%s))", arg_str.data)
    if fname == "cast_bool":
        return str_format("((int)(%s))", arg_str.data)
    return None

# ── 4.5: Pointer operation handlers ────────────────────────────────────

def native_call_ptr_ops(s: ptr[CompilerState], fname: str, node: ptr[AstCall], arg_str: str) -> str:
    """Handle addr_of, ref, deref, cast_ptr. Returns NULL if not a ptr op."""
    if fname == "addr_of" or fname == "ref":
        return str_format("(&%s)", arg_str.data)
    if fname == "deref":
        if node.args.count == 2:
            ptr_e: str = native_compile_expr(s, node.args.items[0])
            val_e: str = native_compile_expr(s, node.args.items[1])
            _emit_line(s, str_format("*(%s) = %s;", ptr_e.data, val_e.data))
            return str_new("(void)0")
        return str_format("(*(%s))", arg_str.data)
    if fname == "deref_set":
        ptr_e2: str = native_compile_expr(s, node.args.items[0])
        val_e2: str = native_compile_expr(s, node.args.items[1])
        return str_format("(*(%s) = %s)", ptr_e2.data, val_e2.data)
    if fname == "cast_ptr":
        return str_format("((void*)(%s))", arg_str.data)
    return None

# ── 4.5: abs / min / max ───────────────────────────────────────────────

def native_call_abs_min_max(s: ptr[CompilerState], fname: str, node: ptr[AstCall], arg_str: str) -> str:
    """Handle abs(), min(), max(). Returns NULL if not applicable."""
    if fname == "abs" and node.args.count == 1:
        t: str = native_infer_type(s, node.args.items[0])
        e: str = native_compile_expr(s, node.args.items[0])
        if t == "double":
            return str_format("fabs(%s)", e.data)
        return str_format("llabs((long long)(%s))", e.data)
    if node.args.count == 2:
        if fname == "min" or fname == "max":
            t2: str = native_infer_type(s, node.args.items[0])
            a: str = native_compile_expr(s, node.args.items[0])
            b: str = native_compile_expr(s, node.args.items[1])
            if t2 == "double":
                if fname == "min":
                    return str_format("fmin(%s, %s)", a.data, b.data)
                return str_format("fmax(%s, %s)", a.data, b.data)
            op: cstr = "<"
            if fname == "max":
                op = ">"
            return str_format("((%s) %s (%s) ? (%s) : (%s))", a.data, op, b.data, a.data, b.data)
    return None

# ── 4.6: len() ──────────────────────────────────────────────────────────

def native_call_len(s: ptr[CompilerState], node: ptr[AstCall]) -> str:
    """Compile len(x) with type dispatch."""
    arg: ptr[AstNode] = node.args.items[0]
    arg_expr: str = native_compile_expr(s, arg)
    # Check array vars
    if arg.tag == TAG_NAME:
        an: ptr[AstName] = arg.data
        ai: ptr[ArrayInfo] = strmap_get(addr_of(s.array_vars), an.id)
        if ai is not None:
            return ai.size
        et: str = strmap_get(addr_of(s.list_vars), an.id)
        if et is not None:
            ln: str = strmap_get(addr_of(s.typed_lists), et)
            if ln is not None:
                return str_format("%s_len(%s)", ln.data, arg_expr.data)
            return str_format("%s->len", arg_expr.data)
    # Fallback by inferred type
    t: str = native_infer_type(s, arg)
    t_base: str = _strip_ptr(t)
    # __len__ special method
    len_method: str = t_base + "___len__"
    if strmap_has(addr_of(s.structs), t_base) and strmap_has(addr_of(s.func_ret_types), len_method):
        return str_format("%s(&(%s))", len_method.data, arg_expr.data)
    if t == "NrStr*":
        return str_format("nr_str_len(%s)", arg_expr.data)
    if t == "NrList*":
        return str_format("nr_list_len(%s)", arg_expr.data)
    if _ends_with_star(t):
        return str_format("%s->len", arg_expr.data)
    return str_format("nr_list_len(%s)", arg_expr.data)

# ── 4.6: Struct constructor ─────────────────────────────────────────────

def native_call_struct_ctor(s: ptr[CompilerState], fname: str, arg_str: str) -> str:
    """Compile StructName(args) → compound literal or _new()."""
    init_key: str = fname + "___init__"
    if strmap_has(addr_of(s.func_ret_types), init_key):
        return str_format("%s_new(%s)", fname.data, arg_str.data)
    if str_len(arg_str) == 0:
        return str_format("(%s){0}", fname.data)
    return str_format("(%s){%s}", fname.data, arg_str.data)

# ── print() handler ─────────────────────────────────────────────────────

def native_compile_print(s: ptr[CompilerState], pc: ptr[AstCall]) -> str:
    """Compile print(args) → printf with type-dispatched format strings."""
    if pc.args.count == 0:
        return str_new("printf(\"\\n\")")

    # Build printf parts for each argument
    fmt: str = str_new("")
    args_c: str = str_new("")
    for i in range(pc.args.count):
        if i > 0:
            fmt = fmt + " "
        arg: ptr[AstNode] = pc.args.items[i]
        t: str = native_infer_type(s, arg)
        expr: str = native_compile_expr(s, arg)
        if t == "double" or t == "float":
            fmt = fmt + "%g"
            args_c = str_concat(args_c, str_format(", %s", expr.data))
        elif t == "NrStr*":
            fmt = fmt + "%.*s"
            args_c = str_concat(args_c, str_format(", (int)(%s)->len, (%s)->data", expr.data, expr.data))
        elif t == "int":
            fmt = fmt + "%d"
            args_c = str_concat(args_c, str_format(", %s", expr.data))
        else:
            fmt = fmt + "%lld"
            args_c = str_concat(args_c, str_format(", (long long)(%s)", expr.data))
    fmt = fmt + "\\n"
    return str_format("printf(\"%s\"%s)", fmt.data, args_c.data)

# ── Emit helper ─────────────────────────────────────────────────────────

def _emit_line(s: ptr[CompilerState], line: str) -> void:
    for i in range(s.indent):
        nr_write_text(s.lines, str_new("    "))
    nr_write_text(s.lines, line)
    nr_write_text(s.lines, str_new("\n"))

# ── Main call dispatcher ───────────────────────────────────────────────

def native_compile_call(s: ptr[CompilerState], node: ptr[AstNode]) -> str:
    """Compile a function call expression."""
    pc: ptr[AstCall] = node.data
    func: ptr[AstNode] = pc.func

    # Compile all arguments
    arg_parts: ptr[str] = None
    if pc.args.count > 0:
        arg_parts = alloc(cast_int(pc.args.count) * 8)
        for i in range(pc.args.count):
            arg_parts[i] = native_compile_expr(s, pc.args.items[i])

    # Auto addr_of: when callee expects T* and arg is a T-typed lvalue, wrap.
    if pc.args.count > 0 and func.tag == TAG_NAME:
        cn_fn: ptr[AstName] = func.data
        ptl_lookup: ptr[ParamTypeList] = strmap_get(addr_of(s.func_param_types), cn_fn.id)
        if ptl_lookup is not None:
            for ai in range(pc.args.count):
                if ai >= ptl_lookup.count:
                    break
                pt: str = ptl_lookup.types[ai]
                if pt is None:
                    continue
                if _ends_with_star(pt) == 0:
                    continue
                if pt == "void*" or pt == "const void*" or pt == "NrStr*":
                    continue
                arg_node: ptr[AstNode] = pc.args.items[ai]
                if _is_addressable_lvalue(s, arg_node) == 0:
                    continue
                at: str = native_infer_type(s, arg_node)
                if at == pt:
                    continue
                expected: str = str_concat(at, str_new("*"))
                if str_eq(expected, pt) == 0:
                    continue
                arg_parts[ai] = str_format("(&(%s))", arg_parts[ai].data)

    # Build arg_str
    arg_str: str = str_new("")
    for i in range(pc.args.count):
        if i > 0:
            arg_str = arg_str + ", "
        arg_str = str_concat(arg_str, arg_parts[i])

    if func.tag == TAG_NAME:
        fn: ptr[AstName] = func.data
        fname: str = fn.id

        # test_assert / test_assert_eq
        if fname == "test_assert":
            if arg_parts is not None:
                free(arg_parts)
            if pc.args.count == 2:
                cond: str = native_compile_expr(s, pc.args.items[0])
                msg: str = native_compile_expr(s, pc.args.items[1])
                return str_format("nr_test_assert_msg(%s, %s)", cond.data, msg.data)
            return str_format("nr_test_assert(%s)", arg_str.data)
        if fname == "test_assert_eq":
            if arg_parts is not None:
                free(arg_parts)
            return str_format("nr_test_assert_eq(%s)", arg_str.data)

        # heap_allocated() / heap_assert(expected) / heap_assert_delta(snap, delta)
        if fname == "heap_allocated":
            if arg_parts is not None:
                free(arg_parts)
            return str_new("nr_heap_allocated()")
        if fname == "heap_assert" and pc.args.count == 1:
            val: str = native_compile_expr(s, pc.args.items[0])
            if arg_parts is not None:
                free(arg_parts)
            return str_format("nr_heap_assert(%s, __FILE__, __LINE__)", val.data)
        if fname == "heap_assert_delta" and pc.args.count == 2:
            snap_e: str = native_compile_expr(s, pc.args.items[0])
            delta_e: str = native_compile_expr(s, pc.args.items[1])
            if arg_parts is not None:
                free(arg_parts)
            return str_format("nr_heap_assert_delta(%s, %s, __FILE__, __LINE__)", snap_e.data, delta_e.data)

        # Struct constructor
        if strmap_has(addr_of(s.structs), fname):
            r: str = native_call_struct_ctor(s, fname, arg_str)
            if arg_parts is not None:
                free(arg_parts)
            return r

        # abs / min / max
        r2: str = native_call_abs_min_max(s, fname, pc, arg_str)
        if r2 is not None:
            if arg_parts is not None:
                free(arg_parts)
            return r2

        # Type casts
        r3: str = native_call_type_cast(s, fname, pc, arg_str)
        if r3 is not None:
            if arg_parts is not None:
                free(arg_parts)
            return r3

        # Pointer ops
        r4: str = native_call_ptr_ops(s, fname, pc, arg_str)
        if r4 is not None:
            if arg_parts is not None:
                free(arg_parts)
            return r4

        # len()
        if fname == "len" and pc.args.count == 1:
            r5: str = native_call_len(s, pc)
            if arg_parts is not None:
                free(arg_parts)
            return r5

        # exit()
        if fname == "exit":
            code: str = arg_str
            if str_len(code) == 0:
                code = str_new("0")
            if arg_parts is not None:
                free(arg_parts)
            return str_format("exit(%s)", code.data)

        # input()
        if fname == "input":
            prompt: str = arg_str
            if str_len(prompt) == 0:
                prompt = str_new("NULL")
            if arg_parts is not None:
                free(arg_parts)
            return str_format("mp_input(%s)", prompt.data)

        # sort(arr, cmp) — qsort wrapper, matching Python's _call_sort
        if fname == "sort" and pc.args.count == 2:
            arr_node: ptr[AstNode] = pc.args.items[0]
            arr_e: str = native_compile_expr(s, arr_node)
            cmp_e: str = native_compile_expr(s, pc.args.items[1])
            if arg_parts is not None:
                free(arg_parts)
            # Look up array info for size and element type
            if arr_node.tag == TAG_NAME:
                arr_n: ptr[AstName] = arr_node.data
                arr_ai: ptr[ArrayInfo] = strmap_get(addr_of(s.array_vars), arr_n.id)
                if arr_ai is not None:
                    return str_format("qsort(%s, %s, sizeof(%s), (int(*)(const void*, const void*))%s)", arr_e.data, arr_ai.size.data, arr_ai.elem_type.data, cmp_e.data)
            return str_format("qsort(%s, 0, 0, (int(*)(const void*, const void*))%s)", arr_e.data, cmp_e.data)

        # str(x) — convert to NrStr*
        if fname == "str" and pc.args.count == 1:
            st: str = native_infer_type(s, pc.args.items[0])
            se: str = native_compile_expr(s, pc.args.items[0])
            if arg_parts is not None:
                free(arg_parts)
            if st == "NrStr*":
                return se
            if st == "double":
                return str_format("nr_str_from_float(%s)", se.data)
            return str_format("nr_str_from_int((int64_t)(%s))", se.data)

        # sizeof(T)
        if fname == "sizeof" and pc.args.count == 1:
            sarg: ptr[AstNode] = pc.args.items[0]
            if sarg.tag == TAG_NAME:
                sn: ptr[AstName] = sarg.data
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("sizeof(%s)", sn.id.data)

        # print() — type-dispatched printf
        if fname == "print":
            if arg_parts is not None:
                free(arg_parts)
            return native_compile_print(s, pc)

        # str_* function coercion: wrap string literal args as stack NrStr*
        # Matches Python compiler's _STR_OBJ_FUNCS (NOT str_new/str_from_*/str_format)
        is_str_obj_func: int = 0
        if fname == "str_len" or fname == "str_eq" or fname == "str_concat" or fname == "str_free":
            is_str_obj_func = 1
        if fname == "str_contains" or fname == "str_starts_with" or fname == "str_ends_with":
            is_str_obj_func = 1
        if fname == "str_slice" or fname == "str_find" or fname == "str_upper" or fname == "str_lower":
            is_str_obj_func = 1
        if fname == "str_repeat" or fname == "str_strip" or fname == "str_split":
            is_str_obj_func = 1
        if is_str_obj_func:
            coerced_parts: str = str_new("")
            for ci in range(pc.args.count):
                if ci > 0:
                    coerced_parts = coerced_parts + ", "
                ca: ptr[AstNode] = pc.args.items[ci]
                if ca.tag == TAG_CONSTANT:
                    cac: ptr[AstConstant] = ca.data
                    if cac.kind == CONST_STR and cac.str_val is not None:
                        escaped_c: str = native_compile_expr(s, ca)
                        slen_c: i64 = str_len(cac.str_val)
                        coerced_parts = str_concat(coerced_parts, str_format("(&(NrStr){.data=(char*)%s,.len=%lld})", escaped_c.data, slen_c))
                        continue
                coerced_parts = str_concat(coerced_parts, native_compile_expr(s, ca))
            arg_str = coerced_parts

        # Builtin table lookup
        c_name: cstr = lookup_builtin(fname)
        if c_name is not None:
            if arg_parts is not None:
                free(arg_parts)
            return str_format("%s(%s)", c_name, arg_str.data)

        # Function in current module's func_ret_types (known function)
        if strmap_has(addr_of(s.func_ret_types), fname):
            if arg_parts is not None:
                free(arg_parts)
            return str_format("%s(%s)", fname.data, arg_str.data)

        # Default: call as-is
        if arg_parts is not None:
            free(arg_parts)
        return str_format("%s(%s)", fname.data, arg_str.data)

    # Attribute call: obj.method(args)
    if func.tag == TAG_ATTRIBUTE:
        pa: ptr[AstAttribute] = func.data
        obj_str: str = native_compile_expr(s, pa.value)
        obj_type: str = native_infer_type(s, pa.value)
        base: str = _strip_ptr(obj_type)
        attr: str = pa.attr

        # os.path.func() — two-level attribute: os.path is the obj, func is the attr
        if pa.value is not None and pa.value.tag == TAG_ATTRIBUTE:
            inner: ptr[AstAttribute] = pa.value.data
            if inner.value is not None and inner.value.tag == TAG_NAME:
                mod_n: ptr[AstName] = inner.value.data
                if str_eq(mod_n.id, str_new("os")) and str_eq(inner.attr, str_new("path")):
                    c_os_path: str = str_new("")
                    if str_eq(attr, str_new("join")):
                        c_os_path = str_new("nr_path_join")
                    elif str_eq(attr, str_new("basename")):
                        c_os_path = str_new("nr_path_basename")
                    elif str_eq(attr, str_new("dirname")):
                        c_os_path = str_new("nr_path_dirname")
                    elif str_eq(attr, str_new("ext")):
                        c_os_path = str_new("nr_path_ext")
                    if str_len(c_os_path) > 0:
                        if arg_parts is not None:
                            free(arg_parts)
                        return str_format("%s(%s)", c_os_path.data, arg_str.data)

        # os.func() — single-level attribute
        if pa.value is not None and pa.value.tag == TAG_NAME:
            os_n: ptr[AstName] = pa.value.data
            if str_eq(os_n.id, str_new("os")):
                c_os: str = str_new("")
                if str_eq(attr, str_new("exists")):
                    c_os = str_new("nr_file_exists")
                elif str_eq(attr, str_new("file_size")):
                    c_os = str_new("nr_file_size")
                elif str_eq(attr, str_new("remove")):
                    c_os = str_new("nr_remove")
                elif str_eq(attr, str_new("rename")):
                    c_os = str_new("nr_rename")
                elif str_eq(attr, str_new("mkdir")):
                    c_os = str_new("nr_dir_create")
                elif str_eq(attr, str_new("rmdir")):
                    c_os = str_new("nr_dir_remove")
                elif str_eq(attr, str_new("isdir")):
                    c_os = str_new("nr_dir_exists")
                elif str_eq(attr, str_new("getcwd")):
                    c_os = str_new("nr_dir_cwd")
                elif str_eq(attr, str_new("listdir")):
                    c_os = str_new("nr_dir_list")
                elif str_eq(attr, str_new("chdir")):
                    c_os = str_new("nr_dir_chdir")
                if str_len(c_os) > 0:
                    if arg_parts is not None:
                        free(arg_parts)
                    return str_format("%s(%s)", c_os.data, arg_str.data)

        # NrStr method dispatch — map to nr_str_* functions
        if obj_type == "NrStr*":
            c_fn: str = str_format("nr_str_%s", attr.data)
            all_a: str = obj_str
            if str_len(arg_str) > 0:
                all_a = str_format("%s, %s", obj_str.data, arg_str.data)
            if arg_parts is not None:
                free(arg_parts)
            return str_format("%s(%s)", c_fn.data, all_a.data)

        # Typed list method dispatch — check if obj is in list_vars
        if pa.value is not None and pa.value.tag == TAG_NAME:
            obj_n: ptr[AstName] = pa.value.data
            et_lookup: str = strmap_get(addr_of(s.list_vars), obj_n.id)
            if et_lookup is not None:
                ln_lookup: str = strmap_get(addr_of(s.typed_lists), et_lookup)
                if ln_lookup is not None:
                    c_method: str = str_format("%s_%s", ln_lookup.data, attr.data)
                    all_tl: str = obj_str
                    if str_len(arg_str) > 0:
                        all_tl = str_format("%s, %s", obj_str.data, arg_str.data)
                    if arg_parts is not None:
                        free(arg_parts)
                    return str_format("%s(%s)", c_method.data, all_tl.data)

        # NrList method dispatch
        if obj_type == "NrList*":
            if attr == "append" and pc.args.count == 1:
                v: str = native_compile_expr(s, pc.args.items[0])
                vt: str = native_infer_type(s, pc.args.items[0])
                boxed: str = v
                if vt == "double":
                    boxed = str_format("nr_val_float(%s)", v.data)
                elif vt == "NrStr*":
                    boxed = str_format("nr_val_str(%s)", v.data)
                else:
                    boxed = str_format("nr_val_int((int64_t)(%s))", v.data)
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("nr_list_append(%s, %s)", obj_str.data, boxed.data)
            if attr == "pop":
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("nr_list_pop(%s)", obj_str.data)
            if attr == "len":
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("nr_list_len(%s)", obj_str.data)

        # NrFile method dispatch
        if obj_type == "NrFile":
            if attr == "write":
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("nr_file_write(%s, %s)", obj_str.data, arg_str.data)
            if attr == "write_line":
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("nr_file_write_line(%s, %s)", obj_str.data, arg_str.data)
            if attr == "read":
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("nr_file_read_all(%s)", obj_str.data)
            if attr == "close":
                if arg_parts is not None:
                    free(arg_parts)
                return str_format("nr_file_close(%s)", obj_str.data)

        # Struct method call
        if strmap_has(addr_of(s.structs), base):
            # Build self arg
            self_arg: str = obj_str
            if _ends_with_star(obj_type) == 0:
                self_arg = str_format("&(%s)", obj_str.data)
            all_args: str = self_arg
            if str_len(arg_str) > 0:
                all_args = str_format("%s, %s", self_arg.data, arg_str.data)
            if arg_parts is not None:
                free(arg_parts)
            return str_format("%s_%s(%s)", base.data, attr.data, all_args.data)

        # Default method call: attr(obj, args)
        all_args2: str = obj_str
        if str_len(arg_str) > 0:
            all_args2 = str_format("%s, %s", obj_str.data, arg_str.data)
        if arg_parts is not None:
            free(arg_parts)
        return str_format("%s(%s)", attr.data, all_args2.data)

    # Function pointer or computed function call
    func_str: str = native_compile_expr(s, func)
    if arg_parts is not None:
        free(arg_parts)
    return str_format("%s(%s)", func_str.data, arg_str.data)

# ── Test ────────────────────────────────────────────────────────────────

def main() -> int:
    # Test builtin lookup
    s1: str = "alloc"
    r1: cstr = lookup_builtin(s1)
    assert r1 is not None
    assert strcmp(r1, "malloc") == 0

    s2: str = "str_new"
    r2: cstr = lookup_builtin(s2)
    assert r2 is not None
    assert strcmp(r2, "nr_str_new") == 0

    s3: str = "read_u8"
    r3: cstr = lookup_builtin(s3)
    assert r3 is not None
    assert strcmp(r3, "nr_read_u8") == 0

    s4: str = "nonexistent"
    assert lookup_builtin(s4) is None

    ok: str = "PASS: native_codegen_call 4.5-4.6"
    print(ok)
    return 0
