"nathra"
def add(a: int, b: int) -> int:
    return a + b


def multiply(a: int, b: int) -> int:
    return a * b


def apply(op: func[int, int, int], a: int, b: int) -> int:
    return op(a, b)


def make_adder_result(x: int) -> int:
    f: func[int, int, int] = add
    return f(x, 10)


def scale2(x: float) -> float:
    return x * 2.0


@test
def test_funcptr_call() -> void:
    f: func[int, int, int] = add
    test_assert(f(3, 4) == 7)
    f = multiply
    test_assert(f(3, 4) == 12)


@test
def test_funcptr_as_arg() -> void:
    test_assert(apply(add, 10, 5) == 15)
    test_assert(apply(multiply, 10, 5) == 50)


@test
def test_funcptr_reassign() -> void:
    result: int = make_adder_result(5)
    test_assert(result == 15)


@test
def test_funcptr_null_init() -> void:
    f: func[float, float] = NULL
    f = scale2
    test_assert(f(3.5) == 7.0)