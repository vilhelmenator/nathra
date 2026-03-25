/* mpy_stamp: 1774473831.350640 */
#include "micropy_rt.h"
#include "native_compile_file.h"

void native_compile_file__emit(CompilerState* restrict s, const MpStr* restrict line);
void native_compile_file__emit_raw(CompilerState* restrict s, const MpStr* restrict line);
void native_compile_file__first_pass(CompilerState* s, AstNodeList body);
int64_t native_compile_file__has_decorator(const AstFunctionDef* restrict fd, const MpStr* restrict name);
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
void native_compile_file__compile_one_func(CompilerState* restrict s, AstFunctionDef* restrict fd, const MpStr* restrict prefix);
void native_compile_file__emit_functions(CompilerState* s, AstNodeList body);
void native_compile_file__emit_runtime_impl(CompilerState* s);
int32_t native_compile_file_native_compile(const uint8_t* restrict ast_buf, int64_t ast_len, uint8_t** restrict out_buf, int64_t* restrict out_len);
int main(void);

void native_compile_file__emit(CompilerState* restrict s, const MpStr* restrict line) {
    for (int64_t i = 0; i < s->indent; i++) {
        mp_write_text(s->lines, mp_str_new("    "));
    }
    mp_write_text(s->lines, line);
    mp_write_text(s->lines, mp_str_new("\n"));
}

void native_compile_file__emit_raw(CompilerState* restrict s, const MpStr* restrict line) {
    "Emit without indentation.";
    mp_write_text(s->lines, line);
    mp_write_text(s->lines, mp_str_new("\n"));
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
            MpStr* ret_type = native_type_map_native_map_type(fd->returns);
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
                            MpStr* ft = native_type_map_native_map_type(aa->annotation);
                            if (mp_str_eq(ft, (&(MpStr){.data=(char*)"__array__",.len=9}))) {
                                if (((aa->annotation != NULL) && (aa->annotation->tag == TAG_SUBSCRIPT))) {
                                    AstSubscript* asub = aa->annotation->data;
                                    AstNode* sl = asub->slice;
                                    if (((sl != NULL) && (sl->tag == TAG_TUPLE))) {
                                        AstTuple* tup = sl->data;
                                        if ((tup->elts.count >= 2)) {
                                            MpStr* et = native_type_map_native_map_type(tup->elts.items[0]);
                                            MpStr* sz = native_codegen_expr_native_compile_expr(s, tup->elts.items[1]);
                                            ft = mp_str_format("__arr_%s_%s", et->data, sz->data);
                                        }
                                    }
                                }
                            }
                            if (mp_str_eq(ft, (&(MpStr){.data=(char*)"__bitfield__",.len=12}))) {
                                if (((aa->annotation != NULL) && (aa->annotation->tag == TAG_SUBSCRIPT))) {
                                    AstSubscript* bf_sub = aa->annotation->data;
                                    AstNode* bf_sl = bf_sub->slice;
                                    if (((bf_sl != NULL) && (bf_sl->tag == TAG_TUPLE))) {
                                        AstTuple* bf_tup = bf_sl->data;
                                        if ((bf_tup->elts.count >= 2)) {
                                            MpStr* bf_t = native_type_map_native_map_type(bf_tup->elts.items[0]);
                                            MpStr* bf_w = native_codegen_expr_native_compile_expr(s, bf_tup->elts.items[1]);
                                            ft = mp_str_format("__bf_%s_%s", bf_t->data, bf_w->data);
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
                    MpStr* mret = native_type_map_native_map_type(md->returns);
                    MpStr* mname = mp_str_concat(mp_str_concat(cd->name, (&(MpStr){.data=(char*)"_",.len=1})), md->name);
                    strmap_strmap_set((&s->func_ret_types), mname, mret);
                }
            }
            continue;
        }
        if ((node->tag == TAG_ANN_ASSIGN)) {
            AstAnnAssign* aa2 = node->data;
            if (((aa2->target != NULL) && (aa2->target->tag == TAG_NAME))) {
                AstName* vn = aa2->target->data;
                MpStr* ct = native_type_map_native_map_type(aa2->annotation);
                int64_t is_upper = 1;
                int64_t name_len = mp_str_len(vn->id);
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

int64_t native_compile_file__has_decorator(const AstFunctionDef* restrict fd, const MpStr* restrict name) {
    "Check if a function definition has a decorator with the given name.";
    for (int64_t i = 0; i < fd->decorators.count; i++) {
        AstNode* dec = fd->decorators.items[i];
        if (((dec != NULL) && (dec->tag == TAG_NAME))) {
            AstName* dn = dec->data;
            if (mp_str_eq(dn->id, name)) {
                return 1;
            }
        }
    }
    return 0;
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
                    if ((mp_str_eq(bn->id, (&(MpStr){.data=(char*)"typed_list",.len=10})) || mp_str_eq(bn->id, (&(MpStr){.data=(char*)"list",.len=4})))) {
                        MpStr* elem_t = native_type_map_native_map_type(asub->slice);
                        if ((strmap_strmap_has((&s->typed_lists), elem_t) == 0)) {
                            MpStr* list_name = mp_str_concat(elem_t, (&(MpStr){.data=(char*)"List",.len=4}));
                            if (mp_str_eq(elem_t, (&(MpStr){.data=(char*)"int64_t",.len=7}))) {
                                list_name = mp_str_new("IntList");
                            } else 
                            if (mp_str_eq(elem_t, (&(MpStr){.data=(char*)"double",.len=6}))) {
                                list_name = mp_str_new("FloatList");
                            } else 
                            if (mp_str_eq(elem_t, (&(MpStr){.data=(char*)"uint8_t",.len=7}))) {
                                list_name = mp_str_new("ByteList");
                            }
                            strmap_strmap_set((&s->typed_lists), elem_t, list_name);
                        }
                    }
                }
            }
        }
        if ((node->tag == TAG_FUNCTION_DEF)) {
            AstFunctionDef* fd = node->data;
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
            MpStr* elem_t = m->keys[i];
            MpStr* list_name = m->values[i];
            MpStr* N = list_name;
            MpStr* T = elem_t;
            native_compile_file__emit_raw(s, mp_str_format("typedef struct { %s* data; int64_t len; int64_t cap; } %s;", T->data, N->data));
            native_compile_file__emit_raw(s, mp_str_format("static inline %s* %s_new(void) { %s* l = (%s*)malloc(sizeof(%s)); l->cap=8; l->len=0; l->data=(%s*)malloc(sizeof(%s)*l->cap); return l; }", N->data, N->data, N->data, N->data, N->data, T->data, T->data));
            native_compile_file__emit_raw(s, mp_str_format("static inline void %s_append(%s* l, %s v) { if(l->len>=l->cap){l->cap*=2;l->data=(%s*)realloc(l->data,sizeof(%s)*l->cap);} l->data[l->len++]=v; }", N->data, N->data, T->data, T->data, T->data));
            native_compile_file__emit_raw(s, mp_str_format("static inline %s %s_get(%s* l, int64_t i) { return l->data[i]; }", T->data, N->data, N->data));
            native_compile_file__emit_raw(s, mp_str_format("static inline void %s_set(%s* l, int64_t i, %s v) { l->data[i]=v; }", N->data, N->data, T->data));
            native_compile_file__emit_raw(s, mp_str_format("static inline int64_t %s_len(%s* l) { return l->len; }", N->data, N->data));
            native_compile_file__emit_raw(s, mp_str_format("static inline %s %s_pop(%s* l) { return l->data[--l->len]; }", T->data, N->data, N->data));
            native_compile_file__emit_raw(s, mp_str_format("static inline void %s_free(%s* l) { if(l){free(l->data);free(l);} }", N->data, N->data));
            native_compile_file__emit_raw(s, mp_str_new(""));
        }
    }
}

int64_t native_compile_file__has_test_funcs(AstNodeList body) {
    "Check if any function has @test decorator.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node != NULL) && (node->tag == TAG_FUNCTION_DEF))) {
            AstFunctionDef* fd = node->data;
            if (native_compile_file__has_decorator(fd, mp_str_new("test"))) {
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
    native_compile_file__emit_raw(s, mp_str_new("#include \"micropy_rt.h\""));
    if (native_compile_file__has_variadic_funcs(body)) {
        native_compile_file__emit_raw(s, mp_str_new("#include <stdarg.h>"));
    }
    if (native_compile_file__has_test_funcs(body)) {
        native_compile_file__emit_raw(s, mp_str_new("#include \"micropy_test.h\""));
    }
    native_compile_file__emit_raw(s, mp_str_new(""));
}

void native_compile_file__emit_forward_typedefs(CompilerState* s, AstNodeList body) {
    "Emit typedef struct X X; for each struct.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node != NULL) && (node->tag == TAG_CLASS_DEF))) {
            AstClassDef* cd = node->data;
            if (strmap_strmap_has((&s->structs), cd->name)) {
                native_compile_file__emit_raw(s, mp_str_format("typedef struct %s %s;", cd->name->data, cd->name->data));
            }
        }
    }
    native_compile_file__emit_raw(s, mp_str_new(""));
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
        native_compile_file__emit_raw(s, mp_str_format("typedef struct %s {", cd->name->data));
        for (int64_t j = 0; j < fl->count; j++) {
            MpStr* ftype = fl->entries[j].ctype;
            MpStr* fname = fl->entries[j].name;
            if (mp_str_starts_with(ftype, mp_str_new("__arr_"))) {
                MpStr* inner = mp_str_slice(ftype, 6, mp_str_len(ftype));
                int64_t last_us = (-1);
                for (int64_t k = 0; k < mp_str_len(inner); k++) {
                    if ((((uint8_t)(inner->data[k])) == 95)) {
                        last_us = k;
                    }
                }
                if ((last_us > 0)) {
                    MpStr* et = mp_str_slice(inner, 0, last_us);
                    MpStr* sz = mp_str_slice(inner, (last_us + 1), mp_str_len(inner));
                    native_compile_file__emit_raw(s, mp_str_format("    %s %s[%s];", et->data, fname->data, sz->data));
                } else {
                    native_compile_file__emit_raw(s, mp_str_format("    /* array field %s */", fname->data));
                }
            } else 
            if (mp_str_starts_with(ftype, mp_str_new("__bf_"))) {
                MpStr* bf_inner = mp_str_slice(ftype, 5, mp_str_len(ftype));
                int64_t bf_last = (-1);
                for (int64_t bk = 0; bk < mp_str_len(bf_inner); bk++) {
                    if ((((uint8_t)(bf_inner->data[bk])) == 95)) {
                        bf_last = bk;
                    }
                }
                if ((bf_last > 0)) {
                    MpStr* bf_t2 = mp_str_slice(bf_inner, 0, bf_last);
                    MpStr* bf_w2 = mp_str_slice(bf_inner, (bf_last + 1), mp_str_len(bf_inner));
                    native_compile_file__emit_raw(s, mp_str_format("    %s %s : %s;", bf_t2->data, fname->data, bf_w2->data));
                } else {
                    native_compile_file__emit_raw(s, mp_str_format("    /* bitfield %s */", fname->data));
                }
            } else 
            if ((mp_str_eq(ftype, (&(MpStr){.data=(char*)"__funcptr__",.len=11})) || mp_str_eq(ftype, (&(MpStr){.data=(char*)"__vec__",.len=7})) || mp_str_eq(ftype, (&(MpStr){.data=(char*)"__typed_list__",.len=14})))) {
                native_compile_file__emit_raw(s, mp_str_format("    /* TODO: %s %s */", ftype->data, fname->data));
            } else {
                native_compile_file__emit_raw(s, mp_str_format("    %s %s;", ftype->data, fname->data));
            }
        }
        native_compile_file__emit_raw(s, mp_str_format("} %s;", cd->name->data));
        MpStr* arg_list = mp_str_new("");
        MpStr* body_list = mp_str_new("");
        int32_t ctor_count = (int32_t)(0);
        for (int64_t j = 0; j < fl->count; j++) {
            MpStr* fname2 = fl->entries[j].name;
            MpStr* ftype2 = fl->entries[j].ctype;
            if (mp_str_starts_with(ftype2, mp_str_new("__"))) {
                continue;
            }
            if ((ctor_count > 0)) {
                arg_list = mp_str_concat(arg_list, (&(MpStr){.data=(char*)", ",.len=2}));
            }
            arg_list = mp_str_concat(arg_list, mp_str_format("%s %s", ftype2->data, fname2->data));
            body_list = mp_str_concat(body_list, mp_str_format("    _s.%s = %s;\n", fname2->data, fname2->data));
            ctor_count = (int32_t)((ctor_count + 1));
        }
        if ((ctor_count == 0)) {
            arg_list = mp_str_new("void");
        }
        native_compile_file__emit_raw(s, mp_str_format("static inline %s _mp_make_%s(%s) {", cd->name->data, cd->name->data, arg_list->data));
        native_compile_file__emit_raw(s, mp_str_format("    %s _s = {0};", cd->name->data));
        native_compile_file__emit_raw(s, body_list);
        native_compile_file__emit_raw(s, mp_str_new("    return _s;"));
        native_compile_file__emit_raw(s, mp_str_new("}"));
        native_compile_file__emit_raw(s, mp_str_new(""));
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
        native_compile_file__emit_raw(s, mp_str_format("typedef enum {", cd->name->data));
        for (int64_t j = 0; j < cd->body.count; j++) {
            AstNode* member = cd->body.items[j];
            if (((member != NULL) && (member->tag == TAG_ASSIGN))) {
                AstAssign* ma = member->data;
                if ((ma->targets.count > 0)) {
                    AstNode* tgt = ma->targets.items[0];
                    if ((tgt->tag == TAG_NAME)) {
                        AstName* mn = tgt->data;
                        MpStr* mval = native_codegen_expr_native_compile_expr(s, ma->value);
                        MpStr* comma = mp_str_new(",");
                        if ((j == (cd->body.count - 1))) {
                            comma = mp_str_new("");
                        }
                        native_compile_file__emit_raw(s, mp_str_format("    %s_%s = %s%s", cd->name->data, mn->id->data, mval->data, comma->data));
                    }
                }
            }
        }
        native_compile_file__emit_raw(s, mp_str_format("} %s;", cd->name->data));
        native_compile_file__emit_raw(s, mp_str_new(""));
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
            MpStr* ct = strmap_strmap_get((&s->constants), vn->id);
            if ((aa->value != NULL)) {
                MpStr* val = native_codegen_expr_native_compile_expr(s, aa->value);
                native_compile_file__emit_raw(s, mp_str_format("const %s %s = %s;", ct->data, vn->id->data, val->data));
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
            MpStr* ct = strmap_strmap_get((&s->mutable_globals), vn->id);
            if ((aa->value != NULL)) {
                MpStr* val = native_codegen_expr_native_compile_expr(s, aa->value);
                native_compile_file__emit_raw(s, mp_str_format("%s %s = %s;", ct->data, vn->id->data, val->data));
            } else {
                native_compile_file__emit_raw(s, mp_str_format("%s %s;", ct->data, vn->id->data));
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
        MpStr* ret = native_type_map_native_map_type(fd->returns);
        if (mp_str_eq(fd->name, (&(MpStr){.data=(char*)"main",.len=4}))) {
            ret = mp_str_new("int");
        }
        AstArguments* args_node = fd->args->data;
        MpStr* arg_str = mp_str_new("");
        for (int64_t j = 0; j < args_node->args.count; j++) {
            AstArg* arg = args_node->args.items[j]->data;
            MpStr* atype = native_type_map_native_map_type(arg->annotation);
            if ((j > 0)) {
                arg_str = mp_str_concat(arg_str, (&(MpStr){.data=(char*)", ",.len=2}));
            }
            arg_str = mp_str_concat(arg_str, mp_str_format("%s %s", atype->data, arg->name->data));
        }
        if ((args_node->vararg != NULL)) {
            if ((args_node->args.count > 0)) {
                arg_str = mp_str_concat(arg_str, (&(MpStr){.data=(char*)", ...",.len=5}));
            } else {
                arg_str = mp_str_new("...");
            }
        } else 
        if ((args_node->args.count == 0)) {
            arg_str = mp_str_new("void");
        }
        native_compile_file__emit_raw(s, mp_str_format("%s %s(%s);", ret->data, fd->name->data, arg_str->data));
    }
    native_compile_file__emit_raw(s, mp_str_new(""));
}

void native_compile_file__compile_one_func(CompilerState* restrict s, AstFunctionDef* restrict fd, const MpStr* restrict prefix) {
    "Compile a single function definition with optional name prefix.";
    if (native_compile_file__is_extern_func(fd)) {
        return;
    }
    MpStr* ret = native_type_map_native_map_type(fd->returns);
    AstArguments* args_node = fd->args->data;
    MpStr* arg_str = mp_str_new("");
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
        MpStr* atype = native_type_map_native_map_type(arg->annotation);
        if ((mp_str_eq(arg->name, (&(MpStr){.data=(char*)"self",.len=4})) && (mp_str_len(prefix) > 0))) {
            MpStr* struct_name = mp_str_slice(prefix, 0, (mp_str_len(prefix) - 1));
            atype = mp_str_concat(struct_name, (&(MpStr){.data=(char*)"*",.len=1}));
        }
        if ((j > 0)) {
            arg_str = mp_str_concat(arg_str, (&(MpStr){.data=(char*)", ",.len=2}));
        }
        arg_str = mp_str_concat(arg_str, mp_str_format("%s %s", atype->data, arg->name->data));
        strmap_strmap_set((&s->func_args), arg->name, atype);
    }
    if ((args_node->vararg != NULL)) {
        if ((args_node->args.count > 0)) {
            arg_str = mp_str_concat(arg_str, (&(MpStr){.data=(char*)", ...",.len=5}));
        } else {
            arg_str = mp_str_new("...");
        }
    } else 
    if ((args_node->args.count == 0)) {
        arg_str = mp_str_new("void");
    }
    s->current_func_ret_type = ret;
    MpStr* fname = fd->name;
    if ((mp_str_len(prefix) > 0)) {
        fname = mp_str_concat(prefix, fd->name);
    }
    if (mp_str_eq(fname, (&(MpStr){.data=(char*)"main",.len=4}))) {
        native_compile_file__emit_raw(s, mp_str_new("int main(void) {"));
    } else {
        native_compile_file__emit_raw(s, mp_str_format("%s %s(%s) {", ret->data, fname->data, arg_str->data));
    }
    s->indent = (int32_t)(1);
    for (int64_t j = 0; j < fd->body.count; j++) {
        native_codegen_stmt_native_compile_stmt(s, fd->body.items[j]);
    }
    s->indent = (int32_t)(0);
    native_compile_file__emit_raw(s, mp_str_new("}"));
    native_compile_file__emit_raw(s, mp_str_new(""));
}

void native_compile_file__emit_functions(CompilerState* s, AstNodeList body) {
    "Compile and emit all function definitions including struct methods.";
    int64_t has_main = 0;
    MpStr** test_names = malloc((256 * 8));
    int32_t test_count = (int32_t)(0);
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if (((node != NULL) && (node->tag == TAG_FUNCTION_DEF))) {
            AstFunctionDef* fd = node->data;
            if (mp_str_eq(fd->name, (&(MpStr){.data=(char*)"main",.len=4}))) {
                has_main = 1;
            }
            native_compile_file__compile_one_func(s, fd, mp_str_new(""));
            if (native_compile_file__has_decorator(fd, mp_str_new("test"))) {
                test_names[test_count] = fd->name;
                test_count = (int32_t)((test_count + 1));
                native_compile_file__emit_raw(s, mp_str_format("static void _mp_run_test_%s(void) {", fd->name->data));
                native_compile_file__emit_raw(s, mp_str_new("    _mp_test_total++;"));
                native_compile_file__emit_raw(s, mp_str_new("    _mp_test_failures = 0;"));
                native_compile_file__emit_raw(s, mp_str_format("    _mp_cprint(_MP_GREEN, \"[ RUN      ] %s\\n\");", fd->name->data));
                native_compile_file__emit_raw(s, mp_str_new("    uint64_t _t1 = _mp_time_ns();"));
                native_compile_file__emit_raw(s, mp_str_format("    %s();", fd->name->data));
                native_compile_file__emit_raw(s, mp_str_new("    uint64_t _t2 = _mp_time_ns();"));
                native_compile_file__emit_raw(s, mp_str_new("    char _tbuf[64]; _mp_fmt_time(_t2 - _t1, _tbuf, sizeof(_tbuf));"));
                native_compile_file__emit_raw(s, mp_str_new("    if (_mp_test_failures == 0) {"));
                native_compile_file__emit_raw(s, mp_str_format("        _mp_cprint(_MP_GREEN, \"[       OK ] %s %%s\\n\", _tbuf);", fd->name->data));
                native_compile_file__emit_raw(s, mp_str_new("    } else {"));
                native_compile_file__emit_raw(s, mp_str_new("        _mp_test_fail_total++;"));
                native_compile_file__emit_raw(s, mp_str_format("        _mp_cprint(_MP_RED, \"[  FAILED  ] %s (%%d failures)\\n\", _mp_test_failures);", fd->name->data));
                native_compile_file__emit_raw(s, mp_str_new("    }"));
                native_compile_file__emit_raw(s, mp_str_new("}"));
                native_compile_file__emit_raw(s, mp_str_new(""));
            }
        } else 
        if (((node != NULL) && (node->tag == TAG_CLASS_DEF))) {
            AstClassDef* cd = node->data;
            if (strmap_strmap_has((&s->structs), cd->name)) {
                MpStr* method_prefix = mp_str_concat(cd->name, (&(MpStr){.data=(char*)"_",.len=1}));
                for (int64_t j = 0; j < cd->body.count; j++) {
                    AstNode* method = cd->body.items[j];
                    if (((method != NULL) && (method->tag == TAG_FUNCTION_DEF))) {
                        AstFunctionDef* md = method->data;
                        AstArguments* m_args = md->args->data;
                        if ((m_args->args.count > 0)) {
                            AstArg* first_arg = m_args->args.items[0]->data;
                            if (mp_str_eq(first_arg->name, (&(MpStr){.data=(char*)"self",.len=4}))) {
                                strmap_strmap_set((&s->func_args), mp_str_new("self"), mp_str_concat(cd->name, (&(MpStr){.data=(char*)"*",.len=1})));
                            }
                        }
                        native_compile_file__compile_one_func(s, md, method_prefix);
                    }
                }
            }
        }
    }
    if (((test_count > 0) && (has_main == 0))) {
        native_compile_file__emit_raw(s, mp_str_new("int main(void) {"));
        native_compile_file__emit_raw(s, mp_str_new("    _mp_time_init();"));
        for (int64_t i = 0; i < test_count; i++) {
            MP_PREFETCH(&test_names[i + 8], 0, 1);
            native_compile_file__emit_raw(s, mp_str_format("    _mp_run_test_%s();", test_names[i]->data));
        }
        native_compile_file__emit_raw(s, mp_str_new("    printf(\"[==========] %d tests, %d failures\\n\", _mp_test_total, _mp_test_fail_total);"));
        native_compile_file__emit_raw(s, mp_str_new("    return _mp_test_fail_total ? 1 : 0;"));
        native_compile_file__emit_raw(s, mp_str_new("}"));
        native_compile_file__emit_raw(s, mp_str_new(""));
    }
    free(test_names);
}

void native_compile_file__emit_runtime_impl(CompilerState* s) {
    "Emit the runtime implementation include at the end.";
    native_compile_file__emit_raw(s, mp_str_new(""));
    native_compile_file__emit_raw(s, mp_str_new("#define MICROPY_RT_IMPL"));
    native_compile_file__emit_raw(s, mp_str_new("#include \"micropy_rt.h\""));
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
    uint8_t* result_buf = mp_writer_to_bytes(s.lines, (&result_len));
    *(out_buf) = result_buf;
    (void)0;
    *(out_len) = result_len;
    (void)0;
    return 0;
}
