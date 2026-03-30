"nathra"
@test
def test_fixed_array_zero_init() -> void:
    data: array[int, 4]
    test_assert(data[0] == 0)
    test_assert(data[3] == 0)


@test
def test_fixed_array_write_read() -> void:
    data: array[int, 5]
    for i in range(5):
        data[i] = i * 10
    test_assert(data[0] == 0)
    test_assert(data[1] == 10)
    test_assert(data[4] == 40)


@test
def test_fixed_array_sum() -> void:
    primes: array[int, 5]
    primes[0] = 2
    primes[1] = 3
    primes[2] = 5
    primes[3] = 7
    primes[4] = 11
    total: int = 0
    for i in range(5):
        total = total + primes[i]
    test_assert(total == 28)


@test
def test_float_array() -> void:
    vals: array[float, 3]
    vals[0] = 1.5
    vals[1] = 2.5
    vals[2] = 3.0
    test_assert(vals[0] + vals[1] == 4.0)
    test_assert(vals[2] == 3.0)


@test
def test_typed_list_append_get() -> void:
    nums: typed_list[int]
    nums = IntList_new()
    IntList_append(nums, 10)
    IntList_append(nums, 20)
    IntList_append(nums, 30)
    test_assert(IntList_len(nums) == 3)
    test_assert(IntList_get(nums, 0) == 10)
    test_assert(IntList_get(nums, 1) == 20)
    test_assert(IntList_get(nums, 2) == 30)
    IntList_free(nums)


@test
def test_typed_list_set_pop() -> void:
    nums: typed_list[int]
    nums = IntList_new()
    IntList_append(nums, 1)
    IntList_append(nums, 2)
    IntList_append(nums, 3)
    IntList_set(nums, 1, 99)
    test_assert(IntList_get(nums, 1) == 99)
    last: int = IntList_pop(nums)
    test_assert(last == 3)
    test_assert(IntList_len(nums) == 2)
    IntList_free(nums)


@test
def test_typed_list_grow() -> void:
    nums: typed_list[int]
    nums = IntList_new()
    for i in range(20):
        IntList_append(nums, i)
    test_assert(IntList_len(nums) == 20)
    test_assert(IntList_get(nums, 0) == 0)
    test_assert(IntList_get(nums, 19) == 19)
    IntList_free(nums)


@test
def test_float_typed_list() -> void:
    vals: typed_list[float]
    vals = FloatList_new()
    FloatList_append(vals, 1.0)
    FloatList_append(vals, 2.0)
    FloatList_append(vals, 3.0)
    test_assert(FloatList_len(vals) == 3)
    test_assert(FloatList_get(vals, 1) == 2.0)
    FloatList_free(vals)
