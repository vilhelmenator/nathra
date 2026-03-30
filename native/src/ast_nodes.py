"nathra"
"""Native AST data structures and binary deserializer for the bootstrap compiler.

Design: Option B from BOOTSTRAP.md — AstNode is a small header (tag + lineno)
with a ptr[void] to a type-specific payload struct. All memory is arena-allocated.
"""

from nathra_stubs import arena_new, arena_free

# ── Node type tags (must match ast_serial.py) ───────────────────────────

TAG_MODULE:        u8 = 0
TAG_FUNCTION_DEF:  u8 = 1
TAG_CLASS_DEF:     u8 = 2
TAG_RETURN:        u8 = 3
TAG_RAISE:         u8 = 4
TAG_EXPR_STMT:     u8 = 5
TAG_IF:            u8 = 6
TAG_WHILE:         u8 = 7
TAG_FOR:           u8 = 8
TAG_WITH:          u8 = 9
TAG_ASSIGN:        u8 = 10
TAG_AUG_ASSIGN:    u8 = 11
TAG_ANN_ASSIGN:    u8 = 12
TAG_ASSERT:        u8 = 13
TAG_BREAK:         u8 = 14
TAG_CONTINUE:      u8 = 15
TAG_PASS:          u8 = 16
TAG_IMPORT:        u8 = 17
TAG_IMPORT_FROM:   u8 = 18
TAG_MATCH:         u8 = 19

TAG_CONSTANT:      u8 = 30
TAG_NAME:          u8 = 31
TAG_CALL:          u8 = 32
TAG_ATTRIBUTE:     u8 = 33
TAG_SUBSCRIPT:     u8 = 34
TAG_BIN_OP:        u8 = 35
TAG_UNARY_OP:      u8 = 36
TAG_BOOL_OP:       u8 = 37
TAG_COMPARE:       u8 = 38
TAG_IF_EXP:        u8 = 39
TAG_TUPLE:         u8 = 40
TAG_LIST:          u8 = 41
TAG_SET:           u8 = 42
TAG_DICT:          u8 = 43
TAG_JOINED_STR:    u8 = 44
TAG_FORMATTED_VAL: u8 = 45
TAG_LIST_COMP:     u8 = 46
TAG_LAMBDA:        u8 = 47

TAG_ARGUMENTS:     u8 = 60
TAG_ARG:           u8 = 61
TAG_KEYWORD:       u8 = 62
TAG_ALIAS:         u8 = 63
TAG_COMPREHENSION: u8 = 64
TAG_WITHITEM:      u8 = 65
TAG_MATCH_CASE:    u8 = 66
TAG_MATCH_VALUE:   u8 = 67
TAG_MATCH_OR:      u8 = 68
TAG_MATCH_AS:      u8 = 69

# ── Field kind tags ─────────────────────────────────────────────────────

FK_NODE:      u8 = 0
FK_NODE_LIST: u8 = 1
FK_STRING:    u8 = 2
FK_INT:       u8 = 3
FK_FLOAT:     u8 = 4
FK_BOOL:      u8 = 5
FK_OP:        u8 = 6
FK_NONE:      u8 = 7

# ── Constant kinds ─────────────────────────────────────────────────────

CONST_INT:      u8 = 0
CONST_FLOAT:    u8 = 1
CONST_STR:      u8 = 2
CONST_BOOL:     u8 = 3
CONST_NONE:     u8 = 4
CONST_ELLIPSIS: u8 = 5

# ── Operator tags ───────────────────────────────────────────────────────

OP_ADD:       u8 = 0
OP_SUB:       u8 = 1
OP_MULT:      u8 = 2
OP_DIV:       u8 = 3
OP_MOD:       u8 = 4
OP_POW:       u8 = 5
OP_FLOOR_DIV: u8 = 6
OP_LSHIFT:    u8 = 7
OP_RSHIFT:    u8 = 8
OP_BIT_OR:    u8 = 9
OP_BIT_XOR:   u8 = 10
OP_BIT_AND:   u8 = 11
OP_UADD:      u8 = 20
OP_USUB:      u8 = 21
OP_NOT:       u8 = 22
OP_INVERT:    u8 = 23
OP_AND:       u8 = 30
OP_OR:        u8 = 31
OP_EQ:        u8 = 40
OP_NOT_EQ:    u8 = 41
OP_LT:        u8 = 42
OP_LT_E:      u8 = 43
OP_GT:        u8 = 44
OP_GT_E:      u8 = 45
OP_IS:        u8 = 46
OP_IS_NOT:    u8 = 47
OP_IN:        u8 = 48
OP_NOT_IN:    u8 = 49

# ── Node list ───────────────────────────────────────────────────────────

class AstNodeList:
    items: ptr[ptr[AstNode]]
    count: i32

# ── Core node header ────────────────────────────────────────────────────

class AstNode:
    tag: u8
    lineno: u16
    data: ptr[void]

# ── Payload structs ─────────────────────────────────────────────────────

# Statements

class AstModule:
    body: AstNodeList

class AstFunctionDef:
    name: str
    args: ptr[AstNode]
    body: AstNodeList
    decorators: AstNodeList
    returns: ptr[AstNode]

class AstClassDef:
    name: str
    bases: AstNodeList
    keywords: AstNodeList
    body: AstNodeList
    decorators: AstNodeList

class AstReturn:
    value: ptr[AstNode]

class AstRaise:
    exc: ptr[AstNode]

class AstExprStmt:
    value: ptr[AstNode]

class AstIf:
    test: ptr[AstNode]
    body: AstNodeList
    orelse: AstNodeList

class AstWhile:
    test: ptr[AstNode]
    body: AstNodeList

class AstFor:
    target: ptr[AstNode]
    iter: ptr[AstNode]
    body: AstNodeList

class AstWith:
    items: AstNodeList
    body: AstNodeList

class AstAssign:
    targets: AstNodeList
    value: ptr[AstNode]

class AstAugAssign:
    target: ptr[AstNode]
    op: u8
    value: ptr[AstNode]

class AstAnnAssign:
    target: ptr[AstNode]
    annotation: ptr[AstNode]
    value: ptr[AstNode]

class AstAssert:
    test: ptr[AstNode]
    msg: ptr[AstNode]

class AstImport:
    names: AstNodeList

class AstImportFrom:
    module: str
    names: AstNodeList

class AstMatch:
    subject: ptr[AstNode]
    cases: AstNodeList

# Expressions

class AstConstant:
    kind: u8
    int_val: i64
    float_val: f64
    str_val: str

class AstName:
    id: str

class AstCall:
    func: ptr[AstNode]
    args: AstNodeList
    keywords: AstNodeList

class AstAttribute:
    value: ptr[AstNode]
    attr: str

class AstSubscript:
    value: ptr[AstNode]
    slice: ptr[AstNode]

class AstBinOp:
    left: ptr[AstNode]
    op: u8
    right: ptr[AstNode]

class AstUnaryOp:
    op: u8
    operand: ptr[AstNode]

class AstBoolOp:
    op: u8
    values: AstNodeList

class AstCompare:
    left: ptr[AstNode]
    ops: ptr[u8]
    op_count: i32
    comparators: AstNodeList

class AstIfExp:
    test: ptr[AstNode]
    body: ptr[AstNode]
    orelse: ptr[AstNode]

class AstTuple:
    elts: AstNodeList

class AstList:
    elts: AstNodeList

class AstSet:
    elts: AstNodeList

class AstDict:
    keys: AstNodeList
    values: AstNodeList

class AstJoinedStr:
    values: AstNodeList

class AstFormattedValue:
    value: ptr[AstNode]
    conversion: i64
    format_spec: ptr[AstNode]

class AstListComp:
    elt: ptr[AstNode]
    generators: AstNodeList

class AstLambda:
    args: ptr[AstNode]
    body: ptr[AstNode]

# Structural / helper

class AstArguments:
    args: AstNodeList
    vararg: ptr[AstNode]
    defaults: AstNodeList

class AstArg:
    name: str
    annotation: ptr[AstNode]

class AstKeyword:
    name: str
    value: ptr[AstNode]

class AstAlias:
    name: str
    asname: str

class AstComprehension:
    target: ptr[AstNode]
    iter: ptr[AstNode]
    ifs: AstNodeList

class AstWithItem:
    context_expr: ptr[AstNode]
    optional_vars: ptr[AstNode]

class AstMatchCase:
    pattern: ptr[AstNode]
    guard: ptr[AstNode]
    body: AstNodeList

class AstMatchValue:
    value: ptr[AstNode]

class AstMatchOr:
    patterns: AstNodeList

class AstMatchAs:
    pattern: ptr[AstNode]
    name: str

# ── Deserializer ────────────────────────────────────────────────────────

def ast_read_str(r: ptr[NrReader], arena: ptr[NrArena]) -> str:
    length: i32 = nr_read_i32(r)
    if length < 0:
        return None
    buf: ptr[byte] = alloc(cast_int(length) + 1)
    nr_read_bytes(r, buf, cast_int(length))
    buf[length] = 0
    s: str = arena_str_new(arena, buf)
    free(buf)
    return s

def ast_read_node(r: ptr[NrReader], arena: ptr[NrArena]) -> ptr[AstNode]:
    tag: u8 = nr_read_u8(r)
    lineno: u16 = nr_read_u16(r)

    node: ptr[AstNode] = arena_alloc(arena, sizeof(AstNode))
    node.tag = tag
    node.lineno = lineno
    node.data = None

    match tag:
        case 0:   ast_read_module(r, arena, node)
        case 1:   ast_read_function_def(r, arena, node)
        case 2:   ast_read_class_def(r, arena, node)
        case 3:   ast_read_return(r, arena, node)
        case 4:   ast_read_raise(r, arena, node)
        case 5:   ast_read_expr_stmt(r, arena, node)
        case 6:   ast_read_if(r, arena, node)
        case 7:   ast_read_while(r, arena, node)
        case 8:   ast_read_for(r, arena, node)
        case 9:   ast_read_with(r, arena, node)
        case 10:  ast_read_assign(r, arena, node)
        case 11:  ast_read_aug_assign(r, arena, node)
        case 12:  ast_read_ann_assign(r, arena, node)
        case 13:  ast_read_assert(r, arena, node)
        case 14:  pass
        case 15:  pass
        case 16:  pass
        case 17:  ast_read_import(r, arena, node)
        case 18:  ast_read_import_from(r, arena, node)
        case 19:  ast_read_match(r, arena, node)
        case 30:  ast_read_constant(r, arena, node)
        case 31:  ast_read_name(r, arena, node)
        case 32:  ast_read_call(r, arena, node)
        case 33:  ast_read_attribute(r, arena, node)
        case 34:  ast_read_subscript(r, arena, node)
        case 35:  ast_read_binop(r, arena, node)
        case 36:  ast_read_unaryop(r, arena, node)
        case 37:  ast_read_boolop(r, arena, node)
        case 38:  ast_read_compare(r, arena, node)
        case 39:  ast_read_ifexp(r, arena, node)
        case 40:  ast_read_tuple(r, arena, node)
        case 41:  ast_read_list(r, arena, node)
        case 42:  ast_read_set(r, arena, node)
        case 43:  ast_read_dict(r, arena, node)
        case 44:  ast_read_joined_str(r, arena, node)
        case 45:  ast_read_formatted_value(r, arena, node)
        case 46:  ast_read_list_comp(r, arena, node)
        case 47:  ast_read_lambda(r, arena, node)
        case 60:  ast_read_arguments(r, arena, node)
        case 61:  ast_read_arg(r, arena, node)
        case 62:  ast_read_keyword(r, arena, node)
        case 63:  ast_read_alias(r, arena, node)
        case 64:  ast_read_comprehension(r, arena, node)
        case 65:  ast_read_withitem(r, arena, node)
        case 66:  ast_read_match_case(r, arena, node)
        case 67:  ast_read_match_value(r, arena, node)
        case 68:  ast_read_match_or(r, arena, node)
        case 69:  ast_read_match_as(r, arena, node)
    return node

def ast_read_node_field(r: ptr[NrReader], arena: ptr[NrArena]) -> ptr[AstNode]:
    """Read FK_NODE or FK_NONE prefix, then the node."""
    kind: u8 = nr_read_u8(r)
    if kind == FK_NONE:
        return None
    return ast_read_node(r, arena)

def ast_read_node_list(r: ptr[NrReader], arena: ptr[NrArena]) -> AstNodeList:
    """Read FK_NODE_LIST prefix + count + nodes."""
    kind: u8 = nr_read_u8(r)
    count: i32 = nr_read_i32(r)
    result: AstNodeList = AstNodeList(None, 0)
    if count > 0:
        result.items = arena_alloc(arena, cast_int(count) * 8)
        result.count = count
        for i in range(count):
            result.items[i] = ast_read_node(r, arena)
    return result

def ast_read_string_field(r: ptr[NrReader], arena: ptr[NrArena]) -> str:
    """Read FK_STRING prefix + string."""
    kind: u8 = nr_read_u8(r)
    return ast_read_str(r, arena)

def ast_read_int_field(r: ptr[NrReader]) -> i64:
    """Read FK_INT prefix + i64."""
    kind: u8 = nr_read_u8(r)
    return nr_read_i64(r)

def ast_read_float_field(r: ptr[NrReader]) -> f64:
    """Read FK_FLOAT prefix + f64."""
    kind: u8 = nr_read_u8(r)
    return nr_read_f64(r)

def ast_read_bool_field(r: ptr[NrReader]) -> u8:
    """Read FK_BOOL prefix + bool."""
    kind: u8 = nr_read_u8(r)
    return nr_read_u8(r)

def ast_read_op_field(r: ptr[NrReader]) -> u8:
    """Read FK_OP prefix + op tag."""
    kind: u8 = nr_read_u8(r)
    return nr_read_u8(r)

# ── Per-node-type readers ───────────────────────────────────────────────

def ast_read_module(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstModule] = arena_alloc(arena, sizeof(AstModule))
    p.body = ast_read_node_list(r, arena)
    node.data = p

def ast_read_function_def(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstFunctionDef] = arena_alloc(arena, sizeof(AstFunctionDef))
    p.name = ast_read_string_field(r, arena)
    p.args = ast_read_node(r, arena)
    p.body = ast_read_node_list(r, arena)
    p.decorators = ast_read_node_list(r, arena)
    p.returns = ast_read_node_field(r, arena)
    node.data = p

def ast_read_class_def(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstClassDef] = arena_alloc(arena, sizeof(AstClassDef))
    p.name = ast_read_string_field(r, arena)
    p.bases = ast_read_node_list(r, arena)
    p.keywords = ast_read_node_list(r, arena)
    p.body = ast_read_node_list(r, arena)
    p.decorators = ast_read_node_list(r, arena)
    node.data = p

def ast_read_return(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstReturn] = arena_alloc(arena, sizeof(AstReturn))
    p.value = ast_read_node_field(r, arena)
    node.data = p

def ast_read_raise(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstRaise] = arena_alloc(arena, sizeof(AstRaise))
    p.exc = ast_read_node_field(r, arena)
    node.data = p

def ast_read_expr_stmt(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstExprStmt] = arena_alloc(arena, sizeof(AstExprStmt))
    p.value = ast_read_node_field(r, arena)
    node.data = p

def ast_read_if(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstIf] = arena_alloc(arena, sizeof(AstIf))
    p.test = ast_read_node_field(r, arena)
    p.body = ast_read_node_list(r, arena)
    p.orelse = ast_read_node_list(r, arena)
    node.data = p

def ast_read_while(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstWhile] = arena_alloc(arena, sizeof(AstWhile))
    p.test = ast_read_node_field(r, arena)
    p.body = ast_read_node_list(r, arena)
    node.data = p

def ast_read_for(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstFor] = arena_alloc(arena, sizeof(AstFor))
    p.target = ast_read_node_field(r, arena)
    p.iter = ast_read_node_field(r, arena)
    p.body = ast_read_node_list(r, arena)
    node.data = p

def ast_read_with(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstWith] = arena_alloc(arena, sizeof(AstWith))
    p.items = ast_read_node_list(r, arena)
    p.body = ast_read_node_list(r, arena)
    node.data = p

def ast_read_assign(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstAssign] = arena_alloc(arena, sizeof(AstAssign))
    p.targets = ast_read_node_list(r, arena)
    p.value = ast_read_node_field(r, arena)
    node.data = p

def ast_read_aug_assign(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstAugAssign] = arena_alloc(arena, sizeof(AstAugAssign))
    p.target = ast_read_node_field(r, arena)
    p.op = ast_read_op_field(r)
    p.value = ast_read_node_field(r, arena)
    node.data = p

def ast_read_ann_assign(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstAnnAssign] = arena_alloc(arena, sizeof(AstAnnAssign))
    p.target = ast_read_node_field(r, arena)
    p.annotation = ast_read_node_field(r, arena)
    p.value = ast_read_node_field(r, arena)
    node.data = p

def ast_read_assert(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstAssert] = arena_alloc(arena, sizeof(AstAssert))
    p.test = ast_read_node_field(r, arena)
    p.msg = ast_read_node_field(r, arena)
    node.data = p

def ast_read_import(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstImport] = arena_alloc(arena, sizeof(AstImport))
    p.names = ast_read_node_list(r, arena)
    node.data = p

def ast_read_import_from(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstImportFrom] = arena_alloc(arena, sizeof(AstImportFrom))
    p.module = ast_read_string_field(r, arena)
    p.names = ast_read_node_list(r, arena)
    node.data = p

def ast_read_match(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstMatch] = arena_alloc(arena, sizeof(AstMatch))
    p.subject = ast_read_node_field(r, arena)
    p.cases = ast_read_node_list(r, arena)
    node.data = p

def ast_read_constant(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstConstant] = arena_alloc(arena, sizeof(AstConstant))
    p.kind = nr_read_u8(r)
    p.int_val = 0
    p.float_val = 0.0
    p.str_val = None
    match p.kind:
        case 0:
            p.int_val = ast_read_int_field(r)
        case 1:
            p.float_val = ast_read_float_field(r)
        case 2:
            p.str_val = ast_read_string_field(r, arena)
        case 3:
            p.int_val = cast_int(ast_read_bool_field(r))
        case 4:
            pass
        case 5:
            pass
    node.data = p

def ast_read_name(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstName] = arena_alloc(arena, sizeof(AstName))
    p.id = ast_read_string_field(r, arena)
    node.data = p

def ast_read_call(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstCall] = arena_alloc(arena, sizeof(AstCall))
    p.func = ast_read_node_field(r, arena)
    p.args = ast_read_node_list(r, arena)
    p.keywords = ast_read_node_list(r, arena)
    node.data = p

def ast_read_attribute(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstAttribute] = arena_alloc(arena, sizeof(AstAttribute))
    p.value = ast_read_node_field(r, arena)
    p.attr = ast_read_string_field(r, arena)
    node.data = p

def ast_read_subscript(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstSubscript] = arena_alloc(arena, sizeof(AstSubscript))
    p.value = ast_read_node_field(r, arena)
    p.slice = ast_read_node_field(r, arena)
    node.data = p

def ast_read_binop(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstBinOp] = arena_alloc(arena, sizeof(AstBinOp))
    p.left = ast_read_node_field(r, arena)
    p.op = ast_read_op_field(r)
    p.right = ast_read_node_field(r, arena)
    node.data = p

def ast_read_unaryop(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstUnaryOp] = arena_alloc(arena, sizeof(AstUnaryOp))
    p.op = ast_read_op_field(r)
    p.operand = ast_read_node_field(r, arena)
    node.data = p

def ast_read_boolop(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstBoolOp] = arena_alloc(arena, sizeof(AstBoolOp))
    p.op = ast_read_op_field(r)
    p.values = ast_read_node_list(r, arena)
    node.data = p

def ast_read_compare(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstCompare] = arena_alloc(arena, sizeof(AstCompare))
    p.left = ast_read_node_field(r, arena)
    op_count: u8 = nr_read_u8(r)
    p.op_count = cast_int(op_count)
    p.ops = arena_alloc(arena, cast_int(op_count))
    for i in range(cast_int(op_count)):
        p.ops[i] = nr_read_u8(r)
    p.comparators = ast_read_node_list(r, arena)
    node.data = p

def ast_read_ifexp(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstIfExp] = arena_alloc(arena, sizeof(AstIfExp))
    p.test = ast_read_node_field(r, arena)
    p.body = ast_read_node_field(r, arena)
    p.orelse = ast_read_node_field(r, arena)
    node.data = p

def ast_read_tuple(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstTuple] = arena_alloc(arena, sizeof(AstTuple))
    p.elts = ast_read_node_list(r, arena)
    node.data = p

def ast_read_list(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstList] = arena_alloc(arena, sizeof(AstList))
    p.elts = ast_read_node_list(r, arena)
    node.data = p

def ast_read_set(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstSet] = arena_alloc(arena, sizeof(AstSet))
    p.elts = ast_read_node_list(r, arena)
    node.data = p

def ast_read_dict(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstDict] = arena_alloc(arena, sizeof(AstDict))
    p.keys = ast_read_node_list(r, arena)
    p.values = ast_read_node_list(r, arena)
    node.data = p

def ast_read_joined_str(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstJoinedStr] = arena_alloc(arena, sizeof(AstJoinedStr))
    p.values = ast_read_node_list(r, arena)
    node.data = p

def ast_read_formatted_value(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstFormattedValue] = arena_alloc(arena, sizeof(AstFormattedValue))
    p.value = ast_read_node_field(r, arena)
    p.conversion = ast_read_int_field(r)
    p.format_spec = ast_read_node_field(r, arena)
    node.data = p

def ast_read_list_comp(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstListComp] = arena_alloc(arena, sizeof(AstListComp))
    p.elt = ast_read_node_field(r, arena)
    p.generators = ast_read_node_list(r, arena)
    node.data = p

def ast_read_lambda(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstLambda] = arena_alloc(arena, sizeof(AstLambda))
    p.args = ast_read_node(r, arena)
    p.body = ast_read_node_field(r, arena)
    node.data = p

def ast_read_arguments(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstArguments] = arena_alloc(arena, sizeof(AstArguments))
    p.args = ast_read_node_list(r, arena)
    p.vararg = ast_read_node_field(r, arena)
    p.defaults = ast_read_node_list(r, arena)
    node.data = p

def ast_read_arg(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstArg] = arena_alloc(arena, sizeof(AstArg))
    p.name = ast_read_string_field(r, arena)
    p.annotation = ast_read_node_field(r, arena)
    node.data = p

def ast_read_keyword(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstKeyword] = arena_alloc(arena, sizeof(AstKeyword))
    p.name = ast_read_string_field(r, arena)
    p.value = ast_read_node_field(r, arena)
    node.data = p

def ast_read_alias(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstAlias] = arena_alloc(arena, sizeof(AstAlias))
    p.name = ast_read_string_field(r, arena)
    p.asname = ast_read_string_field(r, arena)
    node.data = p

def ast_read_comprehension(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstComprehension] = arena_alloc(arena, sizeof(AstComprehension))
    p.target = ast_read_node_field(r, arena)
    p.iter = ast_read_node_field(r, arena)
    p.ifs = ast_read_node_list(r, arena)
    node.data = p

def ast_read_withitem(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstWithItem] = arena_alloc(arena, sizeof(AstWithItem))
    p.context_expr = ast_read_node_field(r, arena)
    p.optional_vars = ast_read_node_field(r, arena)
    node.data = p

def ast_read_match_case(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstMatchCase] = arena_alloc(arena, sizeof(AstMatchCase))
    p.pattern = ast_read_node_field(r, arena)
    p.guard = ast_read_node_field(r, arena)
    p.body = ast_read_node_list(r, arena)
    node.data = p

def ast_read_match_value(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstMatchValue] = arena_alloc(arena, sizeof(AstMatchValue))
    p.value = ast_read_node_field(r, arena)
    node.data = p

def ast_read_match_or(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstMatchOr] = arena_alloc(arena, sizeof(AstMatchOr))
    p.patterns = ast_read_node_list(r, arena)
    node.data = p

def ast_read_match_as(r: ptr[NrReader], arena: ptr[NrArena], node: ptr[AstNode]) -> void:
    p: ptr[AstMatchAs] = arena_alloc(arena, sizeof(AstMatchAs))
    p.pattern = ast_read_node_field(r, arena)
    p.name = ast_read_string_field(r, arena)
    node.data = p

# ── Public entry point ──────────────────────────────────────────────────

def deserialize_ast(buf: ptr[u8], buf_len: i64) -> ptr[AstNode]:
    """Deserialize binary AST buffer into native node tree.

    All memory is arena-allocated. Caller receives the root node.
    """
    arena: ptr[NrArena] = arena_new(buf_len * 64)
    r: ptr[NrReader] = nr_reader_new(buf + 4, buf_len - 4)
    root: ptr[AstNode] = ast_read_node(r, arena)
    return root

def ast_count_nodes(node: ptr[AstNode]) -> int:
    """Count total nodes in tree (for validation)."""
    if node is None:
        return 0
    count: int = 1
    if node.tag == TAG_MODULE:
        p: ptr[AstModule] = node.data
        for i in range(p.body.count):
            count = count + ast_count_nodes(p.body.items[i])
    elif node.tag == TAG_FUNCTION_DEF:
        p2: ptr[AstFunctionDef] = node.data
        count = count + ast_count_nodes(p2.args)
        for i in range(p2.body.count):
            count = count + ast_count_nodes(p2.body.items[i])
        for i in range(p2.decorators.count):
            count = count + ast_count_nodes(p2.decorators.items[i])
        count = count + ast_count_nodes(p2.returns)
    elif node.tag == TAG_CALL:
        p3: ptr[AstCall] = node.data
        count = count + ast_count_nodes(p3.func)
        for i in range(p3.args.count):
            count = count + ast_count_nodes(p3.args.items[i])
    elif node.tag == TAG_BIN_OP:
        p4: ptr[AstBinOp] = node.data
        count = count + ast_count_nodes(p4.left) + ast_count_nodes(p4.right)
    elif node.tag == TAG_RETURN:
        p5: ptr[AstReturn] = node.data
        count = count + ast_count_nodes(p5.value)
    elif node.tag == TAG_EXPR_STMT:
        p6: ptr[AstExprStmt] = node.data
        count = count + ast_count_nodes(p6.value)
    elif node.tag == TAG_ANN_ASSIGN:
        p7: ptr[AstAnnAssign] = node.data
        count = count + ast_count_nodes(p7.target)
        count = count + ast_count_nodes(p7.annotation)
        count = count + ast_count_nodes(p7.value)
    elif node.tag == TAG_ARGUMENTS:
        p8: ptr[AstArguments] = node.data
        for i in range(p8.args.count):
            count = count + ast_count_nodes(p8.args.items[i])
        count = count + ast_count_nodes(p8.vararg)
    elif node.tag == TAG_ARG:
        p9: ptr[AstArg] = node.data
        count = count + ast_count_nodes(p9.annotation)
    return count

def main() -> int:
    buf_len: i64 = 0
    buf: ptr[byte] = read_file_bin("test_ast.bin", addr_of(buf_len))
    if buf is None:
        msg: str = "Error: cannot read test_ast.bin"
        print(msg)
        return 1
    root: ptr[AstNode] = deserialize_ast(buf, buf_len)
    count: int = ast_count_nodes(root)
    print(count)
    free(buf)
    return 0
