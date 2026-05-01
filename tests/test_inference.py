"nathra"
# Regression tests for local type inference (item 1).
# Plain `x = expr` infers the type from the RHS when the name is undeclared.
# Annotations always win — if you declare `x: int`, that's what it is.

struct PointInf:
    x: int
    y: int

def double_int(v: int) -> int:
    return v * 2


@test
def test_infer_int_constant() -> void:
    a = 42
    test_assert(a == 42)
    a = a + 1
    test_assert(a == 43)


@test
def test_infer_float_constant() -> void:
    pi = 3.14
    test_assert(pi > 3.0)
    test_assert(pi < 4.0)


@test
def test_infer_string_literal() -> void:
    s = "hello"
    test_assert(str_len(s) == 5)


@test
def test_infer_from_call() -> void:
    n = double_int(21)
    test_assert(n == 42)


@test
def test_infer_from_binop() -> void:
    a = 10
    b = a + 5
    c = b * 2
    test_assert(c == 30)


@test
def test_infer_from_attribute() -> void:
    p: PointInf = PointInf(7, 11)
    x_copy = p.x
    test_assert(x_copy == 7)


@test
def test_infer_from_ifexp() -> void:
    cond: int = 1
    chosen = 100 if cond else 200
    test_assert(chosen == 100)


@test
def test_annotation_wins() -> void:
    # int8_t annotation wins over int64_t inference
    n: int8_t = 5
    test_assert(n == 5)
