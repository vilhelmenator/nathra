/* mpy_stamp: 1774568699.738692 */
#include "micropy_rt.h"
#include "native_codegen_call.h"

static inline BuiltinEntry _mp_make_BuiltinEntry(char* key, char* value) {
    BuiltinEntry _s = {0};
    _s.key = key;
    _s.value = value;
    return _s;
}

BuiltinEntry builtin_map[152] = {(BuiltinEntry){"print_int", "mp_print_int"}, (BuiltinEntry){"print_float", "mp_print_float"}, (BuiltinEntry){"print_str", "mp_print_str"}, (BuiltinEntry){"print_bool", "mp_print_bool"}, (BuiltinEntry){"print_val", "mp_print_val"}, (BuiltinEntry){"list_new", "mp_list_new"}, (BuiltinEntry){"list_append", "mp_list_append"}, (BuiltinEntry){"list_get", "mp_list_get"}, (BuiltinEntry){"list_set", "mp_list_set"}, (BuiltinEntry){"list_len", "mp_list_len"}, (BuiltinEntry){"list_pop", "mp_list_pop"}, (BuiltinEntry){"list_free", "mp_list_free"}, (BuiltinEntry){"dict_new", "mp_dict_new"}, (BuiltinEntry){"dict_set", "mp_dict_set"}, (BuiltinEntry){"dict_get", "mp_dict_get"}, (BuiltinEntry){"dict_has", "mp_dict_has"}, (BuiltinEntry){"dict_del", "mp_dict_del"}, (BuiltinEntry){"dict_len", "mp_dict_len"}, (BuiltinEntry){"dict_free", "mp_dict_free"}, (BuiltinEntry){"str_new", "mp_str_new"}, (BuiltinEntry){"str_len", "mp_str_len"}, (BuiltinEntry){"str_concat", "mp_str_concat"}, (BuiltinEntry){"str_eq", "mp_str_eq"}, (BuiltinEntry){"str_print", "mp_str_print"}, (BuiltinEntry){"str_free", "mp_str_free"}, (BuiltinEntry){"str_from_int", "mp_str_from_int"}, (BuiltinEntry){"str_from_float", "mp_str_from_float"}, (BuiltinEntry){"str_contains", "mp_str_contains"}, (BuiltinEntry){"str_starts_with", "mp_str_starts_with"}, (BuiltinEntry){"str_ends_with", "mp_str_ends_with"}, (BuiltinEntry){"str_slice", "mp_str_slice"}, (BuiltinEntry){"str_find", "mp_str_find"}, (BuiltinEntry){"str_upper", "mp_str_upper"}, (BuiltinEntry){"str_lower", "mp_str_lower"}, (BuiltinEntry){"str_repeat", "mp_str_repeat"}, (BuiltinEntry){"to_int", "mp_val_to_int"}, (BuiltinEntry){"to_float", "mp_val_to_float"}, (BuiltinEntry){"as_int", "mp_as_int"}, (BuiltinEntry){"as_float", "mp_as_float"}, (BuiltinEntry){"val_int", "mp_val_int"}, (BuiltinEntry){"val_float", "mp_val_float"}, (BuiltinEntry){"val_str", "mp_val_str"}, (BuiltinEntry){"alloc", "malloc"}, (BuiltinEntry){"free", "free"}, (BuiltinEntry){"arena_new", "mp_arena_new"}, (BuiltinEntry){"arena_free", "mp_arena_free"}, (BuiltinEntry){"arena_reset", "mp_arena_reset"}, (BuiltinEntry){"arena_alloc", "mp_arena_alloc"}, (BuiltinEntry){"arena_list_new", "mp_arena_list_new"}, (BuiltinEntry){"arena_str_new", "mp_arena_str_new"}, (BuiltinEntry){"arena_str_new_len", "mp_arena_str_new_len"}, (BuiltinEntry){"read_file_bin", "mp_read_file_bin"}, (BuiltinEntry){"write_file_bin", "mp_write_file_bin"}, (BuiltinEntry){"open", "mp_file_open"}, (BuiltinEntry){"file_open", "mp_file_open"}, (BuiltinEntry){"file_open_safe", "mp_file_open_safe"}, (BuiltinEntry){"file_close", "mp_file_close"}, (BuiltinEntry){"file_write", "mp_file_write"}, (BuiltinEntry){"file_write_str", "mp_file_write_str"}, (BuiltinEntry){"file_write_line", "mp_file_write_line"}, (BuiltinEntry){"file_write_int", "mp_file_write_int"}, (BuiltinEntry){"file_write_float", "mp_file_write_float"}, (BuiltinEntry){"file_read_all", "mp_file_read_all"}, (BuiltinEntry){"file_read_line", "mp_file_read_line"}, (BuiltinEntry){"file_eof", "mp_file_eof"}, (BuiltinEntry){"file_exists", "mp_file_exists"}, (BuiltinEntry){"file_size", "mp_file_size"}, (BuiltinEntry){"dir_create", "mp_dir_create"}, (BuiltinEntry){"dir_remove", "mp_dir_remove"}, (BuiltinEntry){"dir_exists", "mp_dir_exists"}, (BuiltinEntry){"dir_list", "mp_dir_list"}, (BuiltinEntry){"dir_cwd", "mp_dir_cwd"}, (BuiltinEntry){"dir_chdir", "mp_dir_chdir"}, (BuiltinEntry){"path_join", "mp_path_join"}, (BuiltinEntry){"path_ext", "mp_path_ext"}, (BuiltinEntry){"path_basename", "mp_path_basename"}, (BuiltinEntry){"path_dirname", "mp_path_dirname"}, (BuiltinEntry){"remove_file", "mp_remove"}, (BuiltinEntry){"rename_file", "mp_rename"}, (BuiltinEntry){"thread_spawn", "mp_thread_spawn"}, (BuiltinEntry){"thread_join", "mp_thread_join"}, (BuiltinEntry){"mutex_new", "mp_mutex_new"}, (BuiltinEntry){"mutex_lock", "mp_mutex_lock"}, (BuiltinEntry){"mutex_unlock", "mp_mutex_unlock"}, (BuiltinEntry){"mutex_free", "mp_mutex_free"}, (BuiltinEntry){"cond_new", "mp_cond_new"}, (BuiltinEntry){"cond_wait", "mp_cond_wait"}, (BuiltinEntry){"cond_signal", "mp_cond_signal"}, (BuiltinEntry){"cond_broadcast", "mp_cond_broadcast"}, (BuiltinEntry){"cond_free", "mp_cond_free"}, (BuiltinEntry){"sleep_ms", "mp_sleep_ms"}, (BuiltinEntry){"atomic_add", "mp_atomic_add"}, (BuiltinEntry){"atomic_sub", "mp_atomic_sub"}, (BuiltinEntry){"atomic_load", "mp_atomic_load"}, (BuiltinEntry){"atomic_store", "mp_atomic_store"}, (BuiltinEntry){"atomic_cas", "mp_atomic_cas"}, (BuiltinEntry){"channel_new", "mp_channel_new"}, (BuiltinEntry){"channel_send", "mp_channel_send"}, (BuiltinEntry){"channel_recv", "mp_channel_recv"}, (BuiltinEntry){"channel_close", "mp_channel_close"}, (BuiltinEntry){"channel_free", "mp_channel_free"}, (BuiltinEntry){"channel_recv_val", "mp_channel_recv_val"}, (BuiltinEntry){"channel_drain", "mp_channel_drain"}, (BuiltinEntry){"channel_has_data", "mp_channel_has_data"}, (BuiltinEntry){"pool_new", "mp_pool_new"}, (BuiltinEntry){"pool_submit", "mp_pool_submit"}, (BuiltinEntry){"pool_shutdown", "mp_pool_shutdown"}, (BuiltinEntry){"parallel_for", "mp_parallel_for"}, (BuiltinEntry){"rand_seed", "mp_rand_seed"}, (BuiltinEntry){"rand_int", "mp_rand_int"}, (BuiltinEntry){"rand_float", "mp_rand_float"}, (BuiltinEntry){"time_now", "mp_time_now"}, (BuiltinEntry){"time_ms", "mp_time_ms"}, (BuiltinEntry){"str_format", "mp_str_format"}, (BuiltinEntry){"str_strip", "mp_str_strip"}, (BuiltinEntry){"str_lstrip", "mp_str_lstrip"}, (BuiltinEntry){"str_rstrip", "mp_str_rstrip"}, (BuiltinEntry){"str_split", "mp_str_split"}, (BuiltinEntry){"writer_new", "mp_writer_new"}, (BuiltinEntry){"writer_free", "mp_writer_free"}, (BuiltinEntry){"writer_pos", "mp_writer_pos"}, (BuiltinEntry){"write_bytes", "mp_write_bytes"}, (BuiltinEntry){"write_i8", "mp_write_i8"}, (BuiltinEntry){"write_i16", "mp_write_i16"}, (BuiltinEntry){"write_i32", "mp_write_i32"}, (BuiltinEntry){"write_i64", "mp_write_i64"}, (BuiltinEntry){"write_u8", "mp_write_u8"}, (BuiltinEntry){"write_u16", "mp_write_u16"}, (BuiltinEntry){"write_u32", "mp_write_u32"}, (BuiltinEntry){"write_u64", "mp_write_u64"}, (BuiltinEntry){"write_f32", "mp_write_f32"}, (BuiltinEntry){"write_f64", "mp_write_f64"}, (BuiltinEntry){"write_bool", "mp_write_bool"}, (BuiltinEntry){"write_str", "mp_write_str"}, (BuiltinEntry){"writer_to_bytes", "mp_writer_to_bytes"}, (BuiltinEntry){"reader_new", "mp_reader_new"}, (BuiltinEntry){"reader_free", "mp_reader_free"}, (BuiltinEntry){"reader_pos", "mp_reader_pos"}, (BuiltinEntry){"read_bytes", "mp_read_bytes"}, (BuiltinEntry){"read_i8", "mp_read_i8"}, (BuiltinEntry){"read_i16", "mp_read_i16"}, (BuiltinEntry){"read_i32", "mp_read_i32"}, (BuiltinEntry){"read_i64", "mp_read_i64"}, (BuiltinEntry){"read_u8", "mp_read_u8"}, (BuiltinEntry){"read_u16", "mp_read_u16"}, (BuiltinEntry){"read_u32", "mp_read_u32"}, (BuiltinEntry){"read_u64", "mp_read_u64"}, (BuiltinEntry){"read_f32", "mp_read_f32"}, (BuiltinEntry){"read_f64", "mp_read_f64"}, (BuiltinEntry){"read_bool", "mp_read_bool"}, (BuiltinEntry){"read_str", "mp_read_str"}, (BuiltinEntry){"", ""}};

char* native_codegen_call_lookup_builtin(const MpStr* name);
MpStr* native_codegen_call_native_call_type_cast(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_call_ptr_ops(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_call_abs_min_max(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_call_len(CompilerState* restrict s, const AstCall* restrict node);
MpStr* native_codegen_call_native_call_struct_ctor(CompilerState* restrict s, const MpStr* restrict fname, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_compile_print(CompilerState* restrict s, const AstCall* restrict pc);
void native_codegen_call__emit_line(CompilerState* restrict s, const MpStr* restrict line);
MpStr* native_codegen_call_native_compile_call(CompilerState* restrict s, const AstNode* restrict node);
int main(void);

char* native_codegen_call_lookup_builtin(const MpStr* name) {
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

MpStr* native_codegen_call_native_call_type_cast(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str) {
    "Handle int(), float(), str(), cast(), cast_int, etc. Returns NULL if not a cast.";
    if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"int",.len=3})) && (node->args.count == 1))) {
        MpStr* e = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        return mp_str_format("((int64_t)(%s))", e->data);
    }
    if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"float",.len=5})) && (node->args.count == 1))) {
        MpStr* e2 = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        return mp_str_format("((double)(%s))", e2->data);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"cast_int",.len=8}))) {
        return mp_str_format("((int64_t)(%s))", arg_str->data);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"cast_float",.len=10}))) {
        return mp_str_format("((double)(%s))", arg_str->data);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"cast_byte",.len=9}))) {
        return mp_str_format("((uint8_t)(%s))", arg_str->data);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"cast_bool",.len=9}))) {
        return mp_str_format("((int)(%s))", arg_str->data);
    }
    return NULL;
}

void native_codegen_call__emit_line(CompilerState* restrict s, const MpStr* restrict line) {
    for (int64_t i = 0; i < s->indent; i++) {
        mp_write_text(s->lines, mp_str_new("    "));
    }
    mp_write_text(s->lines, line);
    mp_write_text(s->lines, mp_str_new("\n"));
}

MpStr* native_codegen_call_native_call_ptr_ops(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str) {
    "Handle addr_of, ref, deref, cast_ptr. Returns NULL if not a ptr op.";
    if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"addr_of",.len=7})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"ref",.len=3})))) {
        return mp_str_format("(&%s)", arg_str->data);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"deref",.len=5}))) {
        if ((node->args.count == 2)) {
            MpStr* ptr_e = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
            MpStr* val_e = native_codegen_expr_native_compile_expr(s, node->args.items[1]);
            native_codegen_call__emit_line(s, mp_str_format("*(%s) = %s;", ptr_e->data, val_e->data));
            return mp_str_new("(void)0");
        }
        return mp_str_format("(*(%s))", arg_str->data);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"deref_set",.len=9}))) {
        MpStr* ptr_e2 = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        MpStr* val_e2 = native_codegen_expr_native_compile_expr(s, node->args.items[1]);
        return mp_str_format("(*(%s) = %s)", ptr_e2->data, val_e2->data);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"cast_ptr",.len=8}))) {
        return mp_str_format("((void*)(%s))", arg_str->data);
    }
    return NULL;
}

MpStr* native_codegen_call_native_call_abs_min_max(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str) {
    "Handle abs(), min(), max(). Returns NULL if not applicable.";
    if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"abs",.len=3})) && (node->args.count == 1))) {
        MpStr* t = native_infer_native_infer_type(s, node->args.items[0]);
        MpStr* e = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
        if (mp_str_eq(t, (&(MpStr){.data=(char*)"double",.len=6}))) {
            return mp_str_format("fabs(%s)", e->data);
        }
        return mp_str_format("llabs((long long)(%s))", e->data);
    }
    if ((node->args.count == 2)) {
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"min",.len=3})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"max",.len=3})))) {
            MpStr* t2 = native_infer_native_infer_type(s, node->args.items[0]);
            MpStr* a = native_codegen_expr_native_compile_expr(s, node->args.items[0]);
            MpStr* b = native_codegen_expr_native_compile_expr(s, node->args.items[1]);
            if (mp_str_eq(t2, (&(MpStr){.data=(char*)"double",.len=6}))) {
                if (mp_str_eq(fname, (&(MpStr){.data=(char*)"min",.len=3}))) {
                    return mp_str_format("fmin(%s, %s)", a->data, b->data);
                }
                return mp_str_format("fmax(%s, %s)", a->data, b->data);
            }
            char* op = "<";
            if (mp_str_eq(fname, (&(MpStr){.data=(char*)"max",.len=3}))) {
                op = ">";
            }
            return mp_str_format("((%s) %s (%s) ? (%s) : (%s))", a->data, op, b->data, a->data, b->data);
        }
    }
    return NULL;
}

MpStr* native_codegen_call_native_call_len(CompilerState* restrict s, const AstCall* restrict node) {
    "Compile len(x) with type dispatch.";
    AstNode* arg = node->args.items[0];
    MpStr* arg_expr = native_codegen_expr_native_compile_expr(s, arg);
    if ((arg->tag == TAG_NAME)) {
        AstName* an = arg->data;
        ArrayInfo* ai = strmap_strmap_get((&s->array_vars), an->id);
        if ((ai != NULL)) {
            return ai->size;
        }
        MpStr* et = strmap_strmap_get((&s->list_vars), an->id);
        if ((et != NULL)) {
            MpStr* ln = strmap_strmap_get((&s->typed_lists), et);
            if ((ln != NULL)) {
                return mp_str_format("%s_len(%s)", ln->data, arg_expr->data);
            }
            return mp_str_format("%s->len", arg_expr->data);
        }
    }
    MpStr* t = native_infer_native_infer_type(s, arg);
    MpStr* t_base = native_infer__strip_ptr(t);
    MpStr* len_method = mp_str_concat(t_base, (&(MpStr){.data=(char*)"___len__",.len=8}));
    if ((strmap_strmap_has((&s->structs), t_base) && strmap_strmap_has((&s->func_ret_types), len_method))) {
        return mp_str_format("%s(&(%s))", len_method->data, arg_expr->data);
    }
    if (mp_str_eq(t, (&(MpStr){.data=(char*)"MpStr*",.len=6}))) {
        return mp_str_format("mp_str_len(%s)", arg_expr->data);
    }
    if (mp_str_eq(t, (&(MpStr){.data=(char*)"MpList*",.len=7}))) {
        return mp_str_format("mp_list_len(%s)", arg_expr->data);
    }
    if (native_infer__ends_with_star(t)) {
        return mp_str_format("%s->len", arg_expr->data);
    }
    return mp_str_format("mp_list_len(%s)", arg_expr->data);
}

MpStr* native_codegen_call_native_call_struct_ctor(CompilerState* restrict s, const MpStr* restrict fname, const MpStr* restrict arg_str) {
    "Compile StructName(args) → compound literal or _new().";
    MpStr* init_key = mp_str_concat(fname, (&(MpStr){.data=(char*)"___init__",.len=9}));
    if (strmap_strmap_has((&s->func_ret_types), init_key)) {
        return mp_str_format("%s_new(%s)", fname->data, arg_str->data);
    }
    if ((mp_str_len(arg_str) == 0)) {
        return mp_str_format("(%s){0}", fname->data);
    }
    return mp_str_format("(%s){%s}", fname->data, arg_str->data);
}

MpStr* native_codegen_call_native_compile_print(CompilerState* restrict s, const AstCall* restrict pc) {
    "Compile print(args) → printf with type-dispatched format strings.";
    if ((pc->args.count == 0)) {
        return mp_str_new("printf(\"\\n\")");
    }
    MpStr* fmt = mp_str_new("");
    MpStr* args_c = mp_str_new("");
    for (int64_t i = 0; i < pc->args.count; i++) {
        if ((i > 0)) {
            fmt = mp_str_concat(fmt, (&(MpStr){.data=(char*)" ",.len=1}));
        }
        AstNode* arg = pc->args.items[i];
        MpStr* t = native_infer_native_infer_type(s, arg);
        MpStr* expr = native_codegen_expr_native_compile_expr(s, arg);
        if ((mp_str_eq(t, (&(MpStr){.data=(char*)"double",.len=6})) || mp_str_eq(t, (&(MpStr){.data=(char*)"float",.len=5})))) {
            fmt = mp_str_concat(fmt, (&(MpStr){.data=(char*)"%g",.len=2}));
            args_c = mp_str_concat(args_c, mp_str_format(", %s", expr->data));
        } else 
        if (mp_str_eq(t, (&(MpStr){.data=(char*)"MpStr*",.len=6}))) {
            fmt = mp_str_concat(fmt, (&(MpStr){.data=(char*)"%.*s",.len=4}));
            args_c = mp_str_concat(args_c, mp_str_format(", (int)(%s)->len, (%s)->data", expr->data, expr->data));
        } else 
        if (mp_str_eq(t, (&(MpStr){.data=(char*)"int",.len=3}))) {
            fmt = mp_str_concat(fmt, (&(MpStr){.data=(char*)"%d",.len=2}));
            args_c = mp_str_concat(args_c, mp_str_format(", %s", expr->data));
        } else {
            fmt = mp_str_concat(fmt, (&(MpStr){.data=(char*)"%lld",.len=4}));
            args_c = mp_str_concat(args_c, mp_str_format(", (long long)(%s)", expr->data));
        }
    }
    fmt = mp_str_concat(fmt, (&(MpStr){.data=(char*)"\\n",.len=2}));
    return mp_str_format("printf(\"%s\"%s)", fmt->data, args_c->data);
}

MpStr* native_codegen_call_native_compile_call(CompilerState* restrict s, const AstNode* restrict node) {
    "Compile a function call expression.";
    AstCall* pc = node->data;
    AstNode* func = pc->func;
    MpStr** arg_parts = NULL;
    if ((pc->args.count > 0)) {
        arg_parts = malloc((((int64_t)(pc->args.count)) * 8));
        for (int64_t i = 0; i < pc->args.count; i++) {
            MP_PREFETCH(&arg_parts[i + 8], 0, 1);
            arg_parts[i] = native_codegen_expr_native_compile_expr(s, pc->args.items[i]);
        }
    }
    MpStr* arg_str = mp_str_new("");
    for (int64_t i = 0; i < pc->args.count; i++) {
        MP_PREFETCH(&arg_parts[i + 8], 0, 1);
        if ((i > 0)) {
            arg_str = mp_str_concat(arg_str, (&(MpStr){.data=(char*)", ",.len=2}));
        }
        arg_str = mp_str_concat(arg_str, arg_parts[i]);
    }
    if ((func->tag == TAG_NAME)) {
        AstName* fn = func->data;
        MpStr* fname = fn->id;
        if (mp_str_eq(fname, (&(MpStr){.data=(char*)"test_assert",.len=11}))) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            if ((pc->args.count == 2)) {
                MpStr* cond = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
                MpStr* msg = native_codegen_expr_native_compile_expr(s, pc->args.items[1]);
                return mp_str_format("mp_test_assert_msg(%s, %s)", cond->data, msg->data);
            }
            return mp_str_format("mp_test_assert(%s)", arg_str->data);
        }
        if (mp_str_eq(fname, (&(MpStr){.data=(char*)"test_assert_eq",.len=14}))) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return mp_str_format("mp_test_assert_eq(%s)", arg_str->data);
        }
        if (strmap_strmap_has((&s->structs), fname)) {
            MpStr* r = native_codegen_call_native_call_struct_ctor(s, fname, arg_str);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r;
        }
        MpStr* r2 = native_codegen_call_native_call_abs_min_max(s, fname, pc, arg_str);
        if ((r2 != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r2;
        }
        MpStr* r3 = native_codegen_call_native_call_type_cast(s, fname, pc, arg_str);
        if ((r3 != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r3;
        }
        MpStr* r4 = native_codegen_call_native_call_ptr_ops(s, fname, pc, arg_str);
        if ((r4 != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r4;
        }
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"len",.len=3})) && (pc->args.count == 1))) {
            MpStr* r5 = native_codegen_call_native_call_len(s, pc);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return r5;
        }
        if (mp_str_eq(fname, (&(MpStr){.data=(char*)"exit",.len=4}))) {
            MpStr* code = arg_str;
            if ((mp_str_len(code) == 0)) {
                code = mp_str_new("0");
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return mp_str_format("exit(%s)", code->data);
        }
        if (mp_str_eq(fname, (&(MpStr){.data=(char*)"input",.len=5}))) {
            MpStr* prompt = arg_str;
            if ((mp_str_len(prompt) == 0)) {
                prompt = mp_str_new("NULL");
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return mp_str_format("mp_input(%s)", prompt->data);
        }
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"sort",.len=4})) && (pc->args.count == 2))) {
            AstNode* arr_node = pc->args.items[0];
            MpStr* arr_e = native_codegen_expr_native_compile_expr(s, arr_node);
            MpStr* cmp_e = native_codegen_expr_native_compile_expr(s, pc->args.items[1]);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            if ((arr_node->tag == TAG_NAME)) {
                AstName* arr_n = arr_node->data;
                ArrayInfo* arr_ai = strmap_strmap_get((&s->array_vars), arr_n->id);
                if ((arr_ai != NULL)) {
                    return mp_str_format("qsort(%s, %s, sizeof(%s), (int(*)(const void*, const void*))%s)", arr_e->data, arr_ai->size->data, arr_ai->elem_type->data, cmp_e->data);
                }
            }
            return mp_str_format("qsort(%s, 0, 0, (int(*)(const void*, const void*))%s)", arr_e->data, cmp_e->data);
        }
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"str",.len=3})) && (pc->args.count == 1))) {
            MpStr* st = native_infer_native_infer_type(s, pc->args.items[0]);
            MpStr* se = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            if (mp_str_eq(st, (&(MpStr){.data=(char*)"MpStr*",.len=6}))) {
                return se;
            }
            if (mp_str_eq(st, (&(MpStr){.data=(char*)"double",.len=6}))) {
                return mp_str_format("mp_str_from_float(%s)", se->data);
            }
            return mp_str_format("mp_str_from_int((int64_t)(%s))", se->data);
        }
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"sizeof",.len=6})) && (pc->args.count == 1))) {
            AstNode* sarg = pc->args.items[0];
            if ((sarg->tag == TAG_NAME)) {
                AstName* sn = sarg->data;
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("sizeof(%s)", sn->id->data);
            }
        }
        if (mp_str_eq(fname, (&(MpStr){.data=(char*)"print",.len=5}))) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return native_codegen_call_native_compile_print(s, pc);
        }
        int64_t is_str_obj_func = 0;
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"str_len",.len=7})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_eq",.len=6})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_concat",.len=10})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_free",.len=8})))) {
            is_str_obj_func = 1;
        }
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"str_contains",.len=12})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_starts_with",.len=15})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_ends_with",.len=13})))) {
            is_str_obj_func = 1;
        }
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"str_slice",.len=9})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_find",.len=8})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_upper",.len=9})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_lower",.len=9})))) {
            is_str_obj_func = 1;
        }
        if ((mp_str_eq(fname, (&(MpStr){.data=(char*)"str_repeat",.len=10})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_strip",.len=9})) || mp_str_eq(fname, (&(MpStr){.data=(char*)"str_split",.len=9})))) {
            is_str_obj_func = 1;
        }
        if (is_str_obj_func) {
            MpStr* coerced_parts = mp_str_new("");
            for (int64_t ci = 0; ci < pc->args.count; ci++) {
                if ((ci > 0)) {
                    coerced_parts = mp_str_concat(coerced_parts, (&(MpStr){.data=(char*)", ",.len=2}));
                }
                AstNode* ca = pc->args.items[ci];
                if ((ca->tag == TAG_CONSTANT)) {
                    AstConstant* cac = ca->data;
                    if (((cac->kind == CONST_STR) && (cac->str_val != NULL))) {
                        MpStr* escaped_c = native_codegen_expr_native_compile_expr(s, ca);
                        int64_t slen_c = mp_str_len(cac->str_val);
                        coerced_parts = mp_str_concat(coerced_parts, mp_str_format("(&(MpStr){.data=(char*)%s,.len=%lld})", escaped_c->data, slen_c));
                        continue;
                    }
                }
                coerced_parts = mp_str_concat(coerced_parts, native_codegen_expr_native_compile_expr(s, ca));
            }
            arg_str = coerced_parts;
        }
        char* c_name = native_codegen_call_lookup_builtin(fname);
        if ((c_name != NULL)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return mp_str_format("%s(%s)", c_name, arg_str->data);
        }
        if (strmap_strmap_has((&s->func_ret_types), fname)) {
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return mp_str_format("%s(%s)", fname->data, arg_str->data);
        }
        if ((arg_parts != NULL)) {
            free(arg_parts);
        }
        return mp_str_format("%s(%s)", fname->data, arg_str->data);
    }
    if ((func->tag == TAG_ATTRIBUTE)) {
        AstAttribute* pa = func->data;
        MpStr* obj_str = native_codegen_expr_native_compile_expr(s, pa->value);
        MpStr* obj_type = native_infer_native_infer_type(s, pa->value);
        MpStr* base = native_infer__strip_ptr(obj_type);
        MpStr* attr = pa->attr;
        if (((pa->value != NULL) && (pa->value->tag == TAG_ATTRIBUTE))) {
            AstAttribute* inner = pa->value->data;
            if (((inner->value != NULL) && (inner->value->tag == TAG_NAME))) {
                AstName* mod_n = inner->value->data;
                if ((mp_str_eq(mod_n->id, mp_str_new("os")) && mp_str_eq(inner->attr, mp_str_new("path")))) {
                    MpStr* c_os_path = mp_str_new("");
                    if (mp_str_eq(attr, mp_str_new("join"))) {
                        c_os_path = mp_str_new("mp_path_join");
                    } else 
                    if (mp_str_eq(attr, mp_str_new("basename"))) {
                        c_os_path = mp_str_new("mp_path_basename");
                    } else 
                    if (mp_str_eq(attr, mp_str_new("dirname"))) {
                        c_os_path = mp_str_new("mp_path_dirname");
                    } else 
                    if (mp_str_eq(attr, mp_str_new("ext"))) {
                        c_os_path = mp_str_new("mp_path_ext");
                    }
                    if ((mp_str_len(c_os_path) > 0)) {
                        if ((arg_parts != NULL)) {
                            free(arg_parts);
                        }
                        return mp_str_format("%s(%s)", c_os_path->data, arg_str->data);
                    }
                }
            }
        }
        if (((pa->value != NULL) && (pa->value->tag == TAG_NAME))) {
            AstName* os_n = pa->value->data;
            if (mp_str_eq(os_n->id, mp_str_new("os"))) {
                MpStr* c_os = mp_str_new("");
                if (mp_str_eq(attr, mp_str_new("exists"))) {
                    c_os = mp_str_new("mp_file_exists");
                } else 
                if (mp_str_eq(attr, mp_str_new("file_size"))) {
                    c_os = mp_str_new("mp_file_size");
                } else 
                if (mp_str_eq(attr, mp_str_new("remove"))) {
                    c_os = mp_str_new("mp_remove");
                } else 
                if (mp_str_eq(attr, mp_str_new("rename"))) {
                    c_os = mp_str_new("mp_rename");
                } else 
                if (mp_str_eq(attr, mp_str_new("mkdir"))) {
                    c_os = mp_str_new("mp_dir_create");
                } else 
                if (mp_str_eq(attr, mp_str_new("rmdir"))) {
                    c_os = mp_str_new("mp_dir_remove");
                } else 
                if (mp_str_eq(attr, mp_str_new("isdir"))) {
                    c_os = mp_str_new("mp_dir_exists");
                } else 
                if (mp_str_eq(attr, mp_str_new("getcwd"))) {
                    c_os = mp_str_new("mp_dir_cwd");
                } else 
                if (mp_str_eq(attr, mp_str_new("listdir"))) {
                    c_os = mp_str_new("mp_dir_list");
                } else 
                if (mp_str_eq(attr, mp_str_new("chdir"))) {
                    c_os = mp_str_new("mp_dir_chdir");
                }
                if ((mp_str_len(c_os) > 0)) {
                    if ((arg_parts != NULL)) {
                        free(arg_parts);
                    }
                    return mp_str_format("%s(%s)", c_os->data, arg_str->data);
                }
            }
        }
        if (mp_str_eq(obj_type, (&(MpStr){.data=(char*)"MpStr*",.len=6}))) {
            MpStr* c_fn = mp_str_format("mp_str_%s", attr->data);
            MpStr* all_a = obj_str;
            if ((mp_str_len(arg_str) > 0)) {
                all_a = mp_str_format("%s, %s", obj_str->data, arg_str->data);
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return mp_str_format("%s(%s)", c_fn->data, all_a->data);
        }
        if (((pa->value != NULL) && (pa->value->tag == TAG_NAME))) {
            AstName* obj_n = pa->value->data;
            MpStr* et_lookup = strmap_strmap_get((&s->list_vars), obj_n->id);
            if ((et_lookup != NULL)) {
                MpStr* ln_lookup = strmap_strmap_get((&s->typed_lists), et_lookup);
                if ((ln_lookup != NULL)) {
                    MpStr* c_method = mp_str_format("%s_%s", ln_lookup->data, attr->data);
                    MpStr* all_tl = obj_str;
                    if ((mp_str_len(arg_str) > 0)) {
                        all_tl = mp_str_format("%s, %s", obj_str->data, arg_str->data);
                    }
                    if ((arg_parts != NULL)) {
                        free(arg_parts);
                    }
                    return mp_str_format("%s(%s)", c_method->data, all_tl->data);
                }
            }
        }
        if (mp_str_eq(obj_type, (&(MpStr){.data=(char*)"MpList*",.len=7}))) {
            if ((mp_str_eq(attr, (&(MpStr){.data=(char*)"append",.len=6})) && (pc->args.count == 1))) {
                MpStr* v = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
                MpStr* vt = native_infer_native_infer_type(s, pc->args.items[0]);
                MpStr* boxed = v;
                if (mp_str_eq(vt, (&(MpStr){.data=(char*)"double",.len=6}))) {
                    boxed = mp_str_format("mp_val_float(%s)", v->data);
                } else 
                if (mp_str_eq(vt, (&(MpStr){.data=(char*)"MpStr*",.len=6}))) {
                    boxed = mp_str_format("mp_val_str(%s)", v->data);
                } else {
                    boxed = mp_str_format("mp_val_int((int64_t)(%s))", v->data);
                }
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("mp_list_append(%s, %s)", obj_str->data, boxed->data);
            }
            if (mp_str_eq(attr, (&(MpStr){.data=(char*)"pop",.len=3}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("mp_list_pop(%s)", obj_str->data);
            }
            if (mp_str_eq(attr, (&(MpStr){.data=(char*)"len",.len=3}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("mp_list_len(%s)", obj_str->data);
            }
        }
        if (mp_str_eq(obj_type, (&(MpStr){.data=(char*)"MpFile",.len=6}))) {
            if (mp_str_eq(attr, (&(MpStr){.data=(char*)"write",.len=5}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("mp_file_write(%s, %s)", obj_str->data, arg_str->data);
            }
            if (mp_str_eq(attr, (&(MpStr){.data=(char*)"write_line",.len=10}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("mp_file_write_line(%s, %s)", obj_str->data, arg_str->data);
            }
            if (mp_str_eq(attr, (&(MpStr){.data=(char*)"read",.len=4}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("mp_file_read_all(%s)", obj_str->data);
            }
            if (mp_str_eq(attr, (&(MpStr){.data=(char*)"close",.len=5}))) {
                if ((arg_parts != NULL)) {
                    free(arg_parts);
                }
                return mp_str_format("mp_file_close(%s)", obj_str->data);
            }
        }
        if (strmap_strmap_has((&s->structs), base)) {
            MpStr* self_arg = obj_str;
            if ((native_infer__ends_with_star(obj_type) == 0)) {
                self_arg = mp_str_format("&(%s)", obj_str->data);
            }
            MpStr* all_args = self_arg;
            if ((mp_str_len(arg_str) > 0)) {
                all_args = mp_str_format("%s, %s", self_arg->data, arg_str->data);
            }
            if ((arg_parts != NULL)) {
                free(arg_parts);
            }
            return mp_str_format("%s_%s(%s)", base->data, attr->data, all_args->data);
        }
        MpStr* all_args2 = obj_str;
        if ((mp_str_len(arg_str) > 0)) {
            all_args2 = mp_str_format("%s, %s", obj_str->data, arg_str->data);
        }
        if ((arg_parts != NULL)) {
            free(arg_parts);
        }
        return mp_str_format("%s(%s)", attr->data, all_args2->data);
    }
    MpStr* func_str = native_codegen_expr_native_compile_expr(s, func);
    if ((arg_parts != NULL)) {
        free(arg_parts);
    }
    return mp_str_format("%s(%s)", func_str->data, arg_str->data);
}
