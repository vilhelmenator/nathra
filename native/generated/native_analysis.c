/* nth_stamp: 1777595281.407572 */
#include "nathra_rt.h"
#include "native_analysis.h"

int64_t native_analysis__is_alloc_func(const NrStr* name);
int64_t native_analysis__is_free_func(const NrStr* name);
int64_t native_analysis__stmt_is_cold(const AstNode* restrict node, const StrSet* restrict cold_funcs);
int64_t native_analysis__body_is_all_cold(AstNodeList body, StrSet* cold_funcs);
void native_analysis_native_infer_cold_from_body(CompilerState* s, AstNodeList funcs);
int64_t native_analysis__expr_calls_name(const AstNode* restrict e, NrStr* restrict name);
int64_t native_analysis__func_calls_self(AstNodeList body, NrStr* name);
int64_t native_analysis__has_banned_stmt(AstNodeList body);
int64_t native_analysis__is_address_taken(NrStr* name, AstNodeList funcs);
int64_t native_analysis__scan_address_taken(AstNodeList body, NrStr* name);
int64_t native_analysis__call_has_name_arg(const AstNode* restrict call_node, const NrStr* restrict name);
int64_t native_analysis__has_caller(NrStr* name, AstNodeList funcs);
void native_analysis_native_infer_inline_from_body(CompilerState* s, AstNodeList funcs);
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

int64_t native_analysis__expr_calls_name(const AstNode* restrict e, NrStr* restrict name) {
    "Recursively check if an expression tree contains Call(Name(id=name)).";
    if ((e == NULL)) {
        return 0;
    }
    if ((e->tag == TAG_CALL)) {
        AstCall* cn = e->data;
        if (((cn->func != NULL) && (cn->func->tag == TAG_NAME))) {
            AstName* fnn = cn->func->data;
            if (nr_str_eq(fnn->id, name)) {
                return 1;
            }
        }
        if (((cn->func != NULL) && (native_analysis__expr_calls_name(cn->func, name) != 0))) {
            return 1;
        }
        for (int64_t j = 0; j < cn->args.count; j++) {
            if ((native_analysis__expr_calls_name(cn->args.items[j], name) != 0)) {
                return 1;
            }
        }
        return 0;
    }
    if ((e->tag == TAG_BIN_OP)) {
        AstBinOp* bo = e->data;
        if ((native_analysis__expr_calls_name(bo->left, name) != 0)) {
            return 1;
        }
        if ((native_analysis__expr_calls_name(bo->right, name) != 0)) {
            return 1;
        }
        return 0;
    }
    if ((e->tag == TAG_UNARY_OP)) {
        AstUnaryOp* uo = e->data;
        return native_analysis__expr_calls_name(uo->operand, name);
    }
    if ((e->tag == TAG_BOOL_OP)) {
        AstBoolOp* bp = e->data;
        for (int64_t j = 0; j < bp->values.count; j++) {
            if ((native_analysis__expr_calls_name(bp->values.items[j], name) != 0)) {
                return 1;
            }
        }
        return 0;
    }
    if ((e->tag == TAG_COMPARE)) {
        AstCompare* cp = e->data;
        if ((native_analysis__expr_calls_name(cp->left, name) != 0)) {
            return 1;
        }
        for (int64_t j = 0; j < cp->comparators.count; j++) {
            if ((native_analysis__expr_calls_name(cp->comparators.items[j], name) != 0)) {
                return 1;
            }
        }
        return 0;
    }
    if ((e->tag == TAG_IF_EXP)) {
        AstIfExp* ie = e->data;
        if ((native_analysis__expr_calls_name(ie->test, name) != 0)) {
            return 1;
        }
        if ((native_analysis__expr_calls_name(ie->body, name) != 0)) {
            return 1;
        }
        if ((native_analysis__expr_calls_name(ie->orelse, name) != 0)) {
            return 1;
        }
        return 0;
    }
    if ((e->tag == TAG_SUBSCRIPT)) {
        AstSubscript* sb = e->data;
        if ((native_analysis__expr_calls_name(sb->value, name) != 0)) {
            return 1;
        }
        if ((native_analysis__expr_calls_name(sb->slice, name) != 0)) {
            return 1;
        }
        return 0;
    }
    if ((e->tag == TAG_ATTRIBUTE)) {
        AstAttribute* at = e->data;
        return native_analysis__expr_calls_name(at->value, name);
    }
    return 0;
}

int64_t native_analysis__func_calls_self(AstNodeList body, NrStr* name) {
    "True if the body contains a call to a function named `name`.";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_EXPR_STMT)) {
            AstExprStmt* es = node->data;
            if ((native_analysis__expr_calls_name(es->value, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_RETURN)) {
            AstReturn* rn = node->data;
            if ((native_analysis__expr_calls_name(rn->value, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_ASSIGN)) {
            AstAssign* an = node->data;
            if ((native_analysis__expr_calls_name(an->value, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_ANN_ASSIGN)) {
            AstAnnAssign* ann = node->data;
            if ((native_analysis__expr_calls_name(ann->value, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_IF)) {
            AstIf* ifd = node->data;
            if ((native_analysis__expr_calls_name(ifd->test, name) != 0)) {
                return 1;
            }
            if ((native_analysis__func_calls_self(ifd->body, name) != 0)) {
                return 1;
            }
            if ((native_analysis__func_calls_self(ifd->orelse, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_FOR)) {
            AstFor* fd = node->data;
            if ((native_analysis__func_calls_self(fd->body, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_WHILE)) {
            AstWhile* wd = node->data;
            if ((native_analysis__expr_calls_name(wd->test, name) != 0)) {
                return 1;
            }
            if ((native_analysis__func_calls_self(wd->body, name) != 0)) {
                return 1;
            }
        }
    }
    return 0;
}

int64_t native_analysis__has_banned_stmt(AstNodeList body) {
    "True if body contains For / While / nested FunctionDef.\n\n    (Try is not part of the nathra AST.)";
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_FOR)) {
            return 1;
        }
        if ((node->tag == TAG_WHILE)) {
            return 1;
        }
        if ((node->tag == TAG_FUNCTION_DEF)) {
            return 1;
        }
        if ((node->tag == TAG_IF)) {
            AstIf* ifd = node->data;
            if ((native_analysis__has_banned_stmt(ifd->body) != 0)) {
                return 1;
            }
            if ((native_analysis__has_banned_stmt(ifd->orelse) != 0)) {
                return 1;
            }
        }
    }
    return 0;
}

int64_t native_analysis__call_has_name_arg(const AstNode* restrict call_node, const NrStr* restrict name) {
    "True if any of the call's args is a bare Name `name` (address-taken).\n    Walks one level only — passing `f` directly is what we care about.";
    AstCall* cn = call_node->data;
    for (int64_t j = 0; j < cn->args.count; j++) {
        AstNode* arg = cn->args.items[j];
        if (((arg != NULL) && (arg->tag == TAG_NAME))) {
            AstName* an = arg->data;
            if (nr_str_eq(an->id, name)) {
                return 1;
            }
        }
    }
    return 0;
}

int64_t native_analysis__scan_address_taken(AstNodeList body, NrStr* name) {
    for (int64_t i = 0; i < body.count; i++) {
        AstNode* node = body.items[i];
        if ((node == NULL)) {
            continue;
        }
        if ((node->tag == TAG_EXPR_STMT)) {
            AstExprStmt* es = node->data;
            if (((es->value != NULL) && (es->value->tag == TAG_CALL))) {
                if ((native_analysis__call_has_name_arg(es->value, name) != 0)) {
                    return 1;
                }
            }
        }
        if ((node->tag == TAG_ASSIGN)) {
            AstAssign* an = node->data;
            if (((an->value != NULL) && (an->value->tag == TAG_CALL))) {
                if ((native_analysis__call_has_name_arg(an->value, name) != 0)) {
                    return 1;
                }
            }
        }
        if ((node->tag == TAG_ANN_ASSIGN)) {
            AstAnnAssign* ann = node->data;
            if (((ann->value != NULL) && (ann->value->tag == TAG_CALL))) {
                if ((native_analysis__call_has_name_arg(ann->value, name) != 0)) {
                    return 1;
                }
            }
        }
        if ((node->tag == TAG_RETURN)) {
            AstReturn* rn = node->data;
            if (((rn->value != NULL) && (rn->value->tag == TAG_CALL))) {
                if ((native_analysis__call_has_name_arg(rn->value, name) != 0)) {
                    return 1;
                }
            }
        }
        if ((node->tag == TAG_IF)) {
            AstIf* ifd = node->data;
            if ((native_analysis__scan_address_taken(ifd->body, name) != 0)) {
                return 1;
            }
            if ((native_analysis__scan_address_taken(ifd->orelse, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_FOR)) {
            AstFor* fd = node->data;
            if ((native_analysis__scan_address_taken(fd->body, name) != 0)) {
                return 1;
            }
        }
        if ((node->tag == TAG_WHILE)) {
            AstWhile* wd = node->data;
            if ((native_analysis__scan_address_taken(wd->body, name) != 0)) {
                return 1;
            }
        }
    }
    return 0;
}

int64_t native_analysis__is_address_taken(NrStr* name, AstNodeList funcs) {
    "True if `name` appears as a bare Name argument anywhere (not Call.func).";
    for (int64_t i = 0; i < funcs.count; i++) {
        AstNode* node = funcs.items[i];
        if (((node == NULL) || (node->tag != TAG_FUNCTION_DEF))) {
            continue;
        }
        AstFunctionDef* fd = node->data;
        if ((native_analysis__scan_address_taken(fd->body, name) != 0)) {
            return 1;
        }
    }
    return 0;
}

int64_t native_analysis__has_caller(NrStr* name, AstNodeList funcs) {
    "True if any function's body calls `name`.";
    for (int64_t i = 0; i < funcs.count; i++) {
        AstNode* node = funcs.items[i];
        if (((node == NULL) || (node->tag != TAG_FUNCTION_DEF))) {
            continue;
        }
        AstFunctionDef* fd = node->data;
        if ((native_analysis__func_calls_self(fd->body, name) != 0)) {
            return 1;
        }
    }
    return 0;
}

void native_analysis_native_infer_inline_from_body(CompilerState* s, AstNodeList funcs) {
    "Auto-mark small leaf functions as inline. Same heuristics as Python:\n    not noinline/extern/cold, not recursive, not address-taken, body <= 3\n    statements, no banned constructs, has at least one caller.";
    for (int64_t i = 0; i < funcs.count; i++) {
        AstNode* node = funcs.items[i];
        if (((node == NULL) || (node->tag != TAG_FUNCTION_DEF))) {
            continue;
        }
        AstFunctionDef* fd = node->data;
        int64_t skip = 0;
        for (int64_t d = 0; d < fd->decorators.count; d++) {
            AstNode* dnode = fd->decorators.items[d];
            if (((dnode != NULL) && (dnode->tag == TAG_NAME))) {
                AstName* dn = dnode->data;
                if ((nr_str_eq(dn->id, (&(NrStr){.data=(char*)"noinline",.len=8})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"extern",.len=6})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"export",.len=6})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"test",.len=4})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"compile_time",.len=12})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"trait",.len=5})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"generic",.len=7})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"parallel",.len=8})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"stream",.len=6})) || nr_str_eq(dn->id, (&(NrStr){.data=(char*)"inline",.len=6})))) {
                    skip = 1;
                    break;
                }
            }
        }
        if ((skip != 0)) {
            continue;
        }
        if ((strmap_strset_has((&s->cold_funcs), fd->name) != 0)) {
            continue;
        }
        if ((fd->body.count > 3)) {
            continue;
        }
        if ((native_analysis__has_banned_stmt(fd->body) != 0)) {
            continue;
        }
        if ((native_analysis__func_calls_self(fd->body, fd->name) != 0)) {
            continue;
        }
        if ((native_analysis__is_address_taken(fd->name, funcs) != 0)) {
            continue;
        }
        if ((native_analysis__has_caller(fd->name, funcs) == 0)) {
            continue;
        }
        strmap_strset_add((&s->inline_funcs), fd->name);
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
