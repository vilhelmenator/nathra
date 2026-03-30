"nathra"
@test
def test_abs() -> void:
    test_assert(abs(-5) == 5)
    test_assert(abs(5) == 5)
    x: float = -3.14
    test_assert(abs(x) == 3.14)


@test
def test_min_max() -> void:
    test_assert(min(3, 7) == 3)
    test_assert(max(3, 7) == 7)
    test_assert(min(7, 3) == 3)
    test_assert(max(7, 3) == 7)
    a: float = 1.5
    b: float = 2.5
    test_assert(min(a, b) == 1.5)
    test_assert(max(a, b) == 2.5)


@test
def test_int_float_cast() -> void:
    x: float = 3.9
    n: int = int(x)
    test_assert(n == 3)
    m: int = 7
    f: float = float(m)
    test_assert(f == 7.0)


@test
def test_is_none() -> void:
    p: ptr[int] = NULL
    test_assert(p is None)
    test_assert(not (p is not None))


@test
def test_range_negative_step() -> void:
    total: int = 0
    for i in range(5, 0, -1):
        total += i
    test_assert(total == 15)


@test
def test_range_negative_literal() -> void:
    count: int = 0
    for i in range(10, 0, -2):
        count += 1
    test_assert(count == 5)