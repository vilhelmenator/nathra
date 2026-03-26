#define MICROPY_RT_IMPL
#include "micropy_rt.h"

/* Public entry points -- short aliases for ctypes callers */
int32_t native_compile_file_native_compile(const uint8_t*, int64_t, uint8_t**, int64_t*);
int32_t native_compile(const uint8_t* buf, int64_t len, uint8_t** out, int64_t* out_len) {
    return native_compile_file_native_compile(buf, len, out, out_len);
}

/* State-based API for cross-module compilation */
typedef struct CompilerState CompilerState;
CompilerState* native_compile_file_native_state_new(void);
int32_t native_compile_file_native_compile_dep(CompilerState*, const uint8_t*, int64_t,
    const uint8_t*, int64_t, uint8_t**, int64_t*, uint8_t**, int64_t*);
int32_t native_compile_file_native_compile_main(CompilerState*, const uint8_t*, int64_t,
    uint8_t**, int64_t*);

CompilerState* native_state_new(void) {
    return native_compile_file_native_state_new();
}
int32_t native_compile_dep(CompilerState* s, const uint8_t* ast, int64_t ast_len,
    const uint8_t* names, int64_t names_len,
    uint8_t** out_c, int64_t* out_c_len,
    uint8_t** out_h, int64_t* out_h_len) {
    return native_compile_file_native_compile_dep(s, ast, ast_len, names, names_len,
        out_c, out_c_len, out_h, out_h_len);
}
int32_t native_compile_main(CompilerState* s, const uint8_t* ast, int64_t ast_len,
    uint8_t** out, int64_t* out_len) {
    return native_compile_file_native_compile_main(s, ast, ast_len, out, out_len);
}
