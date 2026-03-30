"nathra"
from nathra_stubs import *


# Branch-free select: if/else with same-variable pure assignment → ternary
def clamp(x: int, lo: int, hi: int) -> int:
    result: int = x
    if x < lo:
        result = lo
    else:
        result = x
    if result > hi:
        result = hi
    else:
        result = result
    return result


def abs_val(x: int) -> int:
    result: int = 0
    if x < 0:
        result = -x
    else:
        result = x
    return result


# Loop trip-count hint: range(N) with N <= 8 → #pragma GCC unroll N
def sum4(arr: ptr[int]) -> int:
    total: int = 0
    for i in range(4):
        total = total + arr[i]
    return total


def sum8(arr: ptr[int]) -> int:
    total: int = 0
    for i in range(8):
        total = total + arr[i]
    return total


# range(9) should NOT get the pragma (above threshold)
def sum9(arr: ptr[int]) -> int:
    total: int = 0
    for i in range(9):
        total = total + arr[i]
    return total


@test
def test_branch_free_clamp() -> void:
    test_assert(clamp(5, 0, 10) == 5)
    test_assert(clamp(-3, 0, 10) == 0)
    test_assert(clamp(15, 0, 10) == 10)


@test
def test_branch_free_abs() -> void:
    test_assert(abs_val(7) == 7)
    test_assert(abs_val(-7) == 7)
    test_assert(abs_val(0) == 0)


@test
def test_trip_count_sum4() -> void:
    data: array[int, 4]
    data[0] = 1
    data[1] = 2
    data[2] = 3
    data[3] = 4
    test_assert(sum4(ref(data[0])) == 10)


@test
def test_trip_count_sum8() -> void:
    data: array[int, 8]
    i: int = 0
    while i < 8:
        data[i] = i + 1
        i = i + 1
    test_assert(sum8(ref(data[0])) == 36)