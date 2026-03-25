#ifndef NATIVE_TYPE_MAP_H
#define NATIVE_TYPE_MAP_H
#include "micropy_types.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "ast_nodes.h"
#include "strmap.h"
typedef struct TypeEntry TypeEntry;
struct TypeEntry {
    char* key;
    char* value;
};

char* native_type_map_lookup_type(const MpStr* name);
void native_type_map_alias_init(void);
void native_type_map_alias_clear(void);
MpStr* native_type_map_mangle_type(const MpStr* ctype);
MpStr* native_type_map_native_map_type(const AstNode* node);
int64_t native_type_map_native_get_array_info(const AstNode* restrict node, MpStr** restrict out_elem, MpStr** restrict out_size);
MpStr* native_type_map_native_get_typed_list_elem(const AstNode* node);
int64_t native_type_map_native_get_funcptr_info(const AstNode* restrict node, MpStr** restrict out_ret, MpStr*** restrict out_args, int32_t* restrict out_argc);
int main(void);
extern TypeEntry type_map_entries[];
extern StrMap* alias_map_ptr;
#endif /* NATIVE_TYPE_MAP_H */