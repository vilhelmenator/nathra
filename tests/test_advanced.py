"nathra"
class Counter:
    value: int

    def __init__(self, start: int) -> void:
        self.value = start

    def inc(self) -> void:
        self.value += 1

    def get(self) -> int:
        return self.value

    @staticmethod
    def zero() -> Counter:
        return Counter(0)

    @staticmethod
    def from_value(n: int) -> Counter:
        return Counter(n)


class Point:
    x: float
    y: float

    def __init__(self, x: float, y: float) -> void:
        self.x = x
        self.y = y


def make_point(x: float, y: float) -> Point:
    return Point(x, y)


@test
def test_static_method_no_args() -> void:
    c: Counter = Counter.zero()
    test_assert(c.get() == 0)


@test
def test_static_method_with_args() -> void:
    c: Counter = Counter.from_value(42)
    test_assert(c.get() == 42)
    c.inc()
    test_assert(c.get() == 43)


@test
def test_sizeof_builtin() -> void:
    test_assert(sizeof(int) == 8)
    test_assert(sizeof(float) == 8)
    test_assert(sizeof(byte) == 1)
    test_assert(sizeof(Point) == 16)


@test
def test_tuple_unpack_literal() -> void:
    x, y = (10, 20)
    test_assert(x == 10)
    test_assert(y == 20)


@test
def test_tuple_unpack_struct() -> void:
    px, py = make_point(3.0, 4.0)
    test_assert(px == 3.0)
    test_assert(py == 4.0)