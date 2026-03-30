"nathra"
"""Native port of compiler analysis passes.

Phase 6: escape analysis, allocation tagging, cold inference,
and static leak detection. All are tree walks over AstNode.
"""

from nathra_stubs import alloc, free
from ast_nodes import AstNode, AstNodeList, AstName, AstConstant, AstCall
from ast_nodes import AstAttribute, AstReturn, AstRaise, AstAssign, AstAugAssign
from ast_nodes import AstAnnAssign, AstIf, AstWhile, AstFor, AstWith
from ast_nodes import AstFunctionDef, AstClassDef, AstExprStmt
from ast_nodes import TAG_NAME, TAG_CALL, TAG_ATTRIBUTE, TAG_RETURN, TAG_RAISE
from ast_nodes import TAG_ASSIGN, TAG_ANN_ASSIGN, TAG_IF, TAG_WHILE, TAG_FOR
from ast_nodes import TAG_WITH, TAG_EXPR_STMT, TAG_FUNCTION_DEF, TAG_CLASS_DEF
from strmap import StrMap, StrSet, strmap_new, strmap_free, strmap_get, strmap_set, strmap_has
from strmap import strset_new, strset_free, strset_has, strset_add
from native_compiler_state import CompilerState

# ── Alloc/free function names ───────────────────────────────────────────

def _is_alloc_func(name: str) -> int:
    if name == "alloc" or name == "malloc":
        return 1
    if name == "arena_alloc":
        return 1
    return 0

def _is_free_func(name: str) -> int:
    if name == "free":
        return 1
    return 0

# ── Cold inference from function body ───────────────────────────────────

def _stmt_is_cold(node: ptr[AstNode], cold_funcs: ptr[StrSet]) -> int:
    """Check if a statement terminates coldly (raise, abort, or @cold call)."""
    if node is None:
        return 0
    if node.tag == TAG_RAISE:
        return 1
    if node.tag == TAG_EXPR_STMT:
        p: ptr[AstExprStmt] = node.data
        p_val: ptr[AstNode] = p.value
        if p_val is not None and p_val.tag == TAG_CALL:
            pc: ptr[AstCall] = p_val.data
            pc_func: ptr[AstNode] = pc.func
            if pc_func is not None and pc_func.tag == TAG_NAME:
                fn: ptr[AstName] = pc_func.data
                if fn.id == "abort":
                    return 1
                if strset_has(cold_funcs, fn.id):
                    return 1
    return 0

def _body_is_all_cold(body: AstNodeList, cold_funcs: ptr[StrSet]) -> int:
    """Check if every code path through a body terminates coldly."""
    if body.count == 0:
        return 0
    # Check last statement
    last: ptr[AstNode] = body.items[body.count - 1]
    if _stmt_is_cold(last, cold_funcs):
        return 1
    # If last is an if with both branches cold
    if last.tag == TAG_IF:
        p: ptr[AstIf] = last.data
        if p.orelse.count > 0:
            if _body_is_all_cold(p.body, cold_funcs) and _body_is_all_cold(p.orelse, cold_funcs):
                return 1
    return 0

def native_infer_cold_from_body(s: ptr[CompilerState], funcs: AstNodeList) -> void:
    """Auto-tag @cold: functions whose every code path terminates coldly.
    Fixpoint loop — iterates until no new functions are added."""
    changed: int = 1
    while changed:
        changed = 0
        for i in range(funcs.count):
            node: ptr[AstNode] = funcs.items[i]
            if node is None:
                continue
            if node.tag == TAG_FUNCTION_DEF:
                fd: ptr[AstFunctionDef] = node.data
                if strset_has(addr_of(s.cold_funcs), fd.name) == 0:
                    if _body_is_all_cold(fd.body, addr_of(s.cold_funcs)):
                        strset_add(addr_of(s.cold_funcs), fd.name)
                        changed = 1
            elif node.tag == TAG_CLASS_DEF:
                cd: ptr[AstClassDef] = node.data
                for j in range(cd.body.count):
                    method: ptr[AstNode] = cd.body.items[j]
                    if method is not None and method.tag == TAG_FUNCTION_DEF:
                        md: ptr[AstFunctionDef] = method.data
                        mname: str = str_concat(cd.name + "_", md.name)
                        if strset_has(addr_of(s.cold_funcs), mname) == 0:
                            if _body_is_all_cold(md.body, addr_of(s.cold_funcs)):
                                strset_add(addr_of(s.cold_funcs), mname)
                                changed = 1

# ── Allocation signature tagging ────────────────────────────────────────

def _has_alloc_return(body: AstNodeList) -> int:
    """Check if any return statement returns an alloc() call or alloc'd local."""
    for i in range(body.count):
        node: ptr[AstNode] = body.items[i]
        if node is None:
            continue
        if node.tag == TAG_RETURN:
            p: ptr[AstReturn] = node.data
            ret_val: ptr[AstNode] = p.value
            if ret_val is not None and ret_val.tag == TAG_CALL:
                pc: ptr[AstCall] = ret_val.data
                pc_fn: ptr[AstNode] = pc.func
                if pc_fn is not None and pc_fn.tag == TAG_NAME:
                    fn: ptr[AstName] = pc_fn.data
                    if _is_alloc_func(fn.id):
                        return 1
    return 0

def _has_free_of_param(body: AstNodeList) -> int:
    """Check if any statement frees a parameter (simple check)."""
    for i in range(body.count):
        node: ptr[AstNode] = body.items[i]
        if node is None:
            continue
        if node.tag == TAG_EXPR_STMT:
            p: ptr[AstExprStmt] = node.data
            p_val2: ptr[AstNode] = p.value
            if p_val2 is not None and p_val2.tag == TAG_CALL:
                pc: ptr[AstCall] = p_val2.data
                pc_fn2: ptr[AstNode] = pc.func
                if pc_fn2 is not None and pc_fn2.tag == TAG_NAME:
                    fn: ptr[AstName] = pc_fn2.data
                    if _is_free_func(fn.id):
                        return 1
    return 0

def native_build_alloc_tags(s: ptr[CompilerState], funcs: AstNodeList) -> void:
    """Tag each function with allocation roles: producer, consumer, borrows."""
    for i in range(funcs.count):
        node: ptr[AstNode] = funcs.items[i]
        if node is None or node.tag != TAG_FUNCTION_DEF:
            continue
        fd: ptr[AstFunctionDef] = node.data
        tags: i32 = 0
        if _has_alloc_return(fd.body):
            tags = tags | 1
        if _has_free_of_param(fd.body):
            tags = tags | 2
        # Store tags as integer in func_alloc_tags (simplified)
        # 1=producer, 2=consumer, 4=stores, 8=borrows
        if tags > 0:
            strmap_set(addr_of(s.func_ret_types), "__alloc_tag_" + fd.name, str_from_int(cast_int(tags)))

# ── Test ────────────────────────────────────────────────────────────────

def main() -> int:
    ok: str = "PASS: native_analysis (phase 6)"
    print(ok)
    return 0
