"nathra"
struct Point:
    x: float
    y: float

    def __init__(self, x: float, y: float) -> void:
        self.x = x
        self.y = y


def safe_div(a: int, b: int) -> Result[int]:
    if b == 0:
        raise "division by zero"
    return Ok(a // b)


def double_div(a: int, b: int, c: int) -> Result[int]:
    # try_unwrap propagates errors automatically
    mid: int = try_unwrap(safe_div(a, b))
    result: int = try_unwrap(safe_div(mid, c))
    return Ok(result)


def parse_positive(n: int) -> Result[int]:
    if n <= 0:
        return Err("must be positive")
    return Ok(n * 2)


@test
def test_ok_result() -> void:
    r: Result[int] = safe_div(10, 2)
    test_assert(is_ok(r))
    test_assert(unwrap(r) == 5)


@test
def test_err_result() -> void:
    r: Result[int] = safe_div(10, 0)
    test_assert(is_err(r))
    # err_msg(r) would return "division by zero"


@test
def test_try_unwrap_success() -> void:
    r: Result[int] = double_div(100, 5, 2)
    test_assert(is_ok(r))
    test_assert(unwrap(r) == 10)


@test
def test_try_unwrap_propagates() -> void:
    r: Result[int] = double_div(100, 0, 2)
    test_assert(is_err(r))


@test
def test_const_param() -> void:
    s: const[cstr] = "hello"
    test_assert(s[0] == 104)   # 'h'


@test
def test_named_init_no_ctor() -> void:
    # Struct without __init__ — designated initializer
    p: Point = Point(1.5, 2.5)
    test_assert(p.x == 1.5)
    test_assert(p.y == 2.5)


@test
def test_named_init_kwargs() -> void:
    p: Point = Point(y=9.0, x=3.0)
    test_assert(p.x == 3.0)
    test_assert(p.y == 9.0)