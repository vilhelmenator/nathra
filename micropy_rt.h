
#ifndef MICROPY_RT_H
#define MICROPY_RT_H

#include "micropy_types.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdarg.h>
#include <time.h>
#include <math.h>

#ifdef _WIN32
#include <windows.h>
#include <malloc.h>   /* alloca on MSVC/clang-cl */
/* Undefine any conflicting Windows macros */
#ifdef Rectangle
#undef Rectangle
#endif
#endif

struct MpList {
    MpVal* data;
    int64_t len;
    int64_t cap;
};

struct MpDictEntry {
    char* key;
    MpVal val;
    int used;
};

struct MpDict {
    MpDictEntry* entries;
    int64_t cap;
    int64_t len;
};

struct MpStr {
    char* data;
    int64_t len;
};

/* -------------------------------------------------------------------------
 * Debug allocation tracking — active only when compiled with -DMICROPY_DEBUG.
 *
 * Every malloc/free call in the program (including runtime internals) is
 * routed through the wrappers below, which increment/decrement a shared
 * counter and print a trace line to stderr.
 *
 * The counter is defined once in the main translation unit by the compiler
 * when --debug is set.  At program exit an atexit-registered function asserts
 * the counter is zero, confirming no allocations leaked.
 *
 * Important: the wrapper function bodies are written before the #define
 * macros, so they call the REAL libc malloc/free — no recursion.
 * ------------------------------------------------------------------------- */
#ifdef MICROPY_DEBUG
static inline void* _mp_debug_alloc(size_t n, const char* file, int line) {
    void* p = malloc(n);
    if (p) {
        _mp_alloc_count++;
        fprintf(stderr, "[alloc +%lld]  %s:%d\n",
                (long long)_mp_alloc_count, file, line);
    }
    return p;
}
static inline void _mp_debug_free(void* p, const char* file, int line) {
    if (!p) return;
    _mp_alloc_count--;
    fprintf(stderr, "[free   %lld]  %s:%d\n",
            (long long)_mp_alloc_count, file, line);
    free(p);
}
static inline void _mp_alloc_assert_zero(void) {
    if (_mp_alloc_count != 0)
        fprintf(stderr, "\n[MEMORY] LEAK: %lld live allocation(s) at exit\n",
                (long long)_mp_alloc_count);
    else
        fprintf(stderr, "\n[MEMORY] OK — all allocations freed\n");
}
/* Override malloc/free — must come AFTER the wrapper definitions above */
#  define malloc(n)  _mp_debug_alloc((n), __FILE__, __LINE__)
#  define free(p)    _mp_debug_free((p),  __FILE__, __LINE__)
#else
#  define _mp_alloc_assert_zero() ((void)0)
#endif

static inline MpVal mp_val_int(int64_t v) { MpVal r; memcpy(&r, &v, 8); return r; }
static inline MpVal mp_val_float(double v) { MpVal r; memcpy(&r, &v, 8); return r; }
static inline int64_t mp_as_int(MpVal v) { int64_t r; memcpy(&r, &v, 8); return r; }
static inline double mp_as_float(MpVal v) { double r; memcpy(&r, &v, 8); return r; }

static inline void mp_print_int(int64_t v) { printf("%lld\n", (long long)v); }
static inline void mp_print_float(double v) { printf("%.6f\n", v); }
static inline void mp_print_bool(int v) { printf("%s\n", v ? "True" : "False"); }
static inline void mp_print_str(MpStr* s) { if (s) printf("%.*s\n", (int)s->len, s->data); }
static inline void mp_print_val(MpVal v) { printf("%lld\n", (long long)mp_as_int(v)); }

static inline MpList* mp_list_new(void) {
    MpList* l = (MpList*)malloc(sizeof(MpList));
    l->cap = 8; l->len = 0;
    l->data = (MpVal*)malloc(sizeof(MpVal) * l->cap);
    return l;
}
static inline void mp_list_append(MpList* l, MpVal v) {
    if (l->len >= l->cap) { l->cap *= 2; l->data = (MpVal*)realloc(l->data, sizeof(MpVal) * l->cap); }
    l->data[l->len++] = v;
}
static inline MpVal mp_list_get(MpList* l, int64_t idx) {
    if (idx < 0 || idx >= l->len) { fprintf(stderr, "Index %lld out of range\n", (long long)idx); exit(1); }
    return l->data[idx];
}
static inline void mp_list_set(MpList* l, int64_t idx, MpVal v) {
    if (idx < 0 || idx >= l->len) { fprintf(stderr, "Index %lld out of range\n", (long long)idx); exit(1); }
    l->data[idx] = v;
}
static inline int64_t mp_list_len(MpList* l) { return l->len; }
static inline MpVal mp_list_pop(MpList* l) {
    if (l->len == 0) { fprintf(stderr, "Pop from empty list\n"); exit(1); }
    return l->data[--l->len];
}
static inline void mp_list_free(MpList* l) { if (l) { free(l->data); free(l); } }
static inline MpList* mp_list_slice(MpList* l, int64_t start, int64_t stop) {
    MpList* r = mp_list_new();
    if (start < 0) start = 0;
    if (stop > l->len) stop = l->len;
    for (int64_t i = start; i < stop; i++) mp_list_append(r, l->data[i]);
    return r;
}
static inline MpList* mp_list_concat(MpList* a, MpList* b) {
    MpList* r = mp_list_new();
    for (int64_t i = 0; i < a->len; i++) mp_list_append(r, a->data[i]);
    for (int64_t i = 0; i < b->len; i++) mp_list_append(r, b->data[i]);
    return r;
}
static inline int mp_list_contains(MpList* l, MpVal v) {
    for (int64_t i = 0; i < l->len; i++) {
        if (l->data[i] == v) return 1;
    }
    return 0;
}

static inline MpDict* mp_dict_new(void) {
    MpDict* d = (MpDict*)malloc(sizeof(MpDict));
    d->cap = 16; d->len = 0;
    d->entries = (MpDictEntry*)calloc(d->cap, sizeof(MpDictEntry));
    return d;
}
static inline int64_t _mp_dict_find(MpDict* d, const char* key) {
    for (int64_t i = 0; i < d->cap; i++) { if (d->entries[i].used && strcmp(d->entries[i].key, key) == 0) return i; }
    return -1;
}
static inline int64_t _mp_dict_find_slot(MpDict* d) {
    for (int64_t i = 0; i < d->cap; i++) { if (!d->entries[i].used) return i; }
    int64_t old = d->cap; d->cap *= 2;
    d->entries = (MpDictEntry*)realloc(d->entries, sizeof(MpDictEntry) * d->cap);
    memset(d->entries + old, 0, sizeof(MpDictEntry) * old);
    return old;
}
static inline void mp_dict_set(MpDict* d, const char* key, MpVal val) {
    int64_t idx = _mp_dict_find(d, key);
    if (idx >= 0) { d->entries[idx].val = val; return; }
    idx = _mp_dict_find_slot(d);
    d->entries[idx].key = strdup(key); d->entries[idx].val = val; d->entries[idx].used = 1; d->len++;
}
static inline MpVal mp_dict_get(MpDict* d, const char* key) {
    int64_t idx = _mp_dict_find(d, key);
    if (idx < 0) { fprintf(stderr, "Key not found: %s\n", key); exit(1); }
    return d->entries[idx].val;
}
static inline int mp_dict_has(MpDict* d, const char* key) { return _mp_dict_find(d, key) >= 0; }
static inline void mp_dict_del(MpDict* d, const char* key) {
    int64_t idx = _mp_dict_find(d, key);
    if (idx >= 0) { free(d->entries[idx].key); d->entries[idx].used = 0; d->len--; }
}
static inline int64_t mp_dict_len(MpDict* d) { return d->len; }
static inline void mp_dict_free(MpDict* d) {
    if (d) { for (int64_t i = 0; i < d->cap; i++) { if (d->entries[i].used) free(d->entries[i].key); } free(d->entries); free(d); }
}

static inline MpStr* mp_str_new(const char* s) {
    MpStr* str = (MpStr*)malloc(sizeof(MpStr));
    str->len = strlen(s); str->data = (char*)malloc(str->len + 1);
    memcpy(str->data, s, str->len + 1); return str;
}
static inline MpStr* mp_str_concat(MpStr* a, MpStr* b) {
    MpStr* str = (MpStr*)malloc(sizeof(MpStr));
    str->len = a->len + b->len; str->data = (char*)malloc(str->len + 1);
    memcpy(str->data, a->data, a->len); memcpy(str->data + a->len, b->data, b->len);
    str->data[str->len] = '\0'; return str;
}
static inline int64_t mp_str_len(MpStr* s) { return s->len; }
static inline int mp_str_eq(MpStr* a, MpStr* b) { return a->len == b->len && memcmp(a->data, b->data, a->len) == 0; }
static inline void mp_str_free(MpStr* s) { if (s) { free(s->data); free(s); } }
static inline MpVal mp_val_str(MpStr* s) { return (MpVal)(uintptr_t)s; }
static inline MpStr* mp_str_from_int(int64_t v) {
    char buf[32]; snprintf(buf, sizeof(buf), "%lld", (long long)v);
    return mp_str_new(buf);
}
static inline MpStr* mp_str_from_float(double v) {
    char buf[64]; snprintf(buf, sizeof(buf), "%g", v);
    return mp_str_new(buf);
}
static inline int mp_str_contains(MpStr* s, MpStr* sub) {
    if (sub->len == 0) return 1;
    if (sub->len > s->len) return 0;
    for (int64_t i = 0; i <= s->len - sub->len; i++) {
        if (memcmp(s->data + i, sub->data, sub->len) == 0) return 1;
    }
    return 0;
}
static inline int mp_str_starts_with(MpStr* s, MpStr* pre) {
    return pre->len <= s->len && memcmp(s->data, pre->data, pre->len) == 0;
}
static inline int mp_str_ends_with(MpStr* s, MpStr* suf) {
    return suf->len <= s->len && memcmp(s->data + s->len - suf->len, suf->data, suf->len) == 0;
}
static inline MpStr* mp_str_slice(MpStr* s, int64_t start, int64_t end) {
    if (start < 0) start = 0;
    if (end > s->len) end = s->len;
    if (end < start) end = start;
    MpStr* r = (MpStr*)malloc(sizeof(MpStr));
    r->len = end - start; r->data = (char*)malloc(r->len + 1);
    memcpy(r->data, s->data + start, r->len); r->data[r->len] = '\0';
    return r;
}
static inline int64_t mp_str_find(MpStr* s, MpStr* sub) {
    if (sub->len == 0) return 0;
    if (sub->len > s->len) return -1;
    for (int64_t i = 0; i <= s->len - sub->len; i++) {
        if (memcmp(s->data + i, sub->data, sub->len) == 0) return i;
    }
    return -1;
}
static inline MpStr* mp_str_upper(MpStr* s) {
    MpStr* r = (MpStr*)malloc(sizeof(MpStr));
    r->len = s->len; r->data = (char*)malloc(r->len + 1);
    for (int64_t i = 0; i < r->len; i++) r->data[i] = (char)toupper((unsigned char)s->data[i]);
    r->data[r->len] = '\0'; return r;
}
static inline MpStr* mp_str_lower(MpStr* s) {
    MpStr* r = (MpStr*)malloc(sizeof(MpStr));
    r->len = s->len; r->data = (char*)malloc(r->len + 1);
    for (int64_t i = 0; i < r->len; i++) r->data[i] = (char)tolower((unsigned char)s->data[i]);
    r->data[r->len] = '\0'; return r;
}
static inline MpStr* mp_str_repeat(MpStr* s, int64_t n) {
    if (n <= 0) return mp_str_new("");
    MpStr* r = (MpStr*)malloc(sizeof(MpStr));
    r->len = s->len * n; r->data = (char*)malloc(r->len + 1);
    for (int64_t i = 0; i < n; i++) memcpy(r->data + i * s->len, s->data, s->len);
    r->data[r->len] = '\0'; return r;
}
static inline MpStr* mp_str_strip(MpStr* s) {
    int64_t start = 0, end = s->len;
    while (start < end && isspace((unsigned char)s->data[start])) start++;
    while (end > start && isspace((unsigned char)s->data[end-1])) end--;
    return mp_str_slice(s, start, end);
}
static inline MpStr* mp_str_lstrip(MpStr* s) {
    int64_t start = 0;
    while (start < s->len && isspace((unsigned char)s->data[start])) start++;
    return mp_str_slice(s, start, s->len);
}
static inline MpStr* mp_str_rstrip(MpStr* s) {
    int64_t end = s->len;
    while (end > 0 && isspace((unsigned char)s->data[end-1])) end--;
    return mp_str_slice(s, 0, end);
}
static inline MpList* mp_str_split(MpStr* s, MpStr* sep) {
    MpList* result = mp_list_new();
    if (sep->len == 0) {
        int64_t i = 0;
        while (i < s->len) {
            while (i < s->len && isspace((unsigned char)s->data[i])) i++;
            if (i >= s->len) break;
            int64_t st = i;
            while (i < s->len && !isspace((unsigned char)s->data[i])) i++;
            mp_list_append(result, mp_val_str(mp_str_slice(s, st, i)));
        }
        return result;
    }
    int64_t start = 0, j = 0;
    while (j <= s->len - sep->len) {
        if (memcmp(s->data + j, sep->data, sep->len) == 0) {
            mp_list_append(result, mp_val_str(mp_str_slice(s, start, j)));
            j += sep->len; start = j;
        } else { j++; }
    }
    mp_list_append(result, mp_val_str(mp_str_slice(s, start, s->len)));
    return result;
}
static inline MpStr* mp_str_format(const char* fmt, ...) {
    char buf[4096];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    return mp_str_new(buf);
}

/* ---- Random ---- */
static inline void mp_rand_seed(int64_t seed) { srand((unsigned int)seed); }
static inline int64_t mp_rand_int(int64_t lo, int64_t hi) {
    return lo + (int64_t)((unsigned)rand() % (unsigned)(hi - lo + 1));
}
static inline double mp_rand_float(void) {
    return (double)rand() / ((double)RAND_MAX + 1.0);
}

/* ---- Time ---- */
static inline int64_t mp_time_now(void) { return (int64_t)time(NULL); }
static inline int64_t mp_time_ms(void) {
#ifdef _WIN32
    return (int64_t)GetTickCount64();
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)(ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL);
#endif
}

/* ---- Env ---- */
static inline MpStr* mp_getenv(const char* name) {
    const char* val = getenv(name);
    return val ? mp_str_new(val) : NULL;
}

/* ---- Threading ---- */
/* Cross-platform thread primitives */

#ifdef _WIN32

struct MpThread { HANDLE _t; };
struct MpMutex  { CRITICAL_SECTION _m; };
struct MpCond   { CONDITION_VARIABLE _c; };

typedef struct {
    void* (*func)(void*);
    void* arg;
} _MpThreadTrampoline;

static DWORD WINAPI _mp_thread_proc(LPVOID param) {
    _MpThreadTrampoline* t = (_MpThreadTrampoline*)param;
    t->func(t->arg);
    free(t);
    return 0;
}

static inline MpThread mp_thread_spawn(void* (*func)(void*), void* arg) {
    _MpThreadTrampoline* t = (_MpThreadTrampoline*)malloc(sizeof(_MpThreadTrampoline));
    t->func = func;
    t->arg = arg;
    MpThread th; th._t = CreateThread(NULL, 0, _mp_thread_proc, t, 0, NULL);
    return th;
}

static inline void mp_thread_join(MpThread th) {
    WaitForSingleObject(th._t, INFINITE);
    CloseHandle(th._t);
}

static inline MpMutex* mp_mutex_new(void) {
    MpMutex* m = (MpMutex*)malloc(sizeof(MpMutex));
    InitializeCriticalSection(&m->_m);
    return m;
}

static inline void mp_mutex_lock(MpMutex* m) { EnterCriticalSection(&m->_m); }
static inline void mp_mutex_unlock(MpMutex* m) { LeaveCriticalSection(&m->_m); }
static inline void mp_mutex_free(MpMutex* m) {
    if (m) { DeleteCriticalSection(&m->_m); free(m); }
}

static inline MpCond* mp_cond_new(void) {
    MpCond* c = (MpCond*)malloc(sizeof(MpCond));
    InitializeConditionVariable(&c->_c);
    return c;
}

static inline void mp_cond_wait(MpCond* c, MpMutex* m) {
    SleepConditionVariableCS(&c->_c, &m->_m, INFINITE);
}
static inline void mp_cond_signal(MpCond* c) { WakeConditionVariable(&c->_c); }
static inline void mp_cond_broadcast(MpCond* c) { WakeAllConditionVariable(&c->_c); }
static inline void mp_cond_free(MpCond* c) { if (c) free(c); }

static inline void mp_sleep_ms(int64_t ms) { Sleep((DWORD)ms); }

/* Atomics — MSVC intrinsics */
static inline int64_t mp_atomic_add(volatile int64_t* ptr, int64_t val) {
    return InterlockedExchangeAdd64(ptr, val);
}
static inline int64_t mp_atomic_sub(volatile int64_t* ptr, int64_t val) {
    return InterlockedExchangeAdd64(ptr, -val);
}
static inline int64_t mp_atomic_load(volatile int64_t* ptr) {
    return InterlockedCompareExchange64(ptr, 0, 0);
}
static inline void mp_atomic_store(volatile int64_t* ptr, int64_t val) {
    InterlockedExchange64(ptr, val);
}
static inline int64_t mp_atomic_cas(volatile int64_t* ptr, int64_t expected, int64_t desired) {
    return InterlockedCompareExchange64(ptr, desired, expected);
}

#else /* POSIX */
#include <pthread.h>
#include <unistd.h>

struct MpThread { pthread_t _t; };
struct MpMutex  { pthread_mutex_t _m; };
struct MpCond   { pthread_cond_t _c; };

static inline MpThread mp_thread_spawn(void* (*func)(void*), void* arg) {
    MpThread th;
    pthread_create(&th._t, NULL, func, arg);
    return th;
}

static inline void mp_thread_join(MpThread th) {
    pthread_join(th._t, NULL);
}

static inline MpMutex* mp_mutex_new(void) {
    MpMutex* m = (MpMutex*)malloc(sizeof(MpMutex));
    pthread_mutex_init(&m->_m, NULL);
    return m;
}

static inline void mp_mutex_lock(MpMutex* m) { pthread_mutex_lock(&m->_m); }
static inline void mp_mutex_unlock(MpMutex* m) { pthread_mutex_unlock(&m->_m); }
static inline void mp_mutex_free(MpMutex* m) {
    if (m) { pthread_mutex_destroy(&m->_m); free(m); }
}

static inline MpCond* mp_cond_new(void) {
    MpCond* c = (MpCond*)malloc(sizeof(MpCond));
    pthread_cond_init(&c->_c, NULL);
    return c;
}

static inline void mp_cond_wait(MpCond* c, MpMutex* m) { pthread_cond_wait(&c->_c, &m->_m); }
static inline void mp_cond_signal(MpCond* c) { pthread_cond_signal(&c->_c); }
static inline void mp_cond_broadcast(MpCond* c) { pthread_cond_broadcast(&c->_c); }
static inline void mp_cond_free(MpCond* c) {
    if (c) { pthread_cond_destroy(&c->_c); free(c); }
}

static inline void mp_sleep_ms(int64_t ms) { usleep(ms * 1000); }

/* Atomics — GCC/Clang builtins */
static inline int64_t mp_atomic_add(volatile int64_t* ptr, int64_t val) {
    return __sync_fetch_and_add(ptr, val);
}
static inline int64_t mp_atomic_sub(volatile int64_t* ptr, int64_t val) {
    return __sync_fetch_and_sub(ptr, val);
}
static inline int64_t mp_atomic_load(volatile int64_t* ptr) {
    return __sync_val_compare_and_swap(ptr, 0, 0);
}
static inline void mp_atomic_store(volatile int64_t* ptr, int64_t val) {
    __sync_lock_test_and_set(ptr, val);
}
static inline int64_t mp_atomic_cas(volatile int64_t* ptr, int64_t expected, int64_t desired) {
    return __sync_val_compare_and_swap(ptr, expected, desired);
}

#endif /* _WIN32 / POSIX */

/* ---- Channel (bounded, multi-producer multi-consumer) ---- */
struct MpChannel {
    MpVal* buffer;
    int64_t cap;
    int64_t head;
    int64_t tail;
    int64_t count;
    int closed;
    MpMutex* lock;
    MpCond* not_empty;
    MpCond* not_full;
};

static inline MpChannel* mp_channel_new(int64_t capacity) {
    MpChannel* ch = (MpChannel*)malloc(sizeof(MpChannel));
    ch->buffer = (MpVal*)malloc(sizeof(MpVal) * capacity);
    ch->cap = capacity;
    ch->head = 0;
    ch->tail = 0;
    ch->count = 0;
    ch->closed = 0;
    ch->lock = mp_mutex_new();
    ch->not_empty = mp_cond_new();
    ch->not_full = mp_cond_new();
    return ch;
}

static inline int mp_channel_send(MpChannel* ch, MpVal val) {
    mp_mutex_lock(ch->lock);
    while (ch->count == ch->cap && !ch->closed) {
        mp_cond_wait(ch->not_full, ch->lock);
    }
    if (ch->closed) {
        mp_mutex_unlock(ch->lock);
        return 0;
    }
    ch->buffer[ch->tail] = val;
    ch->tail = (ch->tail + 1) % ch->cap;
    ch->count++;
    mp_cond_signal(ch->not_empty);
    mp_mutex_unlock(ch->lock);
    return 1;
}

static inline int mp_channel_recv(MpChannel* ch, MpVal* out) {
    mp_mutex_lock(ch->lock);
    while (ch->count == 0 && !ch->closed) {
        mp_cond_wait(ch->not_empty, ch->lock);
    }
    if (ch->count == 0 && ch->closed) {
        mp_mutex_unlock(ch->lock);
        return 0;
    }
    *out = ch->buffer[ch->head];
    ch->head = (ch->head + 1) % ch->cap;
    ch->count--;
    mp_cond_signal(ch->not_full);
    mp_mutex_unlock(ch->lock);
    return 1;
}

static inline void mp_channel_close(MpChannel* ch) {
    mp_mutex_lock(ch->lock);
    ch->closed = 1;
    mp_cond_broadcast(ch->not_empty);
    mp_cond_broadcast(ch->not_full);
    mp_mutex_unlock(ch->lock);
}

static inline void mp_channel_free(MpChannel* ch) {
    if (ch) {
        mp_mutex_free(ch->lock);
        mp_cond_free(ch->not_empty);
        mp_cond_free(ch->not_full);
        free(ch->buffer);
        free(ch);
    }
}

/* Higher-level recv that returns the value (0 if closed) */
static inline MpVal mp_channel_recv_val(MpChannel* ch) {
    MpVal out = 0;
    mp_channel_recv(ch, &out);
    return out;
}

/* Try-recv: returns 1 + sets *out if data available, 0 if closed/empty */
typedef struct {
    MpVal value;
    int ok;
} MpRecvResult;

static inline MpRecvResult mp_channel_try_recv_result(MpChannel* ch) {
    MpRecvResult r;
    r.ok = mp_channel_recv(ch, &r.value);
    return r;
}

/* Check if channel has pending data without blocking */
static inline int mp_channel_has_data(MpChannel* ch) {
    mp_mutex_lock(ch->lock);
    int result = ch->count > 0;
    mp_mutex_unlock(ch->lock);
    return result;
}

/* Drain channel into a list (blocks until closed) */
static inline MpList* mp_channel_drain(MpChannel* ch) {
    MpList* result = mp_list_new();
    MpVal v;
    while (mp_channel_recv(ch, &v)) {
        mp_list_append(result, v);
    }
    return result;
}

/* ---- Thread Pool ---- */
typedef struct {
    void (*func)(void*);
    void* arg;
} _MpTask;

struct MpThreadPool {
    MpChannel* tasks;
    MpThread* threads;
    int64_t num_threads;
    volatile int64_t shutdown;
};

static void* _mp_pool_worker(void* arg) {
    MpThreadPool* pool = (MpThreadPool*)arg;
    MpVal task_val;
    while (mp_channel_recv(pool->tasks, &task_val)) {
        _MpTask* task = (_MpTask*)(uintptr_t)mp_as_int(task_val);
        if (task) {
            task->func(task->arg);
            free(task);
        }
    }
    return NULL;
}

static inline MpThreadPool* mp_pool_new(int64_t num_threads, int64_t queue_size) {
    MpThreadPool* pool = (MpThreadPool*)malloc(sizeof(MpThreadPool));
    pool->tasks = mp_channel_new(queue_size);
    pool->num_threads = num_threads;
    pool->shutdown = 0;
    pool->threads = (MpThread*)malloc(sizeof(MpThread) * num_threads);
    for (int64_t i = 0; i < num_threads; i++) {
        pool->threads[i] = mp_thread_spawn(_mp_pool_worker, pool);
    }
    return pool;
}

static inline void mp_pool_submit(MpThreadPool* pool, void (*func)(void*), void* arg) {
    _MpTask* task = (_MpTask*)malloc(sizeof(_MpTask));
    task->func = func;
    task->arg = arg;
    mp_channel_send(pool->tasks, mp_val_int((int64_t)(uintptr_t)task));
}

static inline void mp_pool_shutdown(MpThreadPool* pool) {
    mp_channel_close(pool->tasks);
    for (int64_t i = 0; i < pool->num_threads; i++) {
        mp_thread_join(pool->threads[i]);
    }
    mp_channel_free(pool->tasks);
    free(pool->threads);
    free(pool);
}

/* ---- Parallel For ---- */
typedef struct {
    void (*func)(int64_t, int64_t, void*);
    int64_t start;
    int64_t end;
    void* user_data;
} _MpParallelChunk;

static void* _mp_parallel_worker(void* arg) {
    _MpParallelChunk* chunk = (_MpParallelChunk*)arg;
    chunk->func(chunk->start, chunk->end, chunk->user_data);
    return NULL;
}

static inline void mp_parallel_for(int64_t start, int64_t end,
                                    int64_t num_threads,
                                    void (*func)(int64_t, int64_t, void*),
                                    void* user_data) {
    if (num_threads <= 1 || end - start <= num_threads) {
        func(start, end, user_data);
        return;
    }
    int64_t chunk_size = (end - start + num_threads - 1) / num_threads;
    _MpParallelChunk* chunks = (_MpParallelChunk*)malloc(sizeof(_MpParallelChunk) * num_threads);
    MpThread* threads = (MpThread*)malloc(sizeof(MpThread) * num_threads);
    int64_t actual = 0;

    for (int64_t i = 0; i < num_threads; i++) {
        int64_t s = start + i * chunk_size;
        int64_t e = s + chunk_size;
        if (s >= end) break;
        if (e > end) e = end;
        chunks[i].func = func;
        chunks[i].start = s;
        chunks[i].end = e;
        chunks[i].user_data = user_data;
        threads[i] = mp_thread_spawn(_mp_parallel_worker, &chunks[i]);
        actual++;
    }

    for (int64_t i = 0; i < actual; i++) {
        mp_thread_join(threads[i]);
    }
    free(chunks);
    free(threads);
}

/* ---- File I/O ---- */
typedef FILE* MpFile;

static inline MpFile mp_file_open(const char* path, const char* mode) {
    FILE* f = fopen(path, mode);
    if (!f) { fprintf(stderr, "Cannot open file: %s\n", path); exit(1); }
    return f;
}

static inline MpFile mp_file_open_safe(const char* path, const char* mode) {
    /* Returns NULL instead of exiting on failure */
    return fopen(path, mode);
}

static inline void mp_file_close(MpFile f) {
    if (f) fclose(f);
}

static inline void mp_file_write(MpFile f, const char* data) {
    fputs(data, f);
}

static inline void mp_file_write_str(MpFile f, MpStr* s) {
    fwrite(s->data, 1, s->len, f);
}

static inline void mp_file_write_line(MpFile f, const char* data) {
    fputs(data, f);
    fputc('\n', f);
}

static inline void mp_file_write_int(MpFile f, int64_t v) {
    fprintf(f, "%lld", (long long)v);
}

static inline void mp_file_write_float(MpFile f, double v) {
    fprintf(f, "%.6f", v);
}

static inline MpStr* mp_file_read_all(MpFile f) {
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    MpStr* s = (MpStr*)malloc(sizeof(MpStr));
    s->len = sz;
    s->data = (char*)malloc(sz + 1);
    fread(s->data, 1, sz, f);
    s->data[sz] = '\0';
    return s;
}

static inline MpStr* mp_file_read_line(MpFile f) {
    char buf[4096];
    if (!fgets(buf, sizeof(buf), f)) return NULL;
    int64_t len = strlen(buf);
    /* Strip trailing newline */
    if (len > 0 && buf[len-1] == '\n') { buf[--len] = '\0'; }
    if (len > 0 && buf[len-1] == '\r') { buf[--len] = '\0'; }
    MpStr* s = (MpStr*)malloc(sizeof(MpStr));
    s->len = len;
    s->data = (char*)malloc(len + 1);
    memcpy(s->data, buf, len + 1);
    return s;
}

static inline int mp_file_eof(MpFile f) {
    return feof(f);
}

static inline int mp_file_exists(const char* path) {
    FILE* f = fopen(path, "r");
    if (f) { fclose(f); return 1; }
    return 0;
}

static inline int64_t mp_file_size(const char* path) {
    FILE* f = fopen(path, "rb");
    if (!f) return -1;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fclose(f);
    return (int64_t)sz;
}

/* ---- Directory operations ---- */
/* Cross-platform: uses _WIN32 vs POSIX */

#ifdef _WIN32
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <direct.h>
/* Undefine Windows API names that conflict with user structs */
#ifdef Rectangle
#undef Rectangle
#endif
#define mp_mkdir(p) _mkdir(p)
#define mp_rmdir(p) _rmdir(p)
#define mp_getcwd(b,s) _getcwd(b,s)
#define mp_chdir(p) _chdir(p)
#else
#include <unistd.h>
#include <sys/stat.h>
#include <dirent.h>
#define mp_mkdir(p) mkdir(p, 0755)
#define mp_rmdir(p) rmdir(p)
#define mp_getcwd(b,s) getcwd(b,s)
#define mp_chdir(p) chdir(p)
#endif

static inline int mp_dir_create(const char* path) {
    return mp_mkdir(path) == 0;
}

static inline int mp_dir_remove(const char* path) {
    return mp_rmdir(path) == 0;
}

static inline int mp_dir_exists(const char* path) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesA(path);
    return (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY));
#else
    struct stat st;
    return (stat(path, &st) == 0 && S_ISDIR(st.st_mode));
#endif
}

static inline MpStr* mp_dir_cwd(void) {
    char buf[4096];
    if (mp_getcwd(buf, sizeof(buf))) {
        return mp_str_new(buf);
    }
    return mp_str_new(".");
}

static inline int mp_dir_chdir(const char* path) {
    return mp_chdir(path) == 0;
}

static inline MpList* mp_dir_list(const char* path) {
    MpList* result = mp_list_new();
#ifdef _WIN32
    WIN32_FIND_DATAA fd;
    char pattern[4096];
    snprintf(pattern, sizeof(pattern), "%s\\*", path);
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE) return result;
    do {
        if (strcmp(fd.cFileName, ".") == 0 || strcmp(fd.cFileName, "..") == 0) continue;
        MpStr* name = mp_str_new(fd.cFileName);
        mp_list_append(result, mp_val_str(name));
    } while (FindNextFileA(h, &fd));
    FindClose(h);
#else
    DIR* d = opendir(path);
    if (!d) return result;
    struct dirent* ent;
    while ((ent = readdir(d)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) continue;
        MpStr* name = mp_str_new(ent->d_name);
        mp_list_append(result, mp_val_str(name));
    }
    closedir(d);
#endif
    return result;
}

/* ---- Path helpers ---- */
static inline MpStr* mp_path_join(const char* a, const char* b) {
    int64_t la = strlen(a), lb = strlen(b);
    MpStr* s = (MpStr*)malloc(sizeof(MpStr));
#ifdef _WIN32
    char sep = '\\';
#else
    char sep = '/';
#endif
    s->len = la + 1 + lb;
    s->data = (char*)malloc(s->len + 1);
    memcpy(s->data, a, la);
    s->data[la] = sep;
    memcpy(s->data + la + 1, b, lb);
    s->data[s->len] = '\0';
    return s;
}

static inline MpStr* mp_path_ext(const char* path) {
    const char* dot = strrchr(path, '.');
    if (!dot || dot == path) return mp_str_new("");
    return mp_str_new(dot);
}

static inline MpStr* mp_path_basename(const char* path) {
    const char* last_sep = strrchr(path, '/');
#ifdef _WIN32
    const char* last_bsep = strrchr(path, '\\');
    if (last_bsep && (!last_sep || last_bsep > last_sep)) last_sep = last_bsep;
#endif
    if (last_sep) return mp_str_new(last_sep + 1);
    return mp_str_new(path);
}

static inline MpStr* mp_path_dirname(const char* path) {
    const char* last_sep = strrchr(path, '/');
#ifdef _WIN32
    const char* last_bsep = strrchr(path, '\\');
    if (last_bsep && (!last_sep || last_bsep > last_sep)) last_sep = last_bsep;
#endif
    if (!last_sep) return mp_str_new(".");
    int64_t len = last_sep - path;
    MpStr* s = (MpStr*)malloc(sizeof(MpStr));
    s->len = len;
    s->data = (char*)malloc(len + 1);
    memcpy(s->data, path, len);
    s->data[len] = '\0';
    return s;
}

static inline int mp_remove(const char* path) {
    return remove(path) == 0;
}

static inline int mp_rename(const char* old_path, const char* new_path) {
    return rename(old_path, new_path) == 0;
}

/* ---- Arena Allocator ---- */
struct MpArena {
    char* data;
    int64_t size;
    int64_t offset;
};

static inline MpArena* mp_arena_new(int64_t size) {
    MpArena* a = (MpArena*)malloc(sizeof(MpArena));
    a->data = (char*)malloc(size);
    a->size = size;
    a->offset = 0;
    return a;
}

static inline void* mp_arena_alloc(MpArena* a, int64_t bytes) {
    /* Align to 8 bytes */
    int64_t aligned = (bytes + 7) & ~7;
    if (a->offset + aligned > a->size) {
        /* Grow the arena */
        while (a->offset + aligned > a->size) a->size *= 2;
        a->data = (char*)realloc(a->data, a->size);
    }
    void* ptr = a->data + a->offset;
    a->offset += aligned;
    return ptr;
}

static inline void mp_arena_reset(MpArena* a) {
    a->offset = 0;
}

static inline void mp_arena_free(MpArena* a) {
    if (a) { free(a->data); free(a); }
}

/* Arena-backed containers: allocate from arena, never individually freed */
static inline MpList* mp_arena_list_new(MpArena* a) {
    MpList* l = (MpList*)mp_arena_alloc(a, sizeof(MpList));
    l->cap = 8; l->len = 0;
    l->data = (MpVal*)mp_arena_alloc(a, sizeof(MpVal) * l->cap);
    return l;
}

static inline MpStr* mp_arena_str_new(MpArena* a, const char* s) {
    MpStr* str = (MpStr*)mp_arena_alloc(a, sizeof(MpStr));
    str->len = strlen(s);
    str->data = (char*)mp_arena_alloc(a, str->len + 1);
    memcpy(str->data, s, str->len + 1);
    return str;
}

static inline MpStr* mp_arena_str_new_len(MpArena* a, const char* s, int64_t len) {
    MpStr* str = (MpStr*)mp_arena_alloc(a, sizeof(MpStr));
    str->len = len;
    str->data = (char*)mp_arena_alloc(a, len + 1);
    memcpy(str->data, s, len);
    str->data[len] = '\0';
    return str;
}

/* Hot-reload helpers — load/unload shared libraries at runtime */
#if !defined(_WIN32)
#  include <dlfcn.h>
static inline void* hotreload_open(const char* path) {
    return dlopen(path, RTLD_NOW | RTLD_LOCAL);
}
static inline void* hotreload_sym(void* lib, const char* sym) {
    return dlsym(lib, sym);
}
static inline void hotreload_close(void* lib) {
    if (lib) dlclose(lib);
}
#else
#  include <windows.h>
static inline void* hotreload_open(const char* path) {
    return (void*)LoadLibraryA(path);
}
static inline void* hotreload_sym(void* lib, const char* sym) {
    return (void*)GetProcAddress((HMODULE)lib, sym);
}
static inline void hotreload_close(void* lib) {
    if (lib) FreeLibrary((HMODULE)lib);
}
#endif

/* ---- Binary I/O (MpWriter / MpReader) ---- */

struct MpWriter {
    uint8_t* data;
    int64_t len;
    int64_t cap;
};

static inline MpWriter* mp_writer_new(int64_t initial_cap) {
    MpWriter* w = (MpWriter*)malloc(sizeof(MpWriter));
    if (initial_cap < 64) initial_cap = 64;
    w->data = (uint8_t*)malloc(initial_cap);
    w->len = 0;
    w->cap = initial_cap;
    return w;
}

static inline void mp_writer_free(MpWriter* w) {
    if (w) { free(w->data); free(w); }
}

static inline int64_t mp_writer_pos(MpWriter* w) { return w->len; }

static inline void _mp_writer_grow(MpWriter* w, int64_t need) {
    if (w->len + need <= w->cap) return;
    while (w->cap < w->len + need) w->cap *= 2;
    w->data = (uint8_t*)realloc(w->data, w->cap);
}

static inline void mp_write_bytes(MpWriter* w, const void* ptr, int64_t n) {
    _mp_writer_grow(w, n);
    memcpy(w->data + w->len, ptr, n);
    w->len += n;
}

static inline void mp_write_i8 (MpWriter* w, int8_t   v) { mp_write_bytes(w, &v, 1); }
static inline void mp_write_i16(MpWriter* w, int16_t  v) { mp_write_bytes(w, &v, 2); }
static inline void mp_write_i32(MpWriter* w, int32_t  v) { mp_write_bytes(w, &v, 4); }
static inline void mp_write_i64(MpWriter* w, int64_t  v) { mp_write_bytes(w, &v, 8); }
static inline void mp_write_u8 (MpWriter* w, uint8_t  v) { mp_write_bytes(w, &v, 1); }
static inline void mp_write_u16(MpWriter* w, uint16_t v) { mp_write_bytes(w, &v, 2); }
static inline void mp_write_u32(MpWriter* w, uint32_t v) { mp_write_bytes(w, &v, 4); }
static inline void mp_write_u64(MpWriter* w, uint64_t v) { mp_write_bytes(w, &v, 8); }
static inline void mp_write_f32(MpWriter* w, float    v) { mp_write_bytes(w, &v, 4); }
static inline void mp_write_f64(MpWriter* w, double   v) { mp_write_bytes(w, &v, 8); }
static inline void mp_write_bool(MpWriter* w, int     v) { uint8_t b = v ? 1 : 0; mp_write_bytes(w, &b, 1); }

static inline void mp_write_text(MpWriter* w, MpStr* s) {
    mp_write_bytes(w, s->data, s->len);
}

static inline void mp_write_str(MpWriter* w, MpStr* s) {
    int32_t slen = (int32_t)s->len;
    mp_write_bytes(w, &slen, 4);
    mp_write_bytes(w, s->data, slen);
}

static inline uint8_t* mp_writer_to_bytes(MpWriter* w, int64_t* out_len) {
    *out_len = w->len;
    uint8_t* buf = w->data;
    w->data = NULL;
    w->len = 0;
    w->cap = 0;
    return buf;
}

struct MpReader {
    const uint8_t* data;
    int64_t len;
    int64_t pos;
};

static inline MpReader* mp_reader_new(const uint8_t* buf, int64_t len) {
    MpReader* r = (MpReader*)malloc(sizeof(MpReader));
    r->data = buf;
    r->len = len;
    r->pos = 0;
    return r;
}

static inline void mp_reader_free(MpReader* r) { if (r) free(r); }

static inline int64_t mp_reader_pos(MpReader* r) { return r->pos; }

static inline void mp_read_bytes(MpReader* r, void* dst, int64_t n) {
    if (r->pos + n > r->len) {
        fprintf(stderr, "MpReader: read past end (pos=%lld, need=%lld, len=%lld)\n",
                (long long)r->pos, (long long)n, (long long)r->len);
        abort();
    }
    memcpy(dst, r->data + r->pos, n);
    r->pos += n;
}

static inline int8_t   mp_read_i8 (MpReader* r) { int8_t   v; mp_read_bytes(r, &v, 1); return v; }
static inline int16_t  mp_read_i16(MpReader* r) { int16_t  v; mp_read_bytes(r, &v, 2); return v; }
static inline int32_t  mp_read_i32(MpReader* r) { int32_t  v; mp_read_bytes(r, &v, 4); return v; }
static inline int64_t  mp_read_i64(MpReader* r) { int64_t  v; mp_read_bytes(r, &v, 8); return v; }
static inline uint8_t  mp_read_u8 (MpReader* r) { uint8_t  v; mp_read_bytes(r, &v, 1); return v; }
static inline uint16_t mp_read_u16(MpReader* r) { uint16_t v; mp_read_bytes(r, &v, 2); return v; }
static inline uint32_t mp_read_u32(MpReader* r) { uint32_t v; mp_read_bytes(r, &v, 4); return v; }
static inline uint64_t mp_read_u64(MpReader* r) { uint64_t v; mp_read_bytes(r, &v, 8); return v; }
static inline float    mp_read_f32(MpReader* r) { float    v; mp_read_bytes(r, &v, 4); return v; }
static inline double   mp_read_f64(MpReader* r) { double   v; mp_read_bytes(r, &v, 8); return v; }
static inline int      mp_read_bool(MpReader* r) { uint8_t b; mp_read_bytes(r, &b, 1); return b ? 1 : 0; }

static inline MpStr* mp_read_str(MpReader* r) {
    int32_t slen;
    mp_read_bytes(r, &slen, 4);
    MpStr* s = (MpStr*)malloc(sizeof(MpStr));
    s->len = slen;
    s->data = (char*)malloc(slen + 1);
    mp_read_bytes(r, s->data, slen);
    s->data[slen] = '\0';
    return s;
}

/* ---- Pointer Set (for graph serialization) ---- */

typedef struct MpPtrSet {
    void** ptrs;
    uint32_t* types;
    int32_t count;
    int32_t cap;
} MpPtrSet;

static inline void mp_ptrset_init(MpPtrSet* s, int32_t cap) {
    s->ptrs = (void**)malloc(sizeof(void*) * cap);
    s->types = (uint32_t*)malloc(sizeof(uint32_t) * cap);
    s->count = 0;
    s->cap = cap;
}

static inline int32_t mp_ptrset_find(MpPtrSet* s, void* p) {
    for (int32_t i = 0; i < s->count; i++) {
        if (s->ptrs[i] == p) return i;
    }
    return -1;
}

static inline int32_t mp_ptrset_add(MpPtrSet* s, void* p, uint32_t type_hash) {
    int32_t idx = mp_ptrset_find(s, p);
    if (idx >= 0) return idx;
    if (s->count >= s->cap) {
        s->cap *= 2;
        s->ptrs = (void**)realloc(s->ptrs, sizeof(void*) * s->cap);
        s->types = (uint32_t*)realloc(s->types, sizeof(uint32_t) * s->cap);
    }
    idx = s->count++;
    s->ptrs[idx] = p;
    s->types[idx] = type_hash;
    return idx;
}

static inline void mp_ptrset_free(MpPtrSet* s) {
    free(s->ptrs);
    free(s->types);
}

/* ---- Binary File I/O ---- */

static inline int mp_write_file_bin(const char* path, const uint8_t* buf, int64_t len) {
    FILE* f = fopen(path, "wb");
    if (!f) return -1;
    fwrite(buf, 1, len, f);
    fclose(f);
    return 0;
}

static inline uint8_t* mp_read_file_bin(const char* path, int64_t* out_len) {
    FILE* f = fopen(path, "rb");
    if (!f) { *out_len = 0; return NULL; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t* buf = (uint8_t*)malloc(sz);
    fread(buf, 1, sz, f);
    fclose(f);
    *out_len = (int64_t)sz;
    return buf;
}

/* input(prompt?) — read a line from stdin, strip trailing newline */
static inline MpStr* mp_input(const char* prompt) {
    if (prompt) { fputs(prompt, stdout); fflush(stdout); }
    char _buf[4096];
    if (!fgets(_buf, sizeof(_buf), stdin)) return mp_str_new("");
    size_t _n = strlen(_buf);
    if (_n > 0 && _buf[_n - 1] == '\n') _buf[--_n] = '\0';
    return mp_str_new(_buf);
}

#endif /* MICROPY_RT_H */
