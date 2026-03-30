"nathra"
def apply(fn: func[int, int], x: int) -> int:
    return fn(x)


def apply2(fn: func[int, int, int], x: int, y: int) -> int:
    return fn(x, y)


@test
def test_lambda_basic() -> void:
    dbl: func[int, int] = lambda x: x * 2
    test_assert(dbl(5) == 10)
    test_assert(apply(dbl, 7) == 14)


@test
def test_lambda_passed() -> void:
    add: func[int, int, int] = lambda x, y: x + y
    test_assert(add(3, 4) == 7)
    test_assert(apply2(add, 10, 20) == 30)


@test
def test_lambda_reuse() -> void:
    sq: func[int, int] = lambda x: x * x
    test_assert(sq(4) == 16)
    test_assert(sq(10) == 100)