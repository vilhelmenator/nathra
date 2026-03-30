"nathra"
@test
def test_int_arithmetic() -> void:
    a: int = 10
    b: int = 3
    test_assert(a + b == 13)
    test_assert(a - b == 7)
    test_assert(a * b == 30)
    test_assert(a % b == 1)
    test_assert(a // b == 3)


@test
def test_float_arithmetic() -> void:
    a: float = 1.5
    b: float = 2.5
    test_assert(a + b == 4.0)
    test_assert(a * b == 3.75)
    test_assert(b - a == 1.0)


@test
def test_bool_ops() -> void:
    t: bool = True
    f: bool = False
    test_assert(t)
    test_assert(not f)
    test_assert(t and not f)
    test_assert(t or f)
    test_assert(not (f and t))


@test
def test_comparisons() -> void:
    test_assert(1 < 2)
    test_assert(2 <= 2)
    test_assert(3 > 2)
    test_assert(3 >= 3)
    test_assert(1 == 1)
    test_assert(1 != 2)
    test_assert(not (1 > 2))


@test
def test_bitwise() -> void:
    a: int = 10
    b: int = 12
    test_assert((a & b) == 8)
    test_assert((a | b) == 14)
    test_assert((a ^ b) == 6)
    test_assert(a << 1 == 20)
    test_assert(b >> 1 == 6)
    test_assert(~0 == -1)


@test
def test_cast() -> void:
    x: float = 3.9
    y: int = cast_int(x)
    test_assert(y == 3)
    z: float = cast_float(5)
    test_assert(z == 5.0)


@test
def test_ternary() -> void:
    x: int = 10
    big: int = 1 if x > 5 else 0
    test_assert(big == 1)
    small: int = 1 if x > 100 else 0
    test_assert(small == 0)


@test
def test_aug_assign() -> void:
    x: int = 10
    x += 5
    test_assert(x == 15)
    x -= 3
    test_assert(x == 12)
    x *= 2
    test_assert(x == 24)
    x //= 4
    test_assert(x == 6)
    x %= 4
    test_assert(x == 2)
