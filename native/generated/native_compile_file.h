#ifndef NATIVE_COMPILE_FILE_H
#define NATIVE_COMPILE_FILE_H
#include "micropy_types.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "native_compiler_state.h"
#include "native_type_map.h"
#include "native_infer.h"
#include "native_codegen_expr.h"
#include "native_codegen_call.h"
#include "native_codegen_stmt.h"
#include "native_analysis.h"
void native_compile_file__emit(CompilerState* restrict s, const MpStr* restrict line);
void native_compile_file__emit_raw(CompilerState* restrict s, const MpStr* restrict line);
void native_compile_file__first_pass(CompilerState* s, AstNodeList body);
int64_t native_compile_file__has_decorator(const AstFunctionDef* restrict fd, const MpStr* restrict name);
void native_compile_file__scan_typed_lists(CompilerState* s, AstNodeList body);
void native_compile_file__emit_typed_lists(CompilerState* s);
int64_t native_compile_file__has_test_funcs(AstNodeList body);
int64_t native_compile_file__has_variadic_funcs(AstNodeList body);
void native_compile_file__emit_includes(CompilerState* s, AstNodeList body);
void native_compile_file__emit_forward_typedefs(CompilerState* s, AstNodeList body);
void native_compile_file__emit_struct_defs(CompilerState* s, AstNodeList body);
void native_compile_file__emit_enums(CompilerState* s, AstNodeList body);
void native_compile_file__emit_constants(CompilerState* s, AstNodeList body);
void native_compile_file__emit_globals(CompilerState* s, AstNodeList body);
void native_compile_file__emit_function_prototypes(CompilerState* s, AstNodeList body);
int64_t native_compile_file__is_extern_func(const AstFunctionDef* fd);
void native_compile_file__compile_one_func(CompilerState* restrict s, AstFunctionDef* restrict fd, const MpStr* restrict prefix);
MpStr* native_compile_file__edge_key(const MpStr* restrict a, const MpStr* restrict b);
void native_compile_file__walk_calls_weighted(AstNodeList stmts, MpStr* restrict caller, StrSet* restrict func_names, StrMap* restrict edges, int32_t depth, int64_t is_hot);
void native_compile_file__scan_calls_in_node(const AstNode* restrict node, MpStr* restrict caller, StrSet* restrict func_names, StrMap* restrict edges, int32_t depth, int64_t is_hot);
void native_compile_file__reorder_by_call_graph(const AstFunctionDef** restrict funcs, int32_t count, const StrMap* restrict edges, AstFunctionDef** restrict out);
void native_compile_file__dce_find_calls(const AstNode* restrict node, StrSet* restrict all_names, StrSet* restrict reachable, MpStr** restrict work, int32_t* restrict work_count, MpStr* restrict caller);
void native_compile_file__emit_functions(CompilerState* s, AstNodeList body);
void native_compile_file__emit_runtime_impl(CompilerState* s);
int32_t native_compile_file_native_compile(const uint8_t* restrict ast_buf, int64_t ast_len, uint8_t** restrict out_buf, int64_t* restrict out_len);
CompilerState* native_compile_file_native_state_new(void);
int32_t native_compile_file_native_compile_dep(CompilerState* restrict state, const uint8_t* restrict ast_buf, int64_t ast_len, const uint8_t* restrict used_names_buf, int64_t used_names_len, uint8_t** restrict out_c, int64_t* restrict out_c_len, uint8_t** restrict out_h, int64_t* restrict out_h_len);
int32_t native_compile_file_native_compile_main(CompilerState* restrict state, const uint8_t* restrict ast_buf, int64_t ast_len, uint8_t** restrict out_buf, int64_t* restrict out_len);
int main(void);
#endif /* NATIVE_COMPILE_FILE_H */