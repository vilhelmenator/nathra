"nathra"
from nathra_stubs import *

# ---- helpers ----

def make_and_free_list() -> int:
    nums: list = list_new()
    defer(list_free(nums))
    list_append(nums, val_int(1))
    list_append(nums, val_int(2))
    list_append(nums, val_int(3))
    return as_int(list_get(nums, 2))

def early_return_with_defer() -> int:
    data: list = list_new()
    defer(list_free(data))
    list_append(data, val_int(42))
    if list_len(data) > 0:
        return as_int(list_get(data, 0))
    return 0

def multi_defer() -> int:
    a: list = list_new()
    defer(list_free(a))
    b: list = list_new()
    defer(list_free(b))
    list_append(a, val_int(10))
    list_append(b, val_int(20))
    return as_int(list_get(a, 0)) + as_int(list_get(b, 0))

def defer_str() -> int:
    s: str = str_new("hello")
    defer(str_free(s))
    return str_len(s)

def defer_dict() -> int:
    d: dict = dict_new()
    defer(dict_free(d))
    dict_set(d, "x", val_int(99))
    return as_int(dict_get(d, "x"))


# ---- tests ----

@test
def test_defer_list_freed_on_exit() -> void:
    result: int = make_and_free_list()
    test_assert(result == 3)


@test
def test_defer_early_return() -> void:
    val: int = early_return_with_defer()
    test_assert(val == 42)


@test
def test_defer_multiple() -> void:
    result: int = multi_defer()
    test_assert(result == 30)


@test
def test_defer_str() -> void:
    n: int = defer_str()
    test_assert(n == 5)


@test
def test_defer_dict() -> void:
    v: int = defer_dict()
    test_assert(v == 99)


@test
def test_defer_inline() -> void:
    nums: list = list_new()
    defer(list_free(nums))
    for i in range(5):
        list_append(nums, val_int(i * i))
    test_assert(list_len(nums) == 5)
    test_assert(as_int(list_get(nums, 4)) == 16)