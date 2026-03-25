#ifndef NATIVE_CODEGEN_CALL_H
#define NATIVE_CODEGEN_CALL_H
#include "micropy_types.h"
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

char* native_codegen_call_lookup_builtin(const MpStr* name);
MpStr* native_codegen_call_native_call_type_cast(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_call_ptr_ops(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_call_abs_min_max(CompilerState* restrict s, const MpStr* restrict fname, const AstCall* restrict node, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_call_len(CompilerState* restrict s, const AstCall* restrict node);
MpStr* native_codegen_call_native_call_struct_ctor(CompilerState* restrict s, const MpStr* restrict fname, const MpStr* restrict arg_str);
MpStr* native_codegen_call_native_compile_print(CompilerState* restrict s, const AstCall* restrict pc);
void native_codegen_call__emit_line(CompilerState* restrict s, const MpStr* restrict line);
MpStr* native_codegen_call_native_compile_call(CompilerState* restrict s, const AstNode* restrict node);
int main(void);
extern BuiltinEntry builtin_map[];
#endif /* NATIVE_CODEGEN_CALL_H */