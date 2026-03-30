"nathra"
@test
def test_len_array() -> void:
    nums: array[int, 5] = {1, 2, 3, 4, 5}
    test_assert(len(nums) == 5)


@test
def test_len_in_loop() -> void:
    data: array[float, 4] = {1.0, 2.0, 3.0, 4.0}
    total: float = 0.0
    for i in range(len(data)):
        total = total + data[i]
    test_assert(total == 10.0)


@test
def test_len_typed_list() -> void:
    nums: typed_list[int] = IntList_new()
    IntList_append(nums, 10)
    IntList_append(nums, 20)
    IntList_append(nums, 30)
    test_assert(len(nums) == 3)
    IntList_free(nums)


@test
def test_len_str() -> void:
    s: str = str_new("hello")
    test_assert(len(s) == 5)
    s2: str = str_new("")
    test_assert(len(s2) == 0)