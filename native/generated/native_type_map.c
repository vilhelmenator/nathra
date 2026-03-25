/* mpy_stamp: 1774464469.955419 */
#include "micropy_rt.h"
#include "native_type_map.h"

static inline TypeEntry _mp_make_TypeEntry(char* key, char* value) {
    TypeEntry _s = {0};
    _s.key = key;
    _s.value = value;
    return _s;
}

TypeEntry type_map_entries[28] = {(TypeEntry){"int", "int64_t"}, (TypeEntry){"float", "double"}, (TypeEntry){"bool", "int"}, (TypeEntry){"byte", "uint8_t"}, (TypeEntry){"str", "MpStr*"}, (TypeEntry){"list", "MpList*"}, (TypeEntry){"dict", "MpDict*"}, (TypeEntry){"void", "void"}, (TypeEntry){"arena", "MpArena*"}, (TypeEntry){"file", "MpFile"}, (TypeEntry){"thread", "MpThread"}, (TypeEntry){"mutex", "MpMutex*"}, (TypeEntry){"cond", "MpCond*"}, (TypeEntry){"channel", "MpChannel*"}, (TypeEntry){"threadpool", "MpThreadPool*"}, (TypeEntry){"cstr", "char*"}, (TypeEntry){"va_list", "va_list"}, (TypeEntry){"f32", "float"}, (TypeEntry){"f64", "double"}, (TypeEntry){"i8", "int8_t"}, (TypeEntry){"i16", "int16_t"}, (TypeEntry){"i32", "int32_t"}, (TypeEntry){"i64", "int64_t"}, (TypeEntry){"u8", "uint8_t"}, (TypeEntry){"u16", "uint16_t"}, (TypeEntry){"u32", "uint32_t"}, (TypeEntry){"u64", "uint64_t"}, (TypeEntry){"", ""}};
StrMap* alias_map_ptr = NULL;

char* native_type_map_lookup_type(const MpStr* name);
void native_type_map_alias_init(void);
void native_type_map_alias_clear(void);
MpStr* native_type_map_mangle_type(const MpStr* ctype);
MpStr* native_type_map_native_map_type(const AstNode* node);
int64_t native_type_map_native_get_array_info(const AstNode* restrict node, MpStr** restrict out_elem, MpStr** restrict out_size);
MpStr* native_type_map_native_get_typed_list_elem(const AstNode* node);
int64_t native_type_map_native_get_funcptr_info(const AstNode* restrict node, MpStr** restrict out_ret, MpStr*** restrict out_args, int32_t* restrict out_argc);
int main(void);

char* native_type_map_lookup_type(const MpStr* name) {
    "Look up a type name in the static type map. Returns NULL if not found.";
    int32_t i = (int32_t)(0);
    while ((type_map_entries[i].key[0] != 0)) {
        if ((strcmp(name->data, type_map_entries[i].key) == 0)) {
            return type_map_entries[i].value;
        }
        i = (int32_t)((i + 1));
    }
    return NULL;
}

void native_type_map_alias_init(void) {
    alias_map_ptr = malloc(48);
    {
        StrMap m = strmap_strmap_new(16);
        *(((StrMap*)(alias_map_ptr))) = m;
        (void)0;
    }
}

void native_type_map_alias_clear(void) {
    if ((alias_map_ptr != NULL)) {
        strmap_strmap_free(alias_map_ptr);
        StrMap m = strmap_strmap_new(16);
        *(((StrMap*)(alias_map_ptr))) = m;
        (void)0;
    }
}

MpStr* native_type_map_mangle_type(const MpStr* ctype) {
    "Produce a C-identifier-safe name from a C type string.";
    int64_t len = mp_str_len(ctype);
    uint8_t* buf = malloc(((len * 2) + 1));
    int64_t j = 0;
    int64_t prev_underscore = 0;
    for (int64_t i = 0; i < len; i++) {
        uint8_t ch = (uint8_t)(((uint8_t)(ctype->data[i])));
        if ((ch == 42)) {
            buf[j] = 80;
            buf[(j + 1)] = 116;
            buf[(j + 2)] = 114;
            j = (j + 3);
            prev_underscore = 0;
        } else 
        if ((ch == 32)) {
            if ((prev_underscore == 0)) {
                buf[j] = 95;
                j = (j + 1);
                prev_underscore = 1;
            }
        } else 
        if ((ch == 95)) {
            if ((prev_underscore == 0)) {
                buf[j] = 95;
                j = (j + 1);
                prev_underscore = 1;
            }
        } else {
            buf[j] = ch;
            j = (j + 1);
            prev_underscore = 0;
        }
    }
    buf[j] = 0;
    MpStr* result = mp_str_new(buf);
    free(buf);
    return result;
}

MpStr* native_type_map_native_map_type(const AstNode* node) {
    "Map an AST annotation node to a C type string.";
    if ((node == NULL)) {
        return mp_str_new("void");
    }
    if ((node->tag == TAG_CONSTANT)) {
        AstConstant* p = node->data;
        if ((p->kind == CONST_NONE)) {
            return mp_str_new("void");
        }
        return mp_str_from_int(p->int_val);
    }
    if ((node->tag == TAG_NAME)) {
        AstName* p2 = node->data;
        if ((alias_map_ptr != NULL)) {
            MpStr* alias = strmap_strmap_get(alias_map_ptr, p2->id);
            if ((alias != NULL)) {
                return alias;
            }
        }
        char* mapped = native_type_map_lookup_type(p2->id);
        if ((mapped != NULL)) {
            return mp_str_new(mapped);
        }
        return p2->id;
    }
    if ((node->tag == TAG_ATTRIBUTE)) {
        AstAttribute* p3 = node->data;
        return p3->attr;
    }
    if ((node->tag == TAG_SUBSCRIPT)) {
        AstSubscript* p4 = node->data;
        AstNode* base = p4->value;
        if ((base->tag == TAG_NAME)) {
            AstName* base_name = base->data;
            MpStr* name = base_name->id;
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"array",.len=5}))) {
                return mp_str_new("__array__");
            }
            if ((mp_str_eq(name, (&(MpStr){.data=(char*)"typed_list",.len=10})) || mp_str_eq(name, (&(MpStr){.data=(char*)"list",.len=4})))) {
                return mp_str_new("__typed_list__");
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"dict",.len=4}))) {
                return mp_str_new("MpDict*");
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"ptr",.len=3}))) {
                MpStr* inner = native_type_map_native_map_type(p4->slice);
                return mp_str_concat(inner, (&(MpStr){.data=(char*)"*",.len=1}));
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"func",.len=4}))) {
                return mp_str_new("__funcptr__");
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"vec",.len=3}))) {
                return mp_str_new("__vec__");
            }
            if ((mp_str_eq(name, (&(MpStr){.data=(char*)"volatile",.len=8})) || mp_str_eq(name, (&(MpStr){.data=(char*)"atomic",.len=6})))) {
                MpStr* inner2 = native_type_map_native_map_type(p4->slice);
                return mp_str_concat((&(MpStr){.data=(char*)"volatile ",.len=9}), inner2);
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"thread_local",.len=12}))) {
                MpStr* inner3 = native_type_map_native_map_type(p4->slice);
                return mp_str_concat((&(MpStr){.data=(char*)"MP_TLS ",.len=7}), inner3);
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"static",.len=6}))) {
                MpStr* inner4 = native_type_map_native_map_type(p4->slice);
                return mp_str_concat((&(MpStr){.data=(char*)"__static__ ",.len=11}), inner4);
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"const",.len=5}))) {
                MpStr* inner5 = native_type_map_native_map_type(p4->slice);
                return mp_str_concat((&(MpStr){.data=(char*)"const ",.len=6}), inner5);
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"bitfield",.len=8}))) {
                return mp_str_new("__bitfield__");
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"backref",.len=7}))) {
                MpStr* inner6 = native_type_map_native_map_type(p4->slice);
                return mp_str_concat((&(MpStr){.data=(char*)"__backref__ ",.len=12}), inner6);
            }
            if (mp_str_eq(name, (&(MpStr){.data=(char*)"Result",.len=6}))) {
                MpStr* inner7 = native_type_map_native_map_type(p4->slice);
                MpStr* mangled = native_type_map_mangle_type(inner7);
                return mp_str_concat((&(MpStr){.data=(char*)"Result_",.len=7}), mangled);
            }
        }
    }
    if ((node->tag == TAG_TUPLE)) {
        return mp_str_new("__tuple_ret__");
    }
    return mp_str_new("int64_t");
}

int64_t native_type_map_native_get_array_info(const AstNode* restrict node, MpStr** restrict out_elem, MpStr** restrict out_size) {
    "Parse array[T, N] → elem type and size string. Returns 1 on success.";
    if (((node == NULL) || (node->tag != TAG_SUBSCRIPT))) {
        return 0;
    }
    AstSubscript* p = node->data;
    AstNode* slice = p->slice;
    if (((slice == NULL) || (slice->tag != TAG_TUPLE))) {
        return 0;
    }
    AstTuple* tup = slice->data;
    if ((tup->elts.count != 2)) {
        return 0;
    }
    *(out_elem) = native_type_map_native_map_type(tup->elts.items[0]);
    (void)0;
    AstNode* size_node = tup->elts.items[1];
    if ((size_node->tag == TAG_CONSTANT)) {
        AstConstant* sc = size_node->data;
        *(out_size) = mp_str_from_int(sc->int_val);
        (void)0;
    } else 
    if ((size_node->tag == TAG_NAME)) {
        AstName* sn = size_node->data;
        *(out_size) = sn->id;
        (void)0;
    } else {
        *(out_size) = mp_str_new("0");
        (void)0;
    }
    return 1;
}

MpStr* native_type_map_native_get_typed_list_elem(const AstNode* node) {
    "Parse typed_list[T] or list[T] → element C type.";
    if (((node == NULL) || (node->tag != TAG_SUBSCRIPT))) {
        return mp_str_new("int64_t");
    }
    AstSubscript* p = node->data;
    return native_type_map_native_map_type(p->slice);
}

int64_t native_type_map_native_get_funcptr_info(const AstNode* restrict node, MpStr** restrict out_ret, MpStr*** restrict out_args, int32_t* restrict out_argc) {
    "Parse func[T1, T2, ..., Ret] → ret type + arg types. Returns 1 on success.";
    if (((node == NULL) || (node->tag != TAG_SUBSCRIPT))) {
        return 0;
    }
    AstSubscript* p = node->data;
    AstNode* base = p->value;
    if (((base == NULL) || (base->tag != TAG_NAME))) {
        return 0;
    }
    AstName* bn = base->data;
    if ((bn->id == "func") && ("func" == 0)) {
        return 0;
    }
    AstNode* slice = p->slice;
    if ((slice == NULL)) {
        *(out_ret) = mp_str_new("void");
        (void)0;
        *(out_argc) = 0;
        (void)0;
        return 1;
    }
    if ((slice->tag == TAG_TUPLE)) {
        AstTuple* tup = slice->data;
        int32_t count = tup->elts.count;
        if ((count == 0)) {
            *(out_ret) = mp_str_new("void");
            (void)0;
            *(out_argc) = 0;
            (void)0;
            return 1;
        }
        *(out_ret) = native_type_map_native_map_type(tup->elts.items[(count - 1)]);
        (void)0;
        int32_t arg_count = (int32_t)((count - 1));
        *(out_argc) = arg_count;
        (void)0;
        if ((arg_count > 0)) {
            MpStr** args = malloc((((int64_t)(arg_count)) * 8));
            for (int64_t i = 0; i < arg_count; i++) {
                MP_PREFETCH(&args[i + 8], 0, 1);
                args[i] = native_type_map_native_map_type(tup->elts.items[i]);
            }
            *(out_args) = args;
            (void)0;
        }
        return 1;
    } else {
        *(out_ret) = native_type_map_native_map_type(slice);
        (void)0;
        *(out_argc) = 0;
        (void)0;
        return 1;
    }
}
