#ifndef NATIVE_INFER_H
#define NATIVE_INFER_H
#include "micropy_types.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "native_compiler_state.h"
MpStr* native_infer_native_infer_type(CompilerState* restrict s, AstNode* restrict node);
MpStr* native_infer_native_infer_call_type(CompilerState* restrict s, const AstNode* restrict node);
MpStr* native_infer__strip_ptr(const MpStr* t);
int64_t native_infer__ends_with_star(const MpStr* t);
MpStr* native_infer__binop_method_name(uint8_t op);
int main(void);
#endif /* NATIVE_INFER_H */