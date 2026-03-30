"nathra"
@test
def test_heap_list_cleanup() -> void:
    snap: int = heap_allocated()
    nums: list[int] = [10, 20, 30]
    list_free(nums)
    heap_assert(snap)

@test
def test_heap_string_cleanup() -> void:
    snap: int = heap_allocated()
    s: str = str_new("hello")
    w: str = str_new(" world")
    t: str = str_concat(s, w)
    str_free(t)
    str_free(w)
    str_free(s)
    heap_assert(snap)

@test
def test_heap_delta() -> void:
    snap: int = heap_allocated()
    s: str = str_new("test")
    test_assert(heap_allocated() > snap)
    str_free(s)
    heap_assert_delta(snap, 0)
