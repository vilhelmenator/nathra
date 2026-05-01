"nathra"
# Regression tests for implicit addr_of at call sites (item 3).
# Passing a T value to a function that takes ptr[T] auto-wraps with `&`.
# Only addressable lvalues (locals, struct fields, array elements) are auto-wrapped.

struct CounterAA:
    n: int


def bump_counter(c: ptr[CounterAA]) -> void:
    c.n = c.n + 1


def square_int(v: ptr[int]) -> void:
    v.value = v.value * v.value


def already_pointer(p: ptr[int]) -> int:
    return p.value


@test
def test_auto_addrof_struct_local() -> void:
    c: CounterAA = CounterAA(0)
    bump_counter(c)
    test_assert(c.n == 1)
    bump_counter(c)
    bump_counter(c)
    test_assert(c.n == 3)


@test
def test_auto_addrof_scalar_local() -> void:
    n: int = 5
    square_int(n)
    test_assert(n == 25)


@test
def test_explicit_addr_of_still_works() -> void:
    # User can still write addr_of explicitly — it shouldn't double-wrap.
    n: int = 7
    p: ptr[int] = addr_of(n)
    r: int = already_pointer(p)
    test_assert(r == 7)


@test
def test_array_element_auto_addrof() -> void:
    nums: array[int, 3] = [1, 2, 3]
    square_int(nums[1])  # auto: square_int(&(nums[1]))
    test_assert(nums[1] == 4)
