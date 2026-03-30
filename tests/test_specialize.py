"nathra"
from nathra_stubs import *


# Larger callee — previously blocked by old 20-node cap, now specializes freely
def scaled_sum(arr: ptr[int], n: int, stride: int) -> int:
    total: int = 0
    i: int = 0
    while i < n:
        total = total + arr[i] * stride
        i = i + 1
    return total


# Small callee with two constant params
def scale_add(x: int, factor: int, offset: int) -> int:
    return x * factor + offset


# @hot caller: both callees get 1 distinct constant combo each → specialize freely
@hot
def process_data(arr: ptr[int], n: int) -> int:
    result: int = scaled_sum(arr, n, 4)       # stride=4 constant
    adjusted: int = scale_add(result, 2, 10)  # factor=2, offset=10 constant
    return adjusted


# Multiple distinct constant combos for the same callee — still ≤ 3
@hot
def process_multi(arr: ptr[int], n: int) -> int:
    a: int = scaled_sum(arr, n, 4)   # stride=4
    b: int = scaled_sum(arr, n, 8)   # stride=8  — 2nd distinct combo
    c: int = scaled_sum(arr, n, 16)  # stride=16 — 3rd distinct combo
    return a + b + c


# Non-hot caller — no specialization
def process_data_slow(arr: ptr[int], n: int) -> int:
    return scaled_sum(arr, n, 4)


@test
def test_specialization_hot_path() -> void:
    data: array[int, 4]
    data[0] = 1
    data[1] = 2
    data[2] = 3
    data[3] = 4
    # scaled_sum([1,2,3,4], 4, stride=4) = (1+2+3+4)*4 = 40
    # scale_add(40, factor=2, offset=10) = 40*2+10 = 90
    result: int = process_data(ref(data[0]), 4)
    test_assert(result == 90)


@test
def test_multi_specialization() -> void:
    data: array[int, 4]
    data[0] = 1
    data[1] = 1
    data[2] = 1
    data[3] = 1
    # sum=4, a=4*4=16, b=4*8=32, c=4*16=64 → 112
    result: int = process_multi(ref(data[0]), 4)
    test_assert(result == 112)


@test
def test_non_hot_still_works() -> void:
    data: array[int, 3]
    data[0] = 5
    data[1] = 5
    data[2] = 5
    # scaled_sum([5,5,5], 3, stride=4) = 15*4 = 60
    result: int = process_data_slow(ref(data[0]), 3)
    test_assert(result == 60)