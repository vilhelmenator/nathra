"nathra"
struct Vec2:
    x: float
    y: float

    def __init__(self, x: float, y: float) -> void:
        self.x = x
        self.y = y


@test
def test_structlist_append_get() -> void:
    pts: list[Vec2] = list_new()
    pts.append(Vec2(1.0, 2.0))
    pts.append(Vec2(3.0, 4.0))
    test_assert(len(pts) == 2)
    v: Vec2 = pts[0]
    test_assert(v.x == 1.0)
    test_assert(v.y == 2.0)


@test
def test_structlist_set() -> void:
    pts: list[Vec2] = list_new()
    pts.append(Vec2(0.0, 0.0))
    pts[0] = Vec2(5.0, 6.0)
    v: Vec2 = pts[0]
    test_assert(v.x == 5.0)
    test_assert(v.y == 6.0)


@test
def test_structlist_pop() -> void:
    pts: list[Vec2] = list_new()
    pts.append(Vec2(1.0, 0.0))
    pts.append(Vec2(2.0, 0.0))
    last: Vec2 = pts.pop()
    test_assert(last.x == 2.0)
    test_assert(len(pts) == 1)


@test
def test_structlist_comprehension() -> void:
    pts: list[Vec2] = [Vec2(3.0, 4.0) for _ in range(3)]
    test_assert(len(pts) == 3)
    v: Vec2 = pts[0]
    test_assert(v.x == 3.0)
    test_assert(v.y == 4.0)
    pts.append(Vec2(99.0, 0.0))
    test_assert(pts.len() == 4)