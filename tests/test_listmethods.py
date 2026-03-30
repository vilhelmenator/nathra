"nathra"
@test
def test_list_append_get() -> void:
    nums: list[int] = list_new()
    nums.append(10)
    nums.append(20)
    nums.append(30)
    test_assert(len(nums) == 3)
    test_assert(nums[0] == 10)
    test_assert(nums[1] == 20)
    test_assert(nums[2] == 30)


@test
def test_list_set() -> void:
    nums: list[int] = list_new()
    nums.append(1)
    nums.append(2)
    nums.append(3)
    nums[1] = 99
    test_assert(nums[1] == 99)


@test
def test_list_pop() -> void:
    nums: list[int] = list_new()
    nums.append(7)
    nums.append(8)
    v: int = nums.pop()
    test_assert(v == 8)
    test_assert(len(nums) == 1)


@test
def test_list_float() -> void:
    fs: list[float] = list_new()
    fs.append(1.5)
    fs.append(2.5)
    test_assert(fs[0] == 1.5)
    test_assert(fs[1] == 2.5)


@test
def test_list_len_method() -> void:
    ns: list[int] = list_new()
    ns.append(1)
    ns.append(2)
    test_assert(ns.len() == 2)


@test
def test_listcomp_typed() -> void:
    squares: list[int] = [i * i for i in range(4)]
    test_assert(len(squares) == 4)
    test_assert(squares[0] == 0)
    test_assert(squares[3] == 9)