/* nth_stamp: 1777595589.979964 */
#include "nathra_rt.h"
#include "native_codegen_call.h"

static inline BuiltinEntry _nr_make_BuiltinEntry(char* key, char* value) {
    BuiltinEntry _s = {0};
    _s.key = key;
    _s.value = value;
    return _s;
}

BuiltinEntry builtin_map[152] = {(BuiltinEntry){"print_int", "nr_print_int"}, (BuiltinEntry){"print_float", "nr_print_float"}, (BuiltinEntry){"print_str", "nr_print_str"}, (BuiltinEntry){"print_bool", "nr_print_bool"}, (BuiltinEntry){"print_val", "nr_print_val"}, (BuiltinEntry){"list_new", "nr_list_new"}, (BuiltinEntry){"list_append", "nr_list_append"}, (BuiltinEntry){"list_get", "nr_list_get"}, (BuiltinEntry){"list_set", "nr_list_set"}, (BuiltinEntry){"list_len", "nr_list_len"}, (BuiltinEntry){"list_pop", "nr_list_pop"}, (BuiltinEntry){"list_free", "nr_list_free"}, (BuiltinEntry){"dict_new", "nr_dict_new"}, (BuiltinEntry){"dict_set", "nr_dict_set"}, (BuiltinEntry){"dict_get", "nr_dict_get"}, (BuiltinEntry){"dict_has", "nr_dict_has"}, (BuiltinEntry){"dict_del", "nr_dict_del"}, (BuiltinEntry){"dict_len", "nr_dict_len"}, (BuiltinEntry){"dict_free", "nr_dict_free"}, (BuiltinEntry){"str_new", "nr_str_new"}, (BuiltinEntry){"str_len", "nr_str_len"}, (BuiltinEntry){"str_concat", "nr_str_concat"}, (BuiltinEntry){"str_eq", "nr_str_eq"}, (BuiltinEntry){"str_print", "nr_str_print"}, (BuiltinEntry){"str_free", "nr_str_free"}, (BuiltinEntry){"str_from_int", "nr_str_from_int"}, (BuiltinEntry){"str_from_float", "nr_str_from_float"}, (BuiltinEntry){"str_contains", "nr_str_contains"}, (BuiltinEntry){"str_starts_with", "nr_str_starts_with"}, (BuiltinEntry){"str_ends_with", "nr_str_ends_with"}, (BuiltinEntry){"str_slice", "nr_str_slice"}, (BuiltinEntry){"str_find", "nr_str_find"}, (BuiltinEntry){"str_upper", "nr_str_upper"}, (BuiltinEntry){"str_lower", "nr_str_lower"}, (BuiltinEntry){"str_repeat", "nr_str_repeat"}, (BuiltinEntry){"to_int", "nr_val_to_int"}, (BuiltinEntry){"to_float", "nr_val_to_float"}, (BuiltinEntry){"as_int", "nr_as_int"}, (BuiltinEntry){"as_float", "nr_as_float"}, (BuiltinEntry){"val_int", "nr_val_int"}, (BuiltinEntry){"val_float", "nr_val_float"}, (BuiltinEntry){"val_str", "nr_val_str"}, (BuiltinEntry){"alloc", "malloc"}, (BuiltinEntry){"free", "free"}, (BuiltinEntry){"arena_new", "nr_arena_new"}, (BuiltinEntry){"arena_free", "nr_arena_free"}, (BuiltinEntry){"arena_reset", "nr_arena_reset"}, (BuiltinEntry){"arena_alloc", "nr_arena_alloc"}, (BuiltinEntry){"arena_list_new", "nr_arena_list_new"}, (BuiltinEntry){"arena_str_new", "nr_arena_str_new"}, (BuiltinEntry){"arena_str_new_len", "nr_arena_str_new_len"}, (BuiltinEntry){"read_file_bin", "nr_read_file_bin"}, (BuiltinEntry){"write_file_bin", "nr_write_file_bin"}, (BuiltinEntry){"open", "nr_file_open"}, (BuiltinEntry){"file_open", "nr_file_open"}, (BuiltinEntry){"file_open_safe", "nr_file_open_safe"}, (BuiltinEntry){"file_close", "nr_file_close"}, (BuiltinEntry){"file_write", "nr_file_write"}, (BuiltinEntry){"file_write_str", "nr_file_write_str"}, (BuiltinEntry){"file_write_line", "nr_file_write_line"}, (BuiltinEntry){"file_write_int", "nr_file_write_int"}, (BuiltinEntry){"file_write_float", "nr_file_write_float"}, (BuiltinEntry){"file_read_all", "nr_file_read_all"}, (BuiltinEntry){"file_read_line", "nr_file_read_line"}, (BuiltinEntry){"file_eof", "nr_file_eof"}, (BuiltinEntry){"file_exists", "nr_file_exists"}, (BuiltinEntry){"file_size", "nr_file_size"}, (BuiltinEntry){"dir_create", "nr_dir_create"}, (BuiltinEntry){"dir_remove", "nr_dir_remove"}, (BuiltinEntry){"dir_exists", "nr_dir_exists"}, (BuiltinEntry){"dir_list", "nr_dir_list"}, (BuiltinEntry){"dir_cwd", "nr_dir_cwd"}, (BuiltinEntry){"dir_chdir", "nr_dir_chdir"}, (BuiltinEntry){"path_join", "nr_path_join"}, (BuiltinEntry){"path_ext", "nr_path_ext"}, (BuiltinEntry){"path_basename", "nr_path_basename"}, (BuiltinEntry){"path_dirname", "nr_path_dirname"}, (BuiltinEntry){"remove_file", "nr_remove"}, (BuiltinEntry){"rename_file", "nr_rename"}, (BuiltinEntry){"thread_spawn", "nr_thread_spawn"}, (BuiltinEntry){"thread_join", "nr_thread_join"}, (BuiltinEntry){"mutex_new", "nr_mutex_new"}, (BuiltinEntry){"mutex_lock", "nr_mutex_lock"}, (BuiltinEntry){"mutex_unlock", "nr_mutex_unlock"}, (BuiltinEntry){"mutex_free", "nr_mutex_free"}, (BuiltinEntry){"cond_new", "nr_cond_new"}, (BuiltinEntry){"cond_wait", "nr_cond_wait"}, (BuiltinEntry){"cond_signal", "nr_cond_signal"}, (BuiltinEntry){"cond_broadcast", "nr_cond_broadcast"}, (BuiltinEntry){"cond_free", "nr_cond_free"}, (BuiltinEntry){"sleep_ms", "nr_sleep_ms"}, (BuiltinEntry){"atomic_add", "nr_atomic_add"}, (BuiltinEntry){"atomic_sub", "nr_atomic_sub"}, (BuiltinEntry){"atomic_load", "nr_atomic_load"}, (BuiltinEntry){"atomic_store", "nr_atomic_store"}, (BuiltinEntry){"atomic_cas", "nr_atomic_cas"}, (BuiltinEntry){"channel_new", "nr_channel_new"}, (BuiltinEntry){"channel_send", "nr_channel_send"}, (BuiltinEntry){"channel_recv", "nr_channel_recv"}, (BuiltinEntry){"channel_close", "nr_channel_close"}, (BuiltinEntry){"channel_free", "nr_channel_free"}, (BuiltinEntry){"channel_recv_val", "nr_channel_recv_val"}, (BuiltinEntry){"channel_drain", "nr_channel_drain"}, (BuiltinEntry){"channel_has_data", "nr_channel_has_data"}, (BuiltinEntry){"pool_new", "nr_pool_new"}, (BuiltinEntry){"pool_submit", "nr_pool_submit"}, (BuiltinEntry){"pool_shutdown", "nr_pool_shutdown"}, (BuiltinEntry){"parallel_for", "nr_parallel_for"}, (BuiltinEntry){"rand_seed", "nr_rand_seed"}, (BuiltinEntry){"rand_int", "nr_rand_int"}, (BuiltinEntry){"rand_float", "nr_rand_float"}, (BuiltinEntry){"time_now", "nr_time_now"}, (BuiltinEntry){"time_ms", "nr_time_ms"}, (BuiltinEntry){"str_format", "nr_str_format"}, (BuiltinEntry){"str_strip", "nr_str_strip"}, (BuiltinEntry){"str_lstrip", "nr_str_lstrip"}, (BuiltinEntry){"str_rstrip", "nr_str_rstrip"}, (BuiltinEntry){"str_split", "nr_str_split"}, (BuiltinEntry){"writer_new", "nr_writer_new"}, (BuiltinEntry){"writer_free", "nr_writer_free"}, (BuiltinEntry){"writer_pos", "nr_writer_pos"}, (BuiltinEntry){"write_bytes", "nr_write_bytes"}, (BuiltinEntry){"write_i8", "nr_write_i8"}, (BuiltinEntry){"write_i16", "nr_write_i16"}, (BuiltinEntry){"write_i32", "nr_write_i32"}, (BuiltinEntry){"write_i64", "nr_write_i64"}, (BuiltinEntry){"write_u8", "nr_write_u8"}, (BuiltinEntry){"write_u16", "nr_write_u16"}, (BuiltinEntry){"write_u32", "nr_write_u32"}, (BuiltinEntry){"write_u64", "nr_write_u64"}, (BuiltinEntry){"write_f32", "nr_write_f32"}, (BuiltinEntry){"write_f64", "nr_write_f64"}, (BuiltinEntry){"write_bool", "nr_write_bool"}, (BuiltinEntry){"write_str", "nr_write_str"}, (BuiltinEntry){"writer_to_bytes", "nr_writer_to_bytes"}, (BuiltinEntry){"reader_new", "nr_reader_new"}, (BuiltinEntry){"reader_free", "nr_reader_free"}, (BuiltinEntry){"reader_pos", "nr_reader_pos"}, (BuiltinEntry){"read_bytes", "nr_read_bytes"}, (BuiltinEntry){"read_i8", "nr_read_i8"}, (BuiltinEntry){"read_i16", "nr_read_i16"}, (BuiltinEntry){"read_i32", "nr_read_i32"}, (BuiltinEntry){"read_i64", "nr_read_i64"}, (BuiltinEntry){"read_u8", "nr_read_u8"}, (BuiltinEntry){"read_u16", "nr_read_u16"}, (BuiltinEntry){"read_u32", "nr_read_u32"}, (BuiltinEntry){"read_u64", "nr_read_u64"}, (BuiltinEntry){"read_f32", "nr_read_f32"}, (BuiltinEntry){"read_f64", "nr_read_f64"}, (BuiltinEntry){"read_bool", "nr_read_bool"}, (BuiltinEntry){"read_str", "nr_read_str"}, (BuiltinEntry){"", ""}};

int64_t native_codegen_call__is_addressable_lvalue(CompilerState* restrict s, const AstNode* restrict node);
char* native_codegen_call_lookup_builtin(const NrStr* name);
NrStr* native_codegen_call_native_call_type_cast(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_call_ptr_ops(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_call_abs_min_max(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_call_len(CompilerState* restrict s, const AstCall* restrict node);
NrStr* native_codegen_call_native_call_struct_ctor(CompilerState* restrict s, const NrStr* restrict fname, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_compile_print(CompilerState* restrict s, const AstCall* restrict pc);
void native_codegen_call__emit_line(CompilerState* restrict s, const NrStr* restrict line);
NrStr* native_codegen_call_native_compile_call(CompilerState* restrict s, const AstNode* restrict node);
int main(void);

int64_t native_codegen_call__is_addressable_lvalue(CompilerState* restrict s, const AstNode* restrict node) {
    "True if `node` is an addressable value expression — Name in scope,\n    Attribute on an addressable base, or Subscript of a known array.";
    if ((node == NULL)) {
        return 0;
    }
    if ((node->tag == TAG_NAME)) {
        AstName* n = node->data;
        if (strmap_strmap_has((&s->local_vars), n->id)) {
            return 1;
        }
        if (strmap_strmap_has((&s->func_args), n->id)) {
            return 1;
        }
        if (strmap_strmap_has((&s->mutable_globals), n->id)) {
            return 1;
        }
        if (strmap_strmap_has((&s->constants), n->id)) {
            return 1;
        }
        if (strmap_strmap_has((&s->array_vars), n->id)) {
            return 1;
        }
        return 0;
    }
    if ((node->tag == TAG_ATTRIBUTE)) {
        AstAttribute* a = node->data;
        return native_codegen_call__is_addressable_lvalue(s, a->value);
    }
    if ((node->tag == TAG_SUBSCRIPT)) {
        AstSubscript* sb = node->data;
        if (((sb->value != NULL) && (sb->value->tag == TAG_NAME))) {
            AstName* sn = sb->value->data;
            if (strmap_strmap_has((&s->array_vars), sn->id)) {
                return 1;
            }
        }
        return 0;
    }
    return 0;
}

char* native_codegen_call_lookup_builtin(const NrStr* name) {
    "Look up a builtin function name. Returns C name or NULL.";
    if ((name == NULL)) {
        return NULL;
    }
    if ((name->data == NULL)) {
        return NULL;
    }
    int32_t i = (int32_t)(0);
    while ((builtin_map[i].key[0] != 0)) {
        if ((strcmp(name->data, builtin_map[i].key) == 0)) {
            return builtin_map[i].value;
        }
        i = (int32_t)((i + 1));
    }
    return NULL;
}

NrStr* native_codegen_call_native_call_type_cast(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str) {
    "Handle int(), float(), str(), cast(), cast_int, etc. Returns NULL if not a cast.";
    if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"int",.len=3})) && (node->args.count == 1))) {
        NrStr* e = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        return nr_str_format("((int64_t)(%s))", e->data);
    }
    if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"float",.len=5})) && (node->args.count == 1))) {
        NrStr* e2 = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        return nr_str_format("((double)(%s))", e2->data);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_int",.len=8}))) {
        return nr_str_format("((int64_t)(%s))", arg_str->data);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_float",.len=10}))) {
        return nr_str_format("((double)(%s))", arg_str->data);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_byte",.len=9}))) {
        return nr_str_format("((uint8_t)(%s))", arg_str->data);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_bool",.len=9}))) {
        return nr_str_format("((int)(%s))", arg_str->data);
    }
    return NULL;
}

void native_codegen_call__emit_line(CompilerState* restrict s, const NrStr* restrict line) {
    for (int64_t i = 0; i < s->indent; i++) {
        nr_write_text(s->lines, nr_str_new("    "));
    }
    nr_write_text(s->lines, line);
    nr_write_text(s->lines, nr_str_new("\n"));
}

NrStr* native_codegen_call_native_call_ptr_ops(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str) {
    "Handle addr_of, ref, deref, cast_ptr. Returns NULL if not a ptr op.";
    if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"addr_of",.len=7})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"ref",.len=3})))) {
        return nr_str_format("(&%s)", arg_str->data);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"deref",.len=5}))) {
        if ((node->args.count == 2)) {
            NrStr* ptr_e = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
            NrStr* val_e = native_codegen_expr_native_compile_expr(s, node->args.items[1]);
            native_codegen_call__emit_line(s, nr_str_format("*(%s) = %s;", ptr_e->data, val_e->data));
            return nr_str_new("(void)0");
        }
        return nr_str_format("(*(%s))", arg_str->data);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"deref_set",.len=9}))) {
        NrStr* ptr_e2 = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        NrStr* val_e2 = native_codegen_expr_native_compile_expr(s, node->args.items[1]);
        return nr_str_format("(*(%s) = %s)", ptr_e2->data, val_e2->data);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_ptr",.len=8}))) {
        return nr_str_format("((void*)(%s))", arg_str->data);
    }
    return NULL;
}

NrStr* native_codegen_call_native_call_abs_min_max(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str) {
    "Handle abs(), min(), max(). Returns NULL if not applicable.";
    if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"abs",.len=3})) && (node->args.count == 1))) {
        NrStr* t = native_infer_native_infer_type(s, node->args.items[0]);
        NrStr* e = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        if (nr_str_eq(t, (&(NrStr){.data=(char*)"double",.len=6}))) {
            return nr_str_format("fabs(%s)", e->data);
        }
        return nr_str_format("llabs((long long)(%s))", e->data);
    }
    if ((node->args.count == 2)) {
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"min",.len=3})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"max",.len=3})))) {
            NrStr* t2 = native_infer_native_infer_type(s, node->args.items[0]);
            NrStr* a = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
            NrStr* b = native_codegen_expr_native_compile_expr(s, node->args.items[1]);
            if (nr_str_eq(t2, (&(NrStr){.data=(char*)"double",.len=6}))) {
                if (nr_str_eq(fname, (&(NrStr){.data=(char*)"min",.len=3}))) {
                    return nr_str_format("fmin(%s, %s)", a->data, b->data);
                }
                return nr_str_format("fmax(%s, %s)", a->data, b->data);
            }
            char* op = "<";
            if (nr_str_eq(fname, (&(NrStr){.data=(char*)"max",.len=3}))) {
                op = ">";
            }
            return nr_str_format("((%s) %s (%s) ? (%s) : (%s))", a->data, op, b->data, a->data, b->data);
        }
    }
    return NULL;
}

NrStr* native_codegen_call_native_call_len(CompilerState* restrict s, const AstCall* restrict node) {
    "Compile len(x) with type dispatch.";
    AstNode* arg = node->args.items[0];
    NrStr* arg_expr = native_codegen_expr_native_compile_expr(s, arg);
    if ((arg->tag == TAG_NAME)) {
        AstName* an = arg->data;
        ArrayInfo* ai = strmap_strmap_get((&s->array_vars), an->id);
        if ((ai != NULL)) {
            return ai->size;
        }
        NrStr* et = strmap_strmap_get((&s->list_vars), an->id);
        if ((et != NULL)) {
            NrStr* ln = strmap_strmap_get((&s->typed_lists), et);
            if ((ln != NULL)) {
                return nr_str_format("%s_len(%s)", ln->data, arg_expr->data);
            }
            return nr_str_format("%s->len", arg_expr->data);
        }
    }
    NrStr* t = native_infer_native_infer_type(s, arg);
    NrStr* t_base = native_infer__strip_ptr(t);
    NrStr* len_method = nr_str_concat(t_base, (&(NrStr){.data=(char*)"___len__",.len=8}));
    if ((strmap_strmap_has((&s->structs), t_base) && strmap_strmap_has((&s->func_ret_types), len_method))) {
        return nr_str_format("%s(&(%s))", len_method->data, arg_expr->data);
    }
    if (nr_str_eq(t, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
        return nr_str_format("nr_str_len(%s)", arg_expr->data);
    }
    if (nr_str_eq(t, (&(NrStr){.data=(char*)"NrList*",.len=7}))) {
        return nr_str_format("nr_list_len(%s)", arg_expr->data);
    }
    if (native_infer__ends_with_star(t)) {
        return nr_str_format("%s->len", arg_expr->data);
    }
    return nr_str_format("nr_list_len(%s)", arg_expr->data);
}

NrStr* native_codegen_call_native_call_struct_ctor(CompilerState* restrict s, const NrStr* restrict fname, const NrStr* restrict arg_str) {
    "Compile StructName(args) → compound literal or _new().";
    NrStr* init_key = nr_str_concat(fname, (&(NrStr){.data=(char*)"___init__",.len=9}));
    if (strmap_strmap_has((&s->func_ret_types), init_key)) {
        return nr_str_format("%s_new(%s)", fname->data, arg_str->data);
    }
    if ((nr_str_len(arg_str) == 0)) {
        return nr_str_format("(%s){0}", fname->data);
    }
    return nr_str_format("(%s){%s}", fname->data, arg_str->data);
}

NrStr* native_codegen_call_native_compile_print(CompilerState* restrict s, const AstCall* restrict pc) {
    "Compile print(args) → printf with type-dispatched format strings.";
    if ((pc->args.count == 0)) {
        return nr_str_new("printf(\"\\n\")");
    }
    NrStr* fmt = nr_str_new("");
    NrStr* args_c = nr_str_new("");
    for (int64_t i = 0; i < pc->args.count; i++) {
        if ((i > 0)) {
            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)" ",.len=1}));
        }
        AstNode* arg = pc->args.items[i];
        NrStr* t = native_infer_native_infer_type(s, arg);
        NrStr* expr = native_codegen_expr_native_compile_expr(s, arg);
        if ((nr_str_eq(t, (&(NrStr){.data=(char*)"double",.len=6})) || nr_str_eq(t, (&(NrStr){.data=(char*)"float",.len=5})))) {
            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%g",.len=2}));
            args_c = nr_str_concat(args_c, nr_str_format(", %s", expr->data));
        } else 
        if (nr_str_eq(t, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%.*s",.len=4}));
            args_c = nr_str_concat(args_c, nr_str_format(", (int)(%s)->len, (%s)->data", expr->data, expr->data));
        } else 
        if (nr_str_eq(t, (&(NrStr){.data=(char*)"int",.len=3}))) {
            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%d",.len=2}));
            args_c = nr_str_concat(args_c, nr_str_format(", %s", expr->data));
        } else {
            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%lld",.len=4}));
            args_c = nr_str_concat(args_c, nr_str_format(", (long long)(%s)", expr->data));
        }
    }
    fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"\\n",.len=2}));
    return nr_str_format("printf(\"%s\"%s)", fmt->data, args_c->data);
}

NrStr* native_codegen_call_native_compile_call(CompilerState* restrict s, const AstNode* restrict node) {
    "Compile a function call expression.";
    AstCall* pc = node->data;
    AstNode* func = pc->func;
    NrStr** arg_parts = NULL;
    if ((pc->args.count > 0)) {
        arg_parts = malloc((((int64_t)(pc->args.count)) * 8));
        for (int64_t i = 0; i < pc->args.count; i++) {
            NR_PREFETCH(&arg_parts[i + 8], 0, 1);
            arg_parts[i] = native_codegen_expr_native_compile_expr(s, pc->args.items[i]);
        }
    }
    if (((pc->args.count > 0) && (func->tag == TAG_NAME))) {
        AstName* cn_fn = func->data;
        ParamTypeList* ptl_lookup = strmap_strmap_get((&s->func_param_types), cn_fn->id);
        if ((ptl_lookup != NULL)) {
            for (int64_t ai = 0; ai < pc->args.count; ai++) {
                NR_PREFETCH(&arg_parts[ai + 8], 0, 1);
                if ((ai >= ptl_lookup->count)) {
                    break;
                }
                NrStr* pt = ptl_lookup->types[ai];
                if ((pt == NULL)) {
                    continue;
                }
                if ((native_infer__ends_with_star(pt) == 0)) {
                    continue;
                }
                if ((nr_str_eq(pt, (&(NrStr){.data=(char*)"void*",.len=5})) || nr_str_eq(pt, (&(NrStr){.data=(char*)"const void*",.len=11})) || nr_str_eq(pt, (&(NrStr){.data=(char*)"NrStr*",.len=6})))) {
                    continue;
                }
                AstNode* arg_node = pc->args.items[ai];
                if ((native_codegen_call__is_addressable_lvalue(s, arg_node) == 0)) {
                    continue;
                }
                NrStr* at = native_infer_native_infer_type(s, arg_node);
                if (nr_str_eq(at, pt)) {
                    continue;
                }
                NrStr* expected = nr_str_concat(at, nr_str_new("*"));
                if ((nr_str_eq(expected, pt) == 0)) {
                    continue;
                }
                arg_parts[ai] = nr_str_format("(&(%s))", arg_parts[ai]->data);
            }
        }
    }
    NrStr* arg_str = nr_str_new("");
    for (int64_t i = 0; i < pc->args.count; i++) {
        NR_PREFETCH(&arg_parts[i + 8], 0, 1);
        if ((i > 0)) {
            arg_str = nr_str_concat(arg_str, (&(NrStr){.data=(char*)", ",.len=2}));
        }
        arg_str = nr_str_concat(arg_str, arg_parts[i]);
    }
    if ((func->tag == TAG_NAME)) {
        AstName* fn = func->data;
        NrStr* fname = fn->id;
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"test_assert",.len=11}))) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            if ((pc->args.count == 2)) {
                NrStr* cond = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
                NrStr* msg = native_codegen_expr_native_compile_expr(s, pc->args.items[1]);
                return nr_str_format("nr_test_assert_msg(%s, %s)", cond->data, msg->data);
            }
            return nr_str_format("nr_test_assert(%s)", arg_str->data);
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"test_assert_eq",.len=14}))) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("nr_test_assert_eq(%s)", arg_str->data);
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"heap_allocated",.len=14}))) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_new("nr_heap_allocated()");
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"heap_assert",.len=11})) && (pc->args.count == 1))) {
            NrStr* val = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("nr_heap_assert(%s, __FILE__, __LINE__)", val->data);
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"heap_assert_delta",.len=17})) && (pc->args.count == 2))) {
            NrStr* snap_e = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
            NrStr* delta_e = native_codegen_expr_native_compile_expr(s, pc->args.items[1]);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("nr_heap_assert_delta(%s, %s, __FILE__, __LINE__)", snap_e->data, delta_e->data);
        }
        if (strmap_strmap_has((&s->structs), fname)) {
            NrStr* r = native_codegen_call_native_call_struct_ctor(s, fname, arg_str);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r;
        }
        NrStr* r2 = native_codegen_call_native_call_abs_min_max(s, fname, pc, arg_str);
        if ((r2 != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r2;
        }
        NrStr* r3 = native_codegen_call_native_call_type_cast(s, fname, pc, arg_str);
        if ((r3 != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r3;
        }
        NrStr* r4 = native_codegen_call_native_call_ptr_ops(s, fname, pc, arg_str);
        if ((r4 != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r4;
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"len",.len=3})) && (pc->args.count == 1))) {
            NrStr* r5 = native_codegen_call_native_call_len(s, pc);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r5;
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"exit",.len=4}))) {
            NrStr* code = arg_str;
            if ((nr_str_len(code) == 0)) {
                code = nr_str_new("0");
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("exit(%s)", code->data);
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"input",.len=5}))) {
            NrStr* prompt = arg_str;
            if ((nr_str_len(prompt) == 0)) {
                prompt = nr_str_new("NULL");
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("mp_input(%s)", prompt->data);
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"sort",.len=4})) && (pc->args.count == 2))) {
            AstNode* arr_node = pc->args.items[0];
            NrStr* arr_e = native_codegen_expr_native_compile_expr(s, arr_node);
            NrStr* cmp_e = native_codegen_expr_native_compile_expr(s, pc->args.items[1]);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            if ((arr_node->tag == TAG_NAME)) {
                AstName* arr_n = arr_node->data;
                ArrayInfo* arr_ai = strmap_strmap_get((&s->array_vars), arr_n->id);
                if ((arr_ai != NULL)) {
                    return nr_str_format("qsort(%s, %s, sizeof(%s), (int(*)(const void*, const void*))%s)", arr_e->data, arr_ai->size->data, arr_ai->elem_type->data, cmp_e->data);
                }
            }
            return nr_str_format("qsort(%s, 0, 0, (int(*)(const void*, const void*))%s)", arr_e->data, cmp_e->data);
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"str",.len=3})) && (pc->args.count == 1))) {
            NrStr* st = native_infer_native_infer_type(s, pc->args.items[0]);
            NrStr* se = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            if (nr_str_eq(st, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
                return se;
            }
            if (nr_str_eq(st, (&(NrStr){.data=(char*)"double",.len=6}))) {
                return nr_str_format("nr_str_from_float(%s)", se->data);
            }
            return nr_str_format("nr_str_from_int((int64_t)(%s))", se->data);
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"sizeof",.len=6})) && (pc->args.count == 1))) {
            AstNode* sarg = pc->args.items[0];
            if ((sarg->tag == TAG_NAME)) {
                AstName* sn = sarg->data;
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("sizeof(%s)", sn->id->data);
            }
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"print",.len=5}))) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return native_codegen_call_native_compile_print(s, pc);
        }
        int64_t is_str_obj_func = 0;
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"str_len",.len=7})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_eq",.len=6})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_concat",.len=10})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_free",.len=8})))) {
            is_str_obj_func = 1;
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"str_contains",.len=12})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_starts_with",.len=15})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_ends_with",.len=13})))) {
            is_str_obj_func = 1;
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"str_slice",.len=9})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_find",.len=8})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_upper",.len=9})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_lower",.len=9})))) {
            is_str_obj_func = 1;
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"str_repeat",.len=10})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_strip",.len=9})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"str_split",.len=9})))) {
            is_str_obj_func = 1;
        }
        if (is_str_obj_func) {
            NrStr* coerced_parts = nr_str_new("");
            for (int64_t ci = 0; ci < pc->args.count; ci++) {
                if ((ci > 0)) {
                    coerced_parts = nr_str_concat(coerced_parts, (&(NrStr){.data=(char*)", ",.len=2}));
                }
                AstNode* ca = pc->args.items[ci];
                if ((ca->tag == TAG_CONSTANT)) {
                    AstConstant* cac = ca->data;
                    if (((cac->kind == CONST_STR) && (cac->str_val != NULL))) {
                        NrStr* escaped_c = native_codegen_expr_native_compile_expr(s, ca);
                        int64_t slen_c = nr_str_len(cac->str_val);
                        coerced_parts = nr_str_concat(coerced_parts, nr_str_format("(&(NrStr){.data=(char*)%s,.len=%lld})", escaped_c->data, slen_c));
                        continue;
                    }
                }
                coerced_parts = nr_str_concat(coerced_parts, native_codegen_expr_native_compile_expr(s, ca));
            }
            arg_str = coerced_parts;
        }
        char* c_name = native_codegen_call_lookup_builtin(fname);
        if ((c_name != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("%s(%s)", c_name, arg_str->data);
        }
        if (strmap_strmap_has((&s->func_ret_types), fname)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("%s(%s)", fname->data, arg_str->data);
        }
        if ((arg_parts != NULL)) {
            free(arg_parts);
        }
        return nr_str_format("%s(%s)", fname->data, arg_str->data);
    }
    if ((func->tag == TAG_ATTRIBUTE)) {
        AstAttribute* pa = func->data;
        NrStr* obj_str = native_codegen_expr_native_compile_expr(s, pa->value);
        NrStr* obj_type = native_infer_native_infer_type(s, pa->value);
        NrStr* base = native_infer__strip_ptr(obj_type);
        NrStr* attr = pa->attr;
        if (((pa->value != NULL) && (pa->value->tag == TAG_ATTRIBUTE))) {
            AstAttribute* inner = pa->value->data;
            if (((inner->value != NULL) && (inner->value->tag == TAG_NAME))) {
                AstName* mod_n = inner->value->data;
                if ((nr_str_eq(mod_n->id, nr_str_new("os")) && nr_str_eq(inner->attr, nr_str_new("path")))) {
                    NrStr* c_os_path = nr_str_new("");
                    if (nr_str_eq(attr, nr_str_new("join"))) {
                        c_os_path = nr_str_new("nr_path_join");
                    } else 
                    if (nr_str_eq(attr, nr_str_new("basename"))) {
                        c_os_path = nr_str_new("nr_path_basename");
                    } else 
                    if (nr_str_eq(attr, nr_str_new("dirname"))) {
                        c_os_path = nr_str_new("nr_path_dirname");
                    } else 
                    if (nr_str_eq(attr, nr_str_new("ext"))) {
                        c_os_path = nr_str_new("nr_path_ext");
                    }
                    if ((nr_str_len(c_os_path) > 0)) {
                        if ((arg_parts != NULL)) {
                            free(arg_parts);
                        }
                        return nr_str_format("%s(%s)", c_os_path->data, arg_str->data);
                    }
                }
            }
        }
        if (((pa->value != NULL) && (pa->value->tag == TAG_NAME))) {
            AstName* os_n = pa->value->data;
            if (nr_str_eq(os_n->id, nr_str_new("os"))) {
                NrStr* c_os = nr_str_new("");
                if (nr_str_eq(attr, nr_str_new("exists"))) {
                    c_os = nr_str_new("nr_file_exists");
                } else 
                if (nr_str_eq(attr, nr_str_new("file_size"))) {
                    c_os = nr_str_new("nr_file_size");
                } else 
                if (nr_str_eq(attr, nr_str_new("remove"))) {
                    c_os = nr_str_new("nr_remove");
                } else 
                if (nr_str_eq(attr, nr_str_new("rename"))) {
                    c_os = nr_str_new("nr_rename");
                } else 
                if (nr_str_eq(attr, nr_str_new("mkdir"))) {
                    c_os = nr_str_new("nr_dir_create");
                } else 
                if (nr_str_eq(attr, nr_str_new("rmdir"))) {
                    c_os = nr_str_new("nr_dir_remove");
                } else 
                if (nr_str_eq(attr, nr_str_new("isdir"))) {
                    c_os = nr_str_new("nr_dir_exists");
                } else 
                if (nr_str_eq(attr, nr_str_new("getcwd"))) {
                    c_os = nr_str_new("nr_dir_cwd");
                } else 
                if (nr_str_eq(attr, nr_str_new("listdir"))) {
                    c_os = nr_str_new("nr_dir_list");
                } else 
                if (nr_str_eq(attr, nr_str_new("chdir"))) {
                    c_os = nr_str_new("nr_dir_chdir");
                }
                if ((nr_str_len(c_os) > 0)) {
                    if ((arg_parts != NULL)) {
                        free(arg_parts);
                    }
                    return nr_str_format("%s(%s)", c_os->data, arg_str->data);
                }
            }
        }
        if (nr_str_eq(obj_type, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
            NrStr* c_fn = nr_str_format("nr_str_%s", attr->data);
            NrStr* all_a = obj_str;
            if ((nr_str_len(arg_str) > 0)) {
                all_a = nr_str_format("%s, %s", obj_str->data, arg_str->data);
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("%s(%s)", c_fn->data, all_a->data);
        }
        if (((pa->value != NULL) && (pa->value->tag == TAG_NAME))) {
            AstName* obj_n = pa->value->data;
            NrStr* et_lookup = strmap_strmap_get((&s->list_vars), obj_n->id);
            if ((et_lookup != NULL)) {
                NrStr* ln_lookup = strmap_strmap_get((&s->typed_lists), et_lookup);
                if ((ln_lookup != NULL)) {
                    NrStr* c_method = nr_str_format("%s_%s", ln_lookup->data, attr->data);
                    NrStr* all_tl = obj_str;
                    if ((nr_str_len(arg_str) > 0)) {
                        all_tl = nr_str_format("%s, %s", obj_str->data, arg_str->data);
                    }
                    if ((arg_parts != NULL)) {
                        free(arg_parts);
                    }
                    return nr_str_format("%s(%s)", c_method->data, all_tl->data);
                }
            }
        }
        if (nr_str_eq(obj_type, (&(NrStr){.data=(char*)"NrList*",.len=7}))) {
            if ((nr_str_eq(attr, (&(NrStr){.data=(char*)"append",.len=6})) && (pc->args.count == 1))) {
                NrStr* v = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
                NrStr* vt = native_infer_native_infer_type(s, pc->args.items[0]);
                NrStr* boxed = v;
                if (nr_str_eq(vt, (&(NrStr){.data=(char*)"double",.len=6}))) {
                    boxed = nr_str_format("nr_val_float(%s)", v->data);
                } else 
                if (nr_str_eq(vt, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
                    boxed = nr_str_format("nr_val_str(%s)", v->data);
                } else {
                    boxed = nr_str_format("nr_val_int((int64_t)(%s))", v->data);
                }
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("nr_list_append(%s, %s)", obj_str->data, boxed->data);
            }
            if (nr_str_eq(attr, (&(NrStr){.data=(char*)"pop",.len=3}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("nr_list_pop(%s)", obj_str->data);
            }
            if (nr_str_eq(attr, (&(NrStr){.data=(char*)"len",.len=3}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("nr_list_len(%s)", obj_str->data);
            }
        }
        if (nr_str_eq(obj_type, (&(NrStr){.data=(char*)"NrFile",.len=6}))) {
            if (nr_str_eq(attr, (&(NrStr){.data=(char*)"write",.len=5}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("nr_file_write(%s, %s)", obj_str->data, arg_str->data);
            }
            if (nr_str_eq(attr, (&(NrStr){.data=(char*)"write_line",.len=10}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("nr_file_write_line(%s, %s)", obj_str->data, arg_str->data);
            }
            if (nr_str_eq(attr, (&(NrStr){.data=(char*)"read",.len=4}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("nr_file_read_all(%s)", obj_str->data);
            }
            if (nr_str_eq(attr, (&(NrStr){.data=(char*)"close",.len=5}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return nr_str_format("nr_file_close(%s)", obj_str->data);
            }
        }
        if (strmap_strmap_has((&s->structs), base)) {
            NrStr* self_arg = obj_str;
            if ((native_infer__ends_with_star(obj_type) == 0)) {
                self_arg = nr_str_format("&(%s)", obj_str->data);
            }
            NrStr* all_args = self_arg;
            if ((nr_str_len(arg_str) > 0)) {
                all_args = nr_str_format("%s, %s", self_arg->data, arg_str->data);
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return nr_str_format("%s_%s(%s)", base->data, attr->data, all_args->data);
        }
        NrStr* all_args2 = obj_str;
        if ((nr_str_len(arg_str) > 0)) {
            all_args2 = nr_str_format("%s, %s", obj_str->data, arg_str->data);
        }
        if ((arg_parts != NULL)) {
            free(arg_parts);
        }
        return nr_str_format("%s(%s)", attr->data, all_args2->data);
    }
    NrStr* func_str = native_codegen_expr_native_compile_expr(s, func);
    if ((arg_parts != NULL)) {
        free(arg_parts);
    }
    return nr_str_format("%s(%s)", func_str->data, arg_str->data);
}
