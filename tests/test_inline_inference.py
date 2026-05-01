"nathra"
# Regression tests for inferred @inline (item 6).
# Small leaf functions auto-promoted to `static inline`. Behavior must
# match the explicit-decorator path.

def small_leaf_add(a: int, b: int) -> int:
    return a + b


def small_leaf_max(a: int, b: int) -> int:
    return a if a > b else b


@hot
def hot_caller_inl() -> int:
    # Calls into auto-inlined helpers from a hot loop.
    s: int = 0
    for i in range(10):
        s = small_leaf_add(s, i)
    return s


@test
def test_auto_inline_arithmetic() -> void:
    test_assert(small_leaf_add(2, 3) == 5)
    test_assert(small_leaf_add(0, 0) == 0)


@test
def test_auto_inline_branchy() -> void:
    test_assert(small_leaf_max(7, 4) == 7)
    test_assert(small_leaf_max(2, 9) == 9)


@test
def test_auto_inline_in_hot_loop() -> void:
    # 0 + 1 + ... + 9 = 45
    test_assert(hot_caller_inl() == 45)


# A recursive function must NOT be auto-inlined. We can't observe the
# qualifier from inside compiled code, but we can verify it still runs.
def recursive_factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * recursive_factorial(n - 1)


@test
def test_recursive_not_inlined() -> void:
    test_assert(recursive_factorial(5) == 120)
