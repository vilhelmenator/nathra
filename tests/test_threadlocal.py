"nathra"
# Thread-local storage tests
# Global thread-local: each thread has its own copy
tls_counter: thread_local[int] = 0


def increment_tls() -> void:
    tls_counter += 1


def get_tls() -> int:
    return tls_counter


# Function-local thread-local (must be static in C)
def tls_accumulator(delta: int) -> int:
    acc: thread_local[int] = 0
    acc += delta
    return acc


@test
def test_tls_global_init() -> void:
    test_assert(tls_counter == 0)


@test
def test_tls_global_modify() -> void:
    increment_tls()
    increment_tls()
    increment_tls()
    test_assert(get_tls() == 3)


@test
def test_tls_local_static() -> void:
    # Static thread-local: value persists across calls within the same thread
    a: int = tls_accumulator(10)
    b: int = tls_accumulator(5)
    # First call: 0+10=10, second call: 10+5=15
    test_assert(a == 10)
    test_assert(b == 15)