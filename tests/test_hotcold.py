"nathra"
from nathra_stubs import *


# Cold arm: body is a single raise → extracted to static __attribute__((cold, noreturn))
def safe_divide(a: int, b: int) -> int:
    if b == 0:
        raise "division by zero"
    return a / b


# Cold arm: else branch raises
def require_positive(x: int) -> int:
    if x > 0:
        return x
    else:
        raise "value must be positive"


# Cold arm uses a captured local variable in the raise message
def validate_range(val: int, limit: int) -> int:
    if val >= limit:
        raise "value out of range"
    return val


# Hot arm is only-assign, cold arm is raise — only the raise arm is extracted
def clamp_or_raise(x: int, lo: int, hi: int) -> int:
    if x < lo:
        raise "below minimum"
    if x > hi:
        raise "above maximum"
    return x


@test
def test_cold_body_raise() -> void:
    result: int = safe_divide(10, 2)
    test_assert(result == 5)


@test
def test_cold_else_raise() -> void:
    result: int = require_positive(7)
    test_assert(result == 7)


@test
def test_cold_captured_var() -> void:
    result: int = validate_range(3, 10)
    test_assert(result == 3)


@test
def test_cold_double_guard() -> void:
    result: int = clamp_or_raise(5, 0, 10)
    test_assert(result == 5)