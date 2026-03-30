"nathra"
# Forward declarations: mutually recursive structs (via pointers)
struct Node:
    value: int
    next: ptr[Node]


# Union: all fields share memory
@union
class IntFloat:
    i: int
    f: float


# Bit fields
struct Flags:
    active:   bitfield[u32, 1]
    mode:     bitfield[u32, 3]
    priority: bitfield[u32, 4]


# volatile variable
def get_sensor() -> volatile[int]:
    x: volatile[int] = 42
    return x


# Mutually recursive functions (forward decls allow this)
def is_even(n: int) -> int:
    if n == 0:
        return 1
    return is_odd(n - 1)


def is_odd(n: int) -> int:
    if n == 0:
        return 0
    return is_even(n - 1)


@test
def test_forward_decl_struct() -> void:
    n: Node
    n.value = 99
    n.next = NULL
    test_assert(n.value == 99)
    test_assert(n.next is None)


@test
def test_union() -> void:
    u: IntFloat
    u.i = 0
    test_assert(u.i == 0)
    u.i = 42
    test_assert(u.i == 42)


@test
def test_bitfields() -> void:
    f: Flags
    f.active = 1
    f.mode = 5
    f.priority = 3
    test_assert(f.active == 1)
    test_assert(f.mode == 5)
    test_assert(f.priority == 3)


@test
def test_mutual_recursion() -> void:
    test_assert(is_even(10) == 1)
    test_assert(is_odd(7) == 1)
    test_assert(is_even(3) == 0)