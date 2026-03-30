"nathra"
from nathra_stubs import *

# ---- Shared worker functions ----

def add_to_array(data: ptr[int], index: int, value: int) -> void:
    data[index] = value * value


def fill_range(data: ptr[int], start: int, count: int) -> void:
    i: int = 0
    while i < count:
        data[start + i] = start + i
        i = i + 1


def channel_send_range(ch: channel, start: int, count: int) -> void:
    i: int = 0
    while i < count:
        channel_send(ch, val_int(start + i))
        i = i + 1


# ---- Thread tests ----

@test
def test_thread_spawn_join() -> void:
    results: array[int, 4] = {0}
    t0: thread = thread_spawn(add_to_array, results, 0, 3)
    t1: thread = thread_spawn(add_to_array, results, 1, 5)
    t2: thread = thread_spawn(add_to_array, results, 2, 7)
    t3: thread = thread_spawn(add_to_array, results, 3, 9)
    thread_join(t0)
    thread_join(t1)
    thread_join(t2)
    thread_join(t3)
    test_assert(results[0] == 9)
    test_assert(results[1] == 25)
    test_assert(results[2] == 49)
    test_assert(results[3] == 81)


@test
def test_thread_fill() -> void:
    data: array[int, 12] = {0}
    t0: thread = thread_spawn(fill_range, data, 0, 4)
    t1: thread = thread_spawn(fill_range, data, 4, 4)
    t2: thread = thread_spawn(fill_range, data, 8, 4)
    thread_join(t0)
    thread_join(t1)
    thread_join(t2)
    i: int = 0
    while i < 12:
        test_assert(data[i] == i)
        i = i + 1


# ---- Channel tests ----

@test
def test_channel_send_recv() -> void:
    ch: channel = channel_new(8)
    channel_send(ch, val_int(10))
    channel_send(ch, val_int(20))
    channel_send(ch, val_int(30))
    channel_close(ch)
    a: int = as_int(channel_recv_val(ch))
    b: int = as_int(channel_recv_val(ch))
    c: int = as_int(channel_recv_val(ch))
    channel_free(ch)
    test_assert(a == 10)
    test_assert(b == 20)
    test_assert(c == 30)


@test
def test_channel_producer_threads() -> void:
    ch: channel = channel_new(32)
    t0: thread = thread_spawn(channel_send_range, ch, 0, 5)
    t1: thread = thread_spawn(channel_send_range, ch, 10, 5)
    thread_join(t0)
    thread_join(t1)
    channel_close(ch)
    results: list = channel_drain(ch)
    defer(list_free(results))
    channel_free(ch)
    test_assert(list_len(results) == 10)


@test
def test_channel_has_data() -> void:
    ch: channel = channel_new(4)
    test_assert(channel_has_data(ch) == 0)
    channel_send(ch, val_int(1))
    test_assert(channel_has_data(ch) == 1)
    channel_close(ch)
    channel_free(ch)


# ---- Mutex tests ----

struct MutexCounter:
    value: ptr[int]
    mtx: mutex
    n: int


def mutex_inc_worker(data: ptr[int], m: mutex, iterations: int) -> void:
    i: int = 0
    while i < iterations:
        mutex_lock(m)
        data[0] = data[0] + 1
        mutex_unlock(m)
        i = i + 1


@test
def test_mutex_basic() -> void:
    m: mutex = mutex_new()
    mutex_lock(m)
    mutex_unlock(m)
    mutex_free(m)
    test_assert(1 == 1)  # reaching here means no deadlock


@test
def test_mutex_protected_counter() -> void:
    counter: array[int, 1] = {0}
    m: mutex = mutex_new()
    t0: thread = thread_spawn(mutex_inc_worker, counter, m, 1000)
    t1: thread = thread_spawn(mutex_inc_worker, counter, m, 1000)
    thread_join(t0)
    thread_join(t1)
    mutex_free(m)
    test_assert(counter[0] == 2000)


# ---- Atomic tests ----

def atomic_inc_worker(ptr_val: ptr[int], n: int) -> void:
    i: int = 0
    while i < n:
        atomic_add(ptr_val, 1)
        i = i + 1


@test
def test_atomic_add() -> void:
    counter: array[int, 1] = {0}
    t0: thread = thread_spawn(atomic_inc_worker, counter, 5000)
    t1: thread = thread_spawn(atomic_inc_worker, counter, 5000)
    t2: thread = thread_spawn(atomic_inc_worker, counter, 5000)
    t3: thread = thread_spawn(atomic_inc_worker, counter, 5000)
    thread_join(t0)
    thread_join(t1)
    thread_join(t2)
    thread_join(t3)
    test_assert(counter[0] == 20000)


@test
def test_atomic_load_store() -> void:
    val: array[int, 1] = {0}
    atomic_store(val, 42)
    test_assert(atomic_load(val) == 42)


@test
def test_atomic_cas() -> void:
    val: array[int, 1] = {7}
    # CAS succeeds: expected == actual
    old: int = atomic_cas(val, 7, 99)
    test_assert(old == 7)
    test_assert(atomic_load(val) == 99)
    # CAS fails: expected != actual
    old2: int = atomic_cas(val, 0, 1)
    test_assert(atomic_load(val) == 99)