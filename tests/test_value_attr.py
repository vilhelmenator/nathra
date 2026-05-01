"nathra"
# Regression tests for `.value` on scalar pointers (item 2).
# `p.value` reads/writes through a scalar pointer.
# Struct fields named `value` keep `->` semantics.

struct Box:
    value: int   # field literally named 'value' — must NOT collide
    label: int


@test
def test_value_read() -> void:
    n: int = 42
    p: ptr[int] = addr_of(n)
    test_assert(p.value == 42)


@test
def test_value_write() -> void:
    n: int = 0
    p: ptr[int] = addr_of(n)
    p.value = 99
    test_assert(n == 99)


@test
def test_value_aug_assign() -> void:
    n: int = 10
    p: ptr[int] = addr_of(n)
    p.value += 5
    test_assert(n == 15)
    p.value *= 2
    test_assert(n == 30)


@test
def test_value_float_pointer() -> void:
    f: float = 0.0
    fp: ptr[float] = addr_of(f)
    fp.value = 3.5
    test_assert(f > 3.4)
    test_assert(f < 3.6)


@test
def test_struct_value_field_unchanged() -> void:
    # A struct field named `value` must still use struct field semantics,
    # NOT scalar-pointer dereference.
    b: Box = Box(7, 100)
    test_assert(b.value == 7)
    bp: ptr[Box] = addr_of(b)
    test_assert(bp.value == 7)
    bp.value = 21
    test_assert(b.value == 21)
