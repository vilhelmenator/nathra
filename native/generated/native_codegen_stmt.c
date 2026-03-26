/* mpy_stamp: 1774530501.865886 */
#include "micropy_rt.h"
#include "native_codegen_stmt.h"

void native_codegen_stmt__emit(CompilerState* restrict s, const MpStr* restrict line);
void native_codegen_stmt_native_compile_stmt(CompilerState* restrict s, AstNode* restrict node);
void native_codegen_stmt_native_compile_assert(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_raise(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_aug_assign(CompilerState* restrict s, const AstNode* restrict node);
MpStr* native_codegen_stmt__aug_op_method(uint8_t op);
void native_codegen_stmt_native_compile_return(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_if(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_while(CompilerState* restrict s, const AstNode* restrict node);
MpStr* native_codegen_stmt__infer_cleanup(const MpStr* open_func);
void native_codegen_stmt_native_compile_with(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_assign(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_ann_assign(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_for(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_match(CompilerState* restrict s, const AstNode* restrict node);
MpStr* native_codegen_stmt__match_pattern_cond(CompilerState* restrict s, MpStr* restrict subject, const AstNode* restrict pattern);
int main(void);

void native_codegen_stmt__emit(CompilerState* restrict s, const MpStr* restrict line) {
    for (int64_t i = 0; i < s->indent; i++) {
        mp_write_text(s->lines, mp_str_new("    "));
    }
    mp_write_text(s->lines, line);
    mp_write_text(s->lines, mp_str_new("\n"));
}

MpStr* native_codegen_stmt__infer_cleanup(const MpStr* open_func) {
    "Infer cleanup function from open/create function name.\n    Matches Python compiler's _infer_cleanup (codegen_stmts.py:1660).";
    if ((mp_str_eq(open_func, (&(MpStr){.data=(char*)"open",.len=4})) || mp_str_eq(open_func, (&(MpStr){.data=(char*)"file_open",.len=9})))) {
        return mp_str_new("mp_file_close");
    }
    if (mp_str_ends_with(open_func, mp_str_new("_open"))) {
        MpStr* base = mp_str_slice(open_func, 0, (mp_str_len(open_func) - 5));
        return mp_str_concat(base, (&(MpStr){.data=(char*)"_close",.len=6}));
    }
    if (mp_str_ends_with(open_func, mp_str_new("_new"))) {
        MpStr* base2 = mp_str_slice(open_func, 0, (mp_str_len(open_func) - 4));
        return mp_str_concat(base2, (&(MpStr){.data=(char*)"_free",.len=5}));
    }
    if (mp_str_ends_with(open_func, mp_str_new("_create"))) {
        MpStr* base3 = mp_str_slice(open_func, 0, (mp_str_len(open_func) - 7));
        return mp_str_concat(base3, (&(MpStr){.data=(char*)"_destroy",.len=8}));
    }
    return NULL;
}

void native_codegen_stmt_native_compile_with(CompilerState* restrict s, const AstNode* restrict node) {
    AstWith* p = node->data;
    MpStr** cleanup_fns = malloc((16 * 8));
    MpStr** var_names = malloc((16 * 8));
    int32_t item_count = p->items.count;
    for (int64_t i = 0; i < item_count; i++) {
        MP_PREFETCH(&cleanup_fns[i + 8], 0, 1);
        MP_PREFETCH(&var_names[i + 8], 0, 1);
        AstWithItem* item = p->items.items[i]->data;
        MpStr* enter_expr = native_codegen_expr_native_compile_expr(s, item->context_expr);
        cleanup_fns[i] = NULL;
        var_names[i] = NULL;
        AstNode* ctx = item->context_expr;
        if (((ctx != NULL) && (ctx->tag == TAG_CALL))) {
            AstCall* cc = ctx->data;
            AstNode* cf = cc->func;
            if (((cf != NULL) && (cf->tag == TAG_NAME))) {
                AstName* cfn = cf->data;
                cleanup_fns[i] = native_codegen_stmt__infer_cleanup(cfn->id);
            }
        }
        native_codegen_stmt__emit(s, mp_str_new("{"));
        s->indent = (int32_t)((s->indent + 1));
        if (((item->optional_vars != NULL) && (item->optional_vars->tag == TAG_NAME))) {
            AstName* vn = item->optional_vars->data;
            var_names[i] = vn->id;
            native_codegen_stmt__emit(s, mp_str_format("__auto_type %s = %s;", vn->id->data, enter_expr->data));
        } else {
            native_codegen_stmt__emit(s, mp_str_format("%s;", enter_expr->data));
        }
    }
    for (int64_t i = 0; i < p->body.count; i++) {
        native_codegen_stmt_native_compile_stmt(s, p->body.items[i]);
    }
    for (int64_t i = 0; i < item_count; i++) {
        int32_t idx = (int32_t)(((item_count - 1) - i));
        if (((cleanup_fns[idx] != NULL) && (var_names[idx] != NULL))) {
            native_codegen_stmt__emit(s, mp_str_format("%s(%s);", cleanup_fns[idx]->data, var_names[idx]->data));
        }
        s->indent = (int32_t)((s->indent - 1));
        native_codegen_stmt__emit(s, mp_str_new("}"));
    }
    free(cleanup_fns);
    free(var_names);
}

void native_codegen_stmt_native_compile_for(CompilerState* restrict s, const AstNode* restrict node) {
    "Basic for-range loop: for i in range(n) → for (int64_t i = 0; i < n; i++)";
    AstFor* p = node->data;
    if (((p->target != NULL) && (p->target->tag == TAG_TUPLE))) {
        AstTuple* tgt_tup = p->target->data;
        if (((tgt_tup->elts.count == 2) && (p->iter != NULL) && (p->iter->tag == TAG_CALL))) {
            AstCall* iter_call = p->iter->data;
            if (((iter_call->func != NULL) && (iter_call->func->tag == TAG_NAME))) {
                AstName* iter_fn = iter_call->func->data;
                if ((mp_str_eq(iter_fn->id, (&(MpStr){.data=(char*)"enumerate",.len=9})) && (iter_call->args.count == 1))) {
                    AstNode* idx_node = tgt_tup->elts.items[0];
                    AstNode* val_node = tgt_tup->elts.items[1];
                    if (((idx_node->tag == TAG_NAME) && (val_node->tag == TAG_NAME))) {
                        AstName* idx_n = idx_node->data;
                        AstName* val_n = val_node->data;
                        AstNode* arr_node = iter_call->args.items[0];
                        MpStr* arr_expr = native_codegen_expr_native_compile_expr(s, arr_node);
                        if ((arr_node->tag == TAG_NAME)) {
                            AstName* an = arr_node->data;
                            ArrayInfo* ai2 = strmap_strmap_get((&s->array_vars), an->id);
                            if ((ai2 != NULL)) {
                                native_codegen_stmt__emit(s, mp_str_format("for (int64_t %s = 0; %s < %s; %s++) {", idx_n->id->data, idx_n->id->data, ai2->size->data, idx_n->id->data));
                                s->indent = (int32_t)((s->indent + 1));
                                native_codegen_stmt__emit(s, mp_str_format("%s %s = %s[%s];", ai2->elem_type->data, val_n->id->data, arr_expr->data, idx_n->id->data));
                                strmap_strmap_set((&s->local_vars), idx_n->id, mp_str_new("int64_t"));
                                strmap_strmap_set((&s->local_vars), val_n->id, ai2->elem_type);
                                for (int64_t i = 0; i < p->body.count; i++) {
                                    native_codegen_stmt_native_compile_stmt(s, p->body.items[i]);
                                }
                                s->indent = (int32_t)((s->indent - 1));
                                native_codegen_stmt__emit(s, mp_str_new("}"));
                                return;
                            }
                        }
                    }
                }
            }
        }
        if (((p->iter != NULL) && (p->iter->tag == TAG_CALL))) {
            AstCall* zc = p->iter->data;
            if (((zc->func != NULL) && (zc->func->tag == TAG_NAME))) {
                AstName* zfn = zc->func->data;
                if ((mp_str_eq(zfn->id, (&(MpStr){.data=(char*)"zip",.len=3})) && (zc->args.count == tgt_tup->elts.count))) {
                    AstNode* first_arr = zc->args.items[0];
                    MpStr* bound = mp_str_new("0");
                    if ((first_arr->tag == TAG_NAME)) {
                        AstName* fan = first_arr->data;
                        ArrayInfo* fai = strmap_strmap_get((&s->array_vars), fan->id);
                        if ((fai != NULL)) {
                            bound = fai->size;
                        }
                    }
                    native_codegen_stmt__emit(s, mp_str_format("for (int64_t _zip_i = 0; _zip_i < %s; _zip_i++) {", bound->data));
                    s->indent = (int32_t)((s->indent + 1));
                    for (int64_t zi = 0; zi < zc->args.count; zi++) {
                        AstNode* z_arr = zc->args.items[zi];
                        AstNode* z_tgt = tgt_tup->elts.items[zi];
                        if (((z_tgt->tag == TAG_NAME) && (z_arr->tag == TAG_NAME))) {
                            AstName* z_tn = z_tgt->data;
                            AstName* z_an = z_arr->data;
                            ArrayInfo* z_ai = strmap_strmap_get((&s->array_vars), z_an->id);
                            if ((z_ai != NULL)) {
                                native_codegen_stmt__emit(s, mp_str_format("%s %s = %s[_zip_i];", z_ai->elem_type->data, z_tn->id->data, z_an->id->data));
                                strmap_strmap_set((&s->local_vars), z_tn->id, z_ai->elem_type);
                            }
                        }
                    }
                    for (int64_t zi2 = 0; zi2 < p->body.count; zi2++) {
                        native_codegen_stmt_native_compile_stmt(s, p->body.items[zi2]);
                    }
                    s->indent = (int32_t)((s->indent - 1));
                    native_codegen_stmt__emit(s, mp_str_new("}"));
                    return;
                }
            }
        }
        if (((tgt_tup->elts.count == 2) && (p->iter != NULL) && (p->iter->tag == TAG_CALL))) {
            AstCall* di_call = p->iter->data;
            if (((di_call->func != NULL) && (di_call->func->tag == TAG_ATTRIBUTE))) {
                AstAttribute* di_attr = di_call->func->data;
                if ((mp_str_eq(di_attr->attr, (&(MpStr){.data=(char*)"items",.len=5})) && (di_attr->value != NULL) && (di_attr->value->tag == TAG_NAME))) {
                    AstName* di_obj = di_attr->value->data;
                    MpStr* di_dk = strmap_strmap_get((&s->local_vars), mp_str_concat((&(MpStr){.data=(char*)"__dict_K_",.len=9}), di_obj->id));
                    MpStr* di_dv = strmap_strmap_get((&s->local_vars), mp_str_concat((&(MpStr){.data=(char*)"__dict_V_",.len=9}), di_obj->id));
                    if (((di_dk != NULL) && (di_dv != NULL))) {
                        AstNode* k_node = tgt_tup->elts.items[0];
                        AstNode* v_node = tgt_tup->elts.items[1];
                        if (((k_node->tag == TAG_NAME) && (v_node->tag == TAG_NAME))) {
                            AstName* kn = k_node->data;
                            AstName* vn2 = v_node->data;
                            MpStr* di_idx = mp_str_format("_di_%s", di_obj->id->data);
                            native_codegen_stmt__emit(s, mp_str_format("for (int64_t %s = 0; %s < %s->cap; %s++) {", di_idx->data, di_idx->data, di_obj->id->data, di_idx->data));
                            s->indent = (int32_t)((s->indent + 1));
                            native_codegen_stmt__emit(s, mp_str_format("if (!%s->entries[%s].used) continue;", di_obj->id->data, di_idx->data));
                            if (mp_str_eq(di_dk, (&(MpStr){.data=(char*)"MpStr*",.len=6}))) {
                                native_codegen_stmt__emit(s, mp_str_format("MpStr* %s = mp_str_new(%s->entries[%s].key);", kn->id->data, di_obj->id->data, di_idx->data));
                            } else {
                                native_codegen_stmt__emit(s, mp_str_format("char* %s = %s->entries[%s].key;", kn->id->data, di_obj->id->data, di_idx->data));
                            }
                            if (mp_str_eq(di_dv, (&(MpStr){.data=(char*)"double",.len=6}))) {
                                native_codegen_stmt__emit(s, mp_str_format("double %s = mp_as_float(%s->entries[%s].val);", vn2->id->data, di_obj->id->data, di_idx->data));
                            } else {
                                native_codegen_stmt__emit(s, mp_str_format("%s %s = mp_as_int(%s->entries[%s].val);", di_dv->data, vn2->id->data, di_obj->id->data, di_idx->data));
                            }
                            strmap_strmap_set((&s->local_vars), kn->id, di_dk);
                            strmap_strmap_set((&s->local_vars), vn2->id, di_dv);
                            for (int64_t di_i = 0; di_i < p->body.count; di_i++) {
                                native_codegen_stmt_native_compile_stmt(s, p->body.items[di_i]);
                            }
                            s->indent = (int32_t)((s->indent - 1));
                            native_codegen_stmt__emit(s, mp_str_new("}"));
                            return;
                        }
                    }
                }
            }
        }
        native_codegen_stmt__emit(s, mp_str_new("/* unsupported tuple for target */"));
        return;
    }
    if (((p->target == NULL) || (p->target->tag != TAG_NAME))) {
        native_codegen_stmt__emit(s, mp_str_new("/* unsupported for target */"));
        return;
    }
    AstName* vn = p->target->data;
    MpStr* var = vn->id;
    if (((p->iter != NULL) && (p->iter->tag == TAG_CALL))) {
        AstCall* pc = p->iter->data;
        if (((pc->func != NULL) && (pc->func->tag == TAG_NAME))) {
            AstName* fn = pc->func->data;
            if (mp_str_eq(fn->id, (&(MpStr){.data=(char*)"range",.len=5}))) {
                if ((pc->args.count == 1)) {
                    MpStr* stop = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
                    native_codegen_stmt__emit(s, mp_str_format("for (int64_t %s = 0; %s < %s; %s++) {", var->data, var->data, stop->data, var->data));
                } else 
                if ((pc->args.count == 2)) {
                    MpStr* start = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
                    MpStr* stop2 = native_codegen_expr_native_compile_expr(s, pc->args.items[1]);
                    native_codegen_stmt__emit(s, mp_str_format("for (int64_t %s = %s; %s < %s; %s++) {", var->data, start->data, var->data, stop2->data, var->data));
                } else 
                if ((pc->args.count == 3)) {
                    MpStr* start2 = native_codegen_expr_native_compile_expr(s, pc->args.items[0]);
                    MpStr* stop3 = native_codegen_expr_native_compile_expr(s, pc->args.items[1]);
                    MpStr* step = native_codegen_expr_native_compile_expr(s, pc->args.items[2]);
                    AstNode* step_node = pc->args.items[2];
                    int64_t is_neg = 0;
                    if ((step_node->tag == TAG_UNARY_OP)) {
                        AstUnaryOp* uo = step_node->data;
                        if ((uo->op == OP_USUB)) {
                            is_neg = 1;
                        }
                    } else 
                    if ((step_node->tag == TAG_CONSTANT)) {
                        AstConstant* sc = step_node->data;
                        if (((sc->kind == 0) && (sc->int_val < 0))) {
                            is_neg = 1;
                        }
                    }
                    if (is_neg) {
                        native_codegen_stmt__emit(s, mp_str_format("for (int64_t %s = %s; %s > %s; %s += %s) {", var->data, start2->data, var->data, stop3->data, var->data, step->data));
                    } else {
                        native_codegen_stmt__emit(s, mp_str_format("for (int64_t %s = %s; %s < %s; %s += %s) {", var->data, start2->data, var->data, stop3->data, var->data, step->data));
                    }
                } else {
                    native_codegen_stmt__emit(s, mp_str_new("/* unsupported range() args */"));
                    return;
                }
                s->indent = (int32_t)((s->indent + 1));
                strmap_strmap_set((&s->local_vars), var, mp_str_new("int64_t"));
                for (int64_t i = 0; i < p->body.count; i++) {
                    native_codegen_stmt_native_compile_stmt(s, p->body.items[i]);
                }
                s->indent = (int32_t)((s->indent - 1));
                native_codegen_stmt__emit(s, mp_str_new("}"));
                return;
            }
        }
    }
    if (((p->iter != NULL) && (p->iter->tag == TAG_NAME))) {
        AstName* iter_name = p->iter->data;
        ArrayInfo* arr_info = strmap_strmap_get((&s->array_vars), iter_name->id);
        if ((arr_info != NULL)) {
            MpStr* idx_var = mp_str_format("_i_%s", var->data);
            MpStr* elem_type = arr_info->elem_type;
            MpStr* arr_size = arr_info->size;
            native_codegen_stmt__emit(s, mp_str_format("for (int64_t %s = 0; %s < %s; %s++) {", idx_var->data, idx_var->data, arr_size->data, idx_var->data));
            s->indent = (int32_t)((s->indent + 1));
            native_codegen_stmt__emit(s, mp_str_format("%s %s = %s[%s];", elem_type->data, var->data, iter_name->id->data, idx_var->data));
            strmap_strmap_set((&s->local_vars), var, elem_type);
            for (int64_t i = 0; i < p->body.count; i++) {
                native_codegen_stmt_native_compile_stmt(s, p->body.items[i]);
            }
            s->indent = (int32_t)((s->indent - 1));
            native_codegen_stmt__emit(s, mp_str_new("}"));
            return;
        }
    }
    native_codegen_stmt__emit(s, mp_str_new("/* unsupported for loop */"));
}

void native_codegen_stmt_native_compile_return(CompilerState* restrict s, const AstNode* restrict node) {
    AstReturn* p = node->data;
    if ((p->value != NULL)) {
        MpStr* val = native_codegen_expr_native_compile_expr(s, p->value);
        native_codegen_stmt__emit(s, mp_str_format("return %s;", val->data));
    } else {
        native_codegen_stmt__emit(s, mp_str_new("return;"));
    }
}

void native_codegen_stmt_native_compile_ann_assign(CompilerState* restrict s, const AstNode* restrict node) {
    "Variable declaration with type annotation.";
    AstAnnAssign* p = node->data;
    if (((p->target == NULL) || (p->target->tag != TAG_NAME))) {
        native_codegen_stmt__emit(s, mp_str_new("/* unsupported ann_assign target */"));
        return;
    }
    AstName* vn = p->target->data;
    MpStr* ctype = native_type_map_native_map_type(p->annotation);
    if (mp_str_eq(ctype, (&(MpStr){.data=(char*)"__array__",.len=9}))) {
        MpStr* elem = mp_str_new("int64_t");
        MpStr* size = mp_str_new("0");
        if (((p->annotation != NULL) && (p->annotation->tag == TAG_SUBSCRIPT))) {
            AstSubscript* ann_sub = p->annotation->data;
            AstNode* slice_node = ann_sub->slice;
            if (((slice_node != NULL) && (slice_node->tag == TAG_TUPLE))) {
                AstTuple* tup = slice_node->data;
                if ((tup->elts.count >= 1)) {
                    elem = native_type_map_native_map_type(tup->elts.items[0]);
                }
                if ((tup->elts.count >= 2)) {
                    size = native_codegen_expr_native_compile_expr(s, tup->elts.items[1]);
                }
            }
        }
        if ((p->value != NULL)) {
            MpStr* val = native_codegen_expr_native_compile_expr(s, p->value);
            native_codegen_stmt__emit(s, mp_str_format("%s %s[%s] = %s;", elem->data, vn->id->data, size->data, val->data));
        } else {
            native_codegen_stmt__emit(s, mp_str_format("%s %s[%s] = {0};", elem->data, vn->id->data, size->data));
        }
        strmap_strmap_set((&s->local_vars), vn->id, elem);
        ArrayInfo* ai = malloc(sizeof(ArrayInfo));
        ai->elem_type = elem;
        ai->size = size;
        strmap_strmap_set((&s->array_vars), vn->id, ai);
        return;
    }
    if ((mp_str_eq(ctype, (&(MpStr){.data=(char*)"__funcptr__",.len=11})) || mp_str_eq(ctype, (&(MpStr){.data=(char*)"__vec__",.len=7})))) {
        native_codegen_stmt__emit(s, mp_str_format("/* TODO: %s %s */", ctype->data, vn->id->data));
        return;
    }
    if (mp_str_eq(ctype, (&(MpStr){.data=(char*)"__typed_list__",.len=14}))) {
        MpStr* elem_t = mp_str_new("int64_t");
        if (((p->annotation != NULL) && (p->annotation->tag == TAG_SUBSCRIPT))) {
            AstSubscript* ann_sub2 = p->annotation->data;
            elem_t = native_type_map_native_map_type(ann_sub2->slice);
        }
        MpStr* list_name = strmap_strmap_get((&s->typed_lists), elem_t);
        if ((list_name != NULL)) {
            MpStr* list_type = mp_str_concat(list_name, (&(MpStr){.data=(char*)"*",.len=1}));
            native_codegen_stmt__emit(s, mp_str_format("%s %s = %s_new();", list_type->data, vn->id->data, list_name->data));
            if (((p->value != NULL) && (p->value->tag == TAG_LIST))) {
                AstList* p_list = p->value->data;
                for (int64_t li = 0; li < p_list->elts.count; li++) {
                    MpStr* lv = native_codegen_expr_native_compile_expr(s, p_list->elts.items[li]);
                    native_codegen_stmt__emit(s, mp_str_format("%s_append(%s, %s);", list_name->data, vn->id->data, lv->data));
                }
            }
            strmap_strmap_set((&s->local_vars), vn->id, list_type);
            strmap_strmap_set((&s->list_vars), vn->id, elem_t);
        } else {
            native_codegen_stmt__emit(s, mp_str_format("/* typed_list: unknown elem type %s */", elem_t->data));
        }
        return;
    }
    if (mp_str_starts_with(ctype, mp_str_new("MP_TLS "))) {
        MpStr* actual_tls = mp_str_slice(ctype, 7, mp_str_len(ctype));
        if ((p->value != NULL)) {
            MpStr* val_tls = native_codegen_expr_native_compile_expr(s, p->value);
            native_codegen_stmt__emit(s, mp_str_format("static MP_TLS %s %s = %s;", actual_tls->data, vn->id->data, val_tls->data));
        } else {
            native_codegen_stmt__emit(s, mp_str_format("static MP_TLS %s %s;", actual_tls->data, vn->id->data));
        }
        strmap_strmap_set((&s->local_vars), vn->id, actual_tls);
        return;
    }
    if (mp_str_starts_with(ctype, mp_str_new("__static__ "))) {
        MpStr* actual = mp_str_slice(ctype, 11, mp_str_len(ctype));
        if ((p->value != NULL)) {
            MpStr* val2 = native_codegen_expr_native_compile_expr(s, p->value);
            native_codegen_stmt__emit(s, mp_str_format("static %s %s = %s;", actual->data, vn->id->data, val2->data));
        } else {
            native_codegen_stmt__emit(s, mp_str_format("static %s %s;", actual->data, vn->id->data));
        }
        strmap_strmap_set((&s->local_vars), vn->id, actual);
        return;
    }
    if ((mp_str_eq(ctype, (&(MpStr){.data=(char*)"MpDict*",.len=7})) && (p->annotation != NULL) && (p->annotation->tag == TAG_SUBSCRIPT))) {
        AstSubscript* ann_d = p->annotation->data;
        AstNode* d_base = ann_d->value;
        if (((d_base != NULL) && (d_base->tag == TAG_NAME))) {
            AstName* d_bn = d_base->data;
            if (mp_str_eq(d_bn->id, (&(MpStr){.data=(char*)"dict",.len=4}))) {
                AstNode* d_sl = ann_d->slice;
                if (((d_sl != NULL) && (d_sl->tag == TAG_TUPLE))) {
                    AstTuple* d_tup = d_sl->data;
                    if ((d_tup->elts.count == 2)) {
                        MpStr* dk_type = native_type_map_native_map_type(d_tup->elts.items[0]);
                        MpStr* dv_type = native_type_map_native_map_type(d_tup->elts.items[1]);
                        strmap_strmap_set((&s->local_vars), mp_str_concat((&(MpStr){.data=(char*)"__dict_K_",.len=9}), vn->id), dk_type);
                        strmap_strmap_set((&s->local_vars), mp_str_concat((&(MpStr){.data=(char*)"__dict_V_",.len=9}), vn->id), dv_type);
                        native_codegen_stmt__emit(s, mp_str_format("MpDict* %s = mp_dict_new();", vn->id->data));
                        if (((p->value != NULL) && (p->value->tag == TAG_DICT))) {
                            AstDict* p_dict = p->value->data;
                            for (int64_t di = 0; di < p_dict->keys.count; di++) {
                                MpStr* dk_expr = native_codegen_expr_native_compile_expr(s, p_dict->keys.items[di]);
                                MpStr* dv_expr = native_codegen_expr_native_compile_expr(s, p_dict->values.items[di]);
                                if (mp_str_eq(dk_type, (&(MpStr){.data=(char*)"MpStr*",.len=6}))) {
                                    AstNode* dk_key = p_dict->keys.items[di];
                                    if ((dk_key->tag == TAG_CONSTANT)) {
                                        AstConstant* dkc = dk_key->data;
                                        if ((dkc->kind == CONST_STR)) {
                                            dk_expr = native_codegen_expr_native_compile_expr(s, dk_key);
                                        }
                                    }
                                }
                                MpStr* boxed_dv = mp_str_format("mp_val_int((int64_t)(%s))", dv_expr->data);
                                if (mp_str_eq(dv_type, (&(MpStr){.data=(char*)"double",.len=6}))) {
                                    boxed_dv = mp_str_format("mp_val_float(%s)", dv_expr->data);
                                }
                                native_codegen_stmt__emit(s, mp_str_format("mp_dict_set(%s, %s, %s);", vn->id->data, dk_expr->data, boxed_dv->data));
                            }
                        }
                        strmap_strmap_set((&s->local_vars), vn->id, ctype);
                        return;
                    }
                }
            }
        }
    }
    if ((mp_str_eq(ctype, (&(MpStr){.data=(char*)"MpStr*",.len=6})) && (p->value != NULL) && (p->value->tag == TAG_CONSTANT))) {
        AstConstant* sc = p->value->data;
        if (((sc->kind == CONST_STR) && (sc->str_val != NULL))) {
            MpStr* escaped = native_codegen_expr_native_compile_expr(s, p->value);
            int64_t slen = mp_str_len(sc->str_val);
            native_codegen_stmt__emit(s, mp_str_format("MpStr _stack_%s = {.data=(char*)%s, .len=%lld};", vn->id->data, escaped->data, slen));
            native_codegen_stmt__emit(s, mp_str_format("MpStr* %s = &_stack_%s;", vn->id->data, vn->id->data));
            strmap_strmap_set((&s->local_vars), vn->id, ctype);
            return;
        }
    }
    if ((p->value != NULL)) {
        MpStr* val3 = native_codegen_expr_native_compile_expr(s, p->value);
        native_codegen_stmt__emit(s, mp_str_format("%s %s = %s;", ctype->data, vn->id->data, val3->data));
    } else {
        native_codegen_stmt__emit(s, mp_str_format("%s %s;", ctype->data, vn->id->data));
    }
    strmap_strmap_set((&s->local_vars), vn->id, ctype);
}

MpStr* native_codegen_stmt__match_pattern_cond(CompilerState* restrict s, MpStr* restrict subject, const AstNode* restrict pattern) {
    "Generate a C condition expression for a match pattern.";
    if ((pattern->tag == TAG_MATCH_VALUE)) {
        AstMatchValue* mv2 = pattern->data;
        MpStr* val = native_codegen_expr_native_compile_expr(s, mv2->value);
        return mp_str_format("(%s == %s)", subject->data, val->data);
    }
    if ((pattern->tag == TAG_MATCH_OR)) {
        AstMatchOr* mo2 = pattern->data;
        MpStr* result = mp_str_new("");
        for (int64_t i = 0; i < mo2->patterns.count; i++) {
            MpStr* sub_cond = native_codegen_stmt__match_pattern_cond(s, subject, mo2->patterns.items[i]);
            if ((i > 0)) {
                result = mp_str_concat(result, (&(MpStr){.data=(char*)" || ",.len=4}));
            }
            result = mp_str_concat(result, sub_cond);
        }
        return mp_str_format("(%s)", result->data);
    }
    MpStr* val2 = native_codegen_expr_native_compile_expr(s, pattern);
    return mp_str_format("(%s == %s)", subject->data, val2->data);
}

void native_codegen_stmt_native_compile_match(CompilerState* restrict s, const AstNode* restrict node) {
    "Compile match/case — use switch for int patterns, if/else otherwise.";
    AstMatch* p = node->data;
    MpStr* subject = native_codegen_expr_native_compile_expr(s, p->subject);
    int64_t can_switch = 1;
    for (int64_t i = 0; i < p->cases.count; i++) {
        AstMatchCase* mc = p->cases.items[i]->data;
        if ((mc->guard != NULL)) {
            can_switch = 0;
        }
        AstNode* pat = mc->pattern;
        if ((pat == NULL)) {
            continue;
        }
        if ((pat->tag == TAG_MATCH_AS)) {
            continue;
        }
        if ((pat->tag == TAG_MATCH_VALUE)) {
            continue;
        }
        if ((pat->tag == TAG_MATCH_OR)) {
            continue;
        }
        can_switch = 0;
    }
    if (can_switch) {
        native_codegen_stmt__emit(s, mp_str_format("switch (%s) {", subject->data));
        s->indent = (int32_t)((s->indent + 1));
        for (int64_t i = 0; i < p->cases.count; i++) {
            AstMatchCase* mc2 = p->cases.items[i]->data;
            AstNode* pat2 = mc2->pattern;
            if (((pat2 == NULL) || (pat2->tag == TAG_MATCH_AS))) {
                native_codegen_stmt__emit(s, mp_str_new("default: {"));
            } else 
            if ((pat2->tag == TAG_MATCH_VALUE)) {
                AstMatchValue* mv = pat2->data;
                MpStr* label = native_codegen_expr_native_compile_expr(s, mv->value);
                native_codegen_stmt__emit(s, mp_str_format("case %s: {", label->data));
            } else 
            if ((pat2->tag == TAG_MATCH_OR)) {
                AstMatchOr* mo = pat2->data;
                MpStr* labels = mp_str_new("");
                for (int64_t k = 0; k < mo->patterns.count; k++) {
                    AstNode* sub_pat = mo->patterns.items[k];
                    if ((sub_pat->tag == TAG_MATCH_VALUE)) {
                        AstMatchValue* smv = sub_pat->data;
                        MpStr* sl = native_codegen_expr_native_compile_expr(s, smv->value);
                        labels = mp_str_concat(labels, mp_str_format("case %s: ", sl->data));
                    }
                }
                native_codegen_stmt__emit(s, mp_str_concat(labels, (&(MpStr){.data=(char*)"{",.len=1})));
            }
            s->indent = (int32_t)((s->indent + 1));
            for (int64_t j = 0; j < mc2->body.count; j++) {
                native_codegen_stmt_native_compile_stmt(s, mc2->body.items[j]);
            }
            native_codegen_stmt__emit(s, mp_str_new("break;"));
            s->indent = (int32_t)((s->indent - 1));
            native_codegen_stmt__emit(s, mp_str_new("}"));
        }
        s->indent = (int32_t)((s->indent - 1));
        native_codegen_stmt__emit(s, mp_str_new("}"));
    } else {
        MpStr** hoisted_names = malloc((64 * 8));
        int32_t hoisted_count = (int32_t)(0);
        for (int64_t i = 0; i < p->cases.count; i++) {
            AstMatchCase* mc_h = p->cases.items[i]->data;
            AstNode* pat_h = mc_h->pattern;
            if (((pat_h != NULL) && (pat_h->tag == TAG_MATCH_AS))) {
                AstMatchAs* ma_h = pat_h->data;
                if ((ma_h->name != NULL)) {
                    int64_t already = 0;
                    for (int64_t hj = 0; hj < hoisted_count; hj++) {
                        MP_PREFETCH(&hoisted_names[hj + 8], 0, 1);
                        if (mp_str_eq(hoisted_names[hj], ma_h->name)) {
                            already = 1;
                        }
                    }
                    if ((already == 0)) {
                        native_codegen_stmt__emit(s, mp_str_format("__typeof__(%s) %s = %s;", subject->data, ma_h->name->data, subject->data));
                        hoisted_names[hoisted_count] = ma_h->name;
                        hoisted_count = (int32_t)((hoisted_count + 1));
                    }
                }
            }
        }
        free(hoisted_names);
        int64_t first = 1;
        for (int64_t i = 0; i < p->cases.count; i++) {
            AstMatchCase* mc3 = p->cases.items[i]->data;
            AstNode* pat3 = mc3->pattern;
            int64_t is_wild = 0;
            if ((pat3 == NULL)) {
                is_wild = 1;
            } else 
            if ((pat3->tag == TAG_MATCH_AS)) {
                is_wild = 1;
            }
            if ((is_wild && (mc3->guard == NULL))) {
                if ((first == 0)) {
                    native_codegen_stmt__emit(s, mp_str_new("} else {"));
                } else {
                    native_codegen_stmt__emit(s, mp_str_new("{"));
                }
            } else 
            if ((is_wild && (mc3->guard != NULL))) {
                MpStr* guard_cond = native_codegen_expr_native_compile_expr(s, mc3->guard);
                if (first) {
                    native_codegen_stmt__emit(s, mp_str_format("if (%s) {", guard_cond->data));
                } else {
                    native_codegen_stmt__emit(s, mp_str_format("} else if (%s) {", guard_cond->data));
                }
            } else {
                MpStr* cond = native_codegen_stmt__match_pattern_cond(s, subject, pat3);
                if (first) {
                    native_codegen_stmt__emit(s, mp_str_format("if (%s) {", cond->data));
                } else {
                    native_codegen_stmt__emit(s, mp_str_format("} else if (%s) {", cond->data));
                }
            }
            first = 0;
            s->indent = (int32_t)((s->indent + 1));
            for (int64_t j = 0; j < mc3->body.count; j++) {
                native_codegen_stmt_native_compile_stmt(s, mc3->body.items[j]);
            }
            s->indent = (int32_t)((s->indent - 1));
        }
        if ((p->cases.count > 0)) {
            native_codegen_stmt__emit(s, mp_str_new("}"));
        }
    }
}

void native_codegen_stmt_native_compile_raise(CompilerState* restrict s, const AstNode* restrict node) {
    AstRaise* p = node->data;
    if ((p->exc != NULL)) {
        MpStr* msg = native_codegen_expr_native_compile_expr(s, p->exc);
        MpStr* ret = s->current_func_ret_type;
        if (((ret != NULL) && mp_str_starts_with(ret, mp_str_new("Result_")))) {
            native_codegen_stmt__emit(s, mp_str_format("return %s_err(%s);", ret->data, msg->data));
        } else {
            native_codegen_stmt__emit(s, mp_str_format("fprintf(stderr, \"Error: %%s\\n\", %s); abort();", msg->data));
        }
    } else {
        native_codegen_stmt__emit(s, mp_str_new("fprintf(stderr, \"raise with no argument\\n\"); abort();"));
    }
}

MpStr* native_codegen_stmt__aug_op_method(uint8_t op) {
    if ((op == OP_ADD)) {
        return mp_str_new("__add__");
    }
    if ((op == OP_SUB)) {
        return mp_str_new("__sub__");
    }
    if ((op == OP_MULT)) {
        return mp_str_new("__mul__");
    }
    if ((op == OP_DIV)) {
        return mp_str_new("__truediv__");
    }
    if ((op == OP_MOD)) {
        return mp_str_new("__mod__");
    }
    return NULL;
}

void native_codegen_stmt_native_compile_aug_assign(CompilerState* restrict s, const AstNode* restrict node) {
    AstAugAssign* p = node->data;
    MpStr* tgt_type = native_infer_native_infer_type(s, p->target);
    MpStr* tgt_base = native_infer__strip_ptr(tgt_type);
    if (strmap_strmap_has((&s->structs), tgt_base)) {
        MpStr* method = native_codegen_stmt__aug_op_method(p->op);
        if ((method != NULL)) {
            MpStr* mname = mp_str_concat(mp_str_concat(tgt_base, (&(MpStr){.data=(char*)"_",.len=1})), method);
            if (strmap_strmap_has((&s->func_ret_types), mname)) {
                MpStr* tgt = native_codegen_expr_native_compile_expr(s, p->target);
                MpStr* rhs = native_codegen_expr_native_compile_expr(s, p->value);
                MpStr* self_arg = tgt;
                if ((native_infer__ends_with_star(tgt_type) == 0)) {
                    self_arg = mp_str_format("&(%s)", tgt->data);
                }
                native_codegen_stmt__emit(s, mp_str_format("%s = %s(%s, %s);", tgt->data, mname->data, self_arg->data, rhs->data));
                return;
            }
        }
    }
    MpStr* tgt2 = native_codegen_expr_native_compile_expr(s, p->target);
    MpStr* val = native_codegen_expr_native_compile_expr(s, p->value);
    if ((s->safe_mode != 0)) {
        if ((mp_str_eq(tgt_type, (&(MpStr){.data=(char*)"int64_t",.len=7})) || mp_str_eq(tgt_type, (&(MpStr){.data=(char*)"int",.len=3})) || mp_str_eq(tgt_type, (&(MpStr){.data=(char*)"int32_t",.len=7})) || mp_str_eq(tgt_type, (&(MpStr){.data=(char*)"uint8_t",.len=7})))) {
            if ((p->op == OP_DIV)) {
                native_codegen_stmt__emit(s, mp_str_format("%s = mp_safe_div_i64(%s, %s, __FILE__, __LINE__);", tgt2->data, tgt2->data, val->data));
                return;
            }
            if ((p->op == OP_MOD)) {
                native_codegen_stmt__emit(s, mp_str_format("%s = mp_safe_mod_i64(%s, %s, __FILE__, __LINE__);", tgt2->data, tgt2->data, val->data));
                return;
            }
            if ((p->op == OP_ADD)) {
                native_codegen_stmt__emit(s, mp_str_format("%s = mp_safe_add_i64(%s, %s, __FILE__, __LINE__);", tgt2->data, tgt2->data, val->data));
                return;
            }
            if ((p->op == OP_SUB)) {
                native_codegen_stmt__emit(s, mp_str_format("%s = mp_safe_sub_i64(%s, %s, __FILE__, __LINE__);", tgt2->data, tgt2->data, val->data));
                return;
            }
            if ((p->op == OP_MULT)) {
                native_codegen_stmt__emit(s, mp_str_format("%s = mp_safe_mul_i64(%s, %s, __FILE__, __LINE__);", tgt2->data, tgt2->data, val->data));
                return;
            }
        }
    }
    MpStr* op = native_codegen_expr_native_compile_op(p->op);
    native_codegen_stmt__emit(s, mp_str_format("%s %s= %s;", tgt2->data, op->data, val->data));
}

void native_codegen_stmt_native_compile_assign(CompilerState* restrict s, const AstNode* restrict node) {
    AstAssign* p = node->data;
    MpStr* val = native_codegen_expr_native_compile_expr(s, p->value);
    for (int64_t i = 0; i < p->targets.count; i++) {
        AstNode* tgt_node = p->targets.items[i];
        if ((tgt_node->tag == TAG_SUBSCRIPT)) {
            AstSubscript* ts = tgt_node->data;
            if (((ts->value != NULL) && (ts->value->tag == TAG_NAME))) {
                AstName* tn = ts->value->data;
                MpStr* tl_et = strmap_strmap_get((&s->list_vars), tn->id);
                if ((tl_et != NULL)) {
                    MpStr* tl_ln = strmap_strmap_get((&s->typed_lists), tl_et);
                    if ((tl_ln != NULL)) {
                        MpStr* obj_e = native_codegen_expr_native_compile_expr(s, ts->value);
                        MpStr* idx_e = native_codegen_expr_native_compile_expr(s, ts->slice);
                        native_codegen_stmt__emit(s, mp_str_format("%s_set(%s, %s, %s);", tl_ln->data, obj_e->data, idx_e->data, val->data));
                        continue;
                    }
                }
                MpStr* d_vt = strmap_strmap_get((&s->local_vars), mp_str_concat((&(MpStr){.data=(char*)"__dict_V_",.len=9}), tn->id));
                if ((d_vt != NULL)) {
                    MpStr* d_obj = native_codegen_expr_native_compile_expr(s, ts->value);
                    MpStr* d_key = native_codegen_expr_native_compile_expr(s, ts->slice);
                    MpStr* boxed_v = mp_str_format("mp_val_int((int64_t)(%s))", val->data);
                    if (mp_str_eq(d_vt, (&(MpStr){.data=(char*)"double",.len=6}))) {
                        boxed_v = mp_str_format("mp_val_float(%s)", val->data);
                    }
                    native_codegen_stmt__emit(s, mp_str_format("mp_dict_set(%s, %s, %s);", d_obj->data, d_key->data, boxed_v->data));
                    continue;
                }
            }
        }
        MpStr* tgt = native_codegen_expr_native_compile_expr(s, tgt_node);
        native_codegen_stmt__emit(s, mp_str_format("%s = %s;", tgt->data, val->data));
    }
}

void native_codegen_stmt_native_compile_while(CompilerState* restrict s, const AstNode* restrict node) {
    AstWhile* p = node->data;
    MpStr* cond = native_codegen_expr_native_compile_expr(s, p->test);
    native_codegen_stmt__emit(s, mp_str_format("while (%s) {", cond->data));
    s->indent = (int32_t)((s->indent + 1));
    for (int64_t i = 0; i < p->body.count; i++) {
        native_codegen_stmt_native_compile_stmt(s, p->body.items[i]);
    }
    s->indent = (int32_t)((s->indent - 1));
    native_codegen_stmt__emit(s, mp_str_new("}"));
}

void native_codegen_stmt_native_compile_if(CompilerState* restrict s, const AstNode* restrict node) {
    AstIf* p = node->data;
    MpStr* cond = native_codegen_expr_native_compile_expr(s, p->test);
    MpStr* test_type = native_infer_native_infer_type(s, p->test);
    MpStr* test_base = native_infer__strip_ptr(test_type);
    MpStr* bool_method = mp_str_concat(test_base, (&(MpStr){.data=(char*)"___bool__",.len=9}));
    if ((strmap_strmap_has((&s->structs), test_base) && strmap_strmap_has((&s->func_ret_types), bool_method))) {
        MpStr* obj = native_codegen_expr_native_compile_expr(s, p->test);
        if (native_infer__ends_with_star(test_type)) {
            cond = mp_str_format("%s(%s)", bool_method->data, obj->data);
        } else {
            cond = mp_str_format("%s(&(%s))", bool_method->data, obj->data);
        }
    }
    int64_t is_guard = 0;
    if (((p->orelse.count == 0) && (p->body.count == 1))) {
        AstNode* guard_node = p->body.items[0];
        if ((guard_node->tag == TAG_RAISE)) {
            is_guard = 1;
        }
    }
    if (is_guard) {
        native_codegen_stmt__emit(s, mp_str_format("if (MP_UNLIKELY(%s)) {", cond->data));
    } else {
        native_codegen_stmt__emit(s, mp_str_format("if (%s) {", cond->data));
    }
    s->indent = (int32_t)((s->indent + 1));
    for (int64_t i = 0; i < p->body.count; i++) {
        native_codegen_stmt_native_compile_stmt(s, p->body.items[i]);
    }
    s->indent = (int32_t)((s->indent - 1));
    if ((p->orelse.count > 0)) {
        if ((p->orelse.count == 1)) {
            AstNode* elif_node = p->orelse.items[0];
            if ((elif_node->tag == TAG_IF)) {
                native_codegen_stmt__emit(s, mp_str_new("} else "));
                native_codegen_stmt_native_compile_if(s, elif_node);
                return;
            }
        }
        native_codegen_stmt__emit(s, mp_str_new("} else {"));
        s->indent = (int32_t)((s->indent + 1));
        for (int64_t i = 0; i < p->orelse.count; i++) {
            native_codegen_stmt_native_compile_stmt(s, p->orelse.items[i]);
        }
        s->indent = (int32_t)((s->indent - 1));
    }
    native_codegen_stmt__emit(s, mp_str_new("}"));
}

void native_codegen_stmt_native_compile_assert(CompilerState* restrict s, const AstNode* restrict node) {
    AstAssert* p = node->data;
    MpStr* cond = native_codegen_expr_native_compile_expr(s, p->test);
    if ((p->msg != NULL)) {
        MpStr* msg = native_codegen_expr_native_compile_expr(s, p->msg);
        native_codegen_stmt__emit(s, mp_str_format("if (!(%s)) { fprintf(stderr, \"AssertionError: %%s\\n\", %s); abort(); }", cond->data, msg->data));
    } else {
        native_codegen_stmt__emit(s, mp_str_format("if (!(%s)) { fprintf(stderr, \"AssertionError\\n\"); abort(); }", cond->data));
    }
}

void native_codegen_stmt_native_compile_stmt(CompilerState* restrict s, AstNode* restrict node) {
    "Compile an AST statement node to C code.";
    if ((node == NULL)) {
        return;
    }
    uint8_t tag = node->tag;
    if ((tag == TAG_BREAK)) {
        native_codegen_stmt__emit(s, mp_str_new("break;"));
        return;
    }
    if ((tag == TAG_CONTINUE)) {
        native_codegen_stmt__emit(s, mp_str_new("continue;"));
        return;
    }
    if ((tag == TAG_PASS)) {
        native_codegen_stmt__emit(s, mp_str_new("/* pass */"));
        return;
    }
    if ((tag == TAG_ASSERT)) {
        native_codegen_stmt_native_compile_assert(s, node);
        return;
    }
    if ((tag == TAG_RAISE)) {
        native_codegen_stmt_native_compile_raise(s, node);
        return;
    }
    if ((tag == TAG_EXPR_STMT)) {
        AstExprStmt* p = node->data;
        if (((p->value != NULL) && (p->value->tag == TAG_CALL))) {
            AstCall* call_node = p->value->data;
            if (((call_node->func != NULL) && (call_node->func->tag == TAG_NAME))) {
                AstName* call_fn = call_node->func->data;
                if (mp_str_eq(call_fn->id, (&(MpStr){.data=(char*)"defer",.len=5}))) {
                    if ((call_node->args.count == 1)) {
                        MpStr* deferred = native_codegen_expr_native_compile_expr(s, call_node->args.items[0]);
                        native_codegen_stmt__emit(s, mp_str_format("/* defer: %s */", deferred->data));
                    }
                    return;
                }
                if (mp_str_eq(call_fn->id, (&(MpStr){.data=(char*)"c_code",.len=6}))) {
                    if (((call_node->args.count == 1) && (call_node->args.items[0]->tag == TAG_CONSTANT))) {
                        AstConstant* cc = call_node->args.items[0]->data;
                        if (((cc->kind == CONST_STR) && (cc->str_val != NULL))) {
                            native_codegen_stmt__emit(s, cc->str_val);
                        }
                    }
                    return;
                }
            }
        }
        MpStr* expr = native_codegen_expr_native_compile_expr(s, p->value);
        native_codegen_stmt__emit(s, mp_str_concat(expr, (&(MpStr){.data=(char*)";",.len=1})));
        return;
    }
    if ((tag == TAG_RETURN)) {
        native_codegen_stmt_native_compile_return(s, node);
        return;
    }
    if ((tag == TAG_AUG_ASSIGN)) {
        native_codegen_stmt_native_compile_aug_assign(s, node);
        return;
    }
    if ((tag == TAG_IF)) {
        native_codegen_stmt_native_compile_if(s, node);
        return;
    }
    if ((tag == TAG_WHILE)) {
        native_codegen_stmt_native_compile_while(s, node);
        return;
    }
    if ((tag == TAG_WITH)) {
        native_codegen_stmt_native_compile_with(s, node);
        return;
    }
    if ((tag == TAG_ASSIGN)) {
        native_codegen_stmt_native_compile_assign(s, node);
        return;
    }
    if ((tag == TAG_ANN_ASSIGN)) {
        native_codegen_stmt_native_compile_ann_assign(s, node);
        return;
    }
    if ((tag == TAG_FOR)) {
        native_codegen_stmt_native_compile_for(s, node);
        return;
    }
    if ((tag == TAG_MATCH)) {
        native_codegen_stmt_native_compile_match(s, node);
        return;
    }
    native_codegen_stmt__emit(s, mp_str_new("/* TODO: unsupported statement */"));
}
