"nathra"
"""Compiler state struct for the bootstrap compiler.

Centralizes all the state that infer_type, compile_expr, and compile_stmt
need access to. Replaces the Python Compiler dataclass fields.
"""

from nathra_stubs import alloc, free
from strmap import StrMap, StrSet, strmap_new, strmap_free, strmap_get, strmap_set, strmap_has
from strmap import strset_new, strset_free, strset_has, strset_add

# ── Compiler state ──────────────────────────────────────────────────────

class CompilerState:
    # Output buffer
    lines: ptr[NrWriter]
    header: ptr[NrWriter]
    indent: i32

    # Variable scope
    local_vars: StrMap        # name → ctype
    func_args: StrMap         # name → ctype

    # Module-level declarations
    structs: StrMap           # name → ptr[FieldList]
    constants: StrMap         # name → ctype
    mutable_globals: StrMap   # name → ctype
    enums: StrMap             # name → ptr[EnumMembers]

    # Function metadata
    func_ret_types: StrMap    # fname → ret_ctype
    func_param_types: StrMap  # fname → ptr[ParamTypeList]
    func_param_order: StrMap  # fname → ptr[ParamNameList]

    # Specialized tracking
    typed_lists: StrMap       # elem_type → list_name
    array_vars: StrMap        # varname → ptr[ArrayInfo]
    list_vars: StrMap         # varname → elem_type
    funcptr_rettypes: StrMap  # varname → ret_ctype
    struct_array_fields: StrMap # "struct.field" → elem_ctype
    struct_properties: StrMap  # "struct.prop" → ret_type
    result_types: StrMap      # "Result_T" → inner_ctype

    # Sets
    cold_funcs: StrSet
    inline_funcs: StrSet
    extern_funcs: StrSet
    serializable_structs: StrSet
    str_literal_vars: StrSet

    # Module info
    from_imports: StrMap      # local_name → ptr[ImportInfo]
    modules: StrMap           # mod_name → ptr[ModuleInfo]
    current_module: str
    current_func_ret_type: str

    # Flags
    safe_mode: i32
    reorder_funcs: i32
    dce_roots: ptr[StrSet]      # when non-NULL, only emit functions reachable from these roots

    # Counters
    fstr_counter: i32
    lambda_counter: i32
    lc_counter: i32
    try_counter: i32
    thread_spawn_counter: i32

# ── Helper structs for compound values in maps ─────────────────────────

class FieldEntry:
    name: str
    ctype: str

class FieldList:
    entries: ptr[FieldEntry]
    count: i32

class ArrayInfo:
    elem_type: str
    size: str

class ImportInfo:
    module: str
    orig_name: str

class ParamTypeList:
    types: ptr[str]
    count: i32

def param_type_list_new(count: i32) -> ptr[ParamTypeList]:
    """Allocate a ParamTypeList with `count` slots."""
    p: ptr[ParamTypeList] = alloc(16)
    if count > 0:
        p.types = alloc(cast_int(count) * 8)
    else:
        p.types = None
    p.count = count
    return p

class ParamNameList:
    names: ptr[str]
    count: i32

# ── Initialization ─────────────────────────────────────────────────────

def compiler_state_new() -> CompilerState:
    """Create a fresh compiler state with all maps initialized."""
    s: CompilerState = CompilerState(
        None, None, 0,
        strmap_new(64), strmap_new(32),
        strmap_new(32), strmap_new(32), strmap_new(16), strmap_new(16),
        strmap_new(64), strmap_new(64), strmap_new(32),
        strmap_new(16), strmap_new(32), strmap_new(32), strmap_new(16),
        strmap_new(16), strmap_new(16), strmap_new(16),
        strset_new(16), strset_new(16), strset_new(16), strset_new(16), strset_new(16),
        strmap_new(32), strmap_new(16),
        None, None,
        0, 0, None,
        0, 0, 0, 0, 0
    )
    s.lines = writer_new(4096)
    return s

# ── Field list helpers ──────────────────────────────────────────────────

def field_list_new(count: i32) -> ptr[FieldList]:
    fl: ptr[FieldList] = alloc(16)
    fl.entries = alloc(cast_int(count) * 16)
    fl.count = count
    return fl

def field_list_find(fl: ptr[FieldList], name: str) -> str:
    """Find a field by name, return its ctype or NULL."""
    if fl is None:
        return None
    for i in range(fl.count):
        if str_eq(fl.entries[i].name, name):
            return fl.entries[i].ctype
    return None
