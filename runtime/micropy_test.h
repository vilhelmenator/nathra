
#ifndef MICROPY_TEST_H
#define MICROPY_TEST_H

#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

/* ---- Platform timing ---- */
#if defined(__APPLE__)
#  include <mach/mach_time.h>
static mach_timebase_info_data_t _mp_tb;
static inline void _mp_time_init(void) { mach_timebase_info(&_mp_tb); }
static inline uint64_t _mp_time_ns(void) {
    return (mach_absolute_time() * _mp_tb.numer) / _mp_tb.denom;
}
#elif defined(_WIN32)
#  include <windows.h>
static LARGE_INTEGER _mp_qpf;
static inline void _mp_time_init(void) { QueryPerformanceFrequency(&_mp_qpf); }
static inline uint64_t _mp_time_ns(void) {
    LARGE_INTEGER now; QueryPerformanceCounter(&now);
    return (uint64_t)((1e9 * (double)now.QuadPart) / (double)_mp_qpf.QuadPart);
}
#else
#  include <time.h>
static inline void _mp_time_init(void) {}
static inline uint64_t _mp_time_ns(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}
#endif

/* ---- Human-readable elapsed time ---- */
static inline void _mp_fmt_time(uint64_t ns, char *buf, size_t sz) {
    if      (ns > 1000000000ULL) snprintf(buf, sz, "(%llu seconds)",   (unsigned long long)(ns / 1000000000ULL));
    else if (ns > 1000000ULL)    snprintf(buf, sz, "(%llu milli sec)", (unsigned long long)(ns / 1000000ULL));
    else if (ns > 1000ULL)       snprintf(buf, sz, "(%llu micro sec)", (unsigned long long)(ns / 1000ULL));
    else                         snprintf(buf, sz, "(%llu nano sec)",  (unsigned long long)ns);
}

/* ---- ANSI color ---- */
#if defined(_WIN32)
#  include <io.h>
#  define _mp_use_color() (_isatty(_fileno(stdout)))
#else
#  include <unistd.h>
static inline int _mp_use_color(void) { return isatty(fileno(stdout)); }
#endif

static inline void _mp_cprint(const char *color, const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    if (_mp_use_color()) fputs(color, stdout);
    vprintf(fmt, ap);
    if (_mp_use_color()) fputs("\033[0m", stdout);
    va_end(ap);
}
#define _MP_GREEN "\033[32m"
#define _MP_RED   "\033[31m"

/* ---- Global test state ---- */
static int _mp_test_failures   = 0;
static int _mp_test_total      = 0;
static int _mp_test_fail_total = 0;

/* ---- Assertion macros ---- */
#define mp_test_assert(cond) do { \
    if (!(cond)) { \
        _mp_test_failures++; \
        fprintf(stderr, "    FAILED: %s (%s:%d)\n", #cond, __FILE__, __LINE__); \
    } \
} while(0)

#define mp_test_assert_msg(cond, msg) do { \
    if (!(cond)) { \
        _mp_test_failures++; \
        fprintf(stderr, "    FAILED: %s — %s (%s:%d)\n", #cond, msg, __FILE__, __LINE__); \
    } \
} while(0)

#define mp_test_assert_eq(a, b) do { \
    if ((a) != (b)) { \
        _mp_test_failures++; \
        fprintf(stderr, "    FAILED eq (%s:%d)\n", __FILE__, __LINE__); \
    } \
} while(0)

#endif /* MICROPY_TEST_H */
