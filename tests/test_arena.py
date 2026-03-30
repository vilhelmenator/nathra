"nathra"
from nathra_stubs import *


@test
def test_arena_str_new() -> void:
    a: arena = arena_new(4096)
    defer(arena_free(a))
    s: str = arena_str_new(a, "hello arena")
    test_assert(str_len(s) == 11)
    test_assert(str_eq(s, str_new("hello arena")) == 1)


@test
def test_arena_list_new() -> void:
    a: arena = arena_new(4096)
    defer(arena_free(a))
    nums: list = arena_list_new(a)
    list_append(nums, val_int(10))
    list_append(nums, val_int(20))
    list_append(nums, val_int(30))
    test_assert(list_len(nums) == 3)
    test_assert(as_int(list_get(nums, 0)) == 10)
    test_assert(as_int(list_get(nums, 2)) == 30)


@test
def test_arena_reset() -> void:
    a: arena = arena_new(4096)
    defer(arena_free(a))
    s: str = arena_str_new(a, "before reset")
    test_assert(str_len(s) == 12)
    arena_reset(a)
    # After reset the arena is reusable
    s2: str = arena_str_new(a, "after reset")
    test_assert(str_len(s2) == 11)


@test
def test_arena_multiple_allocs() -> void:
    a: arena = arena_new(65536)
    defer(arena_free(a))
    i: int = 0
    while i < 10:
        label: str = arena_str_new(a, "item")
        test_assert(str_len(label) == 4)
        i = i + 1
    # All allocations fit — arena still alive
    nums: list = arena_list_new(a)
    list_append(nums, val_int(42))
    test_assert(as_int(list_get(nums, 0)) == 42)


@test
def test_arena_batch_pattern() -> void:
    # Simulate batch processing: one arena per batch, reset between batches
    a: arena = arena_new(4096)
    defer(arena_free(a))
    total: int = 0
    batch: int = 0
    while batch < 3:
        nums: list = arena_list_new(a)
        i: int = 0
        while i < 4:
            list_append(nums, val_int(batch * 10 + i))
            i = i + 1
        total = total + as_int(list_get(nums, 3))
        arena_reset(a)
        batch = batch + 1
    # Last value in each batch: 3, 13, 23 → sum = 39
    test_assert(total == 39)


@test
def test_arena_batch_alloc() -> void:
    # Two arena_alloc calls from same arena → single batched bump allocation
    a: arena = arena_new(4096)
    defer(arena_free(a))
    buf1: ptr[byte] = arena_alloc(a, 64)
    buf2: ptr[byte] = arena_alloc(a, 128)
    buf1[0] = 42
    buf2[0] = 99
    test_assert(buf1[0] == 42)
    test_assert(buf2[0] == 99)


@test
def test_arena_batch_lists() -> void:
    # Two arena_list_new calls from same arena → single batched bump + inline init
    a: arena = arena_new(4096)
    defer(arena_free(a))
    evens: list = arena_list_new(a)
    odds: list = arena_list_new(a)
    list_append(evens, val_int(2))
    list_append(evens, val_int(4))
    list_append(odds, val_int(1))
    list_append(odds, val_int(3))
    test_assert(list_len(evens) == 2)
    test_assert(list_len(odds) == 2)
    test_assert(as_int(list_get(evens, 0)) == 2)
    test_assert(as_int(list_get(odds, 0)) == 1)