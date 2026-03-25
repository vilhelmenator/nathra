#ifndef AST_NODES_H
#define AST_NODES_H
#include "micropy_types.h"
typedef struct AstNodeList AstNodeList;
typedef struct AstNode AstNode;
typedef struct AstModule AstModule;
typedef struct AstFunctionDef AstFunctionDef;
typedef struct AstClassDef AstClassDef;
typedef struct AstReturn AstReturn;
typedef struct AstRaise AstRaise;
typedef struct AstExprStmt AstExprStmt;
typedef struct AstIf AstIf;
typedef struct AstWhile AstWhile;
typedef struct AstFor AstFor;
typedef struct AstWith AstWith;
typedef struct AstAssign AstAssign;
typedef struct AstAugAssign AstAugAssign;
typedef struct AstAnnAssign AstAnnAssign;
typedef struct AstAssert AstAssert;
typedef struct AstImport AstImport;
typedef struct AstImportFrom AstImportFrom;
typedef struct AstMatch AstMatch;
typedef struct AstConstant AstConstant;
typedef struct AstName AstName;
typedef struct AstCall AstCall;
typedef struct AstAttribute AstAttribute;
typedef struct AstSubscript AstSubscript;
typedef struct AstBinOp AstBinOp;
typedef struct AstUnaryOp AstUnaryOp;
typedef struct AstBoolOp AstBoolOp;
typedef struct AstCompare AstCompare;
typedef struct AstIfExp AstIfExp;
typedef struct AstTuple AstTuple;
typedef struct AstList AstList;
typedef struct AstSet AstSet;
typedef struct AstDict AstDict;
typedef struct AstJoinedStr AstJoinedStr;
typedef struct AstFormattedValue AstFormattedValue;
typedef struct AstListComp AstListComp;
typedef struct AstLambda AstLambda;
typedef struct AstArguments AstArguments;
typedef struct AstArg AstArg;
typedef struct AstKeyword AstKeyword;
typedef struct AstAlias AstAlias;
typedef struct AstComprehension AstComprehension;
typedef struct AstWithItem AstWithItem;
typedef struct AstMatchCase AstMatchCase;
typedef struct AstMatchValue AstMatchValue;
typedef struct AstMatchOr AstMatchOr;
typedef struct AstMatchAs AstMatchAs;
struct AstNodeList {
    AstNode** items;
    int32_t count;
};

struct AstNode {
    uint8_t tag;
    uint16_t lineno;
    void* data;
};

struct AstModule {
    AstNodeList body;
};

struct AstFunctionDef {
    MpStr* name;
    AstNode* args;
    AstNodeList body;
    AstNodeList decorators;
    AstNode* returns;
};

struct AstClassDef {
    MpStr* name;
    AstNodeList bases;
    AstNodeList keywords;
    AstNodeList body;
    AstNodeList decorators;
};

struct AstReturn {
    AstNode* value;
};

struct AstRaise {
    AstNode* exc;
};

struct AstExprStmt {
    AstNode* value;
};

struct AstIf {
    AstNode* test;
    AstNodeList body;
    AstNodeList orelse;
};

struct AstWhile {
    AstNode* test;
    AstNodeList body;
};

struct AstFor {
    AstNode* target;
    AstNode* iter;
    AstNodeList body;
};

struct AstWith {
    AstNodeList items;
    AstNodeList body;
};

struct AstAssign {
    AstNodeList targets;
    AstNode* value;
};

struct AstAugAssign {
    AstNode* target;
    uint8_t op;
    AstNode* value;
};

struct AstAnnAssign {
    AstNode* target;
    AstNode* annotation;
    AstNode* value;
};

struct AstAssert {
    AstNode* test;
    AstNode* msg;
};

struct AstImport {
    AstNodeList names;
};

struct AstImportFrom {
    MpStr* module;
    AstNodeList names;
};

struct AstMatch {
    AstNode* subject;
    AstNodeList cases;
};

struct AstConstant {
    uint8_t kind;
    int64_t int_val;
    double float_val;
    MpStr* str_val;
};

struct AstName {
    MpStr* id;
};

struct AstCall {
    AstNode* func;
    AstNodeList args;
    AstNodeList keywords;
};

struct AstAttribute {
    AstNode* value;
    MpStr* attr;
};

struct AstSubscript {
    AstNode* value;
    AstNode* slice;
};

struct AstBinOp {
    AstNode* left;
    uint8_t op;
    AstNode* right;
};

struct AstUnaryOp {
    uint8_t op;
    AstNode* operand;
};

struct AstBoolOp {
    uint8_t op;
    AstNodeList values;
};

struct AstCompare {
    AstNode* left;
    uint8_t* ops;
    int32_t op_count;
    AstNodeList comparators;
};

struct AstIfExp {
    AstNode* test;
    AstNode* body;
    AstNode* orelse;
};

struct AstTuple {
    AstNodeList elts;
};

struct AstList {
    AstNodeList elts;
};

struct AstSet {
    AstNodeList elts;
};

struct AstDict {
    AstNodeList keys;
    AstNodeList values;
};

struct AstJoinedStr {
    AstNodeList values;
};

struct AstFormattedValue {
    AstNode* value;
    int64_t conversion;
    AstNode* format_spec;
};

struct AstListComp {
    AstNode* elt;
    AstNodeList generators;
};

struct AstLambda {
    AstNode* args;
    AstNode* body;
};

struct AstArguments {
    AstNodeList args;
    AstNode* vararg;
    AstNodeList defaults;
};

struct AstArg {
    MpStr* name;
    AstNode* annotation;
};

struct AstKeyword {
    MpStr* name;
    AstNode* value;
};

struct AstAlias {
    MpStr* name;
    MpStr* asname;
};

struct AstComprehension {
    AstNode* target;
    AstNode* iter;
    AstNodeList ifs;
};

struct AstWithItem {
    AstNode* context_expr;
    AstNode* optional_vars;
};

struct AstMatchCase {
    AstNode* pattern;
    AstNode* guard;
    AstNodeList body;
};

struct AstMatchValue {
    AstNode* value;
};

struct AstMatchOr {
    AstNodeList patterns;
};

struct AstMatchAs {
    AstNode* pattern;
    MpStr* name;
};

MpStr* ast_nodes_ast_read_str(MpReader* restrict r, MpArena* restrict arena);
AstNode* ast_nodes_ast_read_node(MpReader* restrict r, MpArena* restrict arena);
AstNode* ast_nodes_ast_read_node_field(MpReader* restrict r, MpArena* restrict arena);
AstNodeList ast_nodes_ast_read_node_list(MpReader* restrict r, MpArena* restrict arena);
MpStr* ast_nodes_ast_read_string_field(MpReader* restrict r, MpArena* restrict arena);
int64_t ast_nodes_ast_read_int_field(MpReader* r);
double ast_nodes_ast_read_float_field(MpReader* r);
uint8_t ast_nodes_ast_read_bool_field(MpReader* r);
uint8_t ast_nodes_ast_read_op_field(MpReader* r);
void ast_nodes_ast_read_module(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_function_def(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_class_def(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_return(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_raise(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_expr_stmt(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_if(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_while(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_for(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_with(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_assign(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_aug_assign(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_ann_assign(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_assert(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_import(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_import_from(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_constant(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_name(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_call(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_attribute(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_subscript(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_binop(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_unaryop(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_boolop(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_compare(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_ifexp(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_tuple(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_list(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_set(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_dict(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_joined_str(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_formatted_value(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_list_comp(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_lambda(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_arguments(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_arg(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_keyword(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_alias(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_comprehension(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_withitem(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_case(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_value(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_or(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
void ast_nodes_ast_read_match_as(MpReader* restrict r, MpArena* restrict arena, AstNode* restrict node);
AstNode* ast_nodes_deserialize_ast(const uint8_t* buf, int64_t buf_len);
int64_t ast_nodes_ast_count_nodes(const AstNode* node);
int main(void);
#define TAG_MODULE 0
#define TAG_FUNCTION_DEF 1
#define TAG_CLASS_DEF 2
#define TAG_RETURN 3
#define TAG_RAISE 4
#define TAG_EXPR_STMT 5
#define TAG_IF 6
#define TAG_WHILE 7
#define TAG_FOR 8
#define TAG_WITH 9
#define TAG_ASSIGN 10
#define TAG_AUG_ASSIGN 11
#define TAG_ANN_ASSIGN 12
#define TAG_ASSERT 13
#define TAG_BREAK 14
#define TAG_CONTINUE 15
#define TAG_PASS 16
#define TAG_IMPORT 17
#define TAG_IMPORT_FROM 18
#define TAG_MATCH 19
#define TAG_CONSTANT 30
#define TAG_NAME 31
#define TAG_CALL 32
#define TAG_ATTRIBUTE 33
#define TAG_SUBSCRIPT 34
#define TAG_BIN_OP 35
#define TAG_UNARY_OP 36
#define TAG_BOOL_OP 37
#define TAG_COMPARE 38
#define TAG_IF_EXP 39
#define TAG_TUPLE 40
#define TAG_LIST 41
#define TAG_SET 42
#define TAG_DICT 43
#define TAG_JOINED_STR 44
#define TAG_FORMATTED_VAL 45
#define TAG_LIST_COMP 46
#define TAG_LAMBDA 47
#define TAG_ARGUMENTS 60
#define TAG_ARG 61
#define TAG_KEYWORD 62
#define TAG_ALIAS 63
#define TAG_COMPREHENSION 64
#define TAG_WITHITEM 65
#define TAG_MATCH_CASE 66
#define TAG_MATCH_VALUE 67
#define TAG_MATCH_OR 68
#define TAG_MATCH_AS 69
#define FK_NODE 0
#define FK_NODE_LIST 1
#define FK_STRING 2
#define FK_INT 3
#define FK_FLOAT 4
#define FK_BOOL 5
#define FK_OP 6
#define FK_NONE 7
#define CONST_INT 0
#define CONST_FLOAT 1
#define CONST_STR 2
#define CONST_BOOL 3
#define CONST_NONE 4
#define CONST_ELLIPSIS 5
#define OP_ADD 0
#define OP_SUB 1
#define OP_MULT 2
#define OP_DIV 3
#define OP_MOD 4
#define OP_POW 5
#define OP_FLOOR_DIV 6
#define OP_LSHIFT 7
#define OP_RSHIFT 8
#define OP_BIT_OR 9
#define OP_BIT_XOR 10
#define OP_BIT_AND 11
#define OP_UADD 20
#define OP_USUB 21
#define OP_NOT 22
#define OP_INVERT 23
#define OP_AND 30
#define OP_OR 31
#define OP_EQ 40
#define OP_NOT_EQ 41
#define OP_LT 42
#define OP_LT_E 43
#define OP_GT 44
#define OP_GT_E 45
#define OP_IS 46
#define OP_IS_NOT 47
#define OP_IN 48
#define OP_NOT_IN 49
#endif /* AST_NODES_H */