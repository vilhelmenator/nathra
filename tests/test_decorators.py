"nathra"
from nathra_stubs import *

# =====================================================
# @compile_time
# =====================================================

@compile_time
def gen_squares() -> list:
    return [i * i for i in range(8)]

@compile_time
def gen_fizzbuzz_flags() -> list:
    return [1 if (i % 15 == 0) else 0 for i in range(32)]

@compile_time
def gen_powers_of_two() -> list:
    return [1 << i for i in range(8)]

SQUARES:     array[int, 8]  = gen_squares()
FB_FLAGS:    array[int, 32] = gen_fizzbuzz_flags()
POW2:        array[int, 8]  = gen_powers_of_two()


@test
def test_compile_time_squares() -> void:
    test_assert(SQUARES[0] == 0)
    test_assert(SQUARES[1] == 1)
    test_assert(SQUARES[4] == 16)
    test_assert(SQUARES[7] == 49)


@test
def test_compile_time_fizzbuzz() -> void:
    # multiples of 15 in 0..31: 0, 15, 30
    test_assert(FB_FLAGS[0]  == 1)
    test_assert(FB_FLAGS[1]  == 0)
    test_assert(FB_FLAGS[15] == 1)
    test_assert(FB_FLAGS[30] == 1)
    test_assert(FB_FLAGS[16] == 0)


@test
def test_compile_time_powers_of_two() -> void:
    test_assert(POW2[0] == 1)
    test_assert(POW2[1] == 2)
    test_assert(POW2[7] == 128)


# =====================================================
# @generic
# =====================================================

@generic(T=["int", "float"])
def double_val(x: T) -> T:
    return x * 2

@generic(T=["int", "float"])
def max_val(a: T, b: T) -> T:
    if a > b:
        return a
    return b

@generic(T=["int", "float"])
def clamp(val: T, lo: T, hi: T) -> T:
    if val < lo:
        return lo
    if val > hi:
        return hi
    return val

@generic(T=["int", "float"])
def sum_arr(data: ptr[T], n: int) -> T:
    total: T = cast_int(0)
    i: int = 0
    while i < n:
        total = total + data[i]
        i = i + 1
    return total


@test
def test_generic_double_int() -> void:
    test_assert(double_val_int(7)  == 14)
    test_assert(double_val_int(0)  == 0)
    test_assert(double_val_int(-3) == -6)


@test
def test_generic_double_float() -> void:
    test_assert(double_val_float(3.5) == 7.0)
    test_assert(double_val_float(0.0) == 0.0)


@test
def test_generic_max_int() -> void:
    test_assert(max_val_int(10, 20) == 20)
    test_assert(max_val_int(5,  5)  == 5)
    test_assert(max_val_int(-1, 0)  == 0)


@test
def test_generic_max_float() -> void:
    test_assert(max_val_float(3.14, 2.71) == 3.14)


@test
def test_generic_clamp_int() -> void:
    test_assert(clamp_int(5,   0, 10) == 5)
    test_assert(clamp_int(-5,  0, 10) == 0)
    test_assert(clamp_int(15,  0, 10) == 10)


@test
def test_generic_clamp_float() -> void:
    test_assert(clamp_float(0.5,  0.0, 1.0) == 0.5)
    test_assert(clamp_float(-1.0, 0.0, 1.0) == 0.0)
    test_assert(clamp_float(2.0,  0.0, 1.0) == 1.0)


@test
def test_generic_sum_arr_int() -> void:
    data: array[int, 5] = {1, 2, 3, 4, 5}
    test_assert(sum_arr_int(data, 5) == 15)


@test
def test_generic_sum_arr_float() -> void:
    data: array[float, 3] = {1.0, 2.0, 3.0}
    test_assert(sum_arr_float(data, 3) == 6.0)


# =====================================================
# @unroll
# =====================================================

@unroll(4)
def sum_unrolled(data: ptr[int], n: int) -> int:
    total: int = 0
    for i in range(0, n):
        total = total + data[i]
    return total


@test
def test_unroll_sum() -> void:
    data: array[int, 16] = {0}
    i: int = 0
    while i < 16:
        data[i] = i + 1
        i = i + 1
    result: int = sum_unrolled(data, 16)
    test_assert(result == 136)  # sum(1..16)


@test
def test_unroll_small() -> void:
    data: array[int, 4] = {3, 1, 4, 1}
    result: int = sum_unrolled(data, 4)
    test_assert(result == 9)


# =====================================================
# @parallel
# =====================================================

@parallel(threads=4)
def double_array(data: ptr[int], n: int) -> void:
    for i in range(0, n):
        data[i] = data[i] * 2


@test
def test_parallel_double() -> void:
    data: array[int, 16] = {0}
    i: int = 0
    while i < 16:
        data[i] = i + 1
        i = i + 1
    double_array(data, 16)
    test_assert(data[0]  == 2)
    test_assert(data[7]  == 16)
    test_assert(data[15] == 32)


@test
def test_parallel_single_thread() -> void:
    data: array[int, 4] = {5, 10, 15, 20}
    double_array(data, 4)
    test_assert(data[0] == 10)
    test_assert(data[3] == 40)


# =====================================================
# @platform
# =====================================================

@platform("windows")
def platform_name() -> str:
    return str_new("windows")

@platform("linux")
def platform_name() -> str:
    return str_new("linux")

@platform("macos")
def platform_name() -> str:
    return str_new("macos")


@test
def test_platform_name_defined() -> void:
    name: str = platform_name()
    # whichever platform we're on, it must be one of the three
    is_win:   int = str_eq(name, str_new("windows"))
    is_linux: int = str_eq(name, str_new("linux"))
    is_mac:   int = str_eq(name, str_new("macos"))
    test_assert(is_win == 1 or is_linux == 1 or is_mac == 1)