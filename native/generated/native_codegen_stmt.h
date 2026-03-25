#ifndef NATIVE_CODEGEN_STMT_H
#define NATIVE_CODEGEN_STMT_H
#include "micropy_types.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "native_compiler_state.h"
#include "native_infer.h"
#include "native_codegen_expr.h"
#include "native_type_map.h"
void native_codegen_stmt__emit(CompilerState* restrict s, const MpStr* restrict line);
void native_codegen_stmt_native_compile_stmt(CompilerState* restrict s, AstNode* restrict node);
void native_codegen_stmt_native_compile_assert(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_raise(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_aug_assign(CompilerState* restrict s, const AstNode* restrict node);
MpStr* native_codegen_stmt__aug_op_method(uint8_t op);
void native_codegen_stmt_native_compile_return(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_if(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_while(CompilerState* restrict s, const AstNode* restrict node);
MpStr* native_codegen_stmt__infer_cleanup(const MpStr* open_func);
void native_codegen_stmt_native_compile_with(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_assign(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_ann_assign(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_for(CompilerState* restrict s, const AstNode* restrict node);
void native_codegen_stmt_native_compile_match(CompilerState* restrict s, const AstNode* restrict node);
MpStr* native_codegen_stmt__match_pattern_cond(CompilerState* restrict s, MpStr* restrict subject, const AstNode* restrict pattern);
int main(void);
#endif /* NATIVE_CODEGEN_STMT_H */