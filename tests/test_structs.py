"nathra"
struct Vec2:
    x: float
    y: float


struct Rect:
    x: int
    y: int
    w: int
    h: int


class Direction:
    NORTH = 0
    SOUTH = 1
    EAST = 2
    WEST = 3


@test
def test_struct_fields() -> void:
    v: Vec2 = Vec2(3.0, 4.0)
    test_assert(v.x == 3.0)
    test_assert(v.y == 4.0)


@test
def test_struct_mutation() -> void:
    r: Rect = Rect(0, 0, 100, 50)
    r.x = 10
    r.y = 20
    test_assert(r.x == 10)
    test_assert(r.y == 20)
    test_assert(r.w == 100)
    test_assert(r.h == 50)


@test
def test_struct_reassign() -> void:
    v: Vec2 = Vec2(1.0, 2.0)
    v = Vec2(5.0, 6.0)
    test_assert(v.x == 5.0)
    test_assert(v.y == 6.0)


@test
def test_enum_values() -> void:
    test_assert(Direction.NORTH == 0)
    test_assert(Direction.SOUTH == 1)
    test_assert(Direction.EAST == 2)
    test_assert(Direction.WEST == 3)


@test
def test_enum_variable() -> void:
    d: Direction = Direction.EAST
    test_assert(d == Direction.EAST)
    test_assert(d != Direction.NORTH)
    d = Direction.WEST
    test_assert(d == Direction.WEST)


@test
def test_struct_in_loop() -> void:
    total: float = 0.0
    for i in range(4):
        v: Vec2 = Vec2(cast_float(i), cast_float(i * 2))
        total = total + v.x + v.y
    test_assert(total == 18.0)
