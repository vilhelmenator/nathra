"nathra"
counter: int = 0
ratio: float = 1.5


@test
def test_global_read() -> void:
    test_assert(counter == 0)


@test
def test_global_write() -> void:
    counter = 10
    test_assert(counter == 10)
    counter = 0


@test
def test_global_float() -> void:
    ratio = 3.14
    test_assert(ratio > 3.0)
    ratio = 1.5


@test
def test_global_accumulate() -> void:
    counter = 0
    counter = counter + 5
    counter = counter + 3
    test_assert(counter == 8)
    counter = 0