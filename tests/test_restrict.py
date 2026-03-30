"nathra"
from nathra_stubs import *


# Two non-aliasing ptr params → both get restrict
def copy_bytes(dst: ptr[byte], src: ptr[byte], n: int) -> void:
    i: int = 0
    while i < n:
        dst[i] = src[i]
        i = i + 1


# ptr param directly assigned from another ptr param → no restrict on either
def alias_example(a: ptr[int], b: ptr[int]) -> void:
    a = b           # a and b alias → neither gets restrict
    a[0] = b[0]


# Only one ptr param → no restrict (threshold is 2)
def single_ptr(p: ptr[int], n: int) -> void:
    p[0] = n


# Three non-aliasing ptrs → all three get restrict
def triple_copy(dst: ptr[byte], src1: ptr[byte], src2: ptr[byte], n: int) -> void:
    i: int = 0
    while i < n:
        dst[i] = src1[i]
        i = i + 1


@test
def test_restrict_copy() -> void:
    a: array[byte, 8]
    b: array[byte, 8]
    i: int = 0
    while i < 8:
        b[i] = i + 1
        i = i + 1
    copy_bytes(ref(a[0]), ref(b[0]), 8)
    test_assert(a[0] == 1)
    test_assert(a[7] == 8)


@test
def test_restrict_alias_still_works() -> void:
    x: int = 10
    y: int = 20
    alias_example(ref(x), ref(y))
    # alias_example: a = b reassigns local ptr only, then a[0]=b[0] is y=y (no-op)
    # x and y are unchanged
    test_assert(x == 10)
    test_assert(y == 20)