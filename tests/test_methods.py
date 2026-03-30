"nathra"
class Point:
    x: float
    y: float

    def translate(self, dx: float, dy: float) -> Point:
        return Point(self.x + dx, self.y + dy)

    def scale(self, factor: float) -> Point:
        return Point(self.x * factor, self.y * factor)

    def dot(self, other: Point) -> float:
        return self.x * other.x + self.y * other.y


@test
def test_method_on_struct() -> void:
    p: Point = Point(3.0, 4.0)
    q: Point = p.translate(1.0, 1.0)
    test_assert(q.x == 4.0)
    test_assert(q.y == 5.0)


@test
def test_method_chain_struct() -> void:
    p: Point = Point(1.0, 2.0)
    q: Point = p.scale(3.0)
    test_assert(q.x == 3.0)
    test_assert(q.y == 6.0)


@test
def test_method_two_struct_args() -> void:
    a: Point = Point(1.0, 2.0)
    b: Point = Point(3.0, 4.0)
    d: float = a.dot(b)
    test_assert(d == 11.0)


@test
def test_method_on_typed_list() -> void:
    nums: typed_list[int] = IntList_new()
    nums.append(10)
    nums.append(20)
    nums.append(30)
    test_assert(nums.len() == 3)
    test_assert(nums.get(0) == 10)
    test_assert(nums.get(2) == 30)
    IntList_free(nums)


@test
def test_method_on_str() -> void:
    s: str = str_new("hello")
    test_assert(s.len() == 5)
    s2: str = str_new("")
    test_assert(s2.len() == 0)