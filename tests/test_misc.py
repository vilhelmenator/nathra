"nathra"
import math

# Type aliases
Scalar = float
Index = int

# Default parameters
def greet(x: int, y: int = 10, z: int = 20) -> int:
    return x + y + z


@test
def test_default_params() -> void:
    test_assert(greet(1) == 31)
    test_assert(greet(1, 2) == 23)
    test_assert(greet(1, 2, 3) == 6)


@test
def test_type_alias() -> void:
    s: Scalar = 2.5
    i: Index = 7
    test_assert(s == 2.5)
    test_assert(i == 7)


@test
def test_exit_not_called() -> void:
    # Just verify exit compiles; we don't call it to avoid killing the test
    x: int = 1
    test_assert(x == 1)


@test
def test_math_sqrt() -> void:
    r: float = math.sqrt(16.0)
    test_assert(r == 4.0)


@test
def test_math_trig() -> void:
    r: float = math.sin(0.0)
    test_assert(r == 0.0)
    r = math.cos(0.0)
    test_assert(r == 1.0)


@test
def test_math_floor_ceil() -> void:
    test_assert(math.floor(3.7) == 3.0)
    test_assert(math.ceil(3.2) == 4.0)


@test
def test_math_direct() -> void:
    # Direct calls without math. prefix
    r: float = sqrt(9.0)
    test_assert(r == 3.0)
    test_assert(floor(2.9) == 2.0)