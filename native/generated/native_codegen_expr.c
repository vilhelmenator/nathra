/* nth_stamp: 1774911850.086977 */
#include "nathra_rt.h"
#include "native_codegen_expr.h"

NrStr* native_codegen_call_native_compile_call(CompilerState* s, AstNode* node);
NrStr* native_codegen_expr_native_compile_op(uint8_t op);
NrStr* native_codegen_expr_native_compile_cmpop(uint8_t op);
NrStr* native_codegen_expr__escape_str(const NrStr* s);
NrStr* native_codegen_expr__binop_method(uint8_t op);
NrStr* native_codegen_expr__cmpop_method(uint8_t op);
void native_codegen_expr__emit(CompilerState* restrict s, const NrStr* restrict line);
NrStr* native_codegen_expr_native_compile_expr(CompilerState* restrict s, const AstNode* restrict node);
int main(void);

NrStr* native_codegen_expr_native_compile_op(uint8_t op) {
    "Map binary operator tag to C operator string.";
    if ((op == OP_ADD)) {
        return nr_str_new("+");
    }
    if ((op == OP_SUB)) {
        return nr_str_new("-");
    }
    if ((op == OP_MULT)) {
        return nr_str_new("*");
    }
    if ((op == OP_DIV)) {
        return nr_str_new("/");
    }
    if ((op == OP_MOD)) {
        return nr_str_new("%");
    }
    if ((op == OP_LSHIFT)) {
        return nr_str_new("<<");
    }
    if ((op == OP_RSHIFT)) {
        return nr_str_new(">>");
    }
    if ((op == OP_BIT_AND)) {
        return nr_str_new("&");
    }
    if ((op == OP_BIT_OR)) {
        return nr_str_new("|");
    }
    if ((op == OP_BIT_XOR)) {
        return nr_str_new("^");
    }
    if ((op == OP_FLOOR_DIV)) {
        return nr_str_new("/");
    }
    return nr_str_new("?");
}

NrStr* native_codegen_expr_native_compile_cmpop(uint8_t op) {
    "Map comparison operator tag to C operator string.";
    if ((op == OP_EQ)) {
        return nr_str_new("==");
    }
    if ((op == OP_NOT_EQ)) {
        return nr_str_new("!=");
    }
    if ((op == OP_LT)) {
        return nr_str_new("<");
    }
    if ((op == OP_LT_E)) {
        return nr_str_new("<=");
    }
    if ((op == OP_GT)) {
        return nr_str_new(">");
    }
    if ((op == OP_GT_E)) {
        return nr_str_new(">=");
    }
    if ((op == OP_IS)) {
        return nr_str_new("==");
    }
    if ((op == OP_IS_NOT)) {
        return nr_str_new("!=");
    }
    return nr_str_new("?");
}

NrStr* native_codegen_expr__escape_str(const NrStr* s) {
    "Escape a string for C string literal (\\, \", \\n).";
    int64_t slen = nr_str_len(s);
    uint8_t* buf = malloc(((slen * 2) + 1));
    int64_t j = 0;
    for (int64_t i = 0; i < slen; i++) {
        uint8_t ch = (uint8_t)(((uint8_t)(s->data[i])));
        if ((ch == 92)) {
            buf[j] = 92;
            buf[(j + 1)] = 92;
            j = (j + 2);
        } else 
        if ((ch == 34)) {
            buf[j] = 92;
            buf[(j + 1)] = 34;
            j = (j + 2);
        } else 
        if ((ch == 10)) {
            buf[j] = 92;
            buf[(j + 1)] = 110;
            j = (j + 2);
        } else {
            buf[j] = ch;
            j = (j + 1);
        }
    }
    buf[j] = 0;
    NrStr* result = nr_str_new(buf);
    free(buf);
    return result;
}

NrStr* native_codegen_expr__binop_method(uint8_t op) {
    if ((op == OP_ADD)) {
        return nr_str_new("__add__");
    }
    if ((op == OP_SUB)) {
        return nr_str_new("__sub__");
    }
    if ((op == OP_MULT)) {
        return nr_str_new("__mul__");
    }
    if ((op == OP_DIV)) {
        return nr_str_new("__truediv__");
    }
    if ((op == OP_MOD)) {
        return nr_str_new("__mod__");
    }
    return NULL;
}

NrStr* native_codegen_expr__cmpop_method(uint8_t op) {
    if ((op == OP_EQ)) {
        return nr_str_new("__eq__");
    }
    if ((op == OP_NOT_EQ)) {
        return nr_str_new("__ne__");
    }
    if ((op == OP_LT)) {
        return nr_str_new("__lt__");
    }
    if ((op == OP_LT_E)) {
        return nr_str_new("__le__");
    }
    if ((op == OP_GT)) {
        return nr_str_new("__gt__");
    }
    if ((op == OP_GT_E)) {
        return nr_str_new("__ge__");
    }
    return NULL;
}

void native_codegen_expr__emit(CompilerState* restrict s, const NrStr* restrict line) {
    "Emit a line of C code to the output buffer.";
    for (int64_t i = 0; i < s->indent; i++) {
        nr_write_text(s->lines, nr_str_new("    "));
    }
    nr_write_text(s->lines, line);
    nr_write_text(s->lines, nr_str_new("\n"));
}

NrStr* native_codegen_expr_native_compile_expr(CompilerState* restrict s, const AstNode* restrict node) {
    "Compile an AST expression node to a C expression string.";
    if ((node == NULL)) {
        return nr_str_new("0");
    }
    if ((node->tag == TAG_CONSTANT)) {
        AstConstant* p = node->data;
        if ((p->kind == CONST_NONE)) {
            return nr_str_new("NULL");
        }
        if ((p->kind == CONST_BOOL)) {
            if ((p->int_val != 0)) {
                return nr_str_new("1");
            }
            return nr_str_new("0");
        }
        if ((p->kind == CONST_STR)) {
            NrStr* escaped = native_codegen_expr__escape_str(p->str_val);
            return nr_str_concat(nr_str_new("\""), nr_str_concat(escaped, (&(NrStr){.data=(char*)"\"",.len=1})));
        }
        if ((p->kind == CONST_FLOAT)) {
            return nr_str_from_float(p->float_val);
        }
        if ((p->kind == CONST_INT)) {
            return nr_str_from_int(p->int_val);
        }
        if ((p->kind == CONST_ELLIPSIS)) {
            return nr_str_new("0");
        }
        return nr_str_new("0");
    }
    if ((node->tag == TAG_NAME)) {
        AstName* p2 = node->data;
        if (nr_str_eq(p2->id, (&(NrStr){.data=(char*)"True",.len=4}))) {
            return nr_str_new("1");
        }
        if (nr_str_eq(p2->id, (&(NrStr){.data=(char*)"False",.len=5}))) {
            return nr_str_new("0");
        }
        if (nr_str_eq(p2->id, (&(NrStr){.data=(char*)"None",.len=4}))) {
            return nr_str_new("NULL");
        }
        return p2->id;
    }
    if ((node->tag == TAG_BIN_OP)) {
        AstBinOp* p3 = node->data;
        if ((p3->op == OP_ADD)) {
            NrStr* lt = native_infer_native_infer_type(s, p3->left);
            if (nr_str_eq(lt, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
                NrStr* left = native_codegen_expr_native_compile_expr(s, p3->left);
                NrStr* right = native_codegen_expr_native_compile_expr(s, p3->right);
                if ((p3->left->tag == TAG_CONSTANT)) {
                    AstConstant* lc = p3->left->data;
                    if (((lc->kind == CONST_STR) && (lc->str_val != NULL))) {
                        NrStr* esc_l = native_codegen_expr__escape_str(lc->str_val);
                        left = nr_str_format("(&(NrStr){.data=(char*)\"%s\",.len=%lld})", esc_l->data, nr_str_len(lc->str_val));
                    }
                }
                if ((p3->right->tag == TAG_CONSTANT)) {
                    AstConstant* rc = p3->right->data;
                    if (((rc->kind == CONST_STR) && (rc->str_val != NULL))) {
                        NrStr* esc_r = native_codegen_expr__escape_str(rc->str_val);
                        right = nr_str_format("(&(NrStr){.data=(char*)\"%s\",.len=%lld})", esc_r->data, nr_str_len(rc->str_val));
                    }
                }
                return nr_str_format("nr_str_concat(%s, %s)", left->data, right->data);
            }
        }
        NrStr* lt2 = native_infer_native_infer_type(s, p3->left);
        NrStr* lb = native_infer__strip_ptr(lt2);
        if (strmap_strmap_has((&s->structs), lb)) {
            NrStr* method = native_codegen_expr__binop_method(p3->op);
            if ((method != NULL)) {
                NrStr* mname = nr_str_concat(nr_str_concat(lb, (&(NrStr){.data=(char*)"_",.len=1})), method);
                if (strmap_strmap_has((&s->func_ret_types), mname)) {
                    NrStr* left2 = native_codegen_expr_native_compile_expr(s, p3->left);
                    NrStr* right2 = native_codegen_expr_native_compile_expr(s, p3->right);
                    if (native_infer__ends_with_star(lt2)) {
                        return nr_str_format("%s(%s, %s)", mname->data, left2->data, right2->data);
                    }
                    return nr_str_format("%s(&(%s), %s)", mname->data, left2->data, right2->data);
                }
            }
        }
        NrStr* left3 = native_codegen_expr_native_compile_expr(s, p3->left);
        NrStr* right3 = native_codegen_expr_native_compile_expr(s, p3->right);
        if ((p3->op == OP_POW)) {
            return nr_str_format("pow(%s, %s)", left3->data, right3->data);
        }
        if ((s->safe_mode != 0)) {
            NrStr* lt3 = native_infer_native_infer_type(s, p3->left);
            if ((nr_str_eq(lt3, (&(NrStr){.data=(char*)"int64_t",.len=7})) || nr_str_eq(lt3, (&(NrStr){.data=(char*)"int",.len=3})) || nr_str_eq(lt3, (&(NrStr){.data=(char*)"int32_t",.len=7})) || nr_str_eq(lt3, (&(NrStr){.data=(char*)"uint8_t",.len=7})))) {
                if (((p3->op == OP_DIV) || (p3->op == OP_FLOOR_DIV))) {
                    return nr_str_format("nr_safe_div_i64(%s, %s, __FILE__, __LINE__)", left3->data, right3->data);
                }
                if ((p3->op == OP_MOD)) {
                    return nr_str_format("nr_safe_mod_i64(%s, %s, __FILE__, __LINE__)", left3->data, right3->data);
                }
                if ((p3->op == OP_ADD)) {
                    return nr_str_format("nr_safe_add_i64(%s, %s, __FILE__, __LINE__)", left3->data, right3->data);
                }
                if ((p3->op == OP_SUB)) {
                    return nr_str_format("nr_safe_sub_i64(%s, %s, __FILE__, __LINE__)", left3->data, right3->data);
                }
                if ((p3->op == OP_MULT)) {
                    return nr_str_format("nr_safe_mul_i64(%s, %s, __FILE__, __LINE__)", left3->data, right3->data);
                }
            }
        }
        if ((p3->op == OP_FLOOR_DIV)) {
            return nr_str_format("((%s) / (%s))", left3->data, right3->data);
        }
        NrStr* op = native_codegen_expr_native_compile_op(p3->op);
        return nr_str_format("(%s %s %s)", left3->data, op->data, right3->data);
    }
    if ((node->tag == TAG_UNARY_OP)) {
        AstUnaryOp* p4 = node->data;
        if ((p4->op == OP_USUB)) {
            NrStr* ot = native_infer_native_infer_type(s, p4->operand);
            NrStr* ob = native_infer__strip_ptr(ot);
            NrStr* neg_name = nr_str_concat(ob, (&(NrStr){.data=(char*)"___neg__",.len=8}));
            if (strmap_strmap_has((&s->structs), ob)) {
                if (strmap_strmap_has((&s->func_ret_types), neg_name)) {
                    NrStr* operand = native_codegen_expr_native_compile_expr(s, p4->operand);
                    if (native_infer__ends_with_star(ot)) {
                        return nr_str_format("%s(%s)", neg_name->data, operand->data);
                    }
                    return nr_str_format("%s(&(%s))", neg_name->data, operand->data);
                }
            }
        }
        NrStr* operand2 = native_codegen_expr_native_compile_expr(s, p4->operand);
        if ((p4->op == OP_USUB)) {
            return nr_str_format("(-%s)", operand2->data);
        }
        if ((p4->op == OP_UADD)) {
            return nr_str_format("(+%s)", operand2->data);
        }
        if ((p4->op == OP_NOT)) {
            return nr_str_format("(!%s)", operand2->data);
        }
        if ((p4->op == OP_INVERT)) {
            return nr_str_format("(~%s)", operand2->data);
        }
    }
    if ((node->tag == TAG_BOOL_OP)) {
        AstBoolOp* p5 = node->data;
        NrStr* op_str = nr_str_new(" && ");
        if ((p5->op == OP_OR)) {
            op_str = nr_str_new(" || ");
        }
        NrStr* result = native_codegen_expr_native_compile_expr(s, p5->values.items[0]);
        for (int64_t i = 1; i < p5->values.count; i++) {
            NrStr* part = native_codegen_expr_native_compile_expr(s, p5->values.items[i]);
            result = nr_str_concat(result, nr_str_concat(op_str, part));
        }
        return nr_str_format("(%s)", result->data);
    }
    if ((node->tag == TAG_COMPARE)) {
        AstCompare* p6 = node->data;
        if (((p6->op_count == 1) && (p6->comparators.count == 1))) {
            NrStr* lt3 = native_infer_native_infer_type(s, p6->left);
            if (nr_str_eq(lt3, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
                NrStr* left4 = native_codegen_expr_native_compile_expr(s, p6->left);
                NrStr* right4 = native_codegen_expr_native_compile_expr(s, p6->comparators.items[0]);
                AstNode* cmp_node = p6->comparators.items[0];
                if ((cmp_node->tag == TAG_CONSTANT)) {
                    AstConstant* cmp_c = cmp_node->data;
                    if (((cmp_c->kind == CONST_STR) && (cmp_c->str_val != NULL))) {
                        NrStr* esc_c = native_codegen_expr__escape_str(cmp_c->str_val);
                        right4 = nr_str_format("(&(NrStr){.data=(char*)\"%s\",.len=%lld})", esc_c->data, nr_str_len(cmp_c->str_val));
                    }
                }
                AstNode* left_node = p6->left;
                if ((left_node->tag == TAG_CONSTANT)) {
                    AstConstant* left_c = left_node->data;
                    if (((left_c->kind == CONST_STR) && (left_c->str_val != NULL))) {
                        NrStr* esc_lc = native_codegen_expr__escape_str(left_c->str_val);
                        left4 = nr_str_format("(&(NrStr){.data=(char*)\"%s\",.len=%lld})", esc_lc->data, nr_str_len(left_c->str_val));
                    }
                }
                if ((p6->ops[0] == OP_EQ)) {
                    return nr_str_format("nr_str_eq(%s, %s)", left4->data, right4->data);
                }
                if ((p6->ops[0] == OP_NOT_EQ)) {
                    return nr_str_format("(!nr_str_eq(%s, %s))", left4->data, right4->data);
                }
            }
        }
        if (((p6->op_count == 1) && (p6->comparators.count == 1))) {
            NrStr* lt4 = native_infer_native_infer_type(s, p6->left);
            NrStr* lb2 = native_infer__strip_ptr(lt4);
            if (strmap_strmap_has((&s->structs), lb2)) {
                NrStr* cmethod = native_codegen_expr__cmpop_method(p6->ops[0]);
                if ((cmethod != NULL)) {
                    NrStr* cmname = nr_str_concat(nr_str_concat(lb2, (&(NrStr){.data=(char*)"_",.len=1})), cmethod);
                    if (strmap_strmap_has((&s->func_ret_types), cmname)) {
                        NrStr* left5 = native_codegen_expr_native_compile_expr(s, p6->left);
                        NrStr* right5 = native_codegen_expr_native_compile_expr(s, p6->comparators.items[0]);
                        return nr_str_format("%s(&(%s), %s)", cmname->data, left5->data, right5->data);
                    }
                }
            }
        }
        if (((p6->op_count == 1) && ((p6->ops[0] == OP_IN) || (p6->ops[0] == OP_NOT_IN)))) {
            AstNode* cmp_r = p6->comparators.items[0];
            if (((cmp_r != NULL) && (cmp_r->tag == TAG_NAME))) {
                AstName* cmp_rn = cmp_r->data;
                NrStr* dv_check = strmap_strmap_get((&s->local_vars), nr_str_concat((&(NrStr){.data=(char*)"__dict_V_",.len=9}), cmp_rn->id));
                if ((dv_check != NULL)) {
                    NrStr* in_obj = native_codegen_expr_native_compile_expr(s, cmp_r);
                    NrStr* in_key = native_codegen_expr_native_compile_expr(s, p6->left);
                    NrStr* in_expr = nr_str_format("nr_dict_has(%s, %s)", in_obj->data, in_key->data);
                    if ((p6->ops[0] == OP_NOT_IN)) {
                        in_expr = nr_str_format("(!%s)", in_expr->data);
                    }
                    return in_expr;
                }
                NrStr* l_check = strmap_strmap_get((&s->list_vars), cmp_rn->id);
                if ((l_check != NULL)) {
                    NrStr* in_obj2 = native_codegen_expr_native_compile_expr(s, cmp_r);
                    NrStr* in_val = native_codegen_expr_native_compile_expr(s, p6->left);
                    NrStr* in_boxed = nr_str_format("nr_val_int((int64_t)(%s))", in_val->data);
                    NrStr* in_expr2 = nr_str_format("nr_list_contains(%s, %s)", in_obj2->data, in_boxed->data);
                    if ((p6->ops[0] == OP_NOT_IN)) {
                        in_expr2 = nr_str_format("(!%s)", in_expr2->data);
                    }
                    return in_expr2;
                }
            }
        }
        NrStr* left6 = native_codegen_expr_native_compile_expr(s, p6->left);
        NrStr* result2 = nr_str_new("");
        NrStr* prev = left6;
        for (int64_t i = 0; i < p6->op_count; i++) {
            NrStr* right6 = native_codegen_expr_native_compile_expr(s, p6->comparators.items[i]);
            NrStr* cop = native_codegen_expr_native_compile_cmpop(p6->ops[i]);
            NrStr* part2 = nr_str_format("(%s %s %s)", prev->data, cop->data, right6->data);
            if ((i > 0)) {
                result2 = nr_str_concat(result2, nr_str_concat((&(NrStr){.data=(char*)" && ",.len=4}), part2));
            } else {
                result2 = part2;
            }
            prev = right6;
        }
        return result2;
    }
    if ((node->tag == TAG_IF_EXP)) {
        AstIfExp* p7 = node->data;
        NrStr* test = native_codegen_expr_native_compile_expr(s, p7->test);
        NrStr* body = native_codegen_expr_native_compile_expr(s, p7->body);
        NrStr* orelse = native_codegen_expr_native_compile_expr(s, p7->orelse);
        return nr_str_format("((%s) ? (%s) : (%s))", test->data, body->data, orelse->data);
    }
    if (((node->tag == TAG_TUPLE) || (node->tag == TAG_LIST) || (node->tag == TAG_SET))) {
        AstTuple* p8 = node->data;
        NrStr* result3 = nr_str_new("{");
        for (int64_t i = 0; i < p8->elts.count; i++) {
            if ((i > 0)) {
                result3 = nr_str_concat(result3, (&(NrStr){.data=(char*)", ",.len=2}));
            }
            result3 = nr_str_concat(result3, native_codegen_expr_native_compile_expr(s, p8->elts.items[i]));
        }
        result3 = nr_str_concat(result3, (&(NrStr){.data=(char*)"}",.len=1}));
        return result3;
    }
    if ((node->tag == TAG_SUBSCRIPT)) {
        AstSubscript* p9 = node->data;
        if (((p9->value != NULL) && (p9->value->tag == TAG_NAME))) {
            AstName* sub_n = p9->value->data;
            NrStr* sub_et = strmap_strmap_get((&s->list_vars), sub_n->id);
            if ((sub_et != NULL)) {
                NrStr* sub_ln = strmap_strmap_get((&s->typed_lists), sub_et);
                if ((sub_ln != NULL)) {
                    NrStr* lst = native_codegen_expr_native_compile_expr(s, p9->value);
                    NrStr* idx = native_codegen_expr_native_compile_expr(s, p9->slice);
                    if ((s->safe_mode != 0)) {
                        native_codegen_expr__emit(s, nr_str_format("nr_safe_bounds_check(%s, %s->len, __FILE__, __LINE__);", idx->data, lst->data));
                    }
                    return nr_str_format("%s_get(%s, %s)", sub_ln->data, lst->data, idx->data);
                }
            }
        }
        if (((p9->value != NULL) && (p9->value->tag == TAG_NAME))) {
            AstName* d_n = p9->value->data;
            NrStr* d_vt = strmap_strmap_get((&s->local_vars), nr_str_concat((&(NrStr){.data=(char*)"__dict_V_",.len=9}), d_n->id));
            if ((d_vt != NULL)) {
                NrStr* d_obj = native_codegen_expr_native_compile_expr(s, p9->value);
                NrStr* d_key = native_codegen_expr_native_compile_expr(s, p9->slice);
                NrStr* d_raw = nr_str_format("nr_dict_get(%s, %s)", d_obj->data, d_key->data);
                if (nr_str_eq(d_vt, (&(NrStr){.data=(char*)"double",.len=6}))) {
                    return nr_str_format("nr_as_float(%s)", d_raw->data);
                }
                return nr_str_format("nr_as_int(%s)", d_raw->data);
            }
        }
        NrStr* val = native_codegen_expr_native_compile_expr(s, p9->value);
        NrStr* sl = native_codegen_expr_native_compile_expr(s, p9->slice);
        if (((s->safe_mode != 0) && (p9->value != NULL) && (p9->value->tag == TAG_NAME))) {
            AstName* arr_n = p9->value->data;
            ArrayInfo* arr_ai = strmap_strmap_get((&s->array_vars), arr_n->id);
            if ((arr_ai != NULL)) {
                native_codegen_expr__emit(s, nr_str_format("nr_safe_bounds_check(%s, %s, __FILE__, __LINE__);", sl->data, arr_ai->size->data));
            }
        }
        return nr_str_format("%s[%s]", val->data, sl->data);
    }
    if ((node->tag == TAG_ATTRIBUTE)) {
        AstAttribute* p10 = node->data;
        NrStr* attr_name = p10->attr;
        if (((p10->value != NULL) && (p10->value->tag == TAG_NAME))) {
            AstName* obj_name = p10->value->data;
            if (strmap_strset_has((&s->extern_funcs), obj_name->id)) {
                return nr_str_format("%s_%s", obj_name->id->data, attr_name->data);
            }
        }
        NrStr* val2 = native_codegen_expr_native_compile_expr(s, p10->value);
        NrStr* obj_type = native_infer_native_infer_type(s, p10->value);
        if (native_infer__ends_with_star(obj_type)) {
            if (((s->safe_mode != 0) && (p10->value != NULL) && (p10->value->tag == TAG_NAME))) {
                native_codegen_expr__emit(s, nr_str_format("nr_safe_null_check(%s, __FILE__, __LINE__);", val2->data));
            }
            return nr_str_format("%s->%s", val2->data, attr_name->data);
        }
        return nr_str_format("%s.%s", val2->data, attr_name->data);
    }
    if ((node->tag == TAG_JOINED_STR)) {
        AstJoinedStr* js = node->data;
        NrStr* fmt = nr_str_new("");
        NrStr* args = nr_str_new("");
        for (int64_t i = 0; i < js->values.count; i++) {
            AstNode* part = js->values.items[i];
            if ((part->tag == TAG_CONSTANT)) {
                AstConstant* pc = part->data;
                if (((pc->kind == CONST_STR) && (pc->str_val != NULL))) {
                    int64_t slen = nr_str_len(pc->str_val);
                    for (int64_t ci = 0; ci < slen; ci++) {
                        uint8_t ch = (uint8_t)(((uint8_t)(pc->str_val->data[ci])));
                        if ((ch == 92)) {
                            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"\\\\",.len=2}));
                        } else 
                        if ((ch == 34)) {
                            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"\\\"",.len=2}));
                        } else 
                        if ((ch == 10)) {
                            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"\\n",.len=2}));
                        } else 
                        if ((ch == 9)) {
                            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"\\t",.len=2}));
                        } else 
                        if ((ch == 37)) {
                            fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%%",.len=2}));
                        } else {
                            uint8_t* buf2 = malloc(2);
                            buf2[0] = ch;
                            buf2[1] = 0;
                            fmt = nr_str_concat(fmt, nr_str_new(buf2));
                            free(buf2);
                        }
                    }
                }
            } else 
            if ((part->tag == TAG_FORMATTED_VAL)) {
                AstFormattedValue* fv = part->data;
                NrStr* expr = native_codegen_expr_native_compile_expr(s, fv->value);
                NrStr* t = native_infer_native_infer_type(s, fv->value);
                NrStr* spec = nr_str_new("");
                if (((fv->format_spec != NULL) && (fv->format_spec->tag == TAG_JOINED_STR))) {
                    AstJoinedStr* sp_js = fv->format_spec->data;
                    for (int64_t si = 0; si < sp_js->values.count; si++) {
                        AstNode* sp_part = sp_js->values.items[si];
                        if ((sp_part->tag == TAG_CONSTANT)) {
                            AstConstant* sp_c = sp_part->data;
                            if (((sp_c->kind == CONST_STR) && (sp_c->str_val != NULL))) {
                                spec = nr_str_concat(spec, sp_c->str_val);
                            }
                        }
                    }
                }
                if ((nr_str_len(spec) > 0)) {
                    uint8_t spec_last = (uint8_t)(((uint8_t)(spec->data[(nr_str_len(spec) - 1)])));
                    if ((((spec_last == 100) || (spec_last == 105)) && (nr_str_eq(t, (&(NrStr){.data=(char*)"int64_t",.len=7})) || nr_str_eq(t, (&(NrStr){.data=(char*)"int",.len=3})) || nr_str_eq(t, (&(NrStr){.data=(char*)"uint8_t",.len=7}))))) {
                        NrStr* spec_prefix = nr_str_slice(spec, 0, (nr_str_len(spec) - 1));
                        fmt = nr_str_concat(fmt, nr_str_concat(nr_str_concat(nr_str_new("%"), spec_prefix), nr_str_new("lld")));
                        args = nr_str_concat(args, nr_str_format(", (long long)(%s)", expr->data));
                    } else 
                    if ((((spec_last == 120) || (spec_last == 88)) && (nr_str_eq(t, (&(NrStr){.data=(char*)"int64_t",.len=7})) || nr_str_eq(t, (&(NrStr){.data=(char*)"int",.len=3})) || nr_str_eq(t, (&(NrStr){.data=(char*)"uint8_t",.len=7}))))) {
                        NrStr* spec_prefix2 = nr_str_slice(spec, 0, (nr_str_len(spec) - 1));
                        uint8_t* last_ch_buf = malloc(2);
                        last_ch_buf[0] = spec_last;
                        last_ch_buf[1] = 0;
                        NrStr* last_ch_str = nr_str_new(last_ch_buf);
                        free(last_ch_buf);
                        fmt = nr_str_concat(fmt, nr_str_concat(nr_str_concat(nr_str_concat(nr_str_new("%"), spec_prefix2), nr_str_new("ll")), last_ch_str));
                        args = nr_str_concat(args, nr_str_format(", (long long)(%s)", expr->data));
                    } else 
                    if (((spec_last == 102) && nr_str_eq(t, (&(NrStr){.data=(char*)"double",.len=6})))) {
                        fmt = nr_str_concat(fmt, nr_str_concat(nr_str_new("%"), spec));
                        args = nr_str_concat(args, nr_str_format(", %s", expr->data));
                    } else {
                        fmt = nr_str_concat(fmt, nr_str_concat(nr_str_new("%"), spec));
                        args = nr_str_concat(args, nr_str_format(", %s", expr->data));
                    }
                } else 
                if (nr_str_eq(t, (&(NrStr){.data=(char*)"double",.len=6}))) {
                    fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%g",.len=2}));
                    args = nr_str_concat(args, nr_str_format(", %s", expr->data));
                } else 
                if (nr_str_eq(t, (&(NrStr){.data=(char*)"int64_t",.len=7}))) {
                    fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%lld",.len=4}));
                    args = nr_str_concat(args, nr_str_format(", (long long)(%s)", expr->data));
                } else 
                if (nr_str_eq(t, (&(NrStr){.data=(char*)"uint8_t",.len=7}))) {
                    fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%u",.len=2}));
                    args = nr_str_concat(args, nr_str_format(", (unsigned)(%s)", expr->data));
                } else 
                if (nr_str_eq(t, (&(NrStr){.data=(char*)"int",.len=3}))) {
                    fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%d",.len=2}));
                    args = nr_str_concat(args, nr_str_format(", (int)(%s)", expr->data));
                } else 
                if (nr_str_eq(t, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
                    fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%.*s",.len=4}));
                    args = nr_str_concat(args, nr_str_format(", (int)((%s)->len), ((%s)->data)", expr->data, expr->data));
                } else {
                    fmt = nr_str_concat(fmt, (&(NrStr){.data=(char*)"%lld",.len=4}));
                    args = nr_str_concat(args, nr_str_format(", (long long)(%s)", expr->data));
                }
            }
        }
        s->fstr_counter = (int32_t)((s->fstr_counter + 1));
        NrStr* buf_name = nr_str_format("_fstr_%d", s->fstr_counter);
        NrStr* svar_name = nr_str_format("_fstr_s_%d", s->fstr_counter);
        native_codegen_expr__emit(s, nr_str_format("char %s[512]; snprintf(%s, 512, \"%s\"%s);", buf_name->data, buf_name->data, fmt->data, args->data));
        native_codegen_expr__emit(s, nr_str_format("NrStr %s = {.data=%s,.len=strlen(%s)}; ", svar_name->data, buf_name->data, buf_name->data));
        return nr_str_format("(&%s)", svar_name->data);
    }
    if ((node->tag == TAG_CALL)) {
        return native_codegen_call_native_compile_call(s, node);
    }
    return nr_str_new("0 /* unknown expr */");
}
