#ifndef NATIVE_CODEGEN_CALL_H
#define NATIVE_CODEGEN_CALL_H
#include "nathra_types.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "native_compiler_state.h"
#include "native_infer.h"
#include "native_codegen_expr.h"
typedef struct BuiltinEntry BuiltinEntry;
struct BuiltinEntry {
    char* key;
    char* value;
};

int64_t native_codegen_call__is_addressable_lvalue(CompilerState* restrict s, const AstNode* restrict node);
char* native_codegen_call_lookup_builtin(const NrStr* name);
NrStr* native_codegen_call_native_call_type_cast(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_call_ptr_ops(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_call_abs_min_max(CompilerState* restrict s, const NrStr* restrict fname, const AstCall* restrict node, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_call_len(CompilerState* restrict s, const AstCall* restrict node);
NrStr* native_codegen_call_native_call_struct_ctor(CompilerState* restrict s, const NrStr* restrict fname, const NrStr* restrict arg_str);
NrStr* native_codegen_call_native_compile_print(CompilerState* restrict s, const AstCall* restrict pc);
void native_codegen_call__emit_line(CompilerState* restrict s, const NrStr* restrict line);
NrStr* native_codegen_call_native_compile_call(CompilerState* restrict s, const AstNode* restrict node);
int main(void);
extern BuiltinEntry builtin_map[];
#endif /* NATIVE_CODEGEN_CALL_H */