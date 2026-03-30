"nathra"
def cmp_int(a: ptr[int], b: ptr[int]) -> int:
    if deref(a) < deref(b): return -1
    if deref(a) > deref(b): return 1
    return 0


@test
def test_rand_range() -> void:
    rand_seed(42)
    ok: int = 1
    for i in range(20):
        v: int = rand_int(0, 9)
        if v < 0 or v > 9:
            ok = 0
    test_assert(ok)


@test
def test_rand_float_range() -> void:
    rand_seed(1)
    ok: int = 1
    for i in range(20):
        v: float = rand_float()
        if v < 0.0 or v >= 1.0:
            ok = 0
    test_assert(ok)


@test
def test_sort_array() -> void:
    nums: array[int, 5] = {5, 3, 1, 4, 2}
    sort(nums, cmp_int)
    test_assert(nums[0] == 1)
    test_assert(nums[1] == 2)
    test_assert(nums[2] == 3)
    test_assert(nums[3] == 4)
    test_assert(nums[4] == 5)


@test
def test_time_ms_positive() -> void:
    t: int = time_ms()
    test_assert(t > 0)


@test
def test_time_now_positive() -> void:
    t: int = time_now()
    test_assert(t > 0)


@test
def test_getenv_path() -> void:
    val: ptr[str] = getenv("PATH")
    test_assert(val is not None)