#ifndef NATIVE_ANALYSIS_H
#define NATIVE_ANALYSIS_H
#include "micropy_types.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "strmap.h"
#include "strmap.h"
#include "native_compiler_state.h"
int64_t native_analysis__is_alloc_func(const MpStr* name);
int64_t native_analysis__is_free_func(const MpStr* name);
int64_t native_analysis__stmt_is_cold(const AstNode* restrict node, const StrSet* restrict cold_funcs);
int64_t native_analysis__body_is_all_cold(AstNodeList body, StrSet* cold_funcs);
void native_analysis_native_infer_cold_from_body(CompilerState* s, AstNodeList funcs);
int64_t native_analysis__has_alloc_return(AstNodeList body);
int64_t native_analysis__has_free_of_param(AstNodeList body);
void native_analysis_native_build_alloc_tags(CompilerState* s, AstNodeList funcs);
int main(void);
#endif /* NATIVE_ANALYSIS_H */