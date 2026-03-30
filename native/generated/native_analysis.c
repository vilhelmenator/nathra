/* nth_stamp: 1774911850.086977 */
#include "nathra_rt.h"
#include "native_analysis.h"

int64_t native_analysis__is_alloc_func(const NrStr* name);
int64_t native_analysis__is_free_func(const NrStr* name);
int64_t native_analysis__stmt_is_cold(const AstNode* restrict node, const StrSet* restrict cold_funcs);
int64_t native_analysis__body_is_all_cold(AstNodeList body, StrSet* cold_funcs);
void native_analysis_native_infer_cold_from_body(CompilerState* s, AstNodeList funcs);
int64_t native_analysis__has_alloc_return(AstNodeList body);
int64_t native_analysis__has_free_of_param(AstNodeList body);
void native_analysis_native_build_alloc_tags(CompilerState* s, AstNodeList funcs);
int main(void);

int64_t native_analysis__is_alloc_func(const NrStr* name) {
    if ((nr_str_eq(name, (&(NrStr){.data=(char*)"alloc",.len=5})) || nr_str_eq(name, (&(NrStr){.data=(char*)"malloc",.len=6})))) {
        return 1;
    }
    if (nr_str_eq(name, (&(NrStr){.data=(char*)"arena_alloc",.len=11}))) {
        return 1;
    }
    return 0;
}

int64_t native_analysis__is_free_func(const NrStr* name) {
    if (nr_str_eq(name, (&(NrStr){.data=(char*)"free",.len=4}))) {
        return 1;
    }
    return 0;
}

int64_t native_analysis__stmt_is_cold(const AstNode* restrict node, const StrSet* restrict cold_funcs) {
    "Check if a statement terminates coldly (raise, abort, or @cold call).";
    if ((node == NULL)) {
        return 0;
    }
    if ((node->tag == TAG_RAISE)) {
        return 1;
    }
    if ((node->tag == TAG_EXPR_STMT)) {
        AstExprStmt* p = node->data;
        AstNode* p_val = p->value;
        if (((p_val != NULL) && (p_val->tag == TAG_CALL))) {
            AstCall* pc = p_val->data;
            AstNode* pc_func = pc->func;
            if (((pc_func != NULL) && (pc_func->tag == TAG_NAME))) {
                AstName* fn = pc_func->data;
                if (nr_str_eq(fn->id, (&(NrStr){.data=(char*)"abort",.len=5}))) {
                    return 1;
                }
                if (strmap_strset_has(cold_funcs, fn->id)) {
                    return 1;
                }
            }
        }
    }
    return 0;
}

int64_t native_analysis__body_is_all_cold(AstNodeList body, StrSet* cold_funcs) {
    "Check if every code path through a body terminates coldly.";
    if ((body.count == 0)) {
        return 0;
    }
    AstNode* last = body.items[(body.count - 1)];
    if (native_analysis__stmt_is_cold(last, cold_funcs)) {
        return 1;
    }
    if ((last->tag == TAG_IF)) {
        AstIf* p = last->data;
        if ((p->orelse.count > 0)) {
            if ((native_analysis__body_is_all_cold(p->body, cold_funcs) && native_analysis__body_is_all_cold(p->orelse, cold_funcs))) {
                return 1;
            }
        }
    }
    return 0;
}

void native_analysis_native_infer_cold_from_body(CompilerState* s, AstNodeList funcs) {
    "Auto-tag @cold: functions whose every code path terminates coldly.\n    Fixpoint loop — iterates until no new functions are added.";
    int64_t changed = 1;
    while (changed) {
        changed = 0;
        for (int64_t i = 0; i < funcs.count; i++) {
            AstNode* node = funcs.items[i];
            if ((node == NULL)) {
                continue;
            }
            if ((node->tag == TAG_FUNCTION_DEF)) {
                AstFunctionDef* fd = node->data;
                if ((strmap_strset_has((&s->cold_funcs), fd->name) == 0)) {
                    if (native_analysis__body_is_all_cold(fd->body, (&s->cold_funcs))) {
                        strmap_strset_add((&s->cold_funcs), fd->name);
                        changed = 1;
                    }
                }
            } else 
            if ((node->tag == TAG_CLASS_DEF)) {
                AstClassDef* cd = node->data;
                for (int64_t j = 0; j < cd->body.count; j++) {
                    AstNode* method = cd->body.items[j];
                    if (((method != NULL) && (method->tag == TAG_FUNCTION_DEF))) {
                        AstFunctionDef* md = method->data;
                        NrStr* mname = nr_str_concat(nr_str_concat(cd->name, (&(NrStr){.data=(char*)"_",.len=1})), md->name);
                        if ((strmap_strset_has((&s->cold_funcs), mname) == 0)) {
                            if (native_analysis__body_is_all_cold(md->body, (&s->cold_funcs))) {
                                strmap_strset_add((&s->cold_funcs), mname);
                                changed = 1;
                            }
                        }
                    }
                }
            }
        }
    }
}

int64_t native_analysis__has_alloc_return(AstNodeList body) {
    "Check if any return statement returns an alloc() call or alloc'd local.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_RETURN)) {
            AstReturn* p = node->data;
            AstNode* ret_val = p->value;
            if (((ret_val != NULL) && (ret_val->tag == TAG_CALL))) {
                AstCall* pc = ret_val->data;
                AstNode* pc_fn = pc->func;
                if (((pc_fn != NULL) && (pc_fn->tag == TAG_NAME))) {
                    AstName* fn = pc_fn->data;
                    if (native_analysis__is_alloc_func(fn->id)) {
                        return 1;
                    }
                }
            }
        }
    }
    return 0;
}

int64_t native_analysis__has_free_of_param(AstNodeList body) {
    "Check if any statement frees a parameter (simple check).";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_EXPR_STMT)) {
            AstExprStmt* p = node->data;
            AstNode* p_val2 = p->value;
            if (((p_val2 != NULL) && (p_val2->tag == TAG_CALL))) {
                AstCall* pc = p_val2->data;
                AstNode* pc_fn2 = pc->func;
                if (((pc_fn2 != NULL) && (pc_fn2->tag == TAG_NAME))) {
                    AstName* fn = pc_fn2->data;
                    if (native_analysis__is_free_func(fn->id)) {
                        return 1;
                    }
                }
            }
        }
    }
    return 0;
}

void native_analysis_native_build_alloc_tags(CompilerState* s, AstNodeList funcs) {
    "Tag each function with allocation roles: producer, consumer, borrows.";
    for (int64_t i = 0; i < funcs.count; i++) {
        AstNode* node = funcs.items[i];
        if (((node == NULL) || (node->tag != TAG_FUNCTION_DEF))) {
            continue;
        }
        AstFunctionDef* fd = node->data;
        int32_t tags = (int32_t)(0);
        if (native_analysis__has_alloc_return(fd->body)) {
            tags = (int32_t)((tags | 1));
        }
        if (native_analysis__has_free_of_param(fd->body)) {
            tags = (int32_t)((tags | 2));
        }
        if ((tags > 0)) {
            strmap_strmap_set((&s->func_ret_types), nr_str_concat((&(NrStr){.data=(char*)"__alloc_tag_",.len=12}), fd->name), nr_str_from_int(((int64_t)(tags))));
        }
    }
}
