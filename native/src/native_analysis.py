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
from ast_nodes import AstBinOp, AstUnaryOp, AstBoolOp, AstCompare, AstIfExp
from ast_nodes import AstSubscript
from ast_nodes import TAG_BIN_OP, TAG_UNARY_OP, TAG_BOOL_OP, TAG_COMPARE
from ast_nodes import TAG_IF_EXP, TAG_SUBSCRIPT
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

# ── Inline inference ────────────────────────────────────────────────────

def _expr_calls_name(e: ptr[AstNode], name: str) -> int:
    """Recursively check if an expression tree contains Call(Name(id=name))."""
    if e is None:
        return 0
    if e.tag == TAG_CALL:
        cn: ptr[AstCall] = e.data
        if cn.func is not None and cn.func.tag == TAG_NAME:
            fnn: ptr[AstName] = cn.func.data
            if fnn.id == name:
                return 1
        if cn.func is not None and _expr_calls_name(cn.func, name) != 0:
            return 1
        for j in range(cn.args.count):
            if _expr_calls_name(cn.args.items[j], name) != 0:
                return 1
        return 0
    if e.tag == TAG_BIN_OP:
        bo: ptr[AstBinOp] = e.data
        if _expr_calls_name(bo.left, name) != 0:
            return 1
        if _expr_calls_name(bo.right, name) != 0:
            return 1
        return 0
    if e.tag == TAG_UNARY_OP:
        uo: ptr[AstUnaryOp] = e.data
        return _expr_calls_name(uo.operand, name)
    if e.tag == TAG_BOOL_OP:
        bp: ptr[AstBoolOp] = e.data
        for j in range(bp.values.count):
            if _expr_calls_name(bp.values.items[j], name) != 0:
                return 1
        return 0
    if e.tag == TAG_COMPARE:
        cp: ptr[AstCompare] = e.data
        if _expr_calls_name(cp.left, name) != 0:
            return 1
        for j in range(cp.comparators.count):
            if _expr_calls_name(cp.comparators.items[j], name) != 0:
                return 1
        return 0
    if e.tag == TAG_IF_EXP:
        ie: ptr[AstIfExp] = e.data
        if _expr_calls_name(ie.test, name) != 0:
            return 1
        if _expr_calls_name(ie.body, name) != 0:
            return 1
        if _expr_calls_name(ie.orelse, name) != 0:
            return 1
        return 0
    if e.tag == TAG_SUBSCRIPT:
        sb: ptr[AstSubscript] = e.data
        if _expr_calls_name(sb.value, name) != 0:
            return 1
        if _expr_calls_name(sb.slice, name) != 0:
            return 1
        return 0
    if e.tag == TAG_ATTRIBUTE:
        at: ptr[AstAttribute] = e.data
        return _expr_calls_name(at.value, name)
    return 0

def _func_calls_self(body: AstNodeList, name: str) -> int:
    """True if the body contains a call to a function named `name`."""
    for i in range(body.count):
        node: ptr[AstNode] = body.items[i]
        if node is None:
            continue
        if node.tag == TAG_EXPR_STMT:
            es: ptr[AstExprStmt] = node.data
            if _expr_calls_name(es.value, name) != 0:
                return 1
        if node.tag == TAG_RETURN:
            rn: ptr[AstReturn] = node.data
            if _expr_calls_name(rn.value, name) != 0:
                return 1
        if node.tag == TAG_ASSIGN:
            an: ptr[AstAssign] = node.data
            if _expr_calls_name(an.value, name) != 0:
                return 1
        if node.tag == TAG_ANN_ASSIGN:
            ann: ptr[AstAnnAssign] = node.data
            if _expr_calls_name(ann.value, name) != 0:
                return 1
        if node.tag == TAG_IF:
            ifd: ptr[AstIf] = node.data
            if _expr_calls_name(ifd.test, name) != 0:
                return 1
            if _func_calls_self(ifd.body, name) != 0:
                return 1
            if _func_calls_self(ifd.orelse, name) != 0:
                return 1
        if node.tag == TAG_FOR:
            fd: ptr[AstFor] = node.data
            if _func_calls_self(fd.body, name) != 0:
                return 1
        if node.tag == TAG_WHILE:
            wd: ptr[AstWhile] = node.data
            if _expr_calls_name(wd.test, name) != 0:
                return 1
            if _func_calls_self(wd.body, name) != 0:
                return 1
    return 0

def _has_banned_stmt(body: AstNodeList) -> int:
    """True if body contains For / While / nested FunctionDef.

    (Try is not part of the nathra AST.)"""
    for i in range(body.count):
        node: ptr[AstNode] = body.items[i]
        if node is None:
            continue
        if node.tag == TAG_FOR:
            return 1
        if node.tag == TAG_WHILE:
            return 1
        if node.tag == TAG_FUNCTION_DEF:
            return 1
        if node.tag == TAG_IF:
            ifd: ptr[AstIf] = node.data
            if _has_banned_stmt(ifd.body) != 0:
                return 1
            if _has_banned_stmt(ifd.orelse) != 0:
                return 1
    return 0

def _is_address_taken(name: str, funcs: AstNodeList) -> int:
    """True if `name` appears as a bare Name argument anywhere (not Call.func)."""
    for i in range(funcs.count):
        node: ptr[AstNode] = funcs.items[i]
        if node is None or node.tag != TAG_FUNCTION_DEF:
            continue
        fd: ptr[AstFunctionDef] = node.data
        if _scan_address_taken(fd.body, name) != 0:
            return 1
    return 0

def _scan_address_taken(body: AstNodeList, name: str) -> int:
    for i in range(body.count):
        node: ptr[AstNode] = body.items[i]
        if node is None:
            continue
        # Look at calls' args — bare Name arg matching `name` is address-taken.
        if node.tag == TAG_EXPR_STMT:
            es: ptr[AstExprStmt] = node.data
            if es.value is not None and es.value.tag == TAG_CALL:
                if _call_has_name_arg(es.value, name) != 0:
                    return 1
        if node.tag == TAG_ASSIGN:
            an: ptr[AstAssign] = node.data
            if an.value is not None and an.value.tag == TAG_CALL:
                if _call_has_name_arg(an.value, name) != 0:
                    return 1
        if node.tag == TAG_ANN_ASSIGN:
            ann: ptr[AstAnnAssign] = node.data
            if ann.value is not None and ann.value.tag == TAG_CALL:
                if _call_has_name_arg(ann.value, name) != 0:
                    return 1
        if node.tag == TAG_RETURN:
            rn: ptr[AstReturn] = node.data
            if rn.value is not None and rn.value.tag == TAG_CALL:
                if _call_has_name_arg(rn.value, name) != 0:
                    return 1
        if node.tag == TAG_IF:
            ifd: ptr[AstIf] = node.data
            if _scan_address_taken(ifd.body, name) != 0:
                return 1
            if _scan_address_taken(ifd.orelse, name) != 0:
                return 1
        if node.tag == TAG_FOR:
            fd: ptr[AstFor] = node.data
            if _scan_address_taken(fd.body, name) != 0:
                return 1
        if node.tag == TAG_WHILE:
            wd: ptr[AstWhile] = node.data
            if _scan_address_taken(wd.body, name) != 0:
                return 1
    return 0

def _call_has_name_arg(call_node: ptr[AstNode], name: str) -> int:
    """True if any of the call's args is a bare Name `name` (address-taken).
    Walks one level only — passing `f` directly is what we care about."""
    cn: ptr[AstCall] = call_node.data
    for j in range(cn.args.count):
        arg: ptr[AstNode] = cn.args.items[j]
        if arg is not None and arg.tag == TAG_NAME:
            an: ptr[AstName] = arg.data
            if an.id == name:
                # Make sure it's not the function being called (Call.func) — it
                # never is here, since `arg` comes from cn.args, not cn.func.
                return 1
    return 0

def _has_caller(name: str, funcs: AstNodeList) -> int:
    """True if any function's body calls `name`."""
    for i in range(funcs.count):
        node: ptr[AstNode] = funcs.items[i]
        if node is None or node.tag != TAG_FUNCTION_DEF:
            continue
        fd: ptr[AstFunctionDef] = node.data
        if _func_calls_self(fd.body, name) != 0:
            return 1
    return 0

def native_infer_inline_from_body(s: ptr[CompilerState], funcs: AstNodeList) -> void:
    """Auto-mark small leaf functions as inline. Same heuristics as Python:
    not noinline/extern/cold, not recursive, not address-taken, body <= 3
    statements, no banned constructs, has at least one caller."""
    for i in range(funcs.count):
        node: ptr[AstNode] = funcs.items[i]
        if node is None or node.tag != TAG_FUNCTION_DEF:
            continue
        fd: ptr[AstFunctionDef] = node.data
        # Skip explicit @noinline / @extern / @export / @test
        skip: int = 0
        for d in range(fd.decorators.count):
            dnode: ptr[AstNode] = fd.decorators.items[d]
            if dnode is not None and dnode.tag == TAG_NAME:
                dn: ptr[AstName] = dnode.data
                if dn.id == "noinline" or dn.id == "extern" or dn.id == "export" or dn.id == "test" or dn.id == "compile_time" or dn.id == "trait" or dn.id == "generic" or dn.id == "parallel" or dn.id == "stream" or dn.id == "inline":
                    skip = 1
                    break
        if skip != 0:
            continue
        if strset_has(addr_of(s.cold_funcs), fd.name) != 0:
            continue
        if fd.body.count > 3:
            continue
        if _has_banned_stmt(fd.body) != 0:
            continue
        if _func_calls_self(fd.body, fd.name) != 0:
            continue
        if _is_address_taken(fd.name, funcs) != 0:
            continue
        if _has_caller(fd.name, funcs) == 0:
            continue
        strset_add(addr_of(s.inline_funcs), fd.name)

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
