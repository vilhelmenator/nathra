#ifndef MICROPY_TYPES_H
#define MICROPY_TYPES_H

/*
 * micropy_types.h — primitive types and forward declarations only.
 *
 * This header intentionally has no #include directives beyond the two
 * standard headers below. It is safe to include from any other header
 * without triggering transitive inclusion of stdio.h, stdlib.h,
 * pthread.h, windows.h, etc.
 *
 * Full struct definitions and runtime functions live in micropy_rt.h,
 * which #includes this file.
 */

#include <stdint.h>
#include <stddef.h>

/* Branch-prediction hints — portable across GCC, Clang, MSVC */
#if defined(__GNUC__) || defined(__clang__)
#  define MP_LIKELY(x)   __builtin_expect(!!(x), 1)
#  define MP_UNLIKELY(x) __builtin_expect(!!(x), 0)
#  define MP_PREFETCH(p, rw, loc) __builtin_prefetch((p), (rw), (loc))
#else
#  define MP_LIKELY(x)   (x)
#  define MP_UNLIKELY(x) (x)
#  define MP_PREFETCH(p, rw, loc) ((void)0)
#endif

/* Thread-local storage qualifier — portable across GCC, Clang, MSVC */
#if defined(_MSC_VER)
#  define MP_TLS __declspec(thread)
#elif defined(__GNUC__) || defined(__clang__)
#  define MP_TLS __thread
#else
#  define MP_TLS _Thread_local
#endif

/* Primitive value type (int or float packed into 64 bits) */
typedef uint64_t MpVal;

/* Forward declarations — pointer-safe without full struct definitions */
typedef struct MpStr        MpStr;
typedef struct MpList       MpList;
typedef struct MpDict       MpDict;
typedef struct MpDictEntry  MpDictEntry;
typedef struct MpArena      MpArena;
typedef struct MpChannel    MpChannel;
typedef struct MpThreadPool MpThreadPool;
typedef struct MpThread     MpThread;
typedef struct MpMutex      MpMutex;
typedef struct MpCond       MpCond;

/* Debug allocation counter — referenced by micropy_rt.h debug wrappers.
 * The definition lives in the main translation unit (emitted by the compiler
 * when --debug is active). */
#ifdef MICROPY_DEBUG
extern volatile long long _mp_alloc_count;
#endif

#endif /* MICROPY_TYPES_H */