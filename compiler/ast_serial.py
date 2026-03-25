"""Binary AST serializer for the micropy bootstrap compiler.

Walks a Python ast.Module depth-first and writes a compact binary encoding
that the native compiler can deserialize into C structs.

Wire format per node:
  [u8]  tag (node type)
  [u16] lineno
  Then tag-specific fields, each prefixed by field kind byte:
    0=node  1=node_list  2=string  3=int  4=float  5=bool  6=op  7=none
"""

import ast
import struct
from io import BytesIO

# ── Node type tags ──────────────────────────────────────────────────────

# Statements
TAG_MODULE        = 0
TAG_FUNCTION_DEF  = 1
TAG_CLASS_DEF     = 2
TAG_RETURN        = 3
TAG_RAISE         = 4
TAG_EXPR_STMT     = 5
TAG_IF            = 6
TAG_WHILE         = 7
TAG_FOR           = 8
TAG_WITH          = 9
TAG_ASSIGN        = 10
TAG_AUG_ASSIGN    = 11
TAG_ANN_ASSIGN    = 12
TAG_ASSERT        = 13
TAG_BREAK         = 14
TAG_CONTINUE      = 15
TAG_PASS          = 16
TAG_IMPORT        = 17
TAG_IMPORT_FROM   = 18
TAG_MATCH         = 19

# Expressions
TAG_CONSTANT      = 30
TAG_NAME          = 31
TAG_CALL          = 32
TAG_ATTRIBUTE     = 33
TAG_SUBSCRIPT     = 34
TAG_BIN_OP        = 35
TAG_UNARY_OP      = 36
TAG_BOOL_OP       = 37
TAG_COMPARE       = 38
TAG_IF_EXP        = 39
TAG_TUPLE         = 40
TAG_LIST          = 41
TAG_SET           = 42
TAG_DICT          = 43
TAG_JOINED_STR    = 44
TAG_FORMATTED_VAL = 45
TAG_LIST_COMP     = 46
TAG_LAMBDA        = 47

# Structural / helper
TAG_ARGUMENTS     = 60
TAG_ARG           = 61
TAG_KEYWORD       = 62
TAG_ALIAS         = 63
TAG_COMPREHENSION = 64
TAG_WITHITEM      = 65
TAG_MATCH_CASE    = 66
TAG_MATCH_VALUE   = 67
TAG_MATCH_OR      = 68
TAG_MATCH_AS      = 69

# ── Field kind tags ─────────────────────────────────────────────────────

FK_NODE       = 0
FK_NODE_LIST  = 1
FK_STRING     = 2
FK_INT        = 3
FK_FLOAT      = 4
FK_BOOL       = 5
FK_OP         = 6
FK_NONE       = 7

# ── Operator tags ───────────────────────────────────────────────────────

# Binary ops
OP_ADD       = 0
OP_SUB       = 1
OP_MULT      = 2
OP_DIV       = 3
OP_MOD       = 4
OP_POW       = 5
OP_FLOOR_DIV = 6
OP_LSHIFT    = 7
OP_RSHIFT    = 8
OP_BIT_OR    = 9
OP_BIT_XOR   = 10
OP_BIT_AND   = 11

# Unary ops
OP_UADD      = 20
OP_USUB      = 21
OP_NOT       = 22
OP_INVERT    = 23

# Bool ops
OP_AND        = 30
OP_OR         = 31

# Comparison ops
OP_EQ         = 40
OP_NOT_EQ     = 41
OP_LT         = 42
OP_LT_E       = 43
OP_GT         = 44
OP_GT_E       = 45
OP_IS         = 46
OP_IS_NOT     = 47
OP_IN         = 48
OP_NOT_IN     = 49

# ── Operator mapping ───────────────────────────────────────────────────

_BINOP_MAP = {
    ast.Add: OP_ADD, ast.Sub: OP_SUB, ast.Mult: OP_MULT,
    ast.Div: OP_DIV, ast.Mod: OP_MOD, ast.Pow: OP_POW,
    ast.FloorDiv: OP_FLOOR_DIV, ast.LShift: OP_LSHIFT,
    ast.RShift: OP_RSHIFT, ast.BitOr: OP_BIT_OR,
    ast.BitXor: OP_BIT_XOR, ast.BitAnd: OP_BIT_AND,
}

_UNARYOP_MAP = {
    ast.UAdd: OP_UADD, ast.USub: OP_USUB,
    ast.Not: OP_NOT, ast.Invert: OP_INVERT,
}

_BOOLOP_MAP = {ast.And: OP_AND, ast.Or: OP_OR}

_CMPOP_MAP = {
    ast.Eq: OP_EQ, ast.NotEq: OP_NOT_EQ, ast.Lt: OP_LT,
    ast.LtE: OP_LT_E, ast.Gt: OP_GT, ast.GtE: OP_GT_E,
    ast.Is: OP_IS, ast.IsNot: OP_IS_NOT,
    ast.In: OP_IN, ast.NotIn: OP_NOT_IN,
}


# ── Serializer ──────────────────────────────────────────────────────────

class AstSerializer:
    """Serialize a Python AST to a compact binary format."""

    def __init__(self):
        self.buf = BytesIO()

    def _write_u8(self, v):
        self.buf.write(struct.pack("B", v))

    def _write_u16(self, v):
        self.buf.write(struct.pack("<H", v))

    def _write_i32(self, v):
        self.buf.write(struct.pack("<i", v))

    def _write_i64(self, v):
        self.buf.write(struct.pack("<q", v))

    def _write_f64(self, v):
        self.buf.write(struct.pack("<d", v))

    def _write_str(self, s):
        if s is None:
            self._write_i32(-1)
            return
        data = s.encode("utf-8")
        self._write_i32(len(data))
        self.buf.write(data)

    # ── Field writers ───────────────────────────────────────────────────

    def _write_node_field(self, node):
        """Write a single child node (or none marker)."""
        if node is None:
            self._write_u8(FK_NONE)
        else:
            self._write_u8(FK_NODE)
            self._serialize(node)

    def _write_node_list_field(self, nodes):
        """Write a list of child nodes."""
        self._write_u8(FK_NODE_LIST)
        self._write_i32(len(nodes))
        for n in nodes:
            self._serialize(n)

    def _write_string_field(self, s):
        self._write_u8(FK_STRING)
        self._write_str(s)

    def _write_int_field(self, v):
        self._write_u8(FK_INT)
        self._write_i64(v)

    def _write_float_field(self, v):
        self._write_u8(FK_FLOAT)
        self._write_f64(v)

    def _write_bool_field(self, v):
        self._write_u8(FK_BOOL)
        self._write_u8(1 if v else 0)

    def _write_op_field(self, op):
        self._write_u8(FK_OP)
        op_type = type(op)
        for table in (_BINOP_MAP, _UNARYOP_MAP, _BOOLOP_MAP, _CMPOP_MAP):
            if op_type in table:
                self._write_u8(table[op_type])
                return
        raise ValueError(f"Unknown operator: {op_type.__name__}")

    def _write_op_list_field(self, ops):
        """Write a list of operators (used by Compare)."""
        self._write_u8(FK_NODE_LIST)  # reuse node_list kind for op lists
        self._write_i32(len(ops))
        for op in ops:
            self._write_op_field(op)

    # ── Node header ─────────────────────────────────────────────────────

    def _write_header(self, tag, node):
        self._write_u8(tag)
        self._write_u16(getattr(node, "lineno", 0))

    # ── Main dispatch ───────────────────────────────────────────────────

    def _serialize(self, node):
        method = _DISPATCH.get(type(node))
        if method is None:
            raise ValueError(f"Unsupported AST node: {type(node).__name__}")
        method(self, node)

    # ── Statement serializers ───────────────────────────────────────────

    def _s_module(self, node):
        self._write_header(TAG_MODULE, node)
        self._write_node_list_field(node.body)

    def _s_function_def(self, node):
        self._write_header(TAG_FUNCTION_DEF, node)
        self._write_string_field(node.name)
        self._serialize(node.args)  # arguments node
        self._write_node_list_field(node.body)
        self._write_node_list_field(node.decorator_list)
        self._write_node_field(node.returns)

    def _s_class_def(self, node):
        self._write_header(TAG_CLASS_DEF, node)
        self._write_string_field(node.name)
        self._write_node_list_field(node.bases)
        self._write_node_list_field(node.keywords)
        self._write_node_list_field(node.body)
        self._write_node_list_field(node.decorator_list)

    def _s_return(self, node):
        self._write_header(TAG_RETURN, node)
        self._write_node_field(node.value)

    def _s_raise(self, node):
        self._write_header(TAG_RAISE, node)
        self._write_node_field(node.exc)

    def _s_expr_stmt(self, node):
        self._write_header(TAG_EXPR_STMT, node)
        self._write_node_field(node.value)

    def _s_if(self, node):
        self._write_header(TAG_IF, node)
        self._write_node_field(node.test)
        self._write_node_list_field(node.body)
        self._write_node_list_field(node.orelse)

    def _s_while(self, node):
        self._write_header(TAG_WHILE, node)
        self._write_node_field(node.test)
        self._write_node_list_field(node.body)

    def _s_for(self, node):
        self._write_header(TAG_FOR, node)
        self._write_node_field(node.target)
        self._write_node_field(node.iter)
        self._write_node_list_field(node.body)

    def _s_with(self, node):
        self._write_header(TAG_WITH, node)
        self._write_node_list_field([
            self._make_withitem(item) for item in node.items
        ])
        self._write_node_list_field(node.body)

    def _make_withitem(self, item):
        """Wrap a withitem as a pseudo-node so it can be serialized."""
        return _WithItemWrapper(item)

    def _s_withitem(self, wrapper):
        item = wrapper.item
        self._write_header(TAG_WITHITEM, item)
        self._write_node_field(item.context_expr)
        self._write_node_field(item.optional_vars)

    def _s_assign(self, node):
        self._write_header(TAG_ASSIGN, node)
        self._write_node_list_field(node.targets)
        self._write_node_field(node.value)

    def _s_aug_assign(self, node):
        self._write_header(TAG_AUG_ASSIGN, node)
        self._write_node_field(node.target)
        self._write_op_field(node.op)
        self._write_node_field(node.value)

    def _s_ann_assign(self, node):
        self._write_header(TAG_ANN_ASSIGN, node)
        self._write_node_field(node.target)
        self._write_node_field(node.annotation)
        self._write_node_field(node.value)

    def _s_assert(self, node):
        self._write_header(TAG_ASSERT, node)
        self._write_node_field(node.test)
        self._write_node_field(node.msg)

    def _s_break(self, node):
        self._write_header(TAG_BREAK, node)

    def _s_continue(self, node):
        self._write_header(TAG_CONTINUE, node)

    def _s_pass(self, node):
        self._write_header(TAG_PASS, node)

    def _s_import(self, node):
        self._write_header(TAG_IMPORT, node)
        self._write_node_list_field([
            _AliasWrapper(a) for a in node.names
        ])

    def _s_import_from(self, node):
        self._write_header(TAG_IMPORT_FROM, node)
        self._write_string_field(node.module)
        self._write_node_list_field([
            _AliasWrapper(a) for a in node.names
        ])

    def _s_alias(self, wrapper):
        a = wrapper.alias
        self._write_header(TAG_ALIAS, a)
        self._write_string_field(a.name)
        self._write_string_field(a.asname)

    def _s_match(self, node):
        self._write_header(TAG_MATCH, node)
        self._write_node_field(node.subject)
        self._write_node_list_field([
            _MatchCaseWrapper(c) for c in node.cases
        ])

    def _s_match_case(self, wrapper):
        c = wrapper.case
        self._write_header(TAG_MATCH_CASE, c)
        self._write_node_field(c.pattern)
        self._write_node_field(c.guard)
        self._write_node_list_field(c.body)

    def _s_match_value(self, node):
        self._write_header(TAG_MATCH_VALUE, node)
        self._write_node_field(node.value)

    def _s_match_or(self, node):
        self._write_header(TAG_MATCH_OR, node)
        self._write_node_list_field(node.patterns)

    def _s_match_as(self, node):
        self._write_header(TAG_MATCH_AS, node)
        self._write_node_field(node.pattern)
        self._write_string_field(node.name)

    # ── Expression serializers ──────────────────────────────────────────

    def _s_constant(self, node):
        self._write_header(TAG_CONSTANT, node)
        v = node.value
        if isinstance(v, bool):
            self._write_u8(3)  # kind=bool
            self._write_bool_field(v)
        elif isinstance(v, int):
            self._write_u8(0)  # kind=int
            self._write_int_field(v)
        elif isinstance(v, float):
            self._write_u8(1)  # kind=float
            self._write_float_field(v)
        elif isinstance(v, str):
            self._write_u8(2)  # kind=str
            self._write_string_field(v)
        elif v is None:
            self._write_u8(4)  # kind=none
        elif v is ...:
            self._write_u8(5)  # kind=ellipsis
        else:
            raise ValueError(f"Unsupported constant type: {type(v)}")

    def _s_name(self, node):
        self._write_header(TAG_NAME, node)
        self._write_string_field(node.id)

    def _s_call(self, node):
        self._write_header(TAG_CALL, node)
        self._write_node_field(node.func)
        self._write_node_list_field(node.args)
        self._write_node_list_field(node.keywords)

    def _s_attribute(self, node):
        self._write_header(TAG_ATTRIBUTE, node)
        self._write_node_field(node.value)
        self._write_string_field(node.attr)

    def _s_subscript(self, node):
        self._write_header(TAG_SUBSCRIPT, node)
        self._write_node_field(node.value)
        self._write_node_field(node.slice)

    def _s_binop(self, node):
        self._write_header(TAG_BIN_OP, node)
        self._write_node_field(node.left)
        self._write_op_field(node.op)
        self._write_node_field(node.right)

    def _s_unaryop(self, node):
        self._write_header(TAG_UNARY_OP, node)
        self._write_op_field(node.op)
        self._write_node_field(node.operand)

    def _s_boolop(self, node):
        self._write_header(TAG_BOOL_OP, node)
        self._write_op_field(node.op)
        self._write_node_list_field(node.values)

    def _s_compare(self, node):
        self._write_header(TAG_COMPARE, node)
        self._write_node_field(node.left)
        # ops: write count then each op as a u8 tag
        self._write_u8(len(node.ops))
        for op in node.ops:
            op_tag = _CMPOP_MAP.get(type(op))
            if op_tag is None:
                raise ValueError(f"Unknown comparison op: {type(op).__name__}")
            self._write_u8(op_tag)
        self._write_node_list_field(node.comparators)

    def _s_ifexp(self, node):
        self._write_header(TAG_IF_EXP, node)
        self._write_node_field(node.test)
        self._write_node_field(node.body)
        self._write_node_field(node.orelse)

    def _s_tuple(self, node):
        self._write_header(TAG_TUPLE, node)
        self._write_node_list_field(node.elts)

    def _s_list(self, node):
        self._write_header(TAG_LIST, node)
        self._write_node_list_field(node.elts)

    def _s_set(self, node):
        self._write_header(TAG_SET, node)
        self._write_node_list_field(node.elts)

    def _s_dict(self, node):
        self._write_header(TAG_DICT, node)
        # keys can be None for **unpacking, write as node_list
        self._write_node_list_field(node.keys)
        self._write_node_list_field(node.values)

    def _s_joined_str(self, node):
        self._write_header(TAG_JOINED_STR, node)
        self._write_node_list_field(node.values)

    def _s_formatted_value(self, node):
        self._write_header(TAG_FORMATTED_VAL, node)
        self._write_node_field(node.value)
        self._write_int_field(node.conversion)
        self._write_node_field(node.format_spec)

    def _s_list_comp(self, node):
        self._write_header(TAG_LIST_COMP, node)
        self._write_node_field(node.elt)
        self._write_node_list_field([
            _ComprehensionWrapper(g) for g in node.generators
        ])

    def _s_comprehension(self, wrapper):
        g = wrapper.gen
        self._write_header(TAG_COMPREHENSION, g)
        self._write_node_field(g.target)
        self._write_node_field(g.iter)
        self._write_node_list_field(g.ifs)

    def _s_lambda(self, node):
        self._write_header(TAG_LAMBDA, node)
        self._serialize(node.args)  # arguments node
        self._write_node_field(node.body)

    # ── Structural node serializers ─────────────────────────────────────

    def _s_arguments(self, node):
        self._write_header(TAG_ARGUMENTS, node)
        self._write_node_list_field(node.args)
        # vararg
        if node.vararg:
            self._write_node_field(node.vararg)
        else:
            self._write_u8(FK_NONE)
        self._write_node_list_field(node.defaults)

    def _s_arg(self, node):
        self._write_header(TAG_ARG, node)
        self._write_string_field(node.arg)
        self._write_node_field(node.annotation)

    def _s_keyword(self, node):
        self._write_header(TAG_KEYWORD, node)
        self._write_string_field(node.arg)
        self._write_node_field(node.value)

    # ── Public API ──────────────────────────────────────────────────────

    def serialize(self, tree: ast.Module) -> bytes:
        """Serialize an AST tree to bytes."""
        self.buf = BytesIO()
        # Magic header
        self.buf.write(b"MPYA")  # MicroPy AST
        self._serialize(tree)
        return self.buf.getvalue()


# ── Wrapper classes for non-AST structural nodes ────────────────────────
# These let us route withitems, aliases, comprehensions, and match_cases
# through the same dispatch table.

class _WithItemWrapper:
    def __init__(self, item):
        self.item = item

class _AliasWrapper:
    def __init__(self, alias):
        self.alias = alias

class _ComprehensionWrapper:
    def __init__(self, gen):
        self.gen = gen

class _MatchCaseWrapper:
    def __init__(self, case):
        self.case = case


# ── Dispatch table ──────────────────────────────────────────────────────

_DISPATCH = {
    ast.Module:        AstSerializer._s_module,
    ast.FunctionDef:   AstSerializer._s_function_def,
    ast.ClassDef:      AstSerializer._s_class_def,
    ast.Return:        AstSerializer._s_return,
    ast.Raise:         AstSerializer._s_raise,
    ast.Expr:          AstSerializer._s_expr_stmt,
    ast.If:            AstSerializer._s_if,
    ast.While:         AstSerializer._s_while,
    ast.For:           AstSerializer._s_for,
    ast.With:          AstSerializer._s_with,
    ast.Assign:        AstSerializer._s_assign,
    ast.AugAssign:     AstSerializer._s_aug_assign,
    ast.AnnAssign:     AstSerializer._s_ann_assign,
    ast.Assert:        AstSerializer._s_assert,
    ast.Break:         AstSerializer._s_break,
    ast.Continue:      AstSerializer._s_continue,
    ast.Pass:          AstSerializer._s_pass,
    ast.Import:        AstSerializer._s_import,
    ast.ImportFrom:    AstSerializer._s_import_from,
    ast.Constant:      AstSerializer._s_constant,
    ast.Name:          AstSerializer._s_name,
    ast.Call:          AstSerializer._s_call,
    ast.Attribute:     AstSerializer._s_attribute,
    ast.Subscript:     AstSerializer._s_subscript,
    ast.BinOp:        AstSerializer._s_binop,
    ast.UnaryOp:      AstSerializer._s_unaryop,
    ast.BoolOp:       AstSerializer._s_boolop,
    ast.Compare:      AstSerializer._s_compare,
    ast.IfExp:        AstSerializer._s_ifexp,
    ast.Tuple:        AstSerializer._s_tuple,
    ast.List:         AstSerializer._s_list,
    ast.Set:          AstSerializer._s_set,
    ast.Dict:         AstSerializer._s_dict,
    ast.JoinedStr:    AstSerializer._s_joined_str,
    ast.FormattedValue: AstSerializer._s_formatted_value,
    ast.ListComp:     AstSerializer._s_list_comp,
    ast.Lambda:       AstSerializer._s_lambda,
    ast.arguments:    AstSerializer._s_arguments,
    ast.arg:          AstSerializer._s_arg,
    ast.keyword:      AstSerializer._s_keyword,
    _WithItemWrapper:      AstSerializer._s_withitem,
    _AliasWrapper:         AstSerializer._s_alias,
    _ComprehensionWrapper: AstSerializer._s_comprehension,
}

# Match statement nodes (Python 3.10+)
if hasattr(ast, "Match"):
    _DISPATCH[ast.Match]      = AstSerializer._s_match
    _DISPATCH[ast.MatchValue] = AstSerializer._s_match_value
    _DISPATCH[ast.MatchOr]    = AstSerializer._s_match_or
    _DISPATCH[ast.MatchAs]    = AstSerializer._s_match_as
    _DISPATCH[_MatchCaseWrapper] = AstSerializer._s_match_case


# ── Deserializer (Python-side, for round-trip testing) ──────────────────

class AstDeserializer:
    """Deserialize binary AST back to a description dict (for testing)."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def _read_u8(self):
        v = self.data[self.pos]
        self.pos += 1
        return v

    def _read_u16(self):
        v = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def _read_i32(self):
        v = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def _read_i64(self):
        v = struct.unpack_from("<q", self.data, self.pos)[0]
        self.pos += 8
        return v

    def _read_f64(self):
        v = struct.unpack_from("<d", self.data, self.pos)[0]
        self.pos += 8
        return v

    def _read_str(self):
        length = self._read_i32()
        if length < 0:
            return None
        s = self.data[self.pos:self.pos + length].decode("utf-8")
        self.pos += length
        return s

    def _read_field(self):
        """Read a single field (kind byte + value)."""
        kind = self._read_u8()
        if kind == FK_NONE:
            return None
        elif kind == FK_NODE:
            return self._read_node()
        elif kind == FK_NODE_LIST:
            count = self._read_i32()
            return [self._read_field_or_node() for _ in range(count)]
        elif kind == FK_STRING:
            return self._read_str()
        elif kind == FK_INT:
            return self._read_i64()
        elif kind == FK_FLOAT:
            return self._read_f64()
        elif kind == FK_BOOL:
            return bool(self._read_u8())
        elif kind == FK_OP:
            return ("op", self._read_u8())
        else:
            raise ValueError(f"Unknown field kind: {kind}")

    def _read_field_or_node(self):
        """Read either a bare node or a field-prefixed value."""
        # Peek at the next byte to decide
        # In node_list contexts, items are serialized as bare nodes
        return self._read_node()

    def _read_node(self):
        """Read a complete node."""
        tag = self._read_u8()
        lineno = self._read_u16()
        node = {"tag": tag, "lineno": lineno}

        if tag == TAG_MODULE:
            node["body"] = self._read_field()  # node_list
        elif tag == TAG_FUNCTION_DEF:
            node["name"] = self._read_field()  # string
            node["args"] = self._read_node()   # arguments
            node["body"] = self._read_field()  # node_list
            node["decorators"] = self._read_field()  # node_list
            node["returns"] = self._read_field()  # node or none
        elif tag == TAG_CLASS_DEF:
            node["name"] = self._read_field()
            node["bases"] = self._read_field()
            node["keywords"] = self._read_field()
            node["body"] = self._read_field()
            node["decorators"] = self._read_field()
        elif tag == TAG_RETURN:
            node["value"] = self._read_field()
        elif tag == TAG_RAISE:
            node["exc"] = self._read_field()
        elif tag == TAG_EXPR_STMT:
            node["value"] = self._read_field()
        elif tag == TAG_IF:
            node["test"] = self._read_field()
            node["body"] = self._read_field()
            node["orelse"] = self._read_field()
        elif tag == TAG_WHILE:
            node["test"] = self._read_field()
            node["body"] = self._read_field()
        elif tag == TAG_FOR:
            node["target"] = self._read_field()
            node["iter"] = self._read_field()
            node["body"] = self._read_field()
        elif tag == TAG_WITH:
            node["items"] = self._read_field()
            node["body"] = self._read_field()
        elif tag == TAG_ASSIGN:
            node["targets"] = self._read_field()
            node["value"] = self._read_field()
        elif tag == TAG_AUG_ASSIGN:
            node["target"] = self._read_field()
            node["op"] = self._read_field()
            node["value"] = self._read_field()
        elif tag == TAG_ANN_ASSIGN:
            node["target"] = self._read_field()
            node["annotation"] = self._read_field()
            node["value"] = self._read_field()
        elif tag == TAG_ASSERT:
            node["test"] = self._read_field()
            node["msg"] = self._read_field()
        elif tag in (TAG_BREAK, TAG_CONTINUE, TAG_PASS):
            pass  # no fields
        elif tag == TAG_IMPORT:
            node["names"] = self._read_field()
        elif tag == TAG_IMPORT_FROM:
            node["module"] = self._read_field()
            node["names"] = self._read_field()
        elif tag == TAG_MATCH:
            node["subject"] = self._read_field()
            node["cases"] = self._read_field()
        elif tag == TAG_MATCH_CASE:
            node["pattern"] = self._read_field()
            node["guard"] = self._read_field()
            node["body"] = self._read_field()
        elif tag == TAG_MATCH_VALUE:
            node["value"] = self._read_field()
        elif tag == TAG_MATCH_OR:
            node["patterns"] = self._read_field()
        elif tag == TAG_MATCH_AS:
            node["pattern"] = self._read_field()
            node["name"] = self._read_field()
        elif tag == TAG_CONSTANT:
            kind = self._read_u8()
            if kind == 0:  # int
                node["value"] = self._read_field()
            elif kind == 1:  # float
                node["value"] = self._read_field()
            elif kind == 2:  # str
                node["value"] = self._read_field()
            elif kind == 3:  # bool
                node["value"] = self._read_field()
            elif kind == 4:  # none
                node["value"] = None
            elif kind == 5:  # ellipsis
                node["value"] = ...
            node["const_kind"] = kind
        elif tag == TAG_NAME:
            node["id"] = self._read_field()
        elif tag == TAG_CALL:
            node["func"] = self._read_field()
            node["args"] = self._read_field()
            node["keywords"] = self._read_field()
        elif tag == TAG_ATTRIBUTE:
            node["value"] = self._read_field()
            node["attr"] = self._read_field()
        elif tag == TAG_SUBSCRIPT:
            node["value"] = self._read_field()
            node["slice"] = self._read_field()
        elif tag == TAG_BIN_OP:
            node["left"] = self._read_field()
            node["op"] = self._read_field()
            node["right"] = self._read_field()
        elif tag == TAG_UNARY_OP:
            node["op"] = self._read_field()
            node["operand"] = self._read_field()
        elif tag == TAG_BOOL_OP:
            node["op"] = self._read_field()
            node["values"] = self._read_field()
        elif tag == TAG_COMPARE:
            node["left"] = self._read_field()
            op_count = self._read_u8()
            node["ops"] = [self._read_u8() for _ in range(op_count)]
            node["comparators"] = self._read_field()
        elif tag == TAG_IF_EXP:
            node["test"] = self._read_field()
            node["body"] = self._read_field()
            node["orelse"] = self._read_field()
        elif tag in (TAG_TUPLE, TAG_LIST, TAG_SET):
            node["elts"] = self._read_field()
        elif tag == TAG_DICT:
            node["keys"] = self._read_field()
            node["values"] = self._read_field()
        elif tag == TAG_JOINED_STR:
            node["values"] = self._read_field()
        elif tag == TAG_FORMATTED_VAL:
            node["value"] = self._read_field()
            node["conversion"] = self._read_field()
            node["format_spec"] = self._read_field()
        elif tag == TAG_LIST_COMP:
            node["elt"] = self._read_field()
            node["generators"] = self._read_field()
        elif tag == TAG_COMPREHENSION:
            node["target"] = self._read_field()
            node["iter"] = self._read_field()
            node["ifs"] = self._read_field()
        elif tag == TAG_LAMBDA:
            node["args"] = self._read_node()  # arguments
            node["body"] = self._read_field()
        elif tag == TAG_ARGUMENTS:
            node["args"] = self._read_field()
            node["vararg"] = self._read_field()
            node["defaults"] = self._read_field()
        elif tag == TAG_ARG:
            node["arg"] = self._read_field()
            node["annotation"] = self._read_field()
        elif tag == TAG_KEYWORD:
            node["arg"] = self._read_field()
            node["value"] = self._read_field()
        elif tag == TAG_ALIAS:
            node["name"] = self._read_field()
            node["asname"] = self._read_field()
        elif tag == TAG_WITHITEM:
            node["context_expr"] = self._read_field()
            node["optional_vars"] = self._read_field()
        else:
            raise ValueError(f"Unknown tag in deserializer: {tag}")

        return node

    def deserialize(self):
        """Deserialize from binary, return dict tree."""
        magic = self.data[:4]
        if magic != b"MPYA":
            raise ValueError(f"Bad magic: {magic!r}")
        self.pos = 4
        return self._read_node()


# ── Public convenience functions ────────────────────────────────────────

def serialize_ast(tree: ast.Module) -> bytes:
    """Serialize a Python AST to binary format."""
    return AstSerializer().serialize(tree)


def deserialize_ast(data: bytes) -> dict:
    """Deserialize binary AST to a dict tree (for testing)."""
    return AstDeserializer(data).deserialize()
