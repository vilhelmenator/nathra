#ifndef NATIVE_ANALYSIS_H
#define NATIVE_ANALYSIS_H
#include "nathra_types.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "native_compiler_state.h"
int64_t native_analysis__is_alloc_func(const NrStr* name);
int64_t native_analysis__is_free_func(const NrStr* name);
int64_t native_analysis__stmt_is_cold(const AstNode* restrict node, const StrSet* restrict cold_funcs);
int64_t native_analysis__body_is_all_cold(AstNodeList body, StrSet* cold_funcs);
void native_analysis_native_infer_cold_from_body(CompilerState* s, AstNodeList funcs);
int64_t native_analysis__expr_calls_name(const AstNode* restrict e, NrStr* restrict name);
int64_t native_analysis__func_calls_self(AstNodeList body, NrStr* name);
int64_t native_analysis__has_banned_stmt(AstNodeList body);
int64_t native_analysis__is_address_taken(NrStr* name, AstNodeList funcs);
int64_t native_analysis__scan_address_taken(AstNodeList body, NrStr* name);
int64_t native_analysis__call_has_name_arg(const AstNode* restrict call_node, const NrStr* restrict name);
int64_t native_analysis__has_caller(NrStr* name, AstNodeList funcs);
void native_analysis_native_infer_inline_from_body(CompilerState* s, AstNodeList funcs);
int64_t native_analysis__has_alloc_return(AstNodeList body);
int64_t native_analysis__has_free_of_param(AstNodeList body);
void native_analysis_native_build_alloc_tags(CompilerState* s, AstNodeList funcs);
int main(void);
#endif /* NATIVE_ANALYSIS_H */