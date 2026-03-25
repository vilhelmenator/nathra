#define MICROPY_RT_IMPL
#include "micropy_rt.h"

/* Public entry point — short alias for ctypes callers */
int32_t native_compile_file_native_compile(const uint8_t*, int64_t, uint8_t**, int64_t*);
int32_t native_compile(const uint8_t* buf, int64_t len, uint8_t** out, int64_t* out_len) {
    return native_compile_file_native_compile(buf, len, out, out_len);
}
