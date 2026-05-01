/* nth_stamp: 1774911850.084987 */
#include "nathra_rt.h"
#include "ast_nodes.h"


static inline AstNodeList _nr_make_AstNodeList(AstNode** items, int32_t count) {
    AstNodeList _s = {0};
    _s.items = items;
    _s.count = count;
    return _s;
}

static inline AstNode _nr_make_AstNode(uint8_t tag, uint16_t lineno, void* data) {
    AstNode _s = {0};
    _s.tag = tag;
    _s.lineno = lineno;
    _s.data = data;
    return _s;
}

static inline AstModule _nr_make_AstModule(AstNodeList body) {
    AstModule _s = {0};
    _s.body = body;
    return _s;
}

static inline AstFunctionDef _nr_make_AstFunctionDef(NrStr* name, AstNode* args, AstNodeList body, AstNodeList decorators, AstNode* returns) {
    AstFunctionDef _s = {0};
    _s.name = name;
    _s.args = args;
    _s.body = body;
    _s.decorators = decorators;
    _s.returns = returns;
    return _s;
}

static inline AstClassDef _nr_make_AstClassDef(NrStr* name, AstNodeList bases, AstNodeList keywords, AstNodeList body, AstNodeList decorators) {
    AstClassDef _s = {0};
    _s.name = name;
    _s.bases = bases;
    _s.keywords = keywords;
    _s.body = body;
    _s.decorators = decorators;
    return _s;
}

static inline AstReturn _nr_make_AstReturn(AstNode* value) {
    AstReturn _s = {0};
    _s.value = value;
    return _s;
}

static inline AstRaise _nr_make_AstRaise(AstNode* exc) {
    AstRaise _s = {0};
    _s.exc = exc;
    return _s;
}

static inline AstExprStmt _nr_make_AstExprStmt(AstNode* value) {
    AstExprStmt _s = {0};
    _s.value = value;
    return _s;
}

static inline AstIf _nr_make_AstIf(AstNode* test, AstNodeList body, AstNodeList orelse) {
    AstIf _s = {0};
    _s.test = test;
    _s.body = body;
    _s.orelse = orelse;
    return _s;
}

static inline AstWhile _nr_make_AstWhile(AstNode* test, AstNodeList body) {
    AstWhile _s = {0};
    _s.test = test;
    _s.body = body;
    return _s;
}

static inline AstFor _nr_make_AstFor(AstNode* target, AstNode* iter, AstNodeList body) {
    AstFor _s = {0};
    _s.target = target;
    _s.iter = iter;
    _s.body = body;
    return _s;
}

static inline AstWith _nr_make_AstWith(AstNodeList items, AstNodeList body) {
    AstWith _s = {0};
    _s.items = items;
    _s.body = body;
    return _s;
}

static inline AstAssign _nr_make_AstAssign(AstNodeList targets, AstNode* value) {
    AstAssign _s = {0};
    _s.targets = targets;
    _s.value = value;
    return _s;
}

static inline AstAugAssign _nr_make_AstAugAssign(AstNode* target, uint8_t op, AstNode* value) {
    AstAugAssign _s = {0};
    _s.target = target;
    _s.op = op;
    _s.value = value;
    return _s;
}

static inline AstAnnAssign _nr_make_AstAnnAssign(AstNode* target, AstNode* annotation, AstNode* value) {
    AstAnnAssign _s = {0};
    _s.target = target;
    _s.annotation = annotation;
    _s.value = value;
    return _s;
}

static inline AstAssert _nr_make_AstAssert(AstNode* test, AstNode* msg) {
    AstAssert _s = {0};
    _s.test = test;
    _s.msg = msg;
    return _s;
}

static inline AstImport _nr_make_AstImport(AstNodeList names) {
    AstImport _s = {0};
    _s.names = names;
    return _s;
}

static inline AstImportFrom _nr_make_AstImportFrom(NrStr* module, AstNodeList names) {
    AstImportFrom _s = {0};
    _s.module = module;
    _s.names = names;
    return _s;
}

static inline AstMatch _nr_make_AstMatch(AstNode* subject, AstNodeList cases) {
    AstMatch _s = {0};
    _s.subject = subject;
    _s.cases = cases;
    return _s;
}

static inline AstConstant _nr_make_AstConstant(uint8_t kind, int64_t int_val, double float_val, NrStr* str_val) {
    AstConstant _s = {0};
    _s.kind = kind;
    _s.int_val = int_val;
    _s.float_val = float_val;
    _s.str_val = str_val;
    return _s;
}

static inline AstName _nr_make_AstName(NrStr* id) {
    AstName _s = {0};
    _s.id = id;
    return _s;
}

static inline AstCall _nr_make_AstCall(AstNode* func, AstNodeList args, AstNodeList keywords) {
    AstCall _s = {0};
    _s.func = func;
    _s.args = args;
    _s.keywords = keywords;
    return _s;
}

static inline AstAttribute _nr_make_AstAttribute(AstNode* value, NrStr* attr) {
    AstAttribute _s = {0};
    _s.value = value;
    _s.attr = attr;
    return _s;
}

static inline AstSubscript _nr_make_AstSubscript(AstNode* value, AstNode* slice) {
    AstSubscript _s = {0};
    _s.value = value;
    _s.slice = slice;
    return _s;
}

static inline AstBinOp _nr_make_AstBinOp(AstNode* left, uint8_t op, AstNode* right) {
    AstBinOp _s = {0};
    _s.left = left;
    _s.op = op;
    _s.right = right;
    return _s;
}

static inline AstUnaryOp _nr_make_AstUnaryOp(uint8_t op, AstNode* operand) {
    AstUnaryOp _s = {0};
    _s.op = op;
    _s.operand = operand;
    return _s;
}

static inline AstBoolOp _nr_make_AstBoolOp(uint8_t op, AstNodeList values) {
    AstBoolOp _s = {0};
    _s.op = op;
    _s.values = values;
    return _s;
}

static inline AstCompare _nr_make_AstCompare(AstNode* left, uint8_t* ops, int32_t op_count, AstNodeList comparators) {
    AstCompare _s = {0};
    _s.left = left;
    _s.ops = ops;
    _s.op_count = op_count;
    _s.comparators = comparators;
    return _s;
}

static inline AstIfExp _nr_make_AstIfExp(AstNode* test, AstNode* body, AstNode* orelse) {
    AstIfExp _s = {0};
    _s.test = test;
    _s.body = body;
    _s.orelse = orelse;
    return _s;
}

static inline AstTuple _nr_make_AstTuple(AstNodeList elts) {
    AstTuple _s = {0};
    _s.elts = elts;
    return _s;
}

static inline AstList _nr_make_AstList(AstNodeList elts) {
    AstList _s = {0};
    _s.elts = elts;
    return _s;
}

static inline AstSet _nr_make_AstSet(AstNodeList elts) {
    AstSet _s = {0};
    _s.elts = elts;
    return _s;
}

static inline AstDict _nr_make_AstDict(AstNodeList keys, AstNodeList values) {
    AstDict _s = {0};
    _s.keys = keys;
    _s.values = values;
    return _s;
}

static inline AstJoinedStr _nr_make_AstJoinedStr(AstNodeList values) {
    AstJoinedStr _s = {0};
    _s.values = values;
    return _s;
}

static inline AstFormattedValue _nr_make_AstFormattedValue(AstNode* value, int64_t conversion, AstNode* format_spec) {
    AstFormattedValue _s = {0};
    _s.value = value;
    _s.conversion = conversion;
    _s.format_spec = format_spec;
    return _s;
}

static inline AstListComp _nr_make_AstListComp(AstNode* elt, AstNodeList generators) {
    AstListComp _s = {0};
    _s.elt = elt;
    _s.generators = generators;
    return _s;
}

static inline AstLambda _nr_make_AstLambda(AstNode* args, AstNode* body) {
    AstLambda _s = {0};
    _s.args = args;
    _s.body = body;
    return _s;
}

static inline AstArguments _nr_make_AstArguments(AstNodeList args, AstNode* vararg, AstNodeList defaults) {
    AstArguments _s = {0};
    _s.args = args;
    _s.vararg = vararg;
    _s.defaults = defaults;
    return _s;
}

static inline AstArg _nr_make_AstArg(NrStr* name, AstNode* annotation) {
    AstArg _s = {0};
    _s.name = name;
    _s.annotation = annotation;
    return _s;
}

static inline AstKeyword _nr_make_AstKeyword(NrStr* name, AstNode* value) {
    AstKeyword _s = {0};
    _s.name = name;
    _s.value = value;
    return _s;
}

static inline AstAlias _nr_make_AstAlias(NrStr* name, NrStr* asname) {
    AstAlias _s = {0};
    _s.name = name;
    _s.asname = asname;
    return _s;
}

static inline AstComprehension _nr_make_AstComprehension(AstNode* target, AstNode* iter, AstNodeList ifs) {
    AstComprehension _s = {0};
    _s.target = target;
    _s.iter = iter;
    _s.ifs = ifs;
    return _s;
}

static inline AstWithItem _nr_make_AstWithItem(AstNode* context_expr, AstNode* optional_vars) {
    AstWithItem _s = {0};
    _s.context_expr = context_expr;
    _s.optional_vars = optional_vars;
    return _s;
}

static inline AstMatchCase _nr_make_AstMatchCase(AstNode* pattern, AstNode* guard, AstNodeList body) {
    AstMatchCase _s = {0};
    _s.pattern = pattern;
    _s.guard = guard;
    _s.body = body;
    return _s;
}

static inline AstMatchValue _nr_make_AstMatchValue(AstNode* value) {
    AstMatchValue _s = {0};
    _s.value = value;
    return _s;
}

static inline AstMatchOr _nr_make_AstMatchOr(AstNodeList patterns) {
    AstMatchOr _s = {0};
    _s.patterns = patterns;
    return _s;
}

static inline AstMatchAs _nr_make_AstMatchAs(AstNode* pattern, NrStr* name) {
    AstMatchAs _s = {0};
    _s.pattern = pattern;
    _s.name = name;
    return _s;
}

NrStr* ast_nodes_ast_read_str(NrReader* restrict r, NrArena* restrict arena);
AstNode* ast_nodes_ast_read_node(NrReader* restrict r, NrArena* restrict arena);
AstNode* ast_nodes_ast_read_node_field(NrReader* restrict r, NrArena* restrict arena);
AstNodeList ast_nodes_ast_read_node_list(NrReader* restrict r, NrArena* restrict arena);
NrStr* ast_nodes_ast_read_string_field(NrReader* restrict r, NrArena* restrict arena);
int64_t ast_nodes_ast_read_int_field(NrReader* r);
double ast_nodes_ast_read_float_field(NrReader* r);
uint8_t ast_nodes_ast_read_bool_field(NrReader* r);
uint8_t ast_nodes_ast_read_op_field(NrReader* r);
void ast_nodes_ast_read_module(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_function_def(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_class_def(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_return(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_raise(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_expr_stmt(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_if(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_while(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_for(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_with(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_assign(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_aug_assign(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_ann_assign(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_assert(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_import(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_import_from(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_constant(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_name(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_call(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_attribute(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_subscript(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_binop(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_unaryop(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_boolop(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_compare(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_ifexp(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_tuple(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_list(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_set(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_dict(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_joined_str(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_formatted_value(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_list_comp(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_lambda(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_arguments(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_arg(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_keyword(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_alias(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_comprehension(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_withitem(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_case(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_value(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_or(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_as(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node);
AstNode* ast_nodes_deserialize_ast(const uint8_t* buf, int64_t buf_len);
int64_t ast_nodes_ast_count_nodes(const AstNode* node);
int main(void);

NrStr* ast_nodes_ast_read_str(NrReader* restrict r, NrArena* restrict arena) {
    int32_t length = (int32_t)(nr_read_i32(r));
    if ((length < 0)) {
        return NULL;
    }
    uint8_t* buf = malloc((((int64_t)(length)) + 1));
    nr_read_bytes(r, buf, ((int64_t)(length)));
    buf[length] = 0;
    NrStr* s = nr_arena_str_new(arena, buf);
    free(buf);
    return s;
}

NrStr* ast_nodes_ast_read_string_field(NrReader* restrict r, NrArena* restrict arena) {
    "Read FK_STRING prefix + string.";
    uint8_t kind = (uint8_t)(nr_read_u8(r));
    return ast_nodes_ast_read_str(r, arena);
}

AstNodeList ast_nodes_ast_read_node_list(NrReader* restrict r, NrArena* restrict arena) {
    "Read FK_NODE_LIST prefix + count + nodes.";
    uint8_t kind = (uint8_t)(nr_read_u8(r));
    int32_t count = (int32_t)(nr_read_i32(r));
    {
        AstNodeList result = (AstNodeList){NULL, 0};
        if ((count > 0)) {
            result.items = nr_arena_alloc(arena, (((int64_t)(count)) * 8));
            result.count = count;
            for (int64_t i = 0; i < count; i++) {
                result.items[i] = ast_nodes_ast_read_node(r, arena);
            }
        }
        return result;
    }
}

AstNode* ast_nodes_ast_read_node_field(NrReader* restrict r, NrArena* restrict arena) {
    "Read FK_NODE or FK_NONE prefix, then the node.";
    uint8_t kind = (uint8_t)(nr_read_u8(r));
    if ((kind == FK_NONE)) {
        return NULL;
    }
    return ast_nodes_ast_read_node(r, arena);
}

void ast_nodes_ast_read_function_def(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstFunctionDef* p = nr_arena_alloc(arena, sizeof(AstFunctionDef));
    p->name = ast_nodes_ast_read_string_field(r, arena);
    p->args = ast_nodes_ast_read_node(r, arena);
    p->body = ast_nodes_ast_read_node_list(r, arena);
    p->decorators = ast_nodes_ast_read_node_list(r, arena);
    p->returns = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

uint8_t ast_nodes_ast_read_op_field(NrReader* r) {
    "Read FK_OP prefix + op tag.";
    uint8_t kind = (uint8_t)(nr_read_u8(r));
    return nr_read_u8(r);
}

void ast_nodes_ast_read_boolop(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstBoolOp* p = nr_arena_alloc(arena, sizeof(AstBoolOp));
    p->op = ast_nodes_ast_read_op_field(r);
    p->values = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_import_from(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstImportFrom* p = nr_arena_alloc(arena, sizeof(AstImportFrom));
    p->module = ast_nodes_ast_read_string_field(r, arena);
    p->names = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_binop(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstBinOp* p = nr_arena_alloc(arena, sizeof(AstBinOp));
    p->left = ast_nodes_ast_read_node_field(r, arena);
    p->op = ast_nodes_ast_read_op_field(r);
    p->right = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_match_or(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstMatchOr* p = nr_arena_alloc(arena, sizeof(AstMatchOr));
    p->patterns = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_lambda(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstLambda* p = nr_arena_alloc(arena, sizeof(AstLambda));
    p->args = ast_nodes_ast_read_node(r, arena);
    p->body = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_ann_assign(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstAnnAssign* p = nr_arena_alloc(arena, sizeof(AstAnnAssign));
    p->target = ast_nodes_ast_read_node_field(r, arena);
    p->annotation = ast_nodes_ast_read_node_field(r, arena);
    p->value = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_arguments(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstArguments* p = nr_arena_alloc(arena, sizeof(AstArguments));
    p->args = ast_nodes_ast_read_node_list(r, arena);
    p->vararg = ast_nodes_ast_read_node_field(r, arena);
    p->defaults = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_subscript(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstSubscript* p = nr_arena_alloc(arena, sizeof(AstSubscript));
    p->value = ast_nodes_ast_read_node_field(r, arena);
    p->slice = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_raise(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstRaise* p = nr_arena_alloc(arena, sizeof(AstRaise));
    p->exc = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_attribute(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstAttribute* p = nr_arena_alloc(arena, sizeof(AstAttribute));
    p->value = ast_nodes_ast_read_node_field(r, arena);
    p->attr = ast_nodes_ast_read_string_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_match_case(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstMatchCase* p = nr_arena_alloc(arena, sizeof(AstMatchCase));
    p->pattern = ast_nodes_ast_read_node_field(r, arena);
    p->guard = ast_nodes_ast_read_node_field(r, arena);
    p->body = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_name(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstName* p = nr_arena_alloc(arena, sizeof(AstName));
    p->id = ast_nodes_ast_read_string_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_unaryop(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstUnaryOp* p = nr_arena_alloc(arena, sizeof(AstUnaryOp));
    p->op = ast_nodes_ast_read_op_field(r);
    p->operand = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_list(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstList* p = nr_arena_alloc(arena, sizeof(AstList));
    p->elts = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

double ast_nodes_ast_read_float_field(NrReader* r) {
    "Read FK_FLOAT prefix + f64.";
    uint8_t kind = (uint8_t)(nr_read_u8(r));
    return nr_read_f64(r);
}

int64_t ast_nodes_ast_read_int_field(NrReader* r) {
    "Read FK_INT prefix + i64.";
    uint8_t kind = (uint8_t)(nr_read_u8(r));
    return nr_read_i64(r);
}

uint8_t ast_nodes_ast_read_bool_field(NrReader* r) {
    "Read FK_BOOL prefix + bool.";
    uint8_t kind = (uint8_t)(nr_read_u8(r));
    return nr_read_u8(r);
}

void ast_nodes_ast_read_constant(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstConstant* p = nr_arena_alloc(arena, sizeof(AstConstant));
    p->kind = (uint8_t)(nr_read_u8(r));
    p->int_val = 0;
    p->float_val = 0.0;
    p->str_val = NULL;
    switch (p->kind) {
        case 0: {
            p->int_val = ast_nodes_ast_read_int_field(r);
            break;
        }
        case 1: {
            p->float_val = ast_nodes_ast_read_float_field(r);
            break;
        }
        case 2: {
            p->str_val = ast_nodes_ast_read_string_field(r, arena);
            break;
        }
        case 3: {
            p->int_val = ((int64_t)(ast_nodes_ast_read_bool_field(r)));
            break;
        }
        case 4: {
            /* pass */
            break;
        }
        case 5: {
            /* pass */
            break;
        }
    }
    node->data = p;
}

void ast_nodes_ast_read_ifexp(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstIfExp* p = nr_arena_alloc(arena, sizeof(AstIfExp));
    p->test = ast_nodes_ast_read_node_field(r, arena);
    p->body = ast_nodes_ast_read_node_field(r, arena);
    p->orelse = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_match_as(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstMatchAs* p = nr_arena_alloc(arena, sizeof(AstMatchAs));
    p->pattern = ast_nodes_ast_read_node_field(r, arena);
    p->name = ast_nodes_ast_read_string_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_while(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstWhile* p = nr_arena_alloc(arena, sizeof(AstWhile));
    p->test = ast_nodes_ast_read_node_field(r, arena);
    p->body = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_list_comp(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstListComp* p = nr_arena_alloc(arena, sizeof(AstListComp));
    p->elt = ast_nodes_ast_read_node_field(r, arena);
    p->generators = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_import(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstImport* p = nr_arena_alloc(arena, sizeof(AstImport));
    p->names = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_assign(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstAssign* p = nr_arena_alloc(arena, sizeof(AstAssign));
    p->targets = ast_nodes_ast_read_node_list(r, arena);
    p->value = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_expr_stmt(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstExprStmt* p = nr_arena_alloc(arena, sizeof(AstExprStmt));
    p->value = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_tuple(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstTuple* p = nr_arena_alloc(arena, sizeof(AstTuple));
    p->elts = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_match_value(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstMatchValue* p = nr_arena_alloc(arena, sizeof(AstMatchValue));
    p->value = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_aug_assign(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstAugAssign* p = nr_arena_alloc(arena, sizeof(AstAugAssign));
    p->target = ast_nodes_ast_read_node_field(r, arena);
    p->op = ast_nodes_ast_read_op_field(r);
    p->value = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_arg(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstArg* p = nr_arena_alloc(arena, sizeof(AstArg));
    p->name = ast_nodes_ast_read_string_field(r, arena);
    p->annotation = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_withitem(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstWithItem* p = nr_arena_alloc(arena, sizeof(AstWithItem));
    p->context_expr = ast_nodes_ast_read_node_field(r, arena);
    p->optional_vars = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_call(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstCall* p = nr_arena_alloc(arena, sizeof(AstCall));
    p->func = ast_nodes_ast_read_node_field(r, arena);
    p->args = ast_nodes_ast_read_node_list(r, arena);
    p->keywords = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_keyword(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstKeyword* p = nr_arena_alloc(arena, sizeof(AstKeyword));
    p->name = ast_nodes_ast_read_string_field(r, arena);
    p->value = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_assert(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstAssert* p = nr_arena_alloc(arena, sizeof(AstAssert));
    p->test = ast_nodes_ast_read_node_field(r, arena);
    p->msg = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_if(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstIf* p = nr_arena_alloc(arena, sizeof(AstIf));
    p->test = ast_nodes_ast_read_node_field(r, arena);
    p->body = ast_nodes_ast_read_node_list(r, arena);
    p->orelse = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_comprehension(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstComprehension* p = nr_arena_alloc(arena, sizeof(AstComprehension));
    p->target = ast_nodes_ast_read_node_field(r, arena);
    p->iter = ast_nodes_ast_read_node_field(r, arena);
    p->ifs = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_joined_str(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstJoinedStr* p = nr_arena_alloc(arena, sizeof(AstJoinedStr));
    p->values = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_with(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstWith* p = nr_arena_alloc(arena, sizeof(AstWith));
    p->items = ast_nodes_ast_read_node_list(r, arena);
    p->body = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_module(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstModule* p = nr_arena_alloc(arena, sizeof(AstModule));
    p->body = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_compare(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstCompare* p = nr_arena_alloc(arena, sizeof(AstCompare));
    p->left = ast_nodes_ast_read_node_field(r, arena);
    uint8_t op_count = (uint8_t)(nr_read_u8(r));
    p->op_count = (int32_t)(((int64_t)(op_count)));
    p->ops = nr_arena_alloc(arena, ((int64_t)(op_count)));
    for (int64_t i = 0; i < ((int64_t)(op_count)); i++) {
        p->ops[i] = nr_read_u8(r);
    }
    p->comparators = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_return(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstReturn* p = nr_arena_alloc(arena, sizeof(AstReturn));
    p->value = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_alias(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstAlias* p = nr_arena_alloc(arena, sizeof(AstAlias));
    p->name = ast_nodes_ast_read_string_field(r, arena);
    p->asname = ast_nodes_ast_read_string_field(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_set(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstSet* p = nr_arena_alloc(arena, sizeof(AstSet));
    p->elts = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_dict(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstDict* p = nr_arena_alloc(arena, sizeof(AstDict));
    p->keys = ast_nodes_ast_read_node_list(r, arena);
    p->values = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_for(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstFor* p = nr_arena_alloc(arena, sizeof(AstFor));
    p->target = ast_nodes_ast_read_node_field(r, arena);
    p->iter = ast_nodes_ast_read_node_field(r, arena);
    p->body = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_match(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstMatch* p = nr_arena_alloc(arena, sizeof(AstMatch));
    p->subject = ast_nodes_ast_read_node_field(r, arena);
    p->cases = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_class_def(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstClassDef* p = nr_arena_alloc(arena, sizeof(AstClassDef));
    p->name = ast_nodes_ast_read_string_field(r, arena);
    p->bases = ast_nodes_ast_read_node_list(r, arena);
    p->keywords = ast_nodes_ast_read_node_list(r, arena);
    p->body = ast_nodes_ast_read_node_list(r, arena);
    p->decorators = ast_nodes_ast_read_node_list(r, arena);
    node->data = p;
}

void ast_nodes_ast_read_formatted_value(NrReader* restrict r, NrArena* restrict arena, AstNode* restrict node) {
    AstFormattedValue* p = nr_arena_alloc(arena, sizeof(AstFormattedValue));
    p->value = ast_nodes_ast_read_node_field(r, arena);
    p->conversion = ast_nodes_ast_read_int_field(r);
    p->format_spec = ast_nodes_ast_read_node_field(r, arena);
    node->data = p;
}

AstNode* ast_nodes_ast_read_node(NrReader* restrict r, NrArena* restrict arena) {
    uint8_t tag = (uint8_t)(nr_read_u8(r));
    uint16_t lineno = (uint16_t)(nr_read_u16(r));
    AstNode* node = nr_arena_alloc(arena, sizeof(AstNode));
    node->tag = tag;
    node->lineno = lineno;
    node->data = NULL;
    switch (tag) {
        case 0: {
            ast_nodes_ast_read_module(r, arena, node);
            break;
        }
        case 1: {
            ast_nodes_ast_read_function_def(r, arena, node);
            break;
        }
        case 2: {
            ast_nodes_ast_read_class_def(r, arena, node);
            break;
        }
        case 3: {
            ast_nodes_ast_read_return(r, arena, node);
            break;
        }
        case 4: {
            ast_nodes_ast_read_raise(r, arena, node);
            break;
        }
        case 5: {
            ast_nodes_ast_read_expr_stmt(r, arena, node);
            break;
        }
        case 6: {
            ast_nodes_ast_read_if(r, arena, node);
            break;
        }
        case 7: {
            ast_nodes_ast_read_while(r, arena, node);
            break;
        }
        case 8: {
            ast_nodes_ast_read_for(r, arena, node);
            break;
        }
        case 9: {
            ast_nodes_ast_read_with(r, arena, node);
            break;
        }
        case 10: {
            ast_nodes_ast_read_assign(r, arena, node);
            break;
        }
        case 11: {
            ast_nodes_ast_read_aug_assign(r, arena, node);
            break;
        }
        case 12: {
            ast_nodes_ast_read_ann_assign(r, arena, node);
            break;
        }
        case 13: {
            ast_nodes_ast_read_assert(r, arena, node);
            break;
        }
        case 14: {
            /* pass */
            break;
        }
        case 15: {
            /* pass */
            break;
        }
        case 16: {
            /* pass */
            break;
        }
        case 17: {
            ast_nodes_ast_read_import(r, arena, node);
            break;
        }
        case 18: {
            ast_nodes_ast_read_import_from(r, arena, node);
            break;
        }
        case 19: {
            ast_nodes_ast_read_match(r, arena, node);
            break;
        }
        case 30: {
            ast_nodes_ast_read_constant(r, arena, node);
            break;
        }
        case 31: {
            ast_nodes_ast_read_name(r, arena, node);
            break;
        }
        case 32: {
            ast_nodes_ast_read_call(r, arena, node);
            break;
        }
        case 33: {
            ast_nodes_ast_read_attribute(r, arena, node);
            break;
        }
        case 34: {
            ast_nodes_ast_read_subscript(r, arena, node);
            break;
        }
        case 35: {
            ast_nodes_ast_read_binop(r, arena, node);
            break;
        }
        case 36: {
            ast_nodes_ast_read_unaryop(r, arena, node);
            break;
        }
        case 37: {
            ast_nodes_ast_read_boolop(r, arena, node);
            break;
        }
        case 38: {
            ast_nodes_ast_read_compare(r, arena, node);
            break;
        }
        case 39: {
            ast_nodes_ast_read_ifexp(r, arena, node);
            break;
        }
        case 40: {
            ast_nodes_ast_read_tuple(r, arena, node);
            break;
        }
        case 41: {
            ast_nodes_ast_read_list(r, arena, node);
            break;
        }
        case 42: {
            ast_nodes_ast_read_set(r, arena, node);
            break;
        }
        case 43: {
            ast_nodes_ast_read_dict(r, arena, node);
            break;
        }
        case 44: {
            ast_nodes_ast_read_joined_str(r, arena, node);
            break;
        }
        case 45: {
            ast_nodes_ast_read_formatted_value(r, arena, node);
            break;
        }
        case 46: {
            ast_nodes_ast_read_list_comp(r, arena, node);
            break;
        }
        case 47: {
            ast_nodes_ast_read_lambda(r, arena, node);
            break;
        }
        case 60: {
            ast_nodes_ast_read_arguments(r, arena, node);
            break;
        }
        case 61: {
            ast_nodes_ast_read_arg(r, arena, node);
            break;
        }
        case 62: {
            ast_nodes_ast_read_keyword(r, arena, node);
            break;
        }
        case 63: {
            ast_nodes_ast_read_alias(r, arena, node);
            break;
        }
        case 64: {
            ast_nodes_ast_read_comprehension(r, arena, node);
            break;
        }
        case 65: {
            ast_nodes_ast_read_withitem(r, arena, node);
            break;
        }
        case 66: {
            ast_nodes_ast_read_match_case(r, arena, node);
            break;
        }
        case 67: {
            ast_nodes_ast_read_match_value(r, arena, node);
            break;
        }
        case 68: {
            ast_nodes_ast_read_match_or(r, arena, node);
            break;
        }
        case 69: {
            ast_nodes_ast_read_match_as(r, arena, node);
            break;
        }
    }
    return node;
}

AstNode* ast_nodes_deserialize_ast(const uint8_t* buf, int64_t buf_len) {
    "Deserialize binary AST buffer into native node tree.\n\n    All memory is arena-allocated. Caller receives the root node.\n    ";
    NrArena* arena = nr_arena_new((buf_len * 64));
    NrReader* r = nr_reader_new((buf + 4), (buf_len - 4));
    AstNode* root = ast_nodes_ast_read_node(r, arena);
    return root;
}

int64_t ast_nodes_ast_count_nodes(const AstNode* node) {
    "Count total nodes in tree (for validation).";
    if ((node == NULL)) {
        return 0;
    }
    int64_t count = 1;
    if ((node->tag == TAG_MODULE)) {
        AstModule* p = node->data;
        for (int64_t i = 0; i < p->body.count; i++) {
            count = (count + ast_nodes_ast_count_nodes(p->body.items[i]));
        }
    } else 
    if ((node->tag == TAG_FUNCTION_DEF)) {
        AstFunctionDef* p2 = node->data;
        count = (count + ast_nodes_ast_count_nodes(p2->args));
        for (int64_t i = 0; i < p2->body.count; i++) {
            count = (count + ast_nodes_ast_count_nodes(p2->body.items[i]));
        }
        for (int64_t i = 0; i < p2->decorators.count; i++) {
            count = (count + ast_nodes_ast_count_nodes(p2->decorators.items[i]));
        }
        count = (count + ast_nodes_ast_count_nodes(p2->returns));
    } else 
    if ((node->tag == TAG_CALL)) {
        AstCall* p3 = node->data;
        count = (count + ast_nodes_ast_count_nodes(p3->func));
        for (int64_t i = 0; i < p3->args.count; i++) {
            count = (count + ast_nodes_ast_count_nodes(p3->args.items[i]));
        }
    } else 
    if ((node->tag == TAG_BIN_OP)) {
        AstBinOp* p4 = node->data;
        count = ((count + ast_nodes_ast_count_nodes(p4->left)) + ast_nodes_ast_count_nodes(p4->right));
    } else 
    if ((node->tag == TAG_RETURN)) {
        AstReturn* p5 = node->data;
        count = (count + ast_nodes_ast_count_nodes(p5->value));
    } else 
    if ((node->tag == TAG_EXPR_STMT)) {
        AstExprStmt* p6 = node->data;
        count = (count + ast_nodes_ast_count_nodes(p6->value));
    } else 
    if ((node->tag == TAG_ANN_ASSIGN)) {
        AstAnnAssign* p7 = node->data;
        count = (count + ast_nodes_ast_count_nodes(p7->target));
        count = (count + ast_nodes_ast_count_nodes(p7->annotation));
        count = (count + ast_nodes_ast_count_nodes(p7->value));
    } else 
    if ((node->tag == TAG_ARGUMENTS)) {
        AstArguments* p8 = node->data;
        for (int64_t i = 0; i < p8->args.count; i++) {
            count = (count + ast_nodes_ast_count_nodes(p8->args.items[i]));
        }
        count = (count + ast_nodes_ast_count_nodes(p8->vararg));
    } else 
    if ((node->tag == TAG_ARG)) {
        AstArg* p9 = node->data;
        count = (count + ast_nodes_ast_count_nodes(p9->annotation));
    }
    return count;
}
