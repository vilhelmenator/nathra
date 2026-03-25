/* mpy_stamp: 1774306439.610813 */
#include "micropy_rt.h"
#include "strmap.h"


static inline StrMap _mp_make_StrMap(MpStr** keys, void** values, uint8_t* states, uint32_t* hashes, int32_t count, int32_t cap) {
    StrMap _s = {0};
    _s.keys = keys;
    _s.values = values;
    _s.states = states;
    _s.hashes = hashes;
    _s.count = count;
    _s.cap = cap;
    return _s;
}

static inline StrSet _mp_make_StrSet(MpStr** keys, uint8_t* states, uint32_t* hashes, int32_t count, int32_t cap) {
    StrSet _s = {0};
    _s.keys = keys;
    _s.states = states;
    _s.hashes = hashes;
    _s.count = count;
    _s.cap = cap;
    return _s;
}

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

uint32_t strmap_str_hash(const MpStr* s) {
    "FNV-1a hash of an MpStr.";
    uint64_t h = FNV_OFFSET;
    for (int64_t i = 0; i < mp_str_len(s); i++) {
        h = (h ^ ((uint64_t)(((uint8_t)(s->data[i])))));
        h = (h * FNV_PRIME);
    }
    return ((uint32_t)(h));
}

StrMap strmap_strmap_new(int32_t initial_cap) {
    "Create a new empty hash map.";
    int32_t cap = (int32_t)(16);
    if ((initial_cap > 16)) {
        cap = initial_cap;
    }
    {
        StrMap m = (StrMap){NULL, NULL, NULL, NULL, 0, cap};
        m.keys = malloc((((int64_t)(cap)) * 8));
        m.values = malloc((((int64_t)(cap)) * 8));
        m.states = malloc(((int64_t)(cap)));
        m.hashes = malloc((((int64_t)(cap)) * 4));
        for (int64_t i = 0; i < cap; i++) {
            m.states[i] = EMPTY;
        }
        return m;
    }
}

void strmap_strmap_free(StrMap* m) {
    "Free a hash map's internal storage.";
    free(m->keys);
    free(m->values);
    free(m->states);
    free(m->hashes);
    m->keys = NULL;
    m->values = NULL;
    m->states = NULL;
    m->hashes = NULL;
    m->count = (int32_t)(0);
    m->cap = (int32_t)(0);
}

int32_t strmap__strmap_find_slot(const StrMap* restrict m, const MpStr* restrict key, uint32_t h) {
    "Find the slot for a key (existing or first empty/tombstone).";
    int32_t mask = (int32_t)((m->cap - 1));
    int32_t idx = (int32_t)((((int64_t)(h)) & mask));
    int32_t first_tomb = (int32_t)((-1));
    for (int64_t probe = 0; probe < m->cap; probe++) {
        uint8_t s = m->states[idx];
        if ((s == EMPTY)) {
            if ((first_tomb >= 0)) {
                return first_tomb;
            }
            return idx;
        }
        if ((s == TOMBSTONE)) {
            if ((first_tomb < 0)) {
                first_tomb = idx;
            }
        } else 
        if ((m->hashes[idx] == h)) {
            if (mp_str_eq(m->keys[idx], key)) {
                return idx;
            }
        }
        idx = (int32_t)(((idx + 1) & mask));
    }
    if ((first_tomb >= 0)) {
        return first_tomb;
    }
    return (-1);
}

void strmap_strmap_set(StrMap* restrict m, MpStr* restrict key, void* value) {
    "Insert or update a key-value pair.";
    if (((m->count * 4) >= (m->cap * 3))) {
        strmap__strmap_grow(m);
    }
    uint32_t h = strmap_str_hash(key);
    int32_t idx = strmap__strmap_find_slot(m, key, h);
    if ((m->states[idx] != OCCUPIED)) {
        m->count = (int32_t)((m->count + 1));
    }
    m->keys[idx] = key;
    m->values[idx] = value;
    m->states[idx] = OCCUPIED;
    m->hashes[idx] = h;
}

void strmap__strmap_grow(StrMap* m) {
    "Double the capacity and rehash all entries.";
    MpStr** old_keys = m->keys;
    void** old_values = m->values;
    uint8_t* old_states = m->states;
    uint32_t* old_hashes = m->hashes;
    int32_t old_cap = m->cap;
    int32_t new_cap = (int32_t)((old_cap * 2));
    m->cap = new_cap;
    m->count = (int32_t)(0);
    m->keys = malloc((((int64_t)(new_cap)) * 8));
    m->values = malloc((((int64_t)(new_cap)) * 8));
    m->states = malloc(((int64_t)(new_cap)));
    m->hashes = malloc((((int64_t)(new_cap)) * 4));
    for (int64_t i = 0; i < new_cap; i++) {
        m->states[i] = EMPTY;
    }
    for (int64_t i = 0; i < old_cap; i++) {
        MP_PREFETCH(&old_states[i + 8], 0, 1);
        MP_PREFETCH(&old_keys[i + 8], 0, 1);
        if ((old_states[i] == OCCUPIED)) {
            strmap_strmap_set(m, old_keys[i], old_values[i]);
        }
    }
    free(old_keys);
    free(old_values);
    free(old_states);
    free(old_hashes);
}

void* strmap_strmap_get(const StrMap* restrict m, MpStr* restrict key) {
    "Look up a key. Returns NULL if not found.";
    if ((m->count == 0)) {
        return NULL;
    }
    uint32_t h = strmap_str_hash(key);
    int32_t mask = (int32_t)((m->cap - 1));
    int32_t idx = (int32_t)((((int64_t)(h)) & mask));
    for (int64_t probe = 0; probe < m->cap; probe++) {
        uint8_t s = m->states[idx];
        if ((s == EMPTY)) {
            return NULL;
        }
        if ((s == OCCUPIED)) {
            if ((m->hashes[idx] == h)) {
                if (mp_str_eq(m->keys[idx], key)) {
                    return m->values[idx];
                }
            }
        }
        idx = (int32_t)(((idx + 1) & mask));
    }
    return NULL;
}

int64_t strmap_strmap_has(const StrMap* restrict m, MpStr* restrict key) {
    "Check if a key exists. Returns 1 or 0.";
    if ((m->count == 0)) {
        return 0;
    }
    uint32_t h = strmap_str_hash(key);
    int32_t mask = (int32_t)((m->cap - 1));
    int32_t idx = (int32_t)((((int64_t)(h)) & mask));
    for (int64_t probe = 0; probe < m->cap; probe++) {
        uint8_t s = m->states[idx];
        if ((s == EMPTY)) {
            return 0;
        }
        if ((s == OCCUPIED)) {
            if ((m->hashes[idx] == h)) {
                if (mp_str_eq(m->keys[idx], key)) {
                    return 1;
                }
            }
        }
        idx = (int32_t)(((idx + 1) & mask));
    }
    return 0;
}

int64_t strmap_strmap_delete(StrMap* restrict m, MpStr* restrict key) {
    "Remove a key. Returns 1 if found, 0 if not.";
    if ((m->count == 0)) {
        return 0;
    }
    uint32_t h = strmap_str_hash(key);
    int32_t mask = (int32_t)((m->cap - 1));
    int32_t idx = (int32_t)((((int64_t)(h)) & mask));
    for (int64_t probe = 0; probe < m->cap; probe++) {
        uint8_t s = m->states[idx];
        if ((s == EMPTY)) {
            return 0;
        }
        if ((s == OCCUPIED)) {
            if ((m->hashes[idx] == h)) {
                if (mp_str_eq(m->keys[idx], key)) {
                    m->states[idx] = TOMBSTONE;
                    m->count = (int32_t)((m->count - 1));
                    return 1;
                }
            }
        }
        idx = (int32_t)(((idx + 1) & mask));
    }
    return 0;
}

StrSet strmap_strset_new(int32_t initial_cap) {
    "Create a new empty string set.";
    int32_t cap = (int32_t)(16);
    if ((initial_cap > 16)) {
        cap = initial_cap;
    }
    {
        StrSet s = (StrSet){NULL, NULL, NULL, 0, cap};
        s.keys = malloc((((int64_t)(cap)) * 8));
        s.states = malloc(((int64_t)(cap)));
        s.hashes = malloc((((int64_t)(cap)) * 4));
        for (int64_t i = 0; i < cap; i++) {
            s.states[i] = EMPTY;
        }
        return s;
    }
}

void strmap_strset_free(StrSet* s) {
    "Free a string set's internal storage.";
    free(s->keys);
    free(s->states);
    free(s->hashes);
    s->keys = NULL;
    s->states = NULL;
    s->hashes = NULL;
    s->count = (int32_t)(0);
    s->cap = (int32_t)(0);
}

void strmap_strset_add(StrSet* restrict s, MpStr* restrict key) {
    "Add a key to the set.";
    if (((s->count * 4) >= (s->cap * 3))) {
        strmap__strset_grow(s);
    }
    uint32_t h = strmap_str_hash(key);
    int32_t mask = (int32_t)((s->cap - 1));
    int32_t idx = (int32_t)((((int64_t)(h)) & mask));
    for (int64_t probe = 0; probe < s->cap; probe++) {
        uint8_t st = s->states[idx];
        if (((st == EMPTY) || (st == TOMBSTONE))) {
            s->keys[idx] = key;
            s->states[idx] = OCCUPIED;
            s->hashes[idx] = h;
            s->count = (int32_t)((s->count + 1));
            return;
        }
        if ((s->hashes[idx] == h)) {
            if (mp_str_eq(s->keys[idx], key)) {
                return;
            }
        }
        idx = (int32_t)(((idx + 1) & mask));
    }
}

void strmap__strset_grow(StrSet* s) {
    "Double the capacity and rehash.";
    MpStr** old_keys = s->keys;
    uint8_t* old_states = s->states;
    uint32_t* old_hashes = s->hashes;
    int32_t old_cap = s->cap;
    int32_t new_cap = (int32_t)((old_cap * 2));
    s->cap = new_cap;
    s->count = (int32_t)(0);
    s->keys = malloc((((int64_t)(new_cap)) * 8));
    s->states = malloc(((int64_t)(new_cap)));
    s->hashes = malloc((((int64_t)(new_cap)) * 4));
    for (int64_t i = 0; i < new_cap; i++) {
        s->states[i] = EMPTY;
    }
    for (int64_t i = 0; i < old_cap; i++) {
        MP_PREFETCH(&old_states[i + 8], 0, 1);
        MP_PREFETCH(&old_keys[i + 8], 0, 1);
        if ((old_states[i] == OCCUPIED)) {
            strmap_strset_add(s, old_keys[i]);
        }
    }
    free(old_keys);
    free(old_states);
    free(old_hashes);
}

int64_t strmap_strset_has(const StrSet* restrict s, MpStr* restrict key) {
    "Check if a key is in the set. Returns 1 or 0.";
    if ((s->count == 0)) {
        return 0;
    }
    uint32_t h = strmap_str_hash(key);
    int32_t mask = (int32_t)((s->cap - 1));
    int32_t idx = (int32_t)((((int64_t)(h)) & mask));
    for (int64_t probe = 0; probe < s->cap; probe++) {
        uint8_t st = s->states[idx];
        if ((st == EMPTY)) {
            return 0;
        }
        if ((st == OCCUPIED)) {
            if ((s->hashes[idx] == h)) {
                if (mp_str_eq(s->keys[idx], key)) {
                    return 1;
                }
            }
        }
        idx = (int32_t)(((idx + 1) & mask));
    }
    return 0;
}

int64_t strmap_strset_delete(StrSet* restrict s, MpStr* restrict key) {
    "Remove a key. Returns 1 if found, 0 if not.";
    if ((s->count == 0)) {
        return 0;
    }
    uint32_t h = strmap_str_hash(key);
    int32_t mask = (int32_t)((s->cap - 1));
    int32_t idx = (int32_t)((((int64_t)(h)) & mask));
    for (int64_t probe = 0; probe < s->cap; probe++) {
        uint8_t st = s->states[idx];
        if ((st == EMPTY)) {
            return 0;
        }
        if ((st == OCCUPIED)) {
            if ((s->hashes[idx] == h)) {
                if (mp_str_eq(s->keys[idx], key)) {
                    s->states[idx] = TOMBSTONE;
                    s->count = (int32_t)((s->count - 1));
                    return 1;
                }
            }
        }
        idx = (int32_t)(((idx + 1) & mask));
    }
    return 0;
}
