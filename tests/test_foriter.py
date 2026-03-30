"nathra"
@test
def test_for_array_sum() -> void:
    nums: array[int, 5] = {1, 2, 3, 4, 5}
    total: int = 0
    for n in nums:
        total = total + n
    test_assert(total == 15)


@test
def test_for_array_max() -> void:
    vals: array[int, 4] = {7, 2, 9, 3}
    best: int = vals[0]
    for v in vals:
        if v > best:
            best = v
    test_assert(best == 9)


@test
def test_for_array_count() -> void:
    data: array[int, 6] = {1, 0, 1, 1, 0, 1}
    ones: int = 0
    for x in data:
        if x == 1:
            ones = ones + 1
    test_assert(ones == 4)


@test
def test_for_float_array() -> void:
    fs: array[float, 3] = {1.0, 2.0, 3.0}
    acc: float = 0.0
    for f in fs:
        acc = acc + f
    test_assert(acc == 6.0)


@test
def test_enumerate_array() -> void:
    vals: array[int, 4] = {10, 20, 30, 40}
    idx_sum: int = 0
    val_sum: int = 0
    for i, v in enumerate(vals):
        idx_sum = idx_sum + i
        val_sum = val_sum + v
    test_assert(idx_sum == 6)    # 0+1+2+3
    test_assert(val_sum == 100)  # 10+20+30+40


@test
def test_zip_arrays() -> void:
    a: array[int, 3] = {1, 2, 3}
    b: array[int, 3] = {4, 5, 6}
    dot: int = 0
    for x, y in zip(a, b):
        dot = dot + x * y
    test_assert(dot == 32)  # 1*4 + 2*5 + 3*6


@test
def test_enumerate_indices() -> void:
    arr: array[int, 3] = {100, 200, 300}
    for i, v in enumerate(arr):
        test_assert(arr[i] == v)