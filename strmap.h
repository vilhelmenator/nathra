#ifndef STRMAP_H
#define STRMAP_H
#include "micropy_types.h"
typedef struct StrMap StrMap;
typedef struct StrSet StrSet;
struct StrMap {
    MpStr** keys;
    void** values;
    uint8_t* states;
    uint32_t* hashes;
    int32_t count;
    int32_t cap;
};

struct StrSet {
    MpStr** keys;
    uint8_t* states;
    uint32_t* hashes;
    int32_t count;
    int32_t cap;
};

uint32_t strmap_str_hash(const MpStr* s);
StrMap strmap_strmap_new(int32_t initial_cap);
void strmap_strmap_free(StrMap* m);
int32_t strmap__strmap_find_slot(const StrMap* restrict m, const MpStr* restrict key, uint32_t h);
void strmap__strmap_grow(StrMap* m);
void strmap_strmap_set(StrMap* restrict m, MpStr* restrict key, void* value);
void* strmap_strmap_get(const StrMap* restrict m, MpStr* restrict key);
int64_t strmap_strmap_has(const StrMap* restrict m, MpStr* restrict key);
int64_t strmap_strmap_delete(StrMap* restrict m, MpStr* restrict key);
StrSet strmap_strset_new(int32_t initial_cap);
void strmap_strset_free(StrSet* s);
void strmap__strset_grow(StrSet* s);
void strmap_strset_add(StrSet* restrict s, MpStr* restrict key);
int64_t strmap_strset_has(const StrSet* restrict s, MpStr* restrict key);
int64_t strmap_strset_delete(StrSet* restrict s, MpStr* restrict key);
int main(void);
#define FNV_OFFSET 14695981039346656037
#define FNV_PRIME 1099511628211
#define EMPTY 0
#define OCCUPIED 1
#define TOMBSTONE 2
#endif /* STRMAP_H */