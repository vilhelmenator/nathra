
#ifndef MICROPY_RT_H
#define MICROPY_RT_H

#include "nathra_types.h"
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

struct NrList {
    NrVal* data;
    int64_t len;
    int64_t cap;
};

struct NrDictEntry {
    char* key;
    NrVal val;
    int used;
};

struct NrDict {
    NrDictEntry* entries;
    int64_t cap;
    int64_t len;
};

struct NrStr {
    char* data;
    int64_t len;
};

/* -------------------------------------------------------------------------
 * Debug allocation tracking — active only when compiled with -DNATHRA_DEBUG.
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
#ifdef NATHRA_DEBUG
static inline void* _nr_debug_alloc(size_t n, const char* file, int line) {
    void* p = malloc(n);
    if (p) {
        _nr_alloc_count++;
        fprintf(stderr, "[alloc +%lld]  %s:%d\n",
                (long long)_nr_alloc_count, file, line);
    }
    return p;
}
static inline void _nr_debug_free(void* p, const char* file, int line) {
    if (!p) return;
    _nr_alloc_count--;
    fprintf(stderr, "[free   %lld]  %s:%d\n",
            (long long)_nr_alloc_count, file, line);
    free(p);
}
static inline void _nr_alloc_assert_zero(void) {
    if (_nr_alloc_count != 0)
        fprintf(stderr, "\n[MEMORY] LEAK: %lld live allocation(s) at exit\n",
                (long long)_nr_alloc_count);
    else
        fprintf(stderr, "\n[MEMORY] OK — all allocations freed\n");
}
/* Override malloc/free — must come AFTER the wrapper definitions above */
#  define malloc(n)  _nr_debug_alloc((n), __FILE__, __LINE__)
#  define free(p)    _nr_debug_free((p),  __FILE__, __LINE__)
#else
#  define _nr_alloc_assert_zero() ((void)0)
#endif

static inline NrVal nr_val_int(int64_t v) { NrVal r; memcpy(&r, &v, 8); return r; }
static inline NrVal nr_val_float(double v) { NrVal r; memcpy(&r, &v, 8); return r; }
static inline int64_t nr_as_int(NrVal v) { int64_t r; memcpy(&r, &v, 8); return r; }
static inline double nr_as_float(NrVal v) { double r; memcpy(&r, &v, 8); return r; }

static inline void nr_print_int(int64_t v) { printf("%lld\n", (long long)v); }
static inline void nr_print_float(double v) { printf("%.6f\n", v); }
static inline void nr_print_bool(int v) { printf("%s\n", v ? "True" : "False"); }
static inline void nr_print_str(NrStr* s) { if (s) printf("%.*s\n", (int)s->len, s->data); }
static inline void nr_print_val(NrVal v) { printf("%lld\n", (long long)nr_as_int(v)); }

static inline NrList* nr_list_new(void) {
    NrList* l = (NrList*)malloc(sizeof(NrList));
    l->cap = 8; l->len = 0;
    l->data = (NrVal*)malloc(sizeof(NrVal) * l->cap);
    return l;
}
static inline void nr_list_append(NrList* l, NrVal v) {
    if (l->len >= l->cap) { l->cap *= 2; l->data = (NrVal*)realloc(l->data, sizeof(NrVal) * l->cap); }
    l->data[l->len++] = v;
}
static inline NrVal nr_list_get(NrList* l, int64_t idx) {
    if (idx < 0 || idx >= l->len) { fprintf(stderr, "Index %lld out of range\n", (long long)idx); exit(1); }
    return l->data[idx];
}
static inline void nr_list_set(NrList* l, int64_t idx, NrVal v) {
    if (idx < 0 || idx >= l->len) { fprintf(stderr, "Index %lld out of range\n", (long long)idx); exit(1); }
    l->data[idx] = v;
}
static inline int64_t nr_list_len(NrList* l) { return l->len; }
static inline NrVal nr_list_pop(NrList* l) {
    if (l->len == 0) { fprintf(stderr, "Pop from empty list\n"); exit(1); }
    return l->data[--l->len];
}
static inline void nr_list_free(NrList* l) { if (l) { free(l->data); free(l); } }
static inline NrList* nr_list_slice(NrList* l, int64_t start, int64_t stop) {
    NrList* r = nr_list_new();
    if (start < 0) start = 0;
    if (stop > l->len) stop = l->len;
    for (int64_t i = start; i < stop; i++) nr_list_append(r, l->data[i]);
    return r;
}
static inline NrList* nr_list_concat(NrList* a, NrList* b) {
    NrList* r = nr_list_new();
    for (int64_t i = 0; i < a->len; i++) nr_list_append(r, a->data[i]);
    for (int64_t i = 0; i < b->len; i++) nr_list_append(r, b->data[i]);
    return r;
}
static inline int nr_list_contains(NrList* l, NrVal v) {
    for (int64_t i = 0; i < l->len; i++) {
        if (l->data[i] == v) return 1;
    }
    return 0;
}

static inline NrDict* nr_dict_new(void) {
    NrDict* d = (NrDict*)malloc(sizeof(NrDict));
    d->cap = 16; d->len = 0;
    d->entries = (NrDictEntry*)calloc(d->cap, sizeof(NrDictEntry));
    return d;
}
static inline int64_t _nr_dict_find(NrDict* d, const char* key) {
    for (int64_t i = 0; i < d->cap; i++) { if (d->entries[i].used && strcmp(d->entries[i].key, key) == 0) return i; }
    return -1;
}
static inline int64_t _nr_dict_find_slot(NrDict* d) {
    for (int64_t i = 0; i < d->cap; i++) { if (!d->entries[i].used) return i; }
    int64_t old = d->cap; d->cap *= 2;
    d->entries = (NrDictEntry*)realloc(d->entries, sizeof(NrDictEntry) * d->cap);
    memset(d->entries + old, 0, sizeof(NrDictEntry) * old);
    return old;
}
static inline void nr_dict_set(NrDict* d, const char* key, NrVal val) {
    int64_t idx = _nr_dict_find(d, key);
    if (idx >= 0) { d->entries[idx].val = val; return; }
    idx = _nr_dict_find_slot(d);
    d->entries[idx].key = strdup(key); d->entries[idx].val = val; d->entries[idx].used = 1; d->len++;
}
static inline NrVal nr_dict_get(NrDict* d, const char* key) {
    int64_t idx = _nr_dict_find(d, key);
    if (idx < 0) { fprintf(stderr, "Key not found: %s\n", key); exit(1); }
    return d->entries[idx].val;
}
static inline int nr_dict_has(NrDict* d, const char* key) { return _nr_dict_find(d, key) >= 0; }
static inline void nr_dict_del(NrDict* d, const char* key) {
    int64_t idx = _nr_dict_find(d, key);
    if (idx >= 0) { free(d->entries[idx].key); d->entries[idx].used = 0; d->len--; }
}
static inline int64_t nr_dict_len(NrDict* d) { return d->len; }
static inline void nr_dict_free(NrDict* d) {
    if (d) { for (int64_t i = 0; i < d->cap; i++) { if (d->entries[i].used) free(d->entries[i].key); } free(d->entries); free(d); }
}

static inline NrStr* nr_str_new(const char* s) {
    NrStr* str = (NrStr*)malloc(sizeof(NrStr));
    str->len = strlen(s); str->data = (char*)malloc(str->len + 1);
    memcpy(str->data, s, str->len + 1); return str;
}
static inline NrStr* nr_str_concat(NrStr* a, NrStr* b) {
    NrStr* str = (NrStr*)malloc(sizeof(NrStr));
    str->len = a->len + b->len; str->data = (char*)malloc(str->len + 1);
    memcpy(str->data, a->data, a->len); memcpy(str->data + a->len, b->data, b->len);
    str->data[str->len] = '\0'; return str;
}
static inline int64_t nr_str_len(NrStr* s) { return s->len; }
static inline int nr_str_eq(NrStr* a, NrStr* b) { return a->len == b->len && memcmp(a->data, b->data, a->len) == 0; }
static inline void nr_str_free(NrStr* s) { if (s) { free(s->data); free(s); } }
static inline NrVal nr_val_str(NrStr* s) { return (NrVal)(uintptr_t)s; }
static inline NrStr* nr_str_from_int(int64_t v) {
    char buf[32]; snprintf(buf, sizeof(buf), "%lld", (long long)v);
    return nr_str_new(buf);
}
static inline NrStr* nr_str_from_float(double v) {
    char buf[64]; snprintf(buf, sizeof(buf), "%g", v);
    return nr_str_new(buf);
}
static inline int nr_str_contains(NrStr* s, NrStr* sub) {
    if (sub->len == 0) return 1;
    if (sub->len > s->len) return 0;
    for (int64_t i = 0; i <= s->len - sub->len; i++) {
        if (memcmp(s->data + i, sub->data, sub->len) == 0) return 1;
    }
    return 0;
}
static inline int nr_str_starts_with(NrStr* s, NrStr* pre) {
    return pre->len <= s->len && memcmp(s->data, pre->data, pre->len) == 0;
}
static inline int nr_str_ends_with(NrStr* s, NrStr* suf) {
    return suf->len <= s->len && memcmp(s->data + s->len - suf->len, suf->data, suf->len) == 0;
}
static inline NrStr* nr_str_slice(NrStr* s, int64_t start, int64_t end) {
    if (start < 0) start = 0;
    if (end > s->len) end = s->len;
    if (end < start) end = start;
    NrStr* r = (NrStr*)malloc(sizeof(NrStr));
    r->len = end - start; r->data = (char*)malloc(r->len + 1);
    memcpy(r->data, s->data + start, r->len); r->data[r->len] = '\0';
    return r;
}
static inline int64_t nr_str_find(NrStr* s, NrStr* sub) {
    if (sub->len == 0) return 0;
    if (sub->len > s->len) return -1;
    for (int64_t i = 0; i <= s->len - sub->len; i++) {
        if (memcmp(s->data + i, sub->data, sub->len) == 0) return i;
    }
    return -1;
}
static inline NrStr* nr_str_upper(NrStr* s) {
    NrStr* r = (NrStr*)malloc(sizeof(NrStr));
    r->len = s->len; r->data = (char*)malloc(r->len + 1);
    for (int64_t i = 0; i < r->len; i++) r->data[i] = (char)toupper((unsigned char)s->data[i]);
    r->data[r->len] = '\0'; return r;
}
static inline NrStr* nr_str_lower(NrStr* s) {
    NrStr* r = (NrStr*)malloc(sizeof(NrStr));
    r->len = s->len; r->data = (char*)malloc(r->len + 1);
    for (int64_t i = 0; i < r->len; i++) r->data[i] = (char)tolower((unsigned char)s->data[i]);
    r->data[r->len] = '\0'; return r;
}
static inline NrStr* nr_str_repeat(NrStr* s, int64_t n) {
    if (n <= 0) return nr_str_new("");
    NrStr* r = (NrStr*)malloc(sizeof(NrStr));
    r->len = s->len * n; r->data = (char*)malloc(r->len + 1);
    for (int64_t i = 0; i < n; i++) memcpy(r->data + i * s->len, s->data, s->len);
    r->data[r->len] = '\0'; return r;
}
static inline NrStr* nr_str_strip(NrStr* s) {
    int64_t start = 0, end = s->len;
    while (start < end && isspace((unsigned char)s->data[start])) start++;
    while (end > start && isspace((unsigned char)s->data[end-1])) end--;
    return nr_str_slice(s, start, end);
}
static inline NrStr* nr_str_lstrip(NrStr* s) {
    int64_t start = 0;
    while (start < s->len && isspace((unsigned char)s->data[start])) start++;
    return nr_str_slice(s, start, s->len);
}
static inline NrStr* nr_str_rstrip(NrStr* s) {
    int64_t end = s->len;
    while (end > 0 && isspace((unsigned char)s->data[end-1])) end--;
    return nr_str_slice(s, 0, end);
}
static inline NrList* nr_str_split(NrStr* s, NrStr* sep) {
    NrList* result = nr_list_new();
    if (sep->len == 0) {
        int64_t i = 0;
        while (i < s->len) {
            while (i < s->len && isspace((unsigned char)s->data[i])) i++;
            if (i >= s->len) break;
            int64_t st = i;
            while (i < s->len && !isspace((unsigned char)s->data[i])) i++;
            nr_list_append(result, nr_val_str(nr_str_slice(s, st, i)));
        }
        return result;
    }
    int64_t start = 0, j = 0;
    while (j <= s->len - sep->len) {
        if (memcmp(s->data + j, sep->data, sep->len) == 0) {
            nr_list_append(result, nr_val_str(nr_str_slice(s, start, j)));
            j += sep->len; start = j;
        } else { j++; }
    }
    nr_list_append(result, nr_val_str(nr_str_slice(s, start, s->len)));
    return result;
}
static inline NrStr* nr_str_format(const char* fmt, ...) {
    char buf[4096];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    return nr_str_new(buf);
}

/* ---- Random ---- */
static inline void nr_rand_seed(int64_t seed) { srand((unsigned int)seed); }
static inline int64_t nr_rand_int(int64_t lo, int64_t hi) {
    return lo + (int64_t)((unsigned)rand() % (unsigned)(hi - lo + 1));
}
static inline double nr_rand_float(void) {
    return (double)rand() / ((double)RAND_MAX + 1.0);
}

/* ---- Time ---- */
static inline int64_t nr_time_now(void) { return (int64_t)time(NULL); }
static inline int64_t nr_time_ms(void) {
#ifdef _WIN32
    return (int64_t)GetTickCount64();
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (int64_t)(ts.tv_sec * 1000LL + ts.tv_nsec / 1000000LL);
#endif
}

/* ---- Env ---- */
static inline NrStr* mp_getenv(const char* name) {
    const char* val = getenv(name);
    return val ? nr_str_new(val) : NULL;
}

/* ---- Threading ---- */
/* Cross-platform thread primitives */

#ifdef _WIN32

struct NrThread { HANDLE _t; };
struct NrMutex  { CRITICAL_SECTION _m; };
struct NrCond   { CONDITION_VARIABLE _c; };

typedef struct {
    void* (*func)(void*);
    void* arg;
} _NrThreadTrampoline;

static DWORD WINAPI _nr_thread_proc(LPVOID param) {
    _NrThreadTrampoline* t = (_NrThreadTrampoline*)param;
    t->func(t->arg);
    free(t);
    return 0;
}

static inline NrThread nr_thread_spawn(void* (*func)(void*), void* arg) {
    _NrThreadTrampoline* t = (_NrThreadTrampoline*)malloc(sizeof(_NrThreadTrampoline));
    t->func = func;
    t->arg = arg;
    NrThread th; th._t = CreateThread(NULL, 0, _nr_thread_proc, t, 0, NULL);
    return th;
}

static inline void nr_thread_join(NrThread th) {
    WaitForSingleObject(th._t, INFINITE);
    CloseHandle(th._t);
}

static inline NrMutex* nr_mutex_new(void) {
    NrMutex* m = (NrMutex*)malloc(sizeof(NrMutex));
    InitializeCriticalSection(&m->_m);
    return m;
}

static inline void nr_mutex_lock(NrMutex* m) { EnterCriticalSection(&m->_m); }
static inline void nr_mutex_unlock(NrMutex* m) { LeaveCriticalSection(&m->_m); }
static inline void nr_mutex_free(NrMutex* m) {
    if (m) { DeleteCriticalSection(&m->_m); free(m); }
}

static inline NrCond* nr_cond_new(void) {
    NrCond* c = (NrCond*)malloc(sizeof(NrCond));
    InitializeConditionVariable(&c->_c);
    return c;
}

static inline void nr_cond_wait(NrCond* c, NrMutex* m) {
    SleepConditionVariableCS(&c->_c, &m->_m, INFINITE);
}
static inline void nr_cond_signal(NrCond* c) { WakeConditionVariable(&c->_c); }
static inline void nr_cond_broadcast(NrCond* c) { WakeAllConditionVariable(&c->_c); }
static inline void nr_cond_free(NrCond* c) { if (c) free(c); }

static inline void nr_sleep_ms(int64_t ms) { Sleep((DWORD)ms); }

/* Atomics — MSVC intrinsics */
static inline int64_t nr_atomic_add(volatile int64_t* ptr, int64_t val) {
    return InterlockedExchangeAdd64(ptr, val);
}
static inline int64_t nr_atomic_sub(volatile int64_t* ptr, int64_t val) {
    return InterlockedExchangeAdd64(ptr, -val);
}
static inline int64_t nr_atomic_load(volatile int64_t* ptr) {
    return InterlockedCompareExchange64(ptr, 0, 0);
}
static inline void nr_atomic_store(volatile int64_t* ptr, int64_t val) {
    InterlockedExchange64(ptr, val);
}
static inline int64_t nr_atomic_cas(volatile int64_t* ptr, int64_t expected, int64_t desired) {
    return InterlockedCompareExchange64(ptr, desired, expected);
}

#else /* POSIX */
#include <pthread.h>
#include <unistd.h>

struct NrThread { pthread_t _t; };
struct NrMutex  { pthread_mutex_t _m; };
struct NrCond   { pthread_cond_t _c; };

static inline NrThread nr_thread_spawn(void* (*func)(void*), void* arg) {
    NrThread th;
    pthread_create(&th._t, NULL, func, arg);
    return th;
}

static inline void nr_thread_join(NrThread th) {
    pthread_join(th._t, NULL);
}

static inline NrMutex* nr_mutex_new(void) {
    NrMutex* m = (NrMutex*)malloc(sizeof(NrMutex));
    pthread_mutex_init(&m->_m, NULL);
    return m;
}

static inline void nr_mutex_lock(NrMutex* m) { pthread_mutex_lock(&m->_m); }
static inline void nr_mutex_unlock(NrMutex* m) { pthread_mutex_unlock(&m->_m); }
static inline void nr_mutex_free(NrMutex* m) {
    if (m) { pthread_mutex_destroy(&m->_m); free(m); }
}

static inline NrCond* nr_cond_new(void) {
    NrCond* c = (NrCond*)malloc(sizeof(NrCond));
    pthread_cond_init(&c->_c, NULL);
    return c;
}

static inline void nr_cond_wait(NrCond* c, NrMutex* m) { pthread_cond_wait(&c->_c, &m->_m); }
static inline void nr_cond_signal(NrCond* c) { pthread_cond_signal(&c->_c); }
static inline void nr_cond_broadcast(NrCond* c) { pthread_cond_broadcast(&c->_c); }
static inline void nr_cond_free(NrCond* c) {
    if (c) { pthread_cond_destroy(&c->_c); free(c); }
}

static inline void nr_sleep_ms(int64_t ms) { usleep(ms * 1000); }

/* Atomics — GCC/Clang builtins */
static inline int64_t nr_atomic_add(volatile int64_t* ptr, int64_t val) {
    return __sync_fetch_and_add(ptr, val);
}
static inline int64_t nr_atomic_sub(volatile int64_t* ptr, int64_t val) {
    return __sync_fetch_and_sub(ptr, val);
}
static inline int64_t nr_atomic_load(volatile int64_t* ptr) {
    return __sync_val_compare_and_swap(ptr, 0, 0);
}
static inline void nr_atomic_store(volatile int64_t* ptr, int64_t val) {
    __sync_lock_test_and_set(ptr, val);
}
static inline int64_t nr_atomic_cas(volatile int64_t* ptr, int64_t expected, int64_t desired) {
    return __sync_val_compare_and_swap(ptr, expected, desired);
}

#endif /* _WIN32 / POSIX */

/* ---- Channel (bounded, multi-producer multi-consumer) ---- */
struct NrChannel {
    NrVal* buffer;
    int64_t cap;
    int64_t head;
    int64_t tail;
    int64_t count;
    int closed;
    NrMutex* lock;
    NrCond* not_empty;
    NrCond* not_full;
};

static inline NrChannel* nr_channel_new(int64_t capacity) {
    NrChannel* ch = (NrChannel*)malloc(sizeof(NrChannel));
    ch->buffer = (NrVal*)malloc(sizeof(NrVal) * capacity);
    ch->cap = capacity;
    ch->head = 0;
    ch->tail = 0;
    ch->count = 0;
    ch->closed = 0;
    ch->lock = nr_mutex_new();
    ch->not_empty = nr_cond_new();
    ch->not_full = nr_cond_new();
    return ch;
}

static inline int nr_channel_send(NrChannel* ch, NrVal val) {
    nr_mutex_lock(ch->lock);
    while (ch->count == ch->cap && !ch->closed) {
        nr_cond_wait(ch->not_full, ch->lock);
    }
    if (ch->closed) {
        nr_mutex_unlock(ch->lock);
        return 0;
    }
    ch->buffer[ch->tail] = val;
    ch->tail = (ch->tail + 1) % ch->cap;
    ch->count++;
    nr_cond_signal(ch->not_empty);
    nr_mutex_unlock(ch->lock);
    return 1;
}

static inline int nr_channel_recv(NrChannel* ch, NrVal* out) {
    nr_mutex_lock(ch->lock);
    while (ch->count == 0 && !ch->closed) {
        nr_cond_wait(ch->not_empty, ch->lock);
    }
    if (ch->count == 0 && ch->closed) {
        nr_mutex_unlock(ch->lock);
        return 0;
    }
    *out = ch->buffer[ch->head];
    ch->head = (ch->head + 1) % ch->cap;
    ch->count--;
    nr_cond_signal(ch->not_full);
    nr_mutex_unlock(ch->lock);
    return 1;
}

static inline void nr_channel_close(NrChannel* ch) {
    nr_mutex_lock(ch->lock);
    ch->closed = 1;
    nr_cond_broadcast(ch->not_empty);
    nr_cond_broadcast(ch->not_full);
    nr_mutex_unlock(ch->lock);
}

static inline void nr_channel_free(NrChannel* ch) {
    if (ch) {
        nr_mutex_free(ch->lock);
        nr_cond_free(ch->not_empty);
        nr_cond_free(ch->not_full);
        free(ch->buffer);
        free(ch);
    }
}

/* Higher-level recv that returns the value (0 if closed) */
static inline NrVal nr_channel_recv_val(NrChannel* ch) {
    NrVal out = 0;
    nr_channel_recv(ch, &out);
    return out;
}

/* Try-recv: returns 1 + sets *out if data available, 0 if closed/empty */
typedef struct {
    NrVal value;
    int ok;
} NrRecvResult;

static inline NrRecvResult nr_channel_try_recv_result(NrChannel* ch) {
    NrRecvResult r;
    r.ok = nr_channel_recv(ch, &r.value);
    return r;
}

/* Check if channel has pending data without blocking */
static inline int nr_channel_has_data(NrChannel* ch) {
    nr_mutex_lock(ch->lock);
    int result = ch->count > 0;
    nr_mutex_unlock(ch->lock);
    return result;
}

/* Drain channel into a list (blocks until closed) */
static inline NrList* nr_channel_drain(NrChannel* ch) {
    NrList* result = nr_list_new();
    NrVal v;
    while (nr_channel_recv(ch, &v)) {
        nr_list_append(result, v);
    }
    return result;
}

/* ---- Thread Pool ---- */
typedef struct {
    void (*func)(void*);
    void* arg;
} _MpTask;

struct NrThreadPool {
    NrChannel* tasks;
    NrThread* threads;
    int64_t num_threads;
    volatile int64_t shutdown;
};

static void* _nr_pool_worker(void* arg) {
    NrThreadPool* pool = (NrThreadPool*)arg;
    NrVal task_val;
    while (nr_channel_recv(pool->tasks, &task_val)) {
        _MpTask* task = (_MpTask*)(uintptr_t)nr_as_int(task_val);
        if (task) {
            task->func(task->arg);
            free(task);
        }
    }
    return NULL;
}

static inline NrThreadPool* nr_pool_new(int64_t num_threads, int64_t queue_size) {
    NrThreadPool* pool = (NrThreadPool*)malloc(sizeof(NrThreadPool));
    pool->tasks = nr_channel_new(queue_size);
    pool->num_threads = num_threads;
    pool->shutdown = 0;
    pool->threads = (NrThread*)malloc(sizeof(NrThread) * num_threads);
    for (int64_t i = 0; i < num_threads; i++) {
        pool->threads[i] = nr_thread_spawn(_nr_pool_worker, pool);
    }
    return pool;
}

static inline void nr_pool_submit(NrThreadPool* pool, void (*func)(void*), void* arg) {
    _MpTask* task = (_MpTask*)malloc(sizeof(_MpTask));
    task->func = func;
    task->arg = arg;
    nr_channel_send(pool->tasks, nr_val_int((int64_t)(uintptr_t)task));
}

static inline void nr_pool_shutdown(NrThreadPool* pool) {
    nr_channel_close(pool->tasks);
    for (int64_t i = 0; i < pool->num_threads; i++) {
        nr_thread_join(pool->threads[i]);
    }
    nr_channel_free(pool->tasks);
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

static void* _nr_parallel_worker(void* arg) {
    _MpParallelChunk* chunk = (_MpParallelChunk*)arg;
    chunk->func(chunk->start, chunk->end, chunk->user_data);
    return NULL;
}

static inline void nr_parallel_for(int64_t start, int64_t end,
                                    int64_t num_threads,
                                    void (*func)(int64_t, int64_t, void*),
                                    void* user_data) {
    if (num_threads <= 1 || end - start <= num_threads) {
        func(start, end, user_data);
        return;
    }
    int64_t chunk_size = (end - start + num_threads - 1) / num_threads;
    _MpParallelChunk* chunks = (_MpParallelChunk*)malloc(sizeof(_MpParallelChunk) * num_threads);
    NrThread* threads = (NrThread*)malloc(sizeof(NrThread) * num_threads);
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
        threads[i] = nr_thread_spawn(_nr_parallel_worker, &chunks[i]);
        actual++;
    }

    for (int64_t i = 0; i < actual; i++) {
        nr_thread_join(threads[i]);
    }
    free(chunks);
    free(threads);
}

/* ---- File I/O ---- */
typedef FILE* NrFile;

static inline NrFile nr_file_open(const char* path, const char* mode) {
    FILE* f = fopen(path, mode);
    if (!f) { fprintf(stderr, "Cannot open file: %s\n", path); exit(1); }
    return f;
}

static inline NrFile nr_file_open_safe(const char* path, const char* mode) {
    /* Returns NULL instead of exiting on failure */
    return fopen(path, mode);
}

static inline void nr_file_close(NrFile f) {
    if (f) fclose(f);
}

static inline void nr_file_write(NrFile f, const char* data) {
    fputs(data, f);
}

static inline void nr_file_write_str(NrFile f, NrStr* s) {
    fwrite(s->data, 1, s->len, f);
}

static inline void nr_file_write_line(NrFile f, const char* data) {
    fputs(data, f);
    fputc('\n', f);
}

static inline void nr_file_write_int(NrFile f, int64_t v) {
    fprintf(f, "%lld", (long long)v);
}

static inline void nr_file_write_float(NrFile f, double v) {
    fprintf(f, "%.6f", v);
}

static inline NrStr* nr_file_read_all(NrFile f) {
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    NrStr* s = (NrStr*)malloc(sizeof(NrStr));
    s->len = sz;
    s->data = (char*)malloc(sz + 1);
    fread(s->data, 1, sz, f);
    s->data[sz] = '\0';
    return s;
}

static inline NrStr* nr_file_read_line(NrFile f) {
    char buf[4096];
    if (!fgets(buf, sizeof(buf), f)) return NULL;
    int64_t len = strlen(buf);
    /* Strip trailing newline */
    if (len > 0 && buf[len-1] == '\n') { buf[--len] = '\0'; }
    if (len > 0 && buf[len-1] == '\r') { buf[--len] = '\0'; }
    NrStr* s = (NrStr*)malloc(sizeof(NrStr));
    s->len = len;
    s->data = (char*)malloc(len + 1);
    memcpy(s->data, buf, len + 1);
    return s;
}

static inline int nr_file_eof(NrFile f) {
    return feof(f);
}

static inline int nr_file_exists(const char* path) {
    FILE* f = fopen(path, "r");
    if (f) { fclose(f); return 1; }
    return 0;
}

static inline int64_t nr_file_size(const char* path) {
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

static inline int nr_dir_create(const char* path) {
    return mp_mkdir(path) == 0;
}

static inline int nr_dir_remove(const char* path) {
    return mp_rmdir(path) == 0;
}

static inline int nr_dir_exists(const char* path) {
#ifdef _WIN32
    DWORD attr = GetFileAttributesA(path);
    return (attr != INVALID_FILE_ATTRIBUTES && (attr & FILE_ATTRIBUTE_DIRECTORY));
#else
    struct stat st;
    return (stat(path, &st) == 0 && S_ISDIR(st.st_mode));
#endif
}

static inline NrStr* nr_dir_cwd(void) {
    char buf[4096];
    if (mp_getcwd(buf, sizeof(buf))) {
        return nr_str_new(buf);
    }
    return nr_str_new(".");
}

static inline int nr_dir_chdir(const char* path) {
    return mp_chdir(path) == 0;
}

static inline NrList* nr_dir_list(const char* path) {
    NrList* result = nr_list_new();
#ifdef _WIN32
    WIN32_FIND_DATAA fd;
    char pattern[4096];
    snprintf(pattern, sizeof(pattern), "%s\\*", path);
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE) return result;
    do {
        if (strcmp(fd.cFileName, ".") == 0 || strcmp(fd.cFileName, "..") == 0) continue;
        NrStr* name = nr_str_new(fd.cFileName);
        nr_list_append(result, nr_val_str(name));
    } while (FindNextFileA(h, &fd));
    FindClose(h);
#else
    DIR* d = opendir(path);
    if (!d) return result;
    struct dirent* ent;
    while ((ent = readdir(d)) != NULL) {
        if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) continue;
        NrStr* name = nr_str_new(ent->d_name);
        nr_list_append(result, nr_val_str(name));
    }
    closedir(d);
#endif
    return result;
}

/* ---- Path helpers ---- */
static inline NrStr* nr_path_join(const char* a, const char* b) {
    int64_t la = strlen(a), lb = strlen(b);
    NrStr* s = (NrStr*)malloc(sizeof(NrStr));
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

static inline NrStr* nr_path_ext(const char* path) {
    const char* dot = strrchr(path, '.');
    if (!dot || dot == path) return nr_str_new("");
    return nr_str_new(dot);
}

static inline NrStr* nr_path_basename(const char* path) {
    const char* last_sep = strrchr(path, '/');
#ifdef _WIN32
    const char* last_bsep = strrchr(path, '\\');
    if (last_bsep && (!last_sep || last_bsep > last_sep)) last_sep = last_bsep;
#endif
    if (last_sep) return nr_str_new(last_sep + 1);
    return nr_str_new(path);
}

static inline NrStr* nr_path_dirname(const char* path) {
    const char* last_sep = strrchr(path, '/');
#ifdef _WIN32
    const char* last_bsep = strrchr(path, '\\');
    if (last_bsep && (!last_sep || last_bsep > last_sep)) last_sep = last_bsep;
#endif
    if (!last_sep) return nr_str_new(".");
    int64_t len = last_sep - path;
    NrStr* s = (NrStr*)malloc(sizeof(NrStr));
    s->len = len;
    s->data = (char*)malloc(len + 1);
    memcpy(s->data, path, len);
    s->data[len] = '\0';
    return s;
}

static inline int nr_remove(const char* path) {
    return remove(path) == 0;
}

static inline int nr_rename(const char* old_path, const char* new_path) {
    return rename(old_path, new_path) == 0;
}

/* ---- Arena Allocator ---- */
struct NrArena {
    char* data;
    int64_t size;
    int64_t offset;
};

static inline NrArena* nr_arena_new(int64_t size) {
    NrArena* a = (NrArena*)malloc(sizeof(NrArena));
    a->data = (char*)malloc(size);
    a->size = size;
    a->offset = 0;
    return a;
}

static inline void* nr_arena_alloc(NrArena* a, int64_t bytes) {
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

static inline void nr_arena_reset(NrArena* a) {
    a->offset = 0;
}

static inline void nr_arena_free(NrArena* a) {
    if (a) { free(a->data); free(a); }
}

/* Arena-backed containers: allocate from arena, never individually freed */
static inline NrList* nr_arena_list_new(NrArena* a) {
    NrList* l = (NrList*)nr_arena_alloc(a, sizeof(NrList));
    l->cap = 8; l->len = 0;
    l->data = (NrVal*)nr_arena_alloc(a, sizeof(NrVal) * l->cap);
    return l;
}

static inline NrStr* nr_arena_str_new(NrArena* a, const char* s) {
    NrStr* str = (NrStr*)nr_arena_alloc(a, sizeof(NrStr));
    str->len = strlen(s);
    str->data = (char*)nr_arena_alloc(a, str->len + 1);
    memcpy(str->data, s, str->len + 1);
    return str;
}

static inline NrStr* nr_arena_str_new_len(NrArena* a, const char* s, int64_t len) {
    NrStr* str = (NrStr*)nr_arena_alloc(a, sizeof(NrStr));
    str->len = len;
    str->data = (char*)nr_arena_alloc(a, len + 1);
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

/* ---- Topology-aware reload manager ---- */

/* A loaded cluster — tracks the .so handle and its registration function */
typedef struct {
    const char* name;         /* cluster name (e.g. "renderer") */
    const char* path;         /* path to .so/.dylib/.dll */
    void* handle;             /* dlopen handle */
    int64_t load_time;        /* timestamp of last load */
    int32_t generation;       /* reload generation counter */
    int32_t reloadable;       /* 1 if swappable, 0 if pinned */
} NrCluster;

/* Reload manager — owns all loaded clusters */
typedef struct {
    NrCluster* clusters;
    int32_t count;
    int32_t cap;
} NrReloadManager;

static inline NrReloadManager nr_reload_manager_new(int32_t cap) {
    NrReloadManager rm;
    rm.clusters = (NrCluster*)calloc(cap, sizeof(NrCluster));
    rm.count = 0;
    rm.cap = cap;
    return rm;
}

static inline void nr_reload_manager_free(NrReloadManager* rm) {
    for (int32_t i = 0; i < rm->count; i++) {
        if (rm->clusters[i].handle) {
            hotreload_close(rm->clusters[i].handle);
        }
    }
    free(rm->clusters);
    rm->clusters = NULL;
    rm->count = 0;
}

/* Register a cluster (called once at startup per .so) */
static inline int32_t nr_reload_register(NrReloadManager* rm,
                                          const char* name,
                                          const char* path,
                                          int32_t reloadable) {
    if (rm->count >= rm->cap) return -1;
    int32_t id = rm->count++;
    rm->clusters[id].name = name;
    rm->clusters[id].path = path;
    rm->clusters[id].handle = NULL;
    rm->clusters[id].load_time = 0;
    rm->clusters[id].generation = 0;
    rm->clusters[id].reloadable = reloadable;
    return id;
}

/* Load a cluster's .so and call its registration function.
   The register_fn_name should be "nr_dispatch_register_cluster_N".
   Returns 0 on success, -1 on failure. */
static inline int32_t nr_reload_load(NrReloadManager* rm, int32_t id) {
    if (id < 0 || id >= rm->count) return -1;
    NrCluster* cl = &rm->clusters[id];

    /* Close existing handle if reloading */
    if (cl->handle) {
        hotreload_close(cl->handle);
        cl->handle = NULL;
    }

    cl->handle = hotreload_open(cl->path);
    if (!cl->handle) {
        fprintf(stderr, "nr_reload: failed to load %s (%s)\n",
                cl->name, cl->path);
        return -1;
    }

    /* Look for and call the dispatch registration function */
    char reg_name[128];
    snprintf(reg_name, sizeof(reg_name),
             "nr_dispatch_register_cluster_%d", id);
    void (*reg_fn)(void) = (void(*)(void))hotreload_sym(cl->handle, reg_name);
    if (reg_fn) {
        reg_fn();
    }

    cl->generation++;
    cl->load_time = (int64_t)time(NULL);
    return 0;
}

/* Reload a cluster if it is swappable. Returns 0 on success, -1 on error,
   1 if the cluster is pinned and cannot be reloaded. */
static inline int32_t nr_reload(NrReloadManager* rm, int32_t id) {
    if (id < 0 || id >= rm->count) return -1;
    if (!rm->clusters[id].reloadable) {
        fprintf(stderr, "nr_reload: cluster '%s' is pinned (non-swappable)\n",
                rm->clusters[id].name);
        return 1;
    }
    return nr_reload_load(rm, id);
}

/* Reload a cluster by name. Returns 0 on success. */
static inline int32_t nr_reload_by_name(NrReloadManager* rm,
                                         const char* name) {
    for (int32_t i = 0; i < rm->count; i++) {
        if (strcmp(rm->clusters[i].name, name) == 0) {
            return nr_reload(rm, i);
        }
    }
    fprintf(stderr, "nr_reload: cluster '%s' not found\n", name);
    return -1;
}

/* Reload all swappable clusters. Returns number of failures. */
static inline int32_t nr_reload_all(NrReloadManager* rm) {
    int32_t failures = 0;
    for (int32_t i = 0; i < rm->count; i++) {
        if (rm->clusters[i].reloadable) {
            if (nr_reload_load(rm, i) != 0) {
                failures++;
            }
        }
    }
    return failures;
}

/* ---- Binary I/O (NrWriter / NrReader) ---- */

struct NrWriter {
    uint8_t* data;
    int64_t len;
    int64_t cap;
};

static inline NrWriter* nr_writer_new(int64_t initial_cap) {
    NrWriter* w = (NrWriter*)malloc(sizeof(NrWriter));
    if (initial_cap < 64) initial_cap = 64;
    w->data = (uint8_t*)malloc(initial_cap);
    w->len = 0;
    w->cap = initial_cap;
    return w;
}

static inline void nr_writer_free(NrWriter* w) {
    if (w) { free(w->data); free(w); }
}

static inline int64_t nr_writer_pos(NrWriter* w) { return w->len; }

static inline void _nr_writer_grow(NrWriter* w, int64_t need) {
    if (w->len + need <= w->cap) return;
    while (w->cap < w->len + need) w->cap *= 2;
    w->data = (uint8_t*)realloc(w->data, w->cap);
}

static inline void nr_write_bytes(NrWriter* w, const void* ptr, int64_t n) {
    _nr_writer_grow(w, n);
    memcpy(w->data + w->len, ptr, n);
    w->len += n;
}

static inline void nr_write_i8 (NrWriter* w, int8_t   v) { nr_write_bytes(w, &v, 1); }
static inline void nr_write_i16(NrWriter* w, int16_t  v) { nr_write_bytes(w, &v, 2); }
static inline void nr_write_i32(NrWriter* w, int32_t  v) { nr_write_bytes(w, &v, 4); }
static inline void nr_write_i64(NrWriter* w, int64_t  v) { nr_write_bytes(w, &v, 8); }
static inline void nr_write_u8 (NrWriter* w, uint8_t  v) { nr_write_bytes(w, &v, 1); }
static inline void nr_write_u16(NrWriter* w, uint16_t v) { nr_write_bytes(w, &v, 2); }
static inline void nr_write_u32(NrWriter* w, uint32_t v) { nr_write_bytes(w, &v, 4); }
static inline void nr_write_u64(NrWriter* w, uint64_t v) { nr_write_bytes(w, &v, 8); }
static inline void nr_write_f32(NrWriter* w, float    v) { nr_write_bytes(w, &v, 4); }
static inline void nr_write_f64(NrWriter* w, double   v) { nr_write_bytes(w, &v, 8); }
static inline void nr_write_bool(NrWriter* w, int     v) { uint8_t b = v ? 1 : 0; nr_write_bytes(w, &b, 1); }

static inline void nr_write_text(NrWriter* w, NrStr* s) {
    nr_write_bytes(w, s->data, s->len);
}

static inline void nr_write_str(NrWriter* w, NrStr* s) {
    int32_t slen = (int32_t)s->len;
    nr_write_bytes(w, &slen, 4);
    nr_write_bytes(w, s->data, slen);
}

static inline uint8_t* nr_writer_to_bytes(NrWriter* w, int64_t* out_len) {
    *out_len = w->len;
    uint8_t* buf = w->data;
    w->data = NULL;
    w->len = 0;
    w->cap = 0;
    return buf;
}

struct NrReader {
    const uint8_t* data;
    int64_t len;
    int64_t pos;
};

static inline NrReader* nr_reader_new(const uint8_t* buf, int64_t len) {
    NrReader* r = (NrReader*)malloc(sizeof(NrReader));
    r->data = buf;
    r->len = len;
    r->pos = 0;
    return r;
}

static inline void nr_reader_free(NrReader* r) { if (r) free(r); }

static inline int64_t nr_reader_pos(NrReader* r) { return r->pos; }

static inline void nr_read_bytes(NrReader* r, void* dst, int64_t n) {
    if (r->pos + n > r->len) {
        fprintf(stderr, "NrReader: read past end (pos=%lld, need=%lld, len=%lld)\n",
                (long long)r->pos, (long long)n, (long long)r->len);
        abort();
    }
    memcpy(dst, r->data + r->pos, n);
    r->pos += n;
}

static inline int8_t   nr_read_i8 (NrReader* r) { int8_t   v; nr_read_bytes(r, &v, 1); return v; }
static inline int16_t  nr_read_i16(NrReader* r) { int16_t  v; nr_read_bytes(r, &v, 2); return v; }
static inline int32_t  nr_read_i32(NrReader* r) { int32_t  v; nr_read_bytes(r, &v, 4); return v; }
static inline int64_t  nr_read_i64(NrReader* r) { int64_t  v; nr_read_bytes(r, &v, 8); return v; }
static inline uint8_t  nr_read_u8 (NrReader* r) { uint8_t  v; nr_read_bytes(r, &v, 1); return v; }
static inline uint16_t nr_read_u16(NrReader* r) { uint16_t v; nr_read_bytes(r, &v, 2); return v; }
static inline uint32_t nr_read_u32(NrReader* r) { uint32_t v; nr_read_bytes(r, &v, 4); return v; }
static inline uint64_t nr_read_u64(NrReader* r) { uint64_t v; nr_read_bytes(r, &v, 8); return v; }
static inline float    nr_read_f32(NrReader* r) { float    v; nr_read_bytes(r, &v, 4); return v; }
static inline double   nr_read_f64(NrReader* r) { double   v; nr_read_bytes(r, &v, 8); return v; }
static inline int      nr_read_bool(NrReader* r) { uint8_t b; nr_read_bytes(r, &b, 1); return b ? 1 : 0; }

static inline NrStr* nr_read_str(NrReader* r) {
    int32_t slen;
    nr_read_bytes(r, &slen, 4);
    NrStr* s = (NrStr*)malloc(sizeof(NrStr));
    s->len = slen;
    s->data = (char*)malloc(slen + 1);
    nr_read_bytes(r, s->data, slen);
    s->data[slen] = '\0';
    return s;
}

/* ---- Pointer Set (for graph serialization) ---- */

typedef struct NrPtrSet {
    void** ptrs;
    uint32_t* types;
    int32_t count;
    int32_t cap;
} NrPtrSet;

static inline void nr_ptrset_init(NrPtrSet* s, int32_t cap) {
    s->ptrs = (void**)malloc(sizeof(void*) * cap);
    s->types = (uint32_t*)malloc(sizeof(uint32_t) * cap);
    s->count = 0;
    s->cap = cap;
}

static inline int32_t nr_ptrset_find(NrPtrSet* s, void* p) {
    for (int32_t i = 0; i < s->count; i++) {
        if (s->ptrs[i] == p) return i;
    }
    return -1;
}

static inline int32_t nr_ptrset_add(NrPtrSet* s, void* p, uint32_t type_hash) {
    int32_t idx = nr_ptrset_find(s, p);
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

static inline void nr_ptrset_free(NrPtrSet* s) {
    free(s->ptrs);
    free(s->types);
}

/* ---- Binary File I/O ---- */

static inline int nr_write_file_bin(const char* path, const uint8_t* buf, int64_t len) {
    FILE* f = fopen(path, "wb");
    if (!f) return -1;
    fwrite(buf, 1, len, f);
    fclose(f);
    return 0;
}

static inline uint8_t* nr_read_file_bin(const char* path, int64_t* out_len) {
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
static inline NrStr* mp_input(const char* prompt) {
    if (prompt) { fputs(prompt, stdout); fflush(stdout); }
    char _buf[4096];
    if (!fgets(_buf, sizeof(_buf), stdin)) return nr_str_new("");
    size_t _n = strlen(_buf);
    if (_n > 0 && _buf[_n - 1] == '\n') _buf[--_n] = '\0';
    return nr_str_new(_buf);
}

/* ---- Safety checks (--safe) ---- */
#ifdef NR_SAFE

__attribute__((cold, noreturn))
static void _nr_safe_panic(const char* msg, const char* file, int line) {
    fprintf(stderr, "%s:%d: %s\n", file, line, msg);
    abort();
}

/* Division by zero */
static inline int64_t nr_safe_div_i64(int64_t a, int64_t b, const char* file, int line) {
    if (__builtin_expect(b == 0, 0))
        _nr_safe_panic("division by zero", file, line);
    if (__builtin_expect(a == INT64_MIN && b == -1, 0))
        _nr_safe_panic("integer overflow in division (INT64_MIN / -1)", file, line);
    return a / b;
}
static inline int64_t nr_safe_mod_i64(int64_t a, int64_t b, const char* file, int line) {
    if (__builtin_expect(b == 0, 0))
        _nr_safe_panic("division by zero (modulo)", file, line);
    return a % b;
}

/* Bounds checking */
static inline void nr_safe_bounds_check(int64_t idx, int64_t len, const char* file, int line) {
    if (__builtin_expect(idx < 0 || idx >= len, 0)) {
        char _buf[128];
        snprintf(_buf, sizeof(_buf), "index %lld out of bounds (size %lld)",
                 (long long)idx, (long long)len);
        _nr_safe_panic(_buf, file, line);
    }
}

/* Integer overflow */
static inline int64_t nr_safe_add_i64(int64_t a, int64_t b, const char* file, int line) {
    int64_t r;
    if (__builtin_expect(__builtin_add_overflow(a, b, &r), 0))
        _nr_safe_panic("integer overflow in addition", file, line);
    return r;
}
static inline int64_t nr_safe_sub_i64(int64_t a, int64_t b, const char* file, int line) {
    int64_t r;
    if (__builtin_expect(__builtin_sub_overflow(a, b, &r), 0))
        _nr_safe_panic("integer overflow in subtraction", file, line);
    return r;
}
static inline int64_t nr_safe_mul_i64(int64_t a, int64_t b, const char* file, int line) {
    int64_t r;
    if (__builtin_expect(__builtin_mul_overflow(a, b, &r), 0))
        _nr_safe_panic("integer overflow in multiplication", file, line);
    return r;
}

/* Null pointer dereference */
static inline void nr_safe_null_check(const void* p, const char* file, int line) {
    if (__builtin_expect(p == NULL, 0))
        _nr_safe_panic("null pointer dereference", file, line);
}

#endif /* NR_SAFE */

#endif /* MICROPY_RT_H */
