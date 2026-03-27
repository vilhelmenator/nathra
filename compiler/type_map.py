import ast

# ---------------------------------------------------------------------------
# Type mapping
# ---------------------------------------------------------------------------

# User-defined type aliases: populated by the compiler, checked in map_type.
# Cleared at the start of each compile_file() call.
ALIAS_MAP: dict = {}

# Tuple return type names: populated by compiler, cleared per compile_file().
# Maps (ctype, ...) tuple key → struct_name string.
TUPLE_RET_MAP: dict = {}

TYPE_MAP = {
    "int": "int64_t",
    "float": "double",
    "bool": "int",
    "byte": "uint8_t",
    "str": "MpStr*",
    "list": "MpList*",
    "dict": "MpDict*",
    "void": "void",
    "arena": "MpArena*",
    "file": "MpFile",
    "thread": "MpThread",
    "mutex": "MpMutex*",
    "cond": "MpCond*",
    "channel": "MpChannel*",
    "threadpool": "MpThreadPool*",
    "cstr": "char*",
    "va_list": "va_list",
    # Explicit-width numeric types (useful for SIMD / binary data)
    "f32": "float",
    "f64": "double",
    "i8":  "int8_t",
    "i16": "int16_t",
    "i32": "int32_t",
    "i64": "int64_t",
    "u8":  "uint8_t",
    "u16": "uint16_t",
    "u32": "uint32_t",
    "u64": "uint64_t",
}


def _tuple_field_type(annotation, type_map=None) -> str:
    """Like map_type but encodes array[T, N] as 'T[N]' for tuple struct fields."""
    if type_map is None:
        type_map = TYPE_MAP
    if isinstance(annotation, ast.Subscript):
        base = annotation.value
        if isinstance(base, ast.Name) and base.id == "array":
            sl = annotation.slice
            if isinstance(sl, ast.Tuple) and len(sl.elts) == 2:
                elem = map_type(sl.elts[0], type_map)
                size = sl.elts[1].value if isinstance(sl.elts[1], ast.Constant) else 0
                return f"{elem}[{size}]"
    return map_type(annotation, type_map)


def map_type(annotation, type_map=None) -> str:
    if type_map is None:
        type_map = TYPE_MAP
    if annotation is None:
        return "void"
    if isinstance(annotation, ast.Constant):
        if annotation.value is None:
            return "void"
        return str(annotation.value)
    if isinstance(annotation, ast.Name):
        # Check user-defined type aliases first
        if annotation.id in ALIAS_MAP:
            return ALIAS_MAP[annotation.id]
        if annotation.id in type_map:
            return type_map[annotation.id]
        return annotation.id
    if isinstance(annotation, ast.Attribute):
        # mod.TypeName → just use TypeName (structs are shared in C)
        return annotation.attr
    if isinstance(annotation, ast.Subscript):
        base = annotation.value
        if isinstance(base, ast.Name):
            if base.id == "array":
                return "__array__"
            if base.id in ("typed_list", "list"):
                return "__typed_list__"
            if base.id == "dict":
                return "MpDict*"
            if base.id == "ptr":
                inner = map_type(annotation.slice, type_map)
                return f"{inner}*"
            if base.id == "func":
                return "__funcptr__"
            if base.id == "vec":
                return "__vec__"
            if base.id in ("volatile", "atomic"):
                inner = map_type(annotation.slice, type_map)
                return f"volatile {inner}"
            if base.id == "thread_local":
                inner = map_type(annotation.slice, type_map)
                return f"MP_TLS {inner}"
            if base.id == "static":
                inner = map_type(annotation.slice, type_map)
                return f"__static__ {inner}"
            if base.id == "const":
                inner = map_type(annotation.slice, type_map)
                return f"const {inner}"
            if base.id == "bitfield":
                return "__bitfield__"
            if base.id == "backref":
                inner = map_type(annotation.slice, type_map)
                return f"__backref__ {inner}"
            if base.id == "own":
                inner = map_type(annotation.slice, type_map)
                return f"__own__ {inner}"
            if base.id == "Result":
                inner = map_type(annotation.slice, type_map)
                return f"Result_{mangle_type(inner)}"
    if isinstance(annotation, ast.Tuple):
        # Tuple return type — look up in TUPLE_RET_MAP
        key = tuple(_tuple_field_type(e, type_map) for e in annotation.elts)
        if key in TUPLE_RET_MAP:
            return TUPLE_RET_MAP[key]
        # Generate a name and register it
        parts = [k.replace("*", "Ptr").replace(" ", "_").replace("[", "_").replace("]", "") for k in key]
        name = "_TupleRet_" + "_".join(parts)
        TUPLE_RET_MAP[key] = name
        return name
    return "int64_t"


def mangle_type(ctype: str) -> str:
    """Produce a C-identifier-safe name from a C type string."""
    return ctype.replace("*", "Ptr").replace(" ", "_").replace("__", "_")


def get_bitfield_info(annotation):
    """Parse bitfield[T, N] → (ctype, width) or None."""
    if not isinstance(annotation, ast.Subscript):
        return None
    base = annotation.value
    if not (isinstance(base, ast.Name) and base.id == "bitfield"):
        return None
    sl = annotation.slice
    if isinstance(sl, ast.Tuple) and len(sl.elts) == 2:
        ctype = map_type(sl.elts[0])
        width = sl.elts[1].value if isinstance(sl.elts[1], ast.Constant) else 1
        return (ctype, width)
    return None


# Byte sizes of C scalar types used in vec[T, N]
_VEC_ELEM_SIZES = {
    "double": 8, "float": 4,
    "int64_t": 8, "int32_t": 4, "int16_t": 2, "int8_t": 1,
    "uint64_t": 8, "uint32_t": 4, "uint16_t": 2, "uint8_t": 1,
}


def get_vec_info(annotation, type_map=None):
    """Parse vec[T, N] → (elem_ctype, count, vector_size_bytes) or None."""
    if not isinstance(annotation, ast.Subscript):
        return None
    base = annotation.value
    if not (isinstance(base, ast.Name) and base.id == "vec"):
        return None
    sl = annotation.slice
    if not (isinstance(sl, ast.Tuple) and len(sl.elts) == 2):
        return None
    elem_ctype = map_type(sl.elts[0], type_map)
    if not isinstance(sl.elts[1], ast.Constant):
        return None
    count = int(sl.elts[1].value)
    elem_size = _VEC_ELEM_SIZES.get(elem_ctype, 8)
    return elem_ctype, count, count * elem_size


def get_funcptr_info(annotation, type_map=None):
    """Parse func[T1, T2, ..., Ret] → (ret_ctype, [arg_ctypes]) | None."""
    if type_map is None:
        type_map = TYPE_MAP
    if not isinstance(annotation, ast.Subscript):
        return None
    base = annotation.value
    if not (isinstance(base, ast.Name) and base.id == "func"):
        return None
    slc = annotation.slice
    if isinstance(slc, ast.Tuple):
        types = [map_type(e, type_map) for e in slc.elts]
    elif slc is not None:
        types = [map_type(slc, type_map)]
    else:
        return ("void", [])
    if not types:
        return ("void", [])
    ret = types[-1]
    args = types[:-1] if len(types) > 1 else []
    return (ret, args)


def get_array_info(annotation, type_map=None):
    if isinstance(annotation, ast.Subscript):
        sl = annotation.slice
        if isinstance(sl, ast.Tuple) and len(sl.elts) == 2:
            elem_type = map_type(sl.elts[0], type_map)
            size_node = sl.elts[1]
            if isinstance(size_node, ast.Constant):
                size = size_node.value
            elif isinstance(size_node, ast.Name):
                size = size_node.id  # constant name used as array size
            else:
                size = None
            return elem_type, size
        # array[T] without size — inferred from initializer
        if not isinstance(sl, ast.Tuple):
            elem_type = map_type(sl, type_map)
            return elem_type, None
    return "int64_t", 0


def get_typed_list_elem(annotation, type_map=None):
    if isinstance(annotation, ast.Subscript):
        return map_type(annotation.slice, type_map)
    return "int64_t"


# ---------------------------------------------------------------------------
# Typed container generator
# ---------------------------------------------------------------------------

def gen_typed_list(elem_type: str, name_prefix: str) -> str:
    """Generate a specialized list for a specific C type."""
    N = name_prefix  # e.g. "IntList", "Vec2List"
    T = elem_type  # e.g. "int64_t", "Vec2"
    return f"""
/* ---- Typed List: {N} ({T}) ---- */
typedef struct {{
    {T}* data;
    int64_t len;
    int64_t cap;
}} {N};

static inline {N}* {N}_new(void) {{
    {N}* l = ({N}*)malloc(sizeof({N}));
    l->cap = 8; l->len = 0;
    l->data = ({T}*)malloc(sizeof({T}) * l->cap);
    return l;
}}
static inline void {N}_append({N}* l, {T} v) {{
    if (l->len >= l->cap) {{
        l->cap *= 2;
        l->data = ({T}*)realloc(l->data, sizeof({T}) * l->cap);
    }}
    l->data[l->len++] = v;
}}
static inline {T} {N}_get({N}* l, int64_t idx) {{
    if (idx < 0 || idx >= l->len) {{
        fprintf(stderr, "{N}: index %lld out of range (len=%lld)\\n",
                (long long)idx, (long long)l->len);
        exit(1);
    }}
    return l->data[idx];
}}
static inline void {N}_set({N}* l, int64_t idx, {T} v) {{
    if (idx < 0 || idx >= l->len) {{
        fprintf(stderr, "{N}: index %lld out of range (len=%lld)\\n",
                (long long)idx, (long long)l->len);
        exit(1);
    }}
    l->data[idx] = v;
}}
static inline int64_t {N}_len({N}* l) {{ return l->len; }}
static inline {T} {N}_pop({N}* l) {{
    if (l->len == 0) {{ fprintf(stderr, "{N}: pop from empty\\n"); exit(1); }}
    return l->data[--l->len];
}}
static inline void {N}_free({N}* l) {{
    if (l) {{ free(l->data); free(l); }}
}}
"""
