/* mpy_stamp: 1774564649.180125 */
#include "micropy_rt.h"
#include "native_compiler_state.h"

static inline CompilerState _mp_make_CompilerState(MpWriter* lines, MpWriter* header, int32_t indent, StrMap local_vars, StrMap func_args, StrMap structs, StrMap constants, StrMap mutable_globals, StrMap enums, StrMap func_ret_types, StrMap func_param_types, StrMap func_param_order, StrMap typed_lists, StrMap array_vars, StrMap list_vars, StrMap funcptr_rettypes, StrMap struct_array_fields, StrMap struct_properties, StrMap result_types, StrSet cold_funcs, StrSet extern_funcs, StrSet serializable_structs, StrSet str_literal_vars, StrMap from_imports, StrMap modules, MpStr* current_module, MpStr* current_func_ret_type, int32_t safe_mode, int32_t reorder_funcs, StrSet* dce_roots, int32_t fstr_counter, int32_t lambda_counter, int32_t lc_counter, int32_t try_counter, int32_t thread_spawn_counter) {
    CompilerState _s = {0};
    _s.lines = lines;
    _s.header = header;
    _s.indent = indent;
    _s.local_vars = local_vars;
    _s.func_args = func_args;
    _s.structs = structs;
    _s.constants = constants;
    _s.mutable_globals = mutable_globals;
    _s.enums = enums;
    _s.func_ret_types = func_ret_types;
    _s.func_param_types = func_param_types;
    _s.func_param_order = func_param_order;
    _s.typed_lists = typed_lists;
    _s.array_vars = array_vars;
    _s.list_vars = list_vars;
    _s.funcptr_rettypes = funcptr_rettypes;
    _s.struct_array_fields = struct_array_fields;
    _s.struct_properties = struct_properties;
    _s.result_types = result_types;
    _s.cold_funcs = cold_funcs;
    _s.extern_funcs = extern_funcs;
    _s.serializable_structs = serializable_structs;
    _s.str_literal_vars = str_literal_vars;
    _s.from_imports = from_imports;
    _s.modules = modules;
    _s.current_module = current_module;
    _s.current_func_ret_type = current_func_ret_type;
    _s.safe_mode = safe_mode;
    _s.reorder_funcs = reorder_funcs;
    _s.dce_roots = dce_roots;
    _s.fstr_counter = fstr_counter;
    _s.lambda_counter = lambda_counter;
    _s.lc_counter = lc_counter;
    _s.try_counter = try_counter;
    _s.thread_spawn_counter = thread_spawn_counter;
    return _s;
}

static inline FieldEntry _mp_make_FieldEntry(MpStr* name, MpStr* ctype) {
    FieldEntry _s = {0};
    _s.name = name;
    _s.ctype = ctype;
    return _s;
}

static inline FieldList _mp_make_FieldList(FieldEntry* entries, int32_t count) {
    FieldList _s = {0};
    _s.entries = entries;
    _s.count = count;
    return _s;
}

static inline ArrayInfo _mp_make_ArrayInfo(MpStr* elem_type, MpStr* size) {
    ArrayInfo _s = {0};
    _s.elem_type = elem_type;
    _s.size = size;
    return _s;
}

static inline ImportInfo _mp_make_ImportInfo(MpStr* module, MpStr* orig_name) {
    ImportInfo _s = {0};
    _s.module = module;
    _s.orig_name = orig_name;
    return _s;
}

static inline ParamTypeList _mp_make_ParamTypeList(MpStr** types, int32_t count) {
    ParamTypeList _s = {0};
    _s.types = types;
    _s.count = count;
    return _s;
}

static inline ParamNameList _mp_make_ParamNameList(MpStr** names, int32_t count) {
    ParamNameList _s = {0};
    _s.names = names;
    _s.count = count;
    return _s;
}

CompilerState native_compiler_state_compiler_state_new(void);
FieldList* native_compiler_state_field_list_new(int32_t count);
MpStr* native_compiler_state_field_list_find(const FieldList* restrict fl, const MpStr* restrict name);

CompilerState native_compiler_state_compiler_state_new(void) {
    "Create a fresh compiler state with all maps initialized.";
    {
        CompilerState s = (CompilerState){NULL, NULL, 0, strmap_strmap_new(64), strmap_strmap_new(32), strmap_strmap_new(32), strmap_strmap_new(32), strmap_strmap_new(16), strmap_strmap_new(16), strmap_strmap_new(64), strmap_strmap_new(64), strmap_strmap_new(32), strmap_strmap_new(16), strmap_strmap_new(32), strmap_strmap_new(32), strmap_strmap_new(16), strmap_strmap_new(16), strmap_strmap_new(16), strmap_strmap_new(16), strmap_strset_new(16), strmap_strset_new(16), strmap_strset_new(16), strmap_strset_new(16), strmap_strmap_new(32), strmap_strmap_new(16), NULL, NULL, 0, 0, NULL, 0, 0, 0, 0, 0};
        s.lines = mp_writer_new(4096);
        return s;
    }
}

FieldList* native_compiler_state_field_list_new(int32_t count) {
    FieldList* fl = malloc(16);
    fl->entries = malloc((((int64_t)(count)) * 16));
    fl->count = count;
    return fl;
}

MpStr* native_compiler_state_field_list_find(const FieldList* restrict fl, const MpStr* restrict name) {
    "Find a field by name, return its ctype or NULL.";
    if ((fl == NULL)) {
        return NULL;
    }
    for (int64_t i = 0; i < fl->count; i++) {
        if (mp_str_eq(fl->entries[i].name, name)) {
            return fl->entries[i].ctype;
        }
    }
    return NULL;
}
