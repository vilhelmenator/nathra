#ifndef NATIVE_COMPILER_STATE_H
#define NATIVE_COMPILER_STATE_H
#include "micropy_types.h"
#include "strmap.h"
typedef struct CompilerState CompilerState;
typedef struct FieldEntry FieldEntry;
typedef struct FieldList FieldList;
typedef struct ArrayInfo ArrayInfo;
typedef struct ImportInfo ImportInfo;
typedef struct ParamTypeList ParamTypeList;
typedef struct ParamNameList ParamNameList;
struct CompilerState {
    MpWriter* lines;
    MpWriter* header;
    int32_t indent;
    StrMap local_vars;
    StrMap func_args;
    StrMap structs;
    StrMap constants;
    StrMap mutable_globals;
    StrMap enums;
    StrMap func_ret_types;
    StrMap func_param_types;
    StrMap func_param_order;
    StrMap typed_lists;
    StrMap array_vars;
    StrMap list_vars;
    StrMap funcptr_rettypes;
    StrMap struct_array_fields;
    StrMap struct_properties;
    StrMap result_types;
    StrSet cold_funcs;
    StrSet extern_funcs;
    StrSet serializable_structs;
    StrSet str_literal_vars;
    StrMap from_imports;
    StrMap modules;
    MpStr* current_module;
    MpStr* current_func_ret_type;
    int32_t fstr_counter;
    int32_t lambda_counter;
    int32_t lc_counter;
    int32_t try_counter;
    int32_t thread_spawn_counter;
};

struct FieldEntry {
    MpStr* name;
    MpStr* ctype;
};

struct FieldList {
    FieldEntry* entries;
    int32_t count;
};

struct ArrayInfo {
    MpStr* elem_type;
    MpStr* size;
};

struct ImportInfo {
    MpStr* module;
    MpStr* orig_name;
};

struct ParamTypeList {
    MpStr** types;
    int32_t count;
};

struct ParamNameList {
    MpStr** names;
    int32_t count;
};

CompilerState native_compiler_state_compiler_state_new(void);
FieldList* native_compiler_state_field_list_new(int32_t count);
MpStr* native_compiler_state_field_list_find(const FieldList* restrict fl, const MpStr* restrict name);
#endif /* NATIVE_COMPILER_STATE_H */