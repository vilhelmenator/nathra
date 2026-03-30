"nathra"
@generic(T=["int", "float"])
def double_it(x: T) -> T:
    return x * 2


@generic(T=["int", "float"])
def clamp(val: T, lo: T, hi: T) -> T:
    if val < lo:
        return lo
    if val > hi:
        return hi
    return val


@generic(T=["int", "float"])
def sum_array(data: ptr[T], n: int) -> T:
    total: T = cast_int(0)
    for i in range(n):
        total = total + data[i]
    return total


@compile_time
def gen_squares() -> list:
    return [i * i for i in range(6)]


SQUARES: array[int, 6] = gen_squares()


@test
def test_generic_double_int() -> void:
    x: int = double_it_int(7)
    test_assert(x == 14)
    test_assert(double_it_int(0) == 0)
    test_assert(double_it_int(-3) == -6)


@test
def test_generic_double_float() -> void:
    x: float = double_it_float(3.5)
    test_assert(x == 7.0)
    test_assert(double_it_float(0.0) == 0.0)


@test
def test_generic_clamp_int() -> void:
    test_assert(clamp_int(5, 0, 10) == 5)
    test_assert(clamp_int(-5, 0, 10) == 0)
    test_assert(clamp_int(15, 0, 10) == 10)
    test_assert(clamp_int(0, 0, 10) == 0)
    test_assert(clamp_int(10, 0, 10) == 10)


@test
def test_generic_clamp_float() -> void:
    test_assert(clamp_float(0.5, 0.0, 1.0) == 0.5)
    test_assert(clamp_float(-1.0, 0.0, 1.0) == 0.0)
    test_assert(clamp_float(2.0, 0.0, 1.0) == 1.0)


@test
def test_compile_time_squares() -> void:
    test_assert(SQUARES[0] == 0)
    test_assert(SQUARES[1] == 1)
    test_assert(SQUARES[2] == 4)
    test_assert(SQUARES[3] == 9)
    test_assert(SQUARES[4] == 16)
    test_assert(SQUARES[5] == 25)
