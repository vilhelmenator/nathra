"nathra"
@test
def test_assert_passes() -> void:
    x: int = 5
    assert x == 5
    assert x > 0
    assert x != 99
    test_assert(1 == 1)


@test
def test_assert_with_message() -> void:
    val: int = 42
    assert val == 42, "val should be 42"
    assert val > 0, "val should be positive"
    test_assert(1 == 1)


@test
def test_assert_expression() -> void:
    a: int = 3
    b: int = 4
    assert a + b == 7
    assert a * b == 12
    assert a * a + b * b == 25
    test_assert(1 == 1)