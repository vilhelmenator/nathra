"nathra"
@test
def test_listcomp_range() -> void:
    squares: list = [i * i for i in range(5)]
    test_assert(list_len(squares) == 5)
    test_assert(as_int(list_get(squares, 0)) == 0)
    test_assert(as_int(list_get(squares, 2)) == 4)
    test_assert(as_int(list_get(squares, 4)) == 16)


@test
def test_listcomp_array() -> void:
    nums: array[int, 4] = {1, 2, 3, 4}
    doubled: list = [x * 2 for x in nums]
    test_assert(list_len(doubled) == 4)
    test_assert(as_int(list_get(doubled, 0)) == 2)
    test_assert(as_int(list_get(doubled, 3)) == 8)


@test
def test_listcomp_filter() -> void:
    nums: array[int, 6] = {1, 2, 3, 4, 5, 6}
    evens: list = [x for x in nums if x % 2 == 0]
    test_assert(list_len(evens) == 3)
    test_assert(as_int(list_get(evens, 0)) == 2)
    test_assert(as_int(list_get(evens, 1)) == 4)
    test_assert(as_int(list_get(evens, 2)) == 6)


@test
def test_listcomp_transform_filter() -> void:
    vals: array[int, 5] = {-2, -1, 0, 3, 5}
    pos_sq: list = [x * x for x in vals if x > 0]
    test_assert(list_len(pos_sq) == 2)
    test_assert(as_int(list_get(pos_sq, 0)) == 9)
    test_assert(as_int(list_get(pos_sq, 1)) == 25)