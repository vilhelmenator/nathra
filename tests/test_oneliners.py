"nathra"
struct Counter:
    value: int

    def __bool__(self) -> int:
        return self.value != 0

    def __len__(self) -> int:
        return self.value


# static[T]: persists across calls, initialized once
def next_id() -> int:
    counter: static[int] = 0
    counter += 1
    return counter


# ptr is None / is not None
def is_null(p: ptr[int]) -> int:
    if p is None:
        return 1
    return 0


@test
def test_static_local() -> void:
    a: int = next_id()
    b: int = next_id()
    c: int = next_id()
    test_assert(a == 1)
    test_assert(b == 2)
    test_assert(c == 3)


@test
def test_is_none() -> void:
    test_assert(is_null(NULL) == 1)
    x: int = 42
    test_assert(is_null(addr_of(x)) == 0)


@test
def test_bool_dispatch() -> void:
    zero: Counter = Counter(0)
    nonzero: Counter = Counter(7)
    if zero:
        test_assert(0)   # should not reach
    if nonzero:
        test_assert(1)   # should reach


@test
def test_len_dispatch() -> void:
    c: Counter = Counter(5)
    test_assert(len(c) == 5)


@test
def test_hex_literals() -> void:
    x: int = 0xFF
    y: int = 0b1010
    z: int = 0o17
    test_assert(x == 255)
    test_assert(y == 10)
    test_assert(z == 15)