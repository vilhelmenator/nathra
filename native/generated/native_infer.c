/* nth_stamp: 1774911850.086977 */
#include "nathra_rt.h"
#include "native_infer.h"

NrStr* native_infer_native_infer_type(CompilerState* restrict s, AstNode* restrict node);
NrStr* native_infer_native_infer_call_type(CompilerState* restrict s, const AstNode* restrict node);
NrStr* native_infer__strip_ptr(const NrStr* t);
int64_t native_infer__ends_with_star(const NrStr* t);
NrStr* native_infer__binop_method_name(uint8_t op);
int main(void);

NrStr* native_infer__strip_ptr(const NrStr* t) {
    "Strip trailing * and whitespace: 'Vec3*' → 'Vec3', 'const int*' → 'const int'.";
    if ((t == NULL)) {
        return nr_str_new("");
    }
    int64_t len = nr_str_len(t);
    if ((len > 0)) {
        if ((((uint8_t)(t->data[(len - 1)])) == 42)) {
            int64_t end = (len - 1);
            while (((end > 0) && (((uint8_t)(t->data[(end - 1)])) == 32))) {
                end = (end - 1);
            }
            return nr_str_slice(t, 0, end);
        }
    }
    return t;
}

NrStr* native_infer_native_infer_call_type(CompilerState* restrict s, const AstNode* restrict node) {
    "Infer the return type of a function call.";
    AstCall* p = node->data;
    AstNode* func = p->func;
    if ((func->tag == TAG_NAME)) {
        AstName* fn = func->data;
        NrStr* fname = fn->id;
        NrStr* fpt = strmap_strmap_get((&s->funcptr_rettypes), fname);
        if ((fpt != NULL)) {
            return fpt;
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_int",.len=8}))) {
            return nr_str_new("int64_t");
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_float",.len=10}))) {
            return nr_str_new("double");
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_byte",.len=9}))) {
            return nr_str_new("uint8_t");
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"cast_bool",.len=9}))) {
            return nr_str_new("int");
        }
        if (strmap_strmap_has((&s->structs), fname)) {
            return fname;
        }
        if ((nr_str_eq(fname, (&(NrStr){.data=(char*)"is_ok",.len=5})) || nr_str_eq(fname, (&(NrStr){.data=(char*)"is_err",.len=6})))) {
            return nr_str_new("int");
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"err_msg",.len=7}))) {
            return nr_str_new("char*");
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"input",.len=5}))) {
            return nr_str_new("NrStr*");
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"exit",.len=4}))) {
            return nr_str_new("void");
        }
        if (nr_str_eq(fname, (&(NrStr){.data=(char*)"str",.len=3}))) {
            return nr_str_new("NrStr*");
        }
        ImportInfo* ii = strmap_strmap_get((&s->from_imports), fname);
        if ((ii != NULL)) {
            /* pass */
        }
        NrStr* ret2 = strmap_strmap_get((&s->func_ret_types), fname);
        if ((ret2 != NULL)) {
            return ret2;
        }
        return nr_str_new("int64_t");
    }
    if ((func->tag == TAG_ATTRIBUTE)) {
        AstAttribute* pa = func->data;
        NrStr* obj_type = native_infer_native_infer_type(s, pa->value);
        NrStr* base = native_infer__strip_ptr(obj_type);
        if (strmap_strmap_has((&s->structs), base)) {
            NrStr* method_name = nr_str_concat(nr_str_concat(base, (&(NrStr){.data=(char*)"_",.len=1})), pa->attr);
            NrStr* ret3 = strmap_strmap_get((&s->func_ret_types), method_name);
            if ((ret3 != NULL)) {
                return ret3;
            }
        }
        if (nr_str_eq(obj_type, (&(NrStr){.data=(char*)"NrStr*",.len=6}))) {
            if ((nr_str_eq(pa->attr, (&(NrStr){.data=(char*)"len",.len=3})) || nr_str_eq(pa->attr, (&(NrStr){.data=(char*)"find",.len=4})))) {
                return nr_str_new("int64_t");
            }
            if ((nr_str_eq(pa->attr, (&(NrStr){.data=(char*)"eq",.len=2})) || nr_str_eq(pa->attr, (&(NrStr){.data=(char*)"contains",.len=8})))) {
                return nr_str_new("int");
            }
            return nr_str_new("NrStr*");
        }
    }
    return nr_str_new("int64_t");
}

NrStr* native_infer__binop_method_name(uint8_t op) {
    "Map operator tag to __method__ name for operator overloading.";
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

int64_t native_infer__ends_with_star(const NrStr* t) {
    "Check if type string ends with '*'.";
    if ((t == NULL)) {
        return 0;
    }
    int64_t len = nr_str_len(t);
    if (((len > 0) && (((uint8_t)(t->data[(len - 1)])) == 42))) {
        return 1;
    }
    return 0;
}

NrStr* native_infer_native_infer_type(CompilerState* restrict s, AstNode* restrict node) {
    "Infer the C type of an AST expression node.";
    if ((node == NULL)) {
        return nr_str_new("int64_t");
    }
    if ((node->tag == TAG_CONSTANT)) {
        AstConstant* p = node->data;
        if ((p->kind == 3)) {
            return nr_str_new("int");
        }
        if ((p->kind == 0)) {
            return nr_str_new("int64_t");
        }
        if ((p->kind == 1)) {
            return nr_str_new("double");
        }
        if ((p->kind == 2)) {
            return nr_str_new("NrStr*");
        }
        return nr_str_new("int64_t");
    }
    if ((node->tag == TAG_NAME)) {
        AstName* p2 = node->data;
        NrStr* name = p2->id;
        if ((nr_str_eq(name, (&(NrStr){.data=(char*)"True",.len=4})) || nr_str_eq(name, (&(NrStr){.data=(char*)"False",.len=5})))) {
            return nr_str_new("int");
        }
        NrStr* t = strmap_strmap_get((&s->local_vars), name);
        if ((t != NULL)) {
            return t;
        }
        t = strmap_strmap_get((&s->func_args), name);
        if ((t != NULL)) {
            return t;
        }
        t = strmap_strmap_get((&s->constants), name);
        if ((t != NULL)) {
            return t;
        }
        t = strmap_strmap_get((&s->mutable_globals), name);
        if ((t != NULL)) {
            return t;
        }
        return nr_str_new("int64_t");
    }
    if ((node->tag == TAG_BIN_OP)) {
        AstBinOp* p3 = node->data;
        NrStr* lt = native_infer_native_infer_type(s, p3->left);
        NrStr* rt = native_infer_native_infer_type(s, p3->right);
        NrStr* lb = native_infer__strip_ptr(lt);
        if (strmap_strmap_has((&s->structs), lb)) {
            NrStr* op_method = native_infer__binop_method_name(p3->op);
            if ((op_method != NULL)) {
                NrStr* method_name = nr_str_concat(nr_str_concat(lb, (&(NrStr){.data=(char*)"_",.len=1})), op_method);
                NrStr* ret = strmap_strmap_get((&s->func_ret_types), method_name);
                if ((ret != NULL)) {
                    return ret;
                }
            }
        }
        if ((nr_str_eq(lt, (&(NrStr){.data=(char*)"double",.len=6})) || nr_str_eq(rt, (&(NrStr){.data=(char*)"double",.len=6})))) {
            return nr_str_new("double");
        }
        return nr_str_new("int64_t");
    }
    if ((node->tag == TAG_UNARY_OP)) {
        AstUnaryOp* p4 = node->data;
        if ((p4->op == 22)) {
            return nr_str_new("int");
        }
        return native_infer_native_infer_type(s, p4->operand);
    }
    if (((node->tag == TAG_BOOL_OP) || (node->tag == TAG_COMPARE))) {
        return nr_str_new("int");
    }
    if ((node->tag == TAG_CALL)) {
        return native_infer_native_infer_call_type(s, node);
    }
    if ((node->tag == TAG_ATTRIBUTE)) {
        AstAttribute* p5 = node->data;
        NrStr* obj_type = native_infer_native_infer_type(s, p5->value);
        NrStr* base = native_infer__strip_ptr(obj_type);
        FieldList* fl = strmap_strmap_get((&s->structs), base);
        if ((fl != NULL)) {
            NrStr* ft = native_compiler_state_field_list_find(fl, p5->attr);
            if ((ft != NULL)) {
                if (nr_str_eq(ft, (&(NrStr){.data=(char*)"__array__",.len=9}))) {
                    NrStr* key = nr_str_concat(nr_str_concat(base, (&(NrStr){.data=(char*)".",.len=1})), p5->attr);
                    NrStr* et = strmap_strmap_get((&s->struct_array_fields), key);
                    if ((et != NULL)) {
                        return et;
                    }
                    return nr_str_new("int64_t");
                }
                return ft;
            }
        }
        return nr_str_new("int64_t");
    }
    if ((node->tag == TAG_SUBSCRIPT)) {
        AstSubscript* p6 = node->data;
        AstNode* sub_val = p6->value;
        if (((sub_val != NULL) && (sub_val->tag == TAG_NAME))) {
            AstName* vn = sub_val->data;
            ArrayInfo* ai = strmap_strmap_get((&s->array_vars), vn->id);
            if ((ai != NULL)) {
                return ai->elem_type;
            }
            NrStr* et2 = strmap_strmap_get((&s->list_vars), vn->id);
            if ((et2 != NULL)) {
                return et2;
            }
        }
        if (((sub_val != NULL) && (sub_val->tag == TAG_ATTRIBUTE))) {
            AstAttribute* pa = sub_val->data;
            NrStr* ot = native_infer_native_infer_type(s, pa->value);
            NrStr* b = native_infer__strip_ptr(ot);
            NrStr* key2 = nr_str_concat(nr_str_concat(b, (&(NrStr){.data=(char*)".",.len=1})), pa->attr);
            NrStr* et3 = strmap_strmap_get((&s->struct_array_fields), key2);
            if ((et3 != NULL)) {
                return et3;
            }
            FieldList* fl2 = strmap_strmap_get((&s->structs), b);
            if ((fl2 != NULL)) {
                NrStr* ft2 = native_compiler_state_field_list_find(fl2, pa->attr);
                if ((ft2 != NULL)) {
                    if (native_infer__ends_with_star(ft2)) {
                        return native_infer__strip_ptr(ft2);
                    }
                }
            }
        }
        NrStr* val_type = native_infer_native_infer_type(s, p6->value);
        if (native_infer__ends_with_star(val_type)) {
            return native_infer__strip_ptr(val_type);
        }
        return nr_str_new("int64_t");
    }
    if ((node->tag == TAG_IF_EXP)) {
        AstIfExp* p7 = node->data;
        return native_infer_native_infer_type(s, p7->body);
    }
    if ((node->tag == TAG_JOINED_STR)) {
        return nr_str_new("NrStr*");
    }
    if ((node->tag == TAG_LIST_COMP)) {
        return nr_str_new("NrList*");
    }
    return nr_str_new("int64_t");
}
