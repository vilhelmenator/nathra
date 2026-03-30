"nathra"
class Vec2:
    x: float
    y: float

    def __init__(self, x: float, y: float) -> void:
        self.x = x
        self.y = y

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2:
        return Vec2(self.x * scalar, self.y * scalar)

    def __neg__(self) -> Vec2:
        return Vec2(-self.x, -self.y)

    def __eq__(self, other: Vec2) -> int:
        return self.x == other.x and self.y == other.y

    def __len__(self) -> int:
        return 2

    def dot(self, other: Vec2) -> float:
        return self.x * other.x + self.y * other.y

    def length_sq(self) -> float:
        return self.x * self.x + self.y * self.y


@test
def test_init() -> void:
    v: Vec2 = Vec2(3.0, 4.0)
    test_assert(v.x == 3.0)
    test_assert(v.y == 4.0)


@test
def test_add() -> void:
    a: Vec2 = Vec2(1.0, 2.0)
    b: Vec2 = Vec2(3.0, 4.0)
    c: Vec2 = a + b
    test_assert(c.x == 4.0)
    test_assert(c.y == 6.0)


@test
def test_sub() -> void:
    a: Vec2 = Vec2(5.0, 7.0)
    b: Vec2 = Vec2(2.0, 3.0)
    c: Vec2 = a - b
    test_assert(c.x == 3.0)
    test_assert(c.y == 4.0)


@test
def test_mul() -> void:
    v: Vec2 = Vec2(2.0, 3.0)
    w: Vec2 = v * 2.0
    test_assert(w.x == 4.0)
    test_assert(w.y == 6.0)


@test
def test_neg() -> void:
    v: Vec2 = Vec2(1.0, -2.0)
    n: Vec2 = -v
    test_assert(n.x == -1.0)
    test_assert(n.y == 2.0)


@test
def test_eq() -> void:
    a: Vec2 = Vec2(1.0, 2.0)
    b: Vec2 = Vec2(1.0, 2.0)
    c: Vec2 = Vec2(9.0, 9.0)
    test_assert(a == b)
    test_assert(not (a == c))


@test
def test_len() -> void:
    v: Vec2 = Vec2(1.0, 2.0)
    test_assert(len(v) == 2)


@test
def test_method_with_pointer_self() -> void:
    a: Vec2 = Vec2(1.0, 0.0)
    b: Vec2 = Vec2(0.0, 1.0)
    d: float = a.dot(b)
    test_assert(d == 0.0)
    lsq: float = a.length_sq()
    test_assert(lsq == 1.0)