/* nth_stamp: 1774911850.086977 */
#include "nathra_rt.h"
#include "native_compile_file.h"

void native_compile_file__emit(CompilerState* restrict s, const NrStr* restrict line);
void native_compile_file__emit_raw(CompilerState* restrict s, const NrStr* restrict line);
void native_compile_file__first_pass(CompilerState* s, AstNodeList body);
int64_t native_compile_file__has_decorator(const AstFunctionDef* restrict fd, const NrStr* restrict name);
void native_compile_file__scan_annotation_for_list(CompilerState* restrict s, const AstNode* restrict ann);
void native_compile_file__scan_typed_lists(CompilerState* s, AstNodeList body);
void native_compile_file__emit_typed_lists(CompilerState* s);
int64_t native_compile_file__has_test_funcs(AstNodeList body);
int64_t native_compile_file__has_variadic_funcs(AstNodeList body);
void native_compile_file__emit_includes(CompilerState* s, AstNodeList body);
void native_compile_file__emit_forward_typedefs(CompilerState* s, AstNodeList body);
void native_compile_file__emit_struct_defs(CompilerState* s, AstNodeList body);
void native_compile_file__emit_enums(CompilerState* s, AstNodeList body);
void native_compile_file__emit_constants(CompilerState* s, AstNodeList body);
void native_compile_file__emit_globals(CompilerState* s, AstNodeList body);
void native_compile_file__emit_function_prototypes(CompilerState* s, AstNodeList body);
int64_t native_compile_file__is_extern_func(const AstFunctionDef* fd);
void native_compile_file__compile_one_func(CompilerState* restrict s, AstFunctionDef* restrict fd, const NrStr* restrict prefix);
NrStr* native_compile_file__edge_key(const NrStr* restrict a, const NrStr* restrict b);
void native_compile_file__walk_calls_weighted(AstNodeList stmts, NrStr* restrict caller, StrSet* restrict func_names, StrMap* restrict edges, int32_t depth, int64_t is_hot);
void native_compile_file__scan_calls_in_node(const AstNode* restrict node, NrStr* restrict caller, StrSet* restrict func_names, StrMap* restrict edges, int32_t depth, int64_t is_hot);
void native_compile_file__reorder_by_call_graph(const AstFunctionDef** restrict funcs, int32_t count, const StrMap* restrict edges, AstFunctionDef** restrict out);
void native_compile_file__dce_find_calls(const AstNode* restrict node, StrSet* restrict all_names, StrSet* restrict reachable, NrStr** restrict work, int32_t* restrict work_count, NrStr* restrict caller);
void native_compile_file__emit_functions(CompilerState* s, AstNodeList body);
void native_compile_file__emit_runtime_impl(CompilerState* s);
int32_t native_compile_file_native_compile(const uint8_t* restrict ast_buf, int64_t ast_len, uint8_t** restrict out_buf, int64_t* restrict out_len);
CompilerState* native_compile_file_native_state_new(void);
int32_t native_compile_file_native_compile_dep(CompilerState* restrict state, const uint8_t* restrict ast_buf, int64_t ast_len, const uint8_t* restrict used_names_buf, int64_t used_names_len, uint8_t** restrict out_c, int64_t* restrict out_c_len, uint8_t** restrict out_h, int64_t* restrict out_h_len);
int32_t native_compile_file_native_compile_main(CompilerState* restrict state, const uint8_t* restrict ast_buf, int64_t ast_len, uint8_t** restrict out_buf, int64_t* restrict out_len);
int main(void);

void native_compile_file__emit(CompilerState* restrict s, const NrStr* restrict line) {
    for (int64_t i = 0; i < s->indent; i++) {
        nr_write_text(s->lines, nr_str_new("    "));
    }
    nr_write_text(s->lines, line);
    nr_write_text(s->lines, nr_str_new("\n"));
}

void native_compile_file__emit_raw(CompilerState* restrict s, const NrStr* restrict line) {
    "Emit without indentation.";
    nr_write_text(s->lines, line);
    nr_write_text(s->lines, nr_str_new("\n"));
}

void native_compile_file__first_pass(CompilerState* s, AstNodeList body) {
    "Walk top-level nodes, register functions, structs, constants, globals.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_FUNCTION_DEF)) {
            AstFunctionDef* fd = node->data;
            NrStr* ret_type = native_type_map_native_map_type(fd->returns);
            strmap_strmap_set((&s->func_ret_types), fd->name, ret_type);
            continue;
        }
        if ((node->tag == TAG_CLASS_DEF)) {
            AstClassDef* cd = node->data;
            int64_t is_enum = 1;
            int64_t has_assign = 0;
            for (int64_t j = 0; j < cd->body.count; j++) {
                AstNode* item_check = cd->body.items[j];
                if ((item_check != NULL)) {
                    if (((item_check->tag == TAG_ANN_ASSIGN) || (item_check->tag == TAG_FUNCTION_DEF))) {
                        is_enum = 0;
                    }
                    if ((item_check->tag == TAG_ASSIGN)) {
                        has_assign = 1;
                    }
                }
            }
            if ((is_enum && has_assign)) {
                strmap_strset_add((&s->extern_funcs), cd->name);
                continue;
            }
            int32_t field_count = (int32_t)(0);
            for (int64_t j = 0; j < cd->body.count; j++) {
                AstNode* item = cd->body.items[j];
                if (((item != NULL) && (item->tag == TAG_ANN_ASSIGN))) {
                    field_count = (int32_t)((field_count + 1));
                }
            }
            if ((field_count > 0)) {
                FieldList* fl = native_compiler_state_field_list_new(field_count);
                int32_t idx = (int32_t)(0);
                for (int64_t j = 0; j < cd->body.count; j++) {
                    AstNode* item2 = cd->body.items[j];
                    if (((item2 != NULL) && (item2->tag == TAG_ANN_ASSIGN))) {
                        AstAnnAssign* aa = item2->data;
                        if (((aa->target != NULL) && (aa->target->tag == TAG_NAME))) {
                            AstName* fn = aa->target->data;
                            NrStr* ft = native_type_map_native_map_type(aa->annotation);
                            if (nr_str_eq(ft, (&(NrStr){.data=(char*)"__array__",.len=9}))) {
                                if (((aa->annotation != NULL) && (aa->annotation->tag == TAG_SUBSCRIPT))) {
                                    AstSubscript* asub = aa->annotation->data;
                                    AstNode* sl = asub->slice;
                                    if (((sl != NULL) && (sl->tag == TAG_TUPLE))) {
                                        AstTuple* tup = sl->data;
                                        if ((tup->elts.count >= 2)) {
                                            NrStr* et = native_type_map_native_map_type(tup->elts.items[0]);
                                            NrStr* sz = native_codegen_expr_native_compile_expr(s, tup->elts.items[1]);
                                            ft = nr_str_format("__arr_%s_%s", et->data, sz->data);
                                        }
                                    }
                                }
                            }
                            if (nr_str_eq(ft, (&(NrStr){.data=(char*)"__bitfield__",.len=12}))) {
                                if (((aa->annotation != NULL) && (aa->annotation->tag == TAG_SUBSCRIPT))) {
                                    AstSubscript* bf_sub = aa->annotation->data;
                                    AstNode* bf_sl = bf_sub->slice;
                                    if (((bf_sl != NULL) && (bf_sl->tag == TAG_TUPLE))) {
                                        AstTuple* bf_tup = bf_sl->data;
                                        if ((bf_tup->elts.count >= 2)) {
                                            NrStr* bf_t = native_type_map_native_map_type(bf_tup->elts.items[0]);
                                            NrStr* bf_w = native_codegen_expr_native_compile_expr(s, bf_tup->elts.items[1]);
                                            ft = nr_str_format("__bf_%s_%s", bf_t->data, bf_w->data);
                                        }
                                    }
                                }
                            }
                            fl->entries[idx].name = fn->id;
                            fl->entries[idx].ctype = ft;
                            idx = (int32_t)((idx + 1));
                        }
                    }
                }
                strmap_strmap_set((&s->structs), cd->name, fl);
            }
            for (int64_t j = 0; j < cd->body.count; j++) {
                AstNode* item3 = cd->body.items[j];
                if (((item3 != NULL) && (item3->tag == TAG_FUNCTION_DEF))) {
                    AstFunctionDef* md = item3->data;
                    NrStr* mret = native_type_map_native_map_type(md->returns);
                    NrStr* mname = nr_str_concat(nr_str_concat(cd->name, (&(NrStr){.data=(char*)"_",.len=1})), md->name);
                    strmap_strmap_set((&s->func_ret_types), mname, mret);
                }
            }
            continue;
        }
        if ((node->tag == TAG_ANN_ASSIGN)) {
            AstAnnAssign* aa2 = node->data;
            if (((aa2->target != NULL) && (aa2->target->tag == TAG_NAME))) {
                AstName* vn = aa2->target->data;
                NrStr* ct = native_type_map_native_map_type(aa2->annotation);
                int64_t is_upper = 1;
                int64_t name_len = nr_str_len(vn->id);
                for (int64_t k = 0; k < name_len; k++) {
                    uint8_t ch = (uint8_t)(((uint8_t)(vn->id->data[k])));
                    if (((ch >= 97) && (ch <= 122))) {
                        is_upper = 0;
                    }
                }
                if ((is_upper && (name_len > 0))) {
                    strmap_strmap_set((&s->constants), vn->id, ct);
                } else {
                    strmap_strmap_set((&s->mutable_globals), vn->id, ct);
                }
            }
            continue;
        }
    }
}

int64_t native_compile_file__has_decorator(const AstFunctionDef* restrict fd, const NrStr* restrict name) {
    "Check if a function definition has a decorator with the given name.";
    for (int64_t i = 0; i < fd->decorators.count; i++) {
        AstNode* dec = fd->decorators.items[i];
        if (((dec != NULL) && (dec->tag == TAG_NAME))) {
            AstName* dn = dec->data;
            if (nr_str_eq(dn->id, name)) {
                return 1;
            }
        }
    }
    return 0;
}

void native_compile_file__scan_annotation_for_list(CompilerState* restrict s, const AstNode* restrict ann) {
    "Check if an annotation is list[T] or own[list[T]] and register the typed list.";
    if (((ann == NULL) || (ann->tag != TAG_SUBSCRIPT))) {
        return;
    }
    AstSubscript* asub = ann->data;
    AstNode* sub_val = asub->value;
    if (((sub_val != NULL) && (sub_val->tag == TAG_NAME))) {
        AstName* bn = sub_val->data;
        if ((nr_str_eq(bn->id, (&(NrStr){.data=(char*)"own",.len=3})) && (asub->slice != NULL) && (asub->slice->tag == TAG_SUBSCRIPT))) {
            asub = asub->slice->data;
            sub_val = asub->value;
        }
    }
    if (((sub_val != NULL) && (sub_val->tag == TAG_NAME))) {
        AstName* bn2 = sub_val->data;
        if ((nr_str_eq(bn2->id, (&(NrStr){.data=(char*)"typed_list",.len=10})) || nr_str_eq(bn2->id, (&(NrStr){.data=(char*)"list",.len=4})))) {
            NrStr* elem_t = native_type_map_native_map_type(asub->slice);
            if ((strmap_strmap_has((&s->typed_lists), elem_t) == 0)) {
                NrStr* list_name = nr_str_concat(elem_t, (&(NrStr){.data=(char*)"List",.len=4}));
                if (nr_str_eq(elem_t, (&(NrStr){.data=(char*)"int64_t",.len=7}))) {
                    list_name = nr_str_new("IntList");
                } else 
                if (nr_str_eq(elem_t, (&(NrStr){.data=(char*)"double",.len=6}))) {
                    list_name = nr_str_new("FloatList");
                } else 
                if (nr_str_eq(elem_t, (&(NrStr){.data=(char*)"uint8_t",.len=7}))) {
                    list_name = nr_str_new("ByteList");
                }
                strmap_strmap_set((&s->typed_lists), elem_t, list_name);
            }
        }
    }
}

void native_compile_file__scan_typed_lists(CompilerState* s, AstNodeList body) {
    "Walk AST to find typed_list[T] annotations and register list types.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_ANN_ASSIGN)) {
            AstAnnAssign* aa = node->data;
            if (((aa->annotation != NULL) && (aa->annotation->tag == TAG_SUBSCRIPT))) {
                AstSubscript* asub = aa->annotation->data;
                AstNode* sub_val = asub->value;
                if (((sub_val != NULL) && (sub_val->tag == TAG_NAME))) {
                    AstName* bn = sub_val->data;
                    if ((nr_str_eq(bn->id, (&(NrStr){.data=(char*)"typed_list",.len=10})) || nr_str_eq(bn->id, (&(NrStr){.data=(char*)"list",.len=4})))) {
                        NrStr* elem_t = native_type_map_native_map_type(asub->slice);
                        if ((strmap_strmap_has((&s->typed_lists), elem_t) == 0)) {
                            NrStr* list_name = nr_str_concat(elem_t, (&(NrStr){.data=(char*)"List",.len=4}));
                            if (nr_str_eq(elem_t, (&(NrStr){.data=(char*)"int64_t",.len=7}))) {
                                list_name = nr_str_new("IntList");
                            } else 
                            if (nr_str_eq(elem_t, (&(NrStr){.data=(char*)"double",.len=6}))) {
                                list_name = nr_str_new("FloatList");
                            } else 
                            if (nr_str_eq(elem_t, (&(NrStr){.data=(char*)"uint8_t",.len=7}))) {
                                list_name = nr_str_new("ByteList");
                            }
                            strmap_strmap_set((&s->typed_lists), elem_t, list_name);
                        }
                    }
                }
            }
        }
        if ((node->tag == TAG_FUNCTION_DEF)) {
            AstFunctionDef* fd = node->data;
            if ((fd->args != NULL)) {
                AstArguments* fa = fd->args->data;
                for (int64_t pi = 0; pi < fa->args.count; pi++) {
                    AstArg* pa = fa->args.items[pi]->data;
                    native_compile_file__scan_annotation_for_list(s, pa->annotation);
                }
            }
            native_compile_file__scan_annotation_for_list(s, fd->returns);
            native_compile_file__scan_typed_lists(s, fd->body);
        }
        if ((node->tag == TAG_CLASS_DEF)) {
            AstClassDef* cd = node->data;
            for (int64_t j = 0; j < cd->body.count; j++) {
                AstNode* method = cd->body.items[j];
                if (((method != NULL) && (method->tag == TAG_FUNCTION_DEF))) {
                    AstFunctionDef* md = method->data;
                    native_compile_file__scan_typed_lists(s, md->body);
                }
            }
        }
    }
}

void native_compile_file__emit_typed_lists(CompilerState* s) {
    "Emit typed list C code (struct + new/append/get/set/len/pop/free).";
    StrMap* m = (&s->typed_lists);
    for (int64_t i = 0; i < m->cap; i++) {
        if ((m->states[i] == 1)) {
            NrStr* elem_t = m->keys[i];
            NrStr* list_name = m->values[i];
            NrStr* N = list_name;
            NrStr* T = elem_t;
            native_compile_file__emit_raw(s, nr_str_format("typedef struct { %s* data; int64_t len; int64_t cap; } %s;", T->data, N->data));
            native_compile_file__emit_raw(s, nr_str_format("static inline %s* %s_new(void) { %s* l = (%s*)malloc(sizeof(%s)); l->cap=8; l->len=0; l->data=(%s*)malloc(sizeof(%s)*l->cap); return l; }", N->data, N->data, N->data, N->data, N->data, T->data, T->data));
            native_compile_file__emit_raw(s, nr_str_format("static inline void %s_append(%s* l, %s v) { if(l->len>=l->cap){l->cap*=2;l->data=(%s*)realloc(l->data,sizeof(%s)*l->cap);} l->data[l->len++]=v; }", N->data, N->data, T->data, T->data, T->data));
            native_compile_file__emit_raw(s, nr_str_format("static inline %s %s_get(%s* l, int64_t i) { return l->data[i]; }", T->data, N->data, N->data));
            native_compile_file__emit_raw(s, nr_str_format("static inline void %s_set(%s* l, int64_t i, %s v) { l->data[i]=v; }", N->data, N->data, T->data));
            native_compile_file__emit_raw(s, nr_str_format("static inline int64_t %s_len(%s* l) { return l->len; }", N->data, N->data));
            native_compile_file__emit_raw(s, nr_str_format("static inline %s %s_pop(%s* l) { return l->data[--l->len]; }", T->data, N->data, N->data));
            native_compile_file__emit_raw(s, nr_str_format("static inline void %s_free(%s* l) { if(l){free(l->data);free(l);} }", N->data, N->data));
            native_compile_file__emit_raw(s, nr_str_new(""));
        }
    }
}

int64_t native_compile_file__has_test_funcs(AstNodeList body) {
    "Check if any function has @test decorator.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node != NULL) && (node->tag == TAG_FUNCTION_DEF))) {
            AstFunctionDef* fd = node->data;
            if (native_compile_file__has_decorator(fd, nr_str_new("test"))) {
                return 1;
            }
        }
    }
    return 0;
}

int64_t native_compile_file__has_variadic_funcs(AstNodeList body) {
    "Check if any function has *args (vararg).";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node != NULL) && (node->tag == TAG_FUNCTION_DEF))) {
            AstFunctionDef* fd = node->data;
            AstArguments* args_n = fd->args->data;
            if ((args_n->vararg != NULL)) {
                return 1;
            }
        }
    }
    return 0;
}

void native_compile_file__emit_includes(CompilerState* s, AstNodeList body) {
    if ((s->safe_mode != 0)) {
        native_compile_file__emit_raw(s, nr_str_new("#define NR_SAFE"));
    }
    native_compile_file__emit_raw(s, nr_str_new("#include \"nathra_rt.h\""));
    if (native_compile_file__has_variadic_funcs(body)) {
        native_compile_file__emit_raw(s, nr_str_new("#include <stdarg.h>"));
    }
    if (native_compile_file__has_test_funcs(body)) {
        native_compile_file__emit_raw(s, nr_str_new("#include \"nathra_test.h\""));
    }
    native_compile_file__emit_raw(s, nr_str_new(""));
}

void native_compile_file__emit_forward_typedefs(CompilerState* s, AstNodeList body) {
    "Emit typedef struct X X; for each struct.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node != NULL) && (node->tag == TAG_CLASS_DEF))) {
            AstClassDef* cd = node->data;
            if (strmap_strmap_has((&s->structs), cd->name)) {
                native_compile_file__emit_raw(s, nr_str_format("typedef struct %s %s;", cd->name->data, cd->name->data));
            }
        }
    }
    native_compile_file__emit_raw(s, nr_str_new(""));
}

void native_compile_file__emit_struct_defs(CompilerState* s, AstNodeList body) {
    "Emit struct body definitions.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node == NULL) || (node->tag != TAG_CLASS_DEF))) {
            continue;
        }
        AstClassDef* cd = node->data;
        FieldList* fl = strmap_strmap_get((&s->structs), cd->name);
        if ((fl == NULL)) {
            continue;
        }
        native_compile_file__emit_raw(s, nr_str_format("typedef struct %s {", cd->name->data));
        for (int64_t j = 0; j < fl->count; j++) {
            NrStr* ftype = fl->entries[j].ctype;
            NrStr* fname = fl->entries[j].name;
            if (nr_str_starts_with(ftype, nr_str_new("__arr_"))) {
                NrStr* inner = nr_str_slice(ftype, 6, nr_str_len(ftype));
                int64_t last_us = (-1);
                for (int64_t k = 0; k < nr_str_len(inner); k++) {
                    if ((((uint8_t)(inner->data[k])) == 95)) {
                        last_us = k;
                    }
                }
                if ((last_us > 0)) {
                    NrStr* et = nr_str_slice(inner, 0, last_us);
                    NrStr* sz = nr_str_slice(inner, (last_us + 1), nr_str_len(inner));
                    native_compile_file__emit_raw(s, nr_str_format("    %s %s[%s];", et->data, fname->data, sz->data));
                } else {
                    native_compile_file__emit_raw(s, nr_str_format("    /* array field %s */", fname->data));
                }
            } else 
            if (nr_str_starts_with(ftype, nr_str_new("__bf_"))) {
                NrStr* bf_inner = nr_str_slice(ftype, 5, nr_str_len(ftype));
                int64_t bf_last = (-1);
                for (int64_t bk = 0; bk < nr_str_len(bf_inner); bk++) {
                    if ((((uint8_t)(bf_inner->data[bk])) == 95)) {
                        bf_last = bk;
                    }
                }
                if ((bf_last > 0)) {
                    NrStr* bf_t2 = nr_str_slice(bf_inner, 0, bf_last);
                    NrStr* bf_w2 = nr_str_slice(bf_inner, (bf_last + 1), nr_str_len(bf_inner));
                    native_compile_file__emit_raw(s, nr_str_format("    %s %s : %s;", bf_t2->data, fname->data, bf_w2->data));
                } else {
                    native_compile_file__emit_raw(s, nr_str_format("    /* bitfield %s */", fname->data));
                }
            } else 
            if ((nr_str_eq(ftype, (&(NrStr){.data=(char*)"__funcptr__",.len=11})) || nr_str_eq(ftype, (&(NrStr){.data=(char*)"__vec__",.len=7})) || nr_str_eq(ftype, (&(NrStr){.data=(char*)"__typed_list__",.len=14})))) {
                native_compile_file__emit_raw(s, nr_str_format("    /* TODO: %s %s */", ftype->data, fname->data));
            } else {
                native_compile_file__emit_raw(s, nr_str_format("    %s %s;", ftype->data, fname->data));
            }
        }
        native_compile_file__emit_raw(s, nr_str_format("} %s;", cd->name->data));
        NrStr* arg_list = nr_str_new("");
        NrStr* body_list = nr_str_new("");
        int32_t ctor_count = (int32_t)(0);
        for (int64_t j = 0; j < fl->count; j++) {
            NrStr* fname2 = fl->entries[j].name;
            NrStr* ftype2 = fl->entries[j].ctype;
            if (nr_str_starts_with(ftype2, nr_str_new("__"))) {
                continue;
            }
            if ((ctor_count > 0)) {
                arg_list = nr_str_concat(arg_list, (&(NrStr){.data=(char*)", ",.len=2}));
            }
            arg_list = nr_str_concat(arg_list, nr_str_format("%s %s", ftype2->data, fname2->data));
            body_list = nr_str_concat(body_list, nr_str_format("    _s.%s = %s;\n", fname2->data, fname2->data));
            ctor_count = (int32_t)((ctor_count + 1));
        }
        if ((ctor_count == 0)) {
            arg_list = nr_str_new("void");
        }
        native_compile_file__emit_raw(s, nr_str_format("static inline %s _nr_make_%s(%s) {", cd->name->data, cd->name->data, arg_list->data));
        native_compile_file__emit_raw(s, nr_str_format("    %s _s = {0};", cd->name->data));
        native_compile_file__emit_raw(s, body_list);
        native_compile_file__emit_raw(s, nr_str_new("    return _s;"));
        native_compile_file__emit_raw(s, nr_str_new("}"));
        native_compile_file__emit_raw(s, nr_str_new(""));
    }
}

void native_compile_file__emit_enums(CompilerState* s, AstNodeList body) {
    "Emit typedef enum for enum classes.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node == NULL) || (node->tag != TAG_CLASS_DEF))) {
            continue;
        }
        AstClassDef* cd = node->data;
        if ((strmap_strset_has((&s->extern_funcs), cd->name) == 0)) {
            continue;
        }
        native_compile_file__emit_raw(s, nr_str_format("typedef enum {", cd->name->data));
        for (int64_t j = 0; j < cd->body.count; j++) {
            AstNode* member = cd->body.items[j];
            if (((member != NULL) && (member->tag == TAG_ASSIGN))) {
                AstAssign* ma = member->data;
                if ((ma->targets.count > 0)) {
                    AstNode* tgt = ma->targets.items[0];
                    if ((tgt->tag == TAG_NAME)) {
                        AstName* mn = tgt->data;
                        NrStr* mval = native_codegen_expr_native_compile_expr(s, ma->value);
                        NrStr* comma = nr_str_new(",");
                        if ((j == (cd->body.count - 1))) {
                            comma = nr_str_new("");
                        }
                        native_compile_file__emit_raw(s, nr_str_format("    %s_%s = %s%s", cd->name->data, mn->id->data, mval->data, comma->data));
                    }
                }
            }
        }
        native_compile_file__emit_raw(s, nr_str_format("} %s;", cd->name->data));
        native_compile_file__emit_raw(s, nr_str_new(""));
    }
}

void native_compile_file__emit_constants(CompilerState* s, AstNodeList body) {
    "Emit const declarations for uppercase names.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node == NULL) || (node->tag != TAG_ANN_ASSIGN))) {
            continue;
        }
        AstAnnAssign* aa = node->data;
        if (((aa->target == NULL) || (aa->target->tag != TAG_NAME))) {
            continue;
        }
        AstName* vn = aa->target->data;
        if (strmap_strmap_has((&s->constants), vn->id)) {
            NrStr* ct = strmap_strmap_get((&s->constants), vn->id);
            if ((aa->value != NULL)) {
                NrStr* val = native_codegen_expr_native_compile_expr(s, aa->value);
                native_compile_file__emit_raw(s, nr_str_format("const %s %s = %s;", ct->data, vn->id->data, val->data));
            }
        }
    }
}

void native_compile_file__emit_globals(CompilerState* s, AstNodeList body) {
    "Emit mutable global variable declarations.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node == NULL) || (node->tag != TAG_ANN_ASSIGN))) {
            continue;
        }
        AstAnnAssign* aa = node->data;
        if (((aa->target == NULL) || (aa->target->tag != TAG_NAME))) {
            continue;
        }
        AstName* vn = aa->target->data;
        if (strmap_strmap_has((&s->mutable_globals), vn->id)) {
            NrStr* ct = strmap_strmap_get((&s->mutable_globals), vn->id);
            if ((aa->value != NULL)) {
                NrStr* val = native_codegen_expr_native_compile_expr(s, aa->value);
                native_compile_file__emit_raw(s, nr_str_format("%s %s = %s;", ct->data, vn->id->data, val->data));
            } else {
                native_compile_file__emit_raw(s, nr_str_format("%s %s;", ct->data, vn->id->data));
            }
        }
    }
}

int64_t native_compile_file__is_extern_func(const AstFunctionDef* fd) {
    "Check if function body is just `...` (Ellipsis) — extern declaration.";
    if ((fd->body.count == 1)) {
        AstNode* stmt = fd->body.items[0];
        if (((stmt != NULL) && (stmt->tag == TAG_EXPR_STMT))) {
            AstExprStmt* es = stmt->data;
            if (((es->value != NULL) && (es->value->tag == TAG_CONSTANT))) {
                AstConstant* cc = es->value->data;
                if ((cc->kind == CONST_ELLIPSIS)) {
                    return 1;
                }
            }
        }
    }
    return 0;
}

void native_compile_file__emit_function_prototypes(CompilerState* s, AstNodeList body) {
    "Emit forward declarations for all functions.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node == NULL) || (node->tag != TAG_FUNCTION_DEF))) {
            continue;
        }
        AstFunctionDef* fd = node->data;
        if (native_compile_file__is_extern_func(fd)) {
            continue;
        }
        NrStr* ret = native_type_map_native_map_type(fd->returns);
        if (nr_str_starts_with(ret, nr_str_new("__own__ "))) {
            ret = nr_str_slice(ret, 8, nr_str_len(ret));
        }
        if (nr_str_eq(ret, (&(NrStr){.data=(char*)"__typed_list__",.len=14}))) {
            NrStr* tl_ret_e = native_type_map_native_get_typed_list_elem(fd->returns);
            NrStr* tl_ret_n = strmap_strmap_get((&s->typed_lists), tl_ret_e);
            if ((tl_ret_n != NULL)) {
                ret = nr_str_concat(tl_ret_n, (&(NrStr){.data=(char*)"*",.len=1}));
            }
        }
        if (nr_str_eq(fd->name, (&(NrStr){.data=(char*)"main",.len=4}))) {
            ret = nr_str_new("int");
        }
        AstArguments* args_node = fd->args->data;
        NrStr* arg_str = nr_str_new("");
        for (int64_t j = 0; j < args_node->args.count; j++) {
            AstArg* arg = args_node->args.items[j]->data;
            NrStr* atype = native_type_map_native_map_type(arg->annotation);
            AstNode* p_ann = arg->annotation;
            if (nr_str_starts_with(atype, nr_str_new("__own__ "))) {
                atype = nr_str_slice(atype, 8, nr_str_len(atype));
                if (((p_ann != NULL) && (p_ann->tag == TAG_SUBSCRIPT))) {
                    AstSubscript* own_s = p_ann->data;
                    p_ann = own_s->slice;
                }
            }
            if (nr_str_eq(atype, (&(NrStr){.data=(char*)"__typed_list__",.len=14}))) {
                NrStr* tl_elem = native_type_map_native_get_typed_list_elem(p_ann);
                NrStr* tl_name = strmap_strmap_get((&s->typed_lists), tl_elem);
                if ((tl_name != NULL)) {
                    atype = nr_str_concat(tl_name, (&(NrStr){.data=(char*)"*",.len=1}));
                }
            }
            if ((j > 0)) {
                arg_str = nr_str_concat(arg_str, (&(NrStr){.data=(char*)", ",.len=2}));
            }
            arg_str = nr_str_concat(arg_str, nr_str_format("%s %s", atype->data, arg->name->data));
        }
        if ((args_node->vararg != NULL)) {
            if ((args_node->args.count > 0)) {
                arg_str = nr_str_concat(arg_str, (&(NrStr){.data=(char*)", ...",.len=5}));
            } else {
                arg_str = nr_str_new("...");
            }
        } else 
        if ((args_node->args.count == 0)) {
            arg_str = nr_str_new("void");
        }
        native_compile_file__emit_raw(s, nr_str_format("%s %s(%s);", ret->data, fd->name->data, arg_str->data));
    }
    native_compile_file__emit_raw(s, nr_str_new(""));
}

void native_compile_file__compile_one_func(CompilerState* restrict s, AstFunctionDef* restrict fd, const NrStr* restrict prefix) {
    "Compile a single function definition with optional name prefix.";
    if (native_compile_file__is_extern_func(fd)) {
        return;
    }
    NrStr* ret = native_type_map_native_map_type(fd->returns);
    if (nr_str_starts_with(ret, nr_str_new("__own__ "))) {
        ret = nr_str_slice(ret, 8, nr_str_len(ret));
    }
    if (nr_str_eq(ret, (&(NrStr){.data=(char*)"__typed_list__",.len=14}))) {
        NrStr* tl_ret_e2 = native_type_map_native_get_typed_list_elem(fd->returns);
        NrStr* tl_ret_n2 = strmap_strmap_get((&s->typed_lists), tl_ret_e2);
        if ((tl_ret_n2 != NULL)) {
            ret = nr_str_concat(tl_ret_n2, (&(NrStr){.data=(char*)"*",.len=1}));
        }
    }
    AstArguments* args_node = fd->args->data;
    NrStr* arg_str = nr_str_new("");
    strmap_strmap_free((&s->local_vars));
    s->local_vars = strmap_strmap_new(32);
    strmap_strmap_free((&s->func_args));
    s->func_args = strmap_strmap_new(16);
    strmap_strmap_free((&s->array_vars));
    s->array_vars = strmap_strmap_new(16);
    strmap_strmap_free((&s->list_vars));
    s->list_vars = strmap_strmap_new(16);
    for (int64_t j = 0; j < args_node->args.count; j++) {
        AstArg* arg = args_node->args.items[j]->data;
        NrStr* atype = native_type_map_native_map_type(arg->annotation);
        AstNode* d_ann = arg->annotation;
        if (nr_str_starts_with(atype, nr_str_new("__own__ "))) {
            atype = nr_str_slice(atype, 8, nr_str_len(atype));
            if (((d_ann != NULL) && (d_ann->tag == TAG_SUBSCRIPT))) {
                AstSubscript* own_s2 = d_ann->data;
                d_ann = own_s2->slice;
            }
        }
        if (nr_str_eq(atype, (&(NrStr){.data=(char*)"__typed_list__",.len=14}))) {
            NrStr* tl_elem2 = native_type_map_native_get_typed_list_elem(d_ann);
            NrStr* tl_name2 = strmap_strmap_get((&s->typed_lists), tl_elem2);
            if ((tl_name2 != NULL)) {
                atype = nr_str_concat(tl_name2, (&(NrStr){.data=(char*)"*",.len=1}));
            }
        }
        if ((nr_str_eq(arg->name, (&(NrStr){.data=(char*)"self",.len=4})) && (nr_str_len(prefix) > 0))) {
            NrStr* struct_name = nr_str_slice(prefix, 0, (nr_str_len(prefix) - 1));
            atype = nr_str_concat(struct_name, (&(NrStr){.data=(char*)"*",.len=1}));
        }
        if ((j > 0)) {
            arg_str = nr_str_concat(arg_str, (&(NrStr){.data=(char*)", ",.len=2}));
        }
        arg_str = nr_str_concat(arg_str, nr_str_format("%s %s", atype->data, arg->name->data));
        strmap_strmap_set((&s->func_args), arg->name, atype);
    }
    if ((args_node->vararg != NULL)) {
        if ((args_node->args.count > 0)) {
            arg_str = nr_str_concat(arg_str, (&(NrStr){.data=(char*)", ...",.len=5}));
        } else {
            arg_str = nr_str_new("...");
        }
    } else 
    if ((args_node->args.count == 0)) {
        arg_str = nr_str_new("void");
    }
    s->current_func_ret_type = ret;
    NrStr* fname = fd->name;
    if ((nr_str_len(prefix) > 0)) {
        fname = nr_str_concat(prefix, fd->name);
    }
    if (nr_str_eq(fname, (&(NrStr){.data=(char*)"main",.len=4}))) {
        native_compile_file__emit_raw(s, nr_str_new("int main(void) {"));
    } else {
        native_compile_file__emit_raw(s, nr_str_format("%s %s(%s) {", ret->data, fname->data, arg_str->data));
    }
    s->indent = (int32_t)(1);
    for (int64_t j = 0; j < fd->body.count; j++) {
        native_codegen_stmt_native_compile_stmt(s, fd->body.items[j]);
    }
    s->indent = (int32_t)(0);
    native_compile_file__emit_raw(s, nr_str_new("}"));
    native_compile_file__emit_raw(s, nr_str_new(""));
}

NrStr* native_compile_file__edge_key(const NrStr* restrict a, const NrStr* restrict b) {
    "Build a sorted edge key for undirected graph: 'min|max'.";
    NrStr* sep = nr_str_new("|");
    if ((strcmp(a->data, b->data) < 0)) {
        return nr_str_concat(nr_str_concat(a, sep), b);
    }
    return nr_str_concat(nr_str_concat(b, sep), a);
}

void native_compile_file__scan_calls_in_node(const AstNode* restrict node, NrStr* restrict caller, StrSet* restrict func_names, StrMap* restrict edges, int32_t depth, int64_t is_hot) {
    "Scan a single node for direct calls to known functions.";
    if ((node == NULL)) {
        return;
    }
    if ((node->tag == TAG_CALL)) {
        AstCall* c = node->data;
        if (((c->func != NULL) && (c->func->tag == TAG_NAME))) {
            AstName* fn = c->func->data;
            if (((!nr_str_eq(fn->id, caller)) && strmap_strset_has(func_names, fn->id))) {
                NrStr* key = native_compile_file__edge_key(caller, fn->id);
                int64_t w = 1;
                for (int64_t d = 0; d < depth; d++) {
                    w = (w * 10);
                }
                if (is_hot) {
                    w = (w * 5);
                }
                void* old_ptr = strmap_strmap_get(edges, key);
                if ((old_ptr != NULL)) {
                    w = (w + ((int64_t)(old_ptr)));
                }
                strmap_strmap_set(edges, key, ((void*)(w)));
            }
        }
        for (int64_t i = 0; i < c->args.count; i++) {
            native_compile_file__scan_calls_in_node(c->args.items[i], caller, func_names, edges, depth, is_hot);
        }
        return;
    }
    if ((node->tag == TAG_ASSIGN)) {
        AstAssign* a = node->data;
        native_compile_file__scan_calls_in_node(a->value, caller, func_names, edges, depth, is_hot);
        return;
    }
    if ((node->tag == TAG_ANN_ASSIGN)) {
        AstAnnAssign* aa = node->data;
        native_compile_file__scan_calls_in_node(aa->value, caller, func_names, edges, depth, is_hot);
        return;
    }
    if ((node->tag == TAG_EXPR_STMT)) {
        AstExprStmt* es = node->data;
        native_compile_file__scan_calls_in_node(es->value, caller, func_names, edges, depth, is_hot);
        return;
    }
}

void native_compile_file__walk_calls_weighted(AstNodeList stmts, NrStr* restrict caller, StrSet* restrict func_names, StrMap* restrict edges, int32_t depth, int64_t is_hot) {
    "Walk statements recursively, accumulating weighted call edges.";
    for (int64_t i = 0; i < stmts.count; i++) {
        AstNode* node = stmts.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_FOR)) {
            AstFor* fd = node->data;
            native_compile_file__walk_calls_weighted(fd->body, caller, func_names, edges, (depth + 1), is_hot);
            continue;
        }
        if ((node->tag == TAG_WHILE)) {
            AstWhile* wd = node->data;
            native_compile_file__walk_calls_weighted(wd->body, caller, func_names, edges, (depth + 1), is_hot);
            continue;
        }
        if ((node->tag == TAG_IF)) {
            AstIf* ifd = node->data;
            native_compile_file__walk_calls_weighted(ifd->body, caller, func_names, edges, depth, is_hot);
            native_compile_file__walk_calls_weighted(ifd->orelse, caller, func_names, edges, depth, is_hot);
            continue;
        }
        if ((node->tag == TAG_WITH)) {
            AstWith* wtd = node->data;
            native_compile_file__walk_calls_weighted(wtd->body, caller, func_names, edges, depth, is_hot);
            continue;
        }
        native_compile_file__scan_calls_in_node(node, caller, func_names, edges, depth, is_hot);
    }
}

void native_compile_file__reorder_by_call_graph(const AstFunctionDef** restrict funcs, int32_t count, const StrMap* restrict edges, AstFunctionDef** restrict out) {
    "Greedy layout: seed with heaviest edge, insert remaining adjacent to highest-weight neighbor.";
    if ((count <= 1)) {
        for (int64_t i = 0; i < count; i++) {
            NR_PREFETCH(&out[i + 8], 0, 1);
            NR_PREFETCH(&funcs[i + 8], 0, 1);
            out[i] = funcs[i];
        }
        return;
    }
    int64_t* total_w = malloc((((int64_t)(count)) * 8));
    for (int64_t i = 0; i < count; i++) {
        NR_PREFETCH(&total_w[i + 8], 0, 1);
        total_w[i] = 0;
    }
    int32_t best_edge_a = (int32_t)(0);
    int32_t best_edge_b = (int32_t)(1);
    int64_t best_w = 0;
    for (int64_t i = 0; i < count; i++) {
        NR_PREFETCH(&total_w[i + 8], 0, 1);
        NR_PREFETCH(&funcs[i + 8], 0, 1);
        for (int64_t j = (i + 1); j < count; j++) {
            NR_PREFETCH(&funcs[j + 8], 0, 1);
            NR_PREFETCH(&total_w[j + 8], 0, 1);
            NrStr* key = native_compile_file__edge_key(funcs[i]->name, funcs[j]->name);
            void* wptr = strmap_strmap_get(edges, key);
            if ((wptr != NULL)) {
                int64_t w = ((int64_t)(wptr));
                total_w[i] = (total_w[i] + w);
                total_w[j] = (total_w[j] + w);
                if ((w > best_w)) {
                    best_w = w;
                    best_edge_a = (int32_t)(i);
                    best_edge_b = (int32_t)(j);
                }
            }
        }
    }
    if ((best_w == 0)) {
        for (int64_t i = 0; i < count; i++) {
            NR_PREFETCH(&out[i + 8], 0, 1);
            NR_PREFETCH(&funcs[i + 8], 0, 1);
            out[i] = funcs[i];
        }
        free(total_w);
        return;
    }
    int32_t* placed = malloc((((int64_t)(count)) * 4));
    int32_t* placed_set = malloc((((int64_t)(count)) * 4));
    for (int64_t i = 0; i < count; i++) {
        NR_PREFETCH(&placed_set[i + 8], 0, 1);
        placed_set[i] = 0;
    }
    placed[0] = best_edge_a;
    placed[1] = best_edge_b;
    placed_set[best_edge_a] = 1;
    placed_set[best_edge_b] = 1;
    int32_t placed_count = (int32_t)(2);
    for (int64_t iter = 0; iter < (count - 2); iter++) {
        int32_t best_idx = (int32_t)((-1));
        int64_t best_tw = (-1);
        for (int64_t i = 0; i < count; i++) {
            NR_PREFETCH(&total_w[i + 8], 0, 1);
            NR_PREFETCH(&placed_set[i + 8], 0, 1);
            if (((placed_set[i] == 0) && (total_w[i] > best_tw))) {
                best_tw = total_w[i];
                best_idx = (int32_t)(i);
            }
        }
        if ((best_idx < 0)) {
            for (int64_t i = 0; i < count; i++) {
                NR_PREFETCH(&placed_set[i + 8], 0, 1);
                if ((placed_set[i] == 0)) {
                    best_idx = (int32_t)(i);
                    break;
                }
            }
        }
        int32_t best_neighbor_pos = (int32_t)((placed_count - 1));
        int64_t best_nw = (-1);
        for (int64_t pi = 0; pi < placed_count; pi++) {
            NR_PREFETCH(&placed[pi + 8], 0, 1);
            NrStr* nkey = native_compile_file__edge_key(funcs[best_idx]->name, funcs[placed[pi]]->name);
            void* nwptr = strmap_strmap_get(edges, nkey);
            if ((nwptr != NULL)) {
                int64_t nw = ((int64_t)(nwptr));
                if ((nw > best_nw)) {
                    best_nw = nw;
                    best_neighbor_pos = (int32_t)(pi);
                }
            }
        }
        int32_t insert_pos = (int32_t)((best_neighbor_pos + 1));
        for (int64_t shi = placed_count; shi > insert_pos; shi += (-1)) {
            NR_PREFETCH(&placed[shi + 8], 0, 1);
            placed[shi] = placed[(shi - 1)];
        }
        placed[insert_pos] = best_idx;
        placed_set[best_idx] = 1;
        placed_count = (int32_t)((placed_count + 1));
    }
    for (int64_t i = 0; i < count; i++) {
        NR_PREFETCH(&out[i + 8], 0, 1);
        NR_PREFETCH(&placed[i + 8], 0, 1);
        out[i] = funcs[placed[i]];
    }
    free(total_w);
    free(placed);
    free(placed_set);
}

void native_compile_file__dce_find_calls(const AstNode* restrict node, StrSet* restrict all_names, StrSet* restrict reachable, NrStr** restrict work, int32_t* restrict work_count, NrStr* restrict caller) {
    "Recursively find calls to module functions in a statement, add unreached ones to work list.";
    if ((node == NULL)) {
        return;
    }
    if ((node->tag == TAG_CALL)) {
        AstCall* c = node->data;
        if (((c->func != NULL) && (c->func->tag == TAG_NAME))) {
            AstName* fn = c->func->data;
            if (((!nr_str_eq(fn->id, caller)) && strmap_strset_has(all_names, fn->id) && (strmap_strset_has(reachable, fn->id) == 0))) {
                work[(*(work_count))] = fn->id;
                *(work_count) = ((*(work_count)) + 1);
                (void)0;
            }
        }
        for (int64_t i = 0; i < c->args.count; i++) {
            native_compile_file__dce_find_calls(c->args.items[i], all_names, reachable, work, work_count, caller);
        }
        return;
    }
    if ((node->tag == TAG_EXPR_STMT)) {
        AstExprStmt* es = node->data;
        native_compile_file__dce_find_calls(es->value, all_names, reachable, work, work_count, caller);
        return;
    }
    if ((node->tag == TAG_ASSIGN)) {
        AstAssign* a = node->data;
        native_compile_file__dce_find_calls(a->value, all_names, reachable, work, work_count, caller);
        return;
    }
    if ((node->tag == TAG_ANN_ASSIGN)) {
        AstAnnAssign* aa = node->data;
        native_compile_file__dce_find_calls(aa->value, all_names, reachable, work, work_count, caller);
        return;
    }
    if ((node->tag == TAG_IF)) {
        AstIf* ifd = node->data;
        for (int64_t i = 0; i < ifd->body.count; i++) {
            native_compile_file__dce_find_calls(ifd->body.items[i], all_names, reachable, work, work_count, caller);
        }
        for (int64_t i = 0; i < ifd->orelse.count; i++) {
            native_compile_file__dce_find_calls(ifd->orelse.items[i], all_names, reachable, work, work_count, caller);
        }
        native_compile_file__dce_find_calls(ifd->test, all_names, reachable, work, work_count, caller);
        return;
    }
    if ((node->tag == TAG_FOR)) {
        AstFor* fd = node->data;
        for (int64_t i = 0; i < fd->body.count; i++) {
            native_compile_file__dce_find_calls(fd->body.items[i], all_names, reachable, work, work_count, caller);
        }
        return;
    }
    if ((node->tag == TAG_WHILE)) {
        AstWhile* wd = node->data;
        for (int64_t i = 0; i < wd->body.count; i++) {
            native_compile_file__dce_find_calls(wd->body.items[i], all_names, reachable, work, work_count, caller);
        }
        return;
    }
    if ((node->tag == TAG_WITH)) {
        AstWith* wtd = node->data;
        for (int64_t i = 0; i < wtd->body.count; i++) {
            native_compile_file__dce_find_calls(wtd->body.items[i], all_names, reachable, work, work_count, caller);
        }
        return;
    }
    if ((node->tag == TAG_RETURN)) {
        AstReturn* rt = node->data;
        native_compile_file__dce_find_calls(rt->value, all_names, reachable, work, work_count, caller);
        return;
    }
    if ((node->tag == TAG_BIN_OP)) {
        AstBinOp* bo = node->data;
        native_compile_file__dce_find_calls(bo->left, all_names, reachable, work, work_count, caller);
        native_compile_file__dce_find_calls(bo->right, all_names, reachable, work, work_count, caller);
        return;
    }
    if ((node->tag == TAG_COMPARE)) {
        AstCompare* cmp = node->data;
        native_compile_file__dce_find_calls(cmp->left, all_names, reachable, work, work_count, caller);
        for (int64_t i = 0; i < cmp->comparators.count; i++) {
            native_compile_file__dce_find_calls(cmp->comparators.items[i], all_names, reachable, work, work_count, caller);
        }
        return;
    }
}

void native_compile_file__emit_functions(CompilerState* s, AstNodeList body) {
    "Compile and emit all function definitions including struct methods.";
    int64_t has_main = 0;
    NrStr** test_names = malloc((256 * 8));
    int32_t test_count = (int32_t)(0);
    AstFunctionDef** top_funcs = malloc((((int64_t)(body.count)) * 8));
    int32_t top_count = (int32_t)(0);
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node != NULL) && (node->tag == TAG_FUNCTION_DEF))) {
            AstFunctionDef* fd = node->data;
            if (native_compile_file__has_decorator(fd, nr_str_new("extern"))) {
                continue;
            }
            top_funcs[top_count] = fd;
            top_count = (int32_t)((top_count + 1));
        }
    }
    if (((s->dce_roots != NULL) && (top_count > 0))) {
        StrSet all_names = strmap_strset_new((((int64_t)(top_count)) * 2));
        for (int64_t i = 0; i < top_count; i++) {
            NR_PREFETCH(&top_funcs[i + 8], 0, 1);
            strmap_strset_add((&all_names), top_funcs[i]->name);
        }
        StrSet reachable = strmap_strset_new((((int64_t)(top_count)) * 2));
        NrStr** work = malloc((((int64_t)(top_count)) * 8));
        int32_t work_count = (int32_t)(0);
        for (int64_t i = 0; i < top_count; i++) {
            NR_PREFETCH(&top_funcs[i + 8], 0, 1);
            if ((strmap_strset_has(s->dce_roots, top_funcs[i]->name) || nr_str_eq(top_funcs[i]->name, (&(NrStr){.data=(char*)"main",.len=4})))) {
                work[work_count] = top_funcs[i]->name;
                work_count = (int32_t)((work_count + 1));
            }
        }
        while ((work_count > 0)) {
            work_count = (int32_t)((work_count - 1));
            NrStr* cur_name = work[work_count];
            if (strmap_strset_has((&reachable), cur_name)) {
                continue;
            }
            strmap_strset_add((&reachable), cur_name);
            for (int64_t fi = 0; fi < top_count; fi++) {
                NR_PREFETCH(&top_funcs[fi + 8], 0, 1);
                if (nr_str_eq(top_funcs[fi]->name, cur_name)) {
                    for (int64_t si = 0; si < top_funcs[fi]->body.count; si++) {
                        AstNode* bnode = top_funcs[fi]->body.items[si];
                        if ((bnode != NULL)) {
                            native_compile_file__dce_find_calls(bnode, (&all_names), (&reachable), work, (&work_count), cur_name);
                        }
                    }
                }
            }
        }
        int32_t new_count = (int32_t)(0);
        for (int64_t i = 0; i < top_count; i++) {
            NR_PREFETCH(&top_funcs[i + 8], 0, 1);
            if (strmap_strset_has((&reachable), top_funcs[i]->name)) {
                top_funcs[new_count] = top_funcs[i];
                new_count = (int32_t)((new_count + 1));
            }
        }
        top_count = new_count;
        free(work);
        strmap_strset_free((&all_names));
        strmap_strset_free((&reachable));
    }
    if (((s->reorder_funcs != 0) && (top_count > 1))) {
        StrSet func_names = strmap_strset_new((((int64_t)(top_count)) * 2));
        for (int64_t i = 0; i < top_count; i++) {
            NR_PREFETCH(&top_funcs[i + 8], 0, 1);
            strmap_strset_add((&func_names), top_funcs[i]->name);
        }
        StrMap edges = strmap_strmap_new((((int64_t)(top_count)) * 4));
        for (int64_t i = 0; i < top_count; i++) {
            NR_PREFETCH(&top_funcs[i + 8], 0, 1);
            int64_t is_hot = 0;
            if (native_compile_file__has_decorator(top_funcs[i], nr_str_new("hot"))) {
                is_hot = 1;
            }
            native_compile_file__walk_calls_weighted(top_funcs[i]->body, top_funcs[i]->name, (&func_names), (&edges), 0, is_hot);
        }
        AstFunctionDef** reordered = malloc((((int64_t)(top_count)) * 8));
        native_compile_file__reorder_by_call_graph(top_funcs, top_count, (&edges), reordered);
        for (int64_t i = 0; i < top_count; i++) {
            NR_PREFETCH(&top_funcs[i + 8], 0, 1);
            NR_PREFETCH(&reordered[i + 8], 0, 1);
            top_funcs[i] = reordered[i];
        }
        free(reordered);
        strmap_strmap_free((&edges));
        strmap_strset_free((&func_names));
    }
    for (int64_t i = 0; i < top_count; i++) {
        NR_PREFETCH(&top_funcs[i + 8], 0, 1);
        AstFunctionDef* fd2 = top_funcs[i];
        if (nr_str_eq(fd2->name, (&(NrStr){.data=(char*)"main",.len=4}))) {
            has_main = 1;
        }
        native_compile_file__compile_one_func(s, fd2, nr_str_new(""));
        if (native_compile_file__has_decorator(fd2, nr_str_new("test"))) {
            test_names[test_count] = fd2->name;
            test_count = (int32_t)((test_count + 1));
            native_compile_file__emit_raw(s, nr_str_format("static void _nr_run_test_%s(void) {", fd2->name->data));
            native_compile_file__emit_raw(s, nr_str_new("    _nr_test_total++;"));
            native_compile_file__emit_raw(s, nr_str_new("    _nr_test_failures = 0;"));
            native_compile_file__emit_raw(s, nr_str_format("    _nr_cprint(_NR_GREEN, \"[ RUN      ] %s\\n\");", fd2->name->data));
            native_compile_file__emit_raw(s, nr_str_new("    uint64_t _t1 = _nr_time_ns();"));
            native_compile_file__emit_raw(s, nr_str_format("    %s();", fd2->name->data));
            native_compile_file__emit_raw(s, nr_str_new("    uint64_t _t2 = _nr_time_ns();"));
            native_compile_file__emit_raw(s, nr_str_new("    char _tbuf[64]; _mp_fmt_time(_t2 - _t1, _tbuf, sizeof(_tbuf));"));
            native_compile_file__emit_raw(s, nr_str_new("    if (_nr_test_failures == 0) {"));
            native_compile_file__emit_raw(s, nr_str_format("        _nr_cprint(_NR_GREEN, \"[       OK ] %s %%s\\n\", _tbuf);", fd2->name->data));
            native_compile_file__emit_raw(s, nr_str_new("    } else {"));
            native_compile_file__emit_raw(s, nr_str_new("        _nr_test_fail_total++;"));
            native_compile_file__emit_raw(s, nr_str_format("        _nr_cprint(_NR_RED, \"[  FAILED  ] %s (%%d failures)\\n\", _nr_test_failures);", fd2->name->data));
            native_compile_file__emit_raw(s, nr_str_new("    }"));
            native_compile_file__emit_raw(s, nr_str_new("}"));
            native_compile_file__emit_raw(s, nr_str_new(""));
        }
    }
    free(top_funcs);
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* snode = body.items[i];
        if (((snode != NULL) && (snode->tag == TAG_CLASS_DEF))) {
            AstClassDef* cd = snode->data;
            if (strmap_strmap_has((&s->structs), cd->name)) {
                NrStr* method_prefix = nr_str_concat(cd->name, (&(NrStr){.data=(char*)"_",.len=1}));
                for (int64_t j = 0; j < cd->body.count; j++) {
                    AstNode* method = cd->body.items[j];
                    if (((method != NULL) && (method->tag == TAG_FUNCTION_DEF))) {
                        AstFunctionDef* md = method->data;
                        AstArguments* m_args = md->args->data;
                        if ((m_args->args.count > 0)) {
                            AstArg* first_arg = m_args->args.items[0]->data;
                            if (nr_str_eq(first_arg->name, (&(NrStr){.data=(char*)"self",.len=4}))) {
                                strmap_strmap_set((&s->func_args), nr_str_new("self"), nr_str_concat(cd->name, (&(NrStr){.data=(char*)"*",.len=1})));
                            }
                        }
                        native_compile_file__compile_one_func(s, md, method_prefix);
                    }
                }
            }
        }
    }
    if (((test_count > 0) && (has_main == 0))) {
        native_compile_file__emit_raw(s, nr_str_new("int main(void) {"));
        native_compile_file__emit_raw(s, nr_str_new("    _nr_time_init();"));
        for (int64_t i = 0; i < test_count; i++) {
            NR_PREFETCH(&test_names[i + 8], 0, 1);
            native_compile_file__emit_raw(s, nr_str_format("    _nr_run_test_%s();", test_names[i]->data));
        }
        native_compile_file__emit_raw(s, nr_str_new("    printf(\"[==========] %d tests, %d failures\\n\", _nr_test_total, _nr_test_fail_total);"));
        native_compile_file__emit_raw(s, nr_str_new("    return _nr_test_fail_total ? 1 : 0;"));
        native_compile_file__emit_raw(s, nr_str_new("}"));
        native_compile_file__emit_raw(s, nr_str_new(""));
    }
    free(test_names);
}

void native_compile_file__emit_runtime_impl(CompilerState* s) {
    "Emit the runtime implementation include at the end.";
    native_compile_file__emit_raw(s, nr_str_new(""));
    native_compile_file__emit_raw(s, nr_str_new("#define NATHRA_RT_IMPL"));
    native_compile_file__emit_raw(s, nr_str_new("#include \"nathra_rt.h\""));
}

int32_t native_compile_file_native_compile(const uint8_t* restrict ast_buf, int64_t ast_len, uint8_t** restrict out_buf, int64_t* restrict out_len) {
    "Compile a serialized AST to C source code.\n\n    Args:\n        ast_buf: Binary AST buffer (from ast_serial.py)\n        ast_len: Length of the buffer\n        out_buf: Output pointer — set to malloc'd C source string\n        out_len: Output length\n\n    Returns: 0 on success, -1 on error.\n    ";
    AstNode* root = ast_nodes_deserialize_ast(ast_buf, ast_len);
    if ((root == NULL)) {
        return (-2);
    }
    if ((root->tag != TAG_MODULE)) {
        return ((int64_t)(root->tag));
    }
    AstModule* mod = root->data;
    CompilerState s = native_compiler_state_compiler_state_new();
    native_compile_file__first_pass((&s), mod->body);
    native_compile_file__scan_typed_lists((&s), mod->body);
    native_analysis_native_infer_cold_from_body((&s), mod->body);
    native_analysis_native_build_alloc_tags((&s), mod->body);
    native_compile_file__emit_includes((&s), mod->body);
    native_compile_file__emit_typed_lists((&s));
    native_compile_file__emit_forward_typedefs((&s), mod->body);
    native_compile_file__emit_enums((&s), mod->body);
    native_compile_file__emit_struct_defs((&s), mod->body);
    native_compile_file__emit_constants((&s), mod->body);
    native_compile_file__emit_globals((&s), mod->body);
    native_compile_file__emit_function_prototypes((&s), mod->body);
    native_compile_file__emit_functions((&s), mod->body);
    native_compile_file__emit_runtime_impl((&s));
    int64_t result_len = 0;
    uint8_t* result_buf = nr_writer_to_bytes(s.lines, (&result_len));
    *(out_buf) = result_buf;
    (void)0;
    *(out_len) = result_len;
    (void)0;
    return 0;
}

CompilerState* native_compile_file_native_state_new(void) {
    "Create a persistent compiler state for multi-module compilation.";
    CompilerState* s = malloc(sizeof(CompilerState));
    {
        CompilerState init = native_compiler_state_compiler_state_new();
        *(s) = init;
        (void)0;
    }
    return s;
}

int32_t native_compile_file_native_compile_dep(CompilerState* restrict state, const uint8_t* restrict ast_buf, int64_t ast_len, const uint8_t* restrict used_names_buf, int64_t used_names_len, uint8_t** restrict out_c, int64_t* restrict out_c_len, uint8_t** restrict out_h, int64_t* restrict out_h_len) {
    "Compile a dependency module, load its types into state, emit C + H.\n\n    used_names_buf: packed list of imported names (i32 count, then i32 len + bytes each).\n    Pass NULL/0 to skip DCE (emit everything).\n\n    Returns: 0 on success, negative on error.\n    ";
    AstNode* root = ast_nodes_deserialize_ast(ast_buf, ast_len);
    if ((root == NULL)) {
        return (-2);
    }
    if ((root->tag != TAG_MODULE)) {
        return (-3);
    }
    AstModule* mod = root->data;
    {
        StrSet used_set = strmap_strset_new(16);
        int64_t has_dce = 0;
        if (((used_names_buf != NULL) && (used_names_len > 0))) {
            has_dce = 1;
            int64_t start = 0;
            for (int64_t pos = 0; pos < used_names_len; pos++) {
                NR_PREFETCH(&used_names_buf[pos + 8], 0, 1);
                if ((used_names_buf[pos] == 0)) {
                    if ((pos > start)) {
                        int64_t slen = (pos - start);
                        uint8_t* nbuf = malloc((slen + 1));
                        for (int64_t bi = 0; bi < slen; bi++) {
                            NR_PREFETCH(&nbuf[bi + 8], 0, 1);
                            nbuf[bi] = used_names_buf[(start + bi)];
                        }
                        nbuf[slen] = 0;
                        strmap_strset_add((&used_set), nr_str_new(nbuf));
                        free(nbuf);
                    }
                    start = (pos + 1);
                }
            }
        }
        native_compile_file__first_pass(state, mod->body);
        native_compile_file__scan_typed_lists(state, mod->body);
        NrWriter* saved_lines = state->lines;
        NrWriter* saved_header = state->header;
        state->lines = nr_writer_new(4096);
        state->header = nr_writer_new(1024);
        if (has_dce) {
            state->dce_roots = (&used_set);
        }
        native_compile_file__emit_includes(state, mod->body);
        native_compile_file__emit_typed_lists(state);
        native_compile_file__emit_forward_typedefs(state, mod->body);
        native_compile_file__emit_enums(state, mod->body);
        native_compile_file__emit_struct_defs(state, mod->body);
        native_compile_file__emit_constants(state, mod->body);
        native_compile_file__emit_globals(state, mod->body);
        native_compile_file__emit_function_prototypes(state, mod->body);
        native_compile_file__emit_functions(state, mod->body);
        native_compile_file__emit_runtime_impl(state);
        state->dce_roots = NULL;
        int64_t c_len = 0;
        uint8_t* c_buf = nr_writer_to_bytes(state->lines, (&c_len));
        *(out_c) = c_buf;
        (void)0;
        *(out_c_len) = c_len;
        (void)0;
        int64_t h_len = 0;
        uint8_t* h_buf = nr_writer_to_bytes(state->header, (&h_len));
        *(out_h) = h_buf;
        (void)0;
        *(out_h_len) = h_len;
        (void)0;
        state->lines = saved_lines;
        state->header = saved_header;
        strmap_strset_free((&used_set));
    }
    return 0;
}

int32_t native_compile_file_native_compile_main(CompilerState* restrict state, const uint8_t* restrict ast_buf, int64_t ast_len, uint8_t** restrict out_buf, int64_t* restrict out_len) {
    "Compile the main module using accumulated types from prior native_compile_dep calls.";
    AstNode* root = ast_nodes_deserialize_ast(ast_buf, ast_len);
    if ((root == NULL)) {
        return (-2);
    }
    if ((root->tag != TAG_MODULE)) {
        return (-3);
    }
    AstModule* mod = root->data;
    native_compile_file__first_pass(state, mod->body);
    native_compile_file__scan_typed_lists(state, mod->body);
    native_analysis_native_infer_cold_from_body(state, mod->body);
    native_analysis_native_build_alloc_tags(state, mod->body);
    state->lines = nr_writer_new(4096);
    native_compile_file__emit_includes(state, mod->body);
    native_compile_file__emit_typed_lists(state);
    native_compile_file__emit_forward_typedefs(state, mod->body);
    native_compile_file__emit_enums(state, mod->body);
    native_compile_file__emit_struct_defs(state, mod->body);
    native_compile_file__emit_constants(state, mod->body);
    native_compile_file__emit_globals(state, mod->body);
    native_compile_file__emit_function_prototypes(state, mod->body);
    native_compile_file__emit_functions(state, mod->body);
    native_compile_file__emit_runtime_impl(state);
    int64_t result_len = 0;
    uint8_t* result_buf = nr_writer_to_bytes(state->lines, (&result_len));
    *(out_buf) = result_buf;
    (void)0;
    *(out_len) = result_len;
    (void)0;
    return 0;
}
