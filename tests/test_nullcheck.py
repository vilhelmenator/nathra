"nathra"
# Null analysis tests — tests that provably non-null pointers get no checks,
# and that guarded access (if p is not None) narrows correctly.
# Compile with --safe to enable runtime checks on unknown pointers.

struct Node:
    value: int
    next: ptr[Node]

# ── Provably non-null: alloc, addr_of, constructor ──────────────────────

@test
def test_alloc_nonnull() -> void:
    """alloc() is provably non-null — no check emitted."""
    p: ptr[int] = alloc(8)
    deref(p, 42)
    test_assert(deref(p) == 42)
    free(p)

@test
def test_addr_of_nonnull() -> void:
    """addr_of() is provably non-null — no check emitted."""
    x: int = 99
    p: ptr[int] = addr_of(x)
    test_assert(deref(p) == 99)

# ── Guarded access: if p is not None narrows to non-null ─────────────────

@test
def test_guarded_access() -> void:
    """if p is not None narrows p to non-null inside the body."""
    n: Node = Node(42, None)
    p: ptr[Node] = addr_of(n)
    if p is not None:
        test_assert(p.value == 42)

@test
def test_guarded_null_param() -> void:
    """Parameter with None guard — no crash."""
    _check_node(None)
    n: Node = Node(7, None)
    _check_node(addr_of(n))

def _check_node(p: ptr[Node]) -> int:
    if p is not None:
        return p.value
    return -1

# ── While loop narrowing ────────────────────────────────────────────────

@test
def test_while_narrowing() -> void:
    """while p is not None narrows p to non-null inside the loop."""
    a: Node = Node(1, None)
    b: Node = Node(2, addr_of(a))
    c: Node = Node(3, addr_of(b))
    total: int = 0
    cur: ptr[Node] = addr_of(c)
    while cur is not None:
        total = total + cur.value
        cur = cur.next
    test_assert(total == 6)

# ── Float division by zero is NOT an error (IEEE 754) ───────────────────

@test
def test_safe_null_with_arith() -> void:
    """Combining null checks with arithmetic safety."""
    x: int = 10
    p: ptr[int] = alloc(8)
    deref(p, x + 5)
    test_assert(deref(p) == 15)
    free(p)
