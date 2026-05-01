#ifndef NATIVE_INFER_H
#define NATIVE_INFER_H
#include "nathra_types.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "native_compiler_state.h"
NrStr* native_infer_native_infer_type(CompilerState* restrict s, AstNode* restrict node);
NrStr* native_infer_native_try_infer_type(CompilerState* restrict s, const AstNode* restrict node);
NrStr* native_infer_native_infer_call_type(CompilerState* restrict s, const AstNode* restrict node);
NrStr* native_infer__strip_ptr(const NrStr* t);
int64_t native_infer__ends_with_star(const NrStr* t);
int64_t native_infer__is_scalar_ptr_base(NrStr* base);
NrStr* native_infer__binop_method_name(uint8_t op);
int main(void);
#endif /* NATIVE_INFER_H */