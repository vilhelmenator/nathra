#ifndef NATIVE_CODEGEN_EXPR_H
#define NATIVE_CODEGEN_EXPR_H
#include "micropy_types.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "native_compiler_state.h"
#include "native_infer.h"
MpStr* native_codegen_expr_native_compile_op(uint8_t op);
MpStr* native_codegen_expr_native_compile_cmpop(uint8_t op);
MpStr* native_codegen_expr__escape_str(const MpStr* s);
MpStr* native_codegen_expr__binop_method(uint8_t op);
MpStr* native_codegen_expr__cmpop_method(uint8_t op);
void native_codegen_expr__emit(CompilerState* restrict s, const MpStr* restrict line);
MpStr* native_codegen_expr_native_compile_expr(CompilerState* restrict s, const AstNode* restrict node);
int main(void);
#endif /* NATIVE_CODEGEN_EXPR_H */