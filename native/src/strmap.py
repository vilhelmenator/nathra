"nathra"
"""String-keyed hash map and set for the bootstrap compiler.

StrMap: open-addressing hash table with FNV-1a hashing and linear probe.
StrSet: same structure without values — for membership tests.

All keys are NrStr* (not copied — caller owns lifetime).
"""

from nathra_stubs import alloc, free

# ── FNV-1a hash ─────────────────────────────────────────────────────────

FNV_OFFSET: u64 = 14695981039346656037
FNV_PRIME:  u64 = 1099511628211

def str_hash(s: str) -> u32:
    """FNV-1a hash of an NrStr."""
    h: u64 = FNV_OFFSET
    for i in range(str_len(s)):
        h = h ^ cast(u64, cast(u8, s.data[i]))
        h = h * FNV_PRIME
    return cast(u32, h)

# ── StrMap ──────────────────────────────────────────────────────────────

EMPTY:     u8 = 0
OCCUPIED:  u8 = 1
TOMBSTONE: u8 = 2

class StrMap:
    keys:   ptr[str]
    values: ptr[ptr[void]]
    states: ptr[u8]
    hashes: ptr[u32]
    count:  i32
    cap:    i32

def strmap_new(initial_cap: i32) -> StrMap:
    """Create a new empty hash map."""
    cap: i32 = 16
    if initial_cap > 16:
        cap = initial_cap
    m: StrMap = StrMap(None, None, None, None, 0, cap)
    m.keys   = alloc(cast_int(cap) * 8)
    m.values = alloc(cast_int(cap) * 8)
    m.states = alloc(cast_int(cap))
    m.hashes = alloc(cast_int(cap) * 4)
    for i in range(cap):
        m.states[i] = EMPTY
    return m

def strmap_free(m: ptr[StrMap]) -> void:
    """Free a hash map's internal storage."""
    free(m.keys)
    free(m.values)
    free(m.states)
    free(m.hashes)
    m.keys = None
    m.values = None
    m.states = None
    m.hashes = None
    m.count = 0
    m.cap = 0

def _strmap_find_slot(m: ptr[StrMap], key: str, h: u32) -> i32:
    """Find the slot for a key (existing or first empty/tombstone)."""
    mask: i32 = m.cap - 1
    idx: i32 = cast_int(h) & mask
    first_tomb: i32 = -1
    for probe in range(m.cap):
        s: u8 = m.states[idx]
        if s == EMPTY:
            if first_tomb >= 0:
                return first_tomb
            return idx
        if s == TOMBSTONE:
            if first_tomb < 0:
                first_tomb = idx
        elif m.hashes[idx] == h:
            if str_eq(m.keys[idx], key):
                return idx
        idx = (idx + 1) & mask
    if first_tomb >= 0:
        return first_tomb
    return -1

def _strmap_grow(m: ptr[StrMap]) -> void:
    """Double the capacity and rehash all entries."""
    old_keys:   ptr[str]       = m.keys
    old_values: ptr[ptr[void]] = m.values
    old_states: ptr[u8]        = m.states
    old_hashes: ptr[u32]       = m.hashes
    old_cap:    i32            = m.cap

    new_cap: i32 = old_cap * 2
    m.cap = new_cap
    m.count = 0
    m.keys   = alloc(cast_int(new_cap) * 8)
    m.values = alloc(cast_int(new_cap) * 8)
    m.states = alloc(cast_int(new_cap))
    m.hashes = alloc(cast_int(new_cap) * 4)
    for i in range(new_cap):
        m.states[i] = EMPTY

    for i in range(old_cap):
        if old_states[i] == OCCUPIED:
            strmap_set(m, old_keys[i], old_values[i])

    free(old_keys)
    free(old_values)
    free(old_states)
    free(old_hashes)

def strmap_set(m: ptr[StrMap], key: str, value: ptr[void]) -> void:
    """Insert or update a key-value pair."""
    if m.count * 4 >= m.cap * 3:
        _strmap_grow(m)
    h: u32 = str_hash(key)
    idx: i32 = _strmap_find_slot(m, key, h)
    if m.states[idx] != OCCUPIED:
        m.count = m.count + 1
    m.keys[idx]   = key
    m.values[idx] = value
    m.states[idx] = OCCUPIED
    m.hashes[idx] = h

def strmap_get(m: ptr[StrMap], key: str) -> ptr[void]:
    """Look up a key. Returns NULL if not found."""
    if m.count == 0:
        return None
    h: u32 = str_hash(key)
    mask: i32 = m.cap - 1
    idx: i32 = cast_int(h) & mask
    for probe in range(m.cap):
        s: u8 = m.states[idx]
        if s == EMPTY:
            return None
        if s == OCCUPIED:
            if m.hashes[idx] == h:
                if str_eq(m.keys[idx], key):
                    return m.values[idx]
        idx = (idx + 1) & mask
    return None

def strmap_has(m: ptr[StrMap], key: str) -> int:
    """Check if a key exists. Returns 1 or 0."""
    if m.count == 0:
        return 0
    h: u32 = str_hash(key)
    mask: i32 = m.cap - 1
    idx: i32 = cast_int(h) & mask
    for probe in range(m.cap):
        s: u8 = m.states[idx]
        if s == EMPTY:
            return 0
        if s == OCCUPIED:
            if m.hashes[idx] == h:
                if str_eq(m.keys[idx], key):
                    return 1
        idx = (idx + 1) & mask
    return 0

def strmap_delete(m: ptr[StrMap], key: str) -> int:
    """Remove a key. Returns 1 if found, 0 if not."""
    if m.count == 0:
        return 0
    h: u32 = str_hash(key)
    mask: i32 = m.cap - 1
    idx: i32 = cast_int(h) & mask
    for probe in range(m.cap):
        s: u8 = m.states[idx]
        if s == EMPTY:
            return 0
        if s == OCCUPIED:
            if m.hashes[idx] == h:
                if str_eq(m.keys[idx], key):
                    m.states[idx] = TOMBSTONE
                    m.count = m.count - 1
                    return 1
        idx = (idx + 1) & mask
    return 0

# ── StrSet ──────────────────────────────────────────────────────────────

class StrSet:
    keys:   ptr[str]
    states: ptr[u8]
    hashes: ptr[u32]
    count:  i32
    cap:    i32

def strset_new(initial_cap: i32) -> StrSet:
    """Create a new empty string set."""
    cap: i32 = 16
    if initial_cap > 16:
        cap = initial_cap
    s: StrSet = StrSet(None, None, None, 0, cap)
    s.keys   = alloc(cast_int(cap) * 8)
    s.states = alloc(cast_int(cap))
    s.hashes = alloc(cast_int(cap) * 4)
    for i in range(cap):
        s.states[i] = EMPTY
    return s

def strset_free(s: ptr[StrSet]) -> void:
    """Free a string set's internal storage."""
    free(s.keys)
    free(s.states)
    free(s.hashes)
    s.keys = None
    s.states = None
    s.hashes = None
    s.count = 0
    s.cap = 0

def _strset_grow(s: ptr[StrSet]) -> void:
    """Double the capacity and rehash."""
    old_keys:   ptr[str] = s.keys
    old_states: ptr[u8]  = s.states
    old_hashes: ptr[u32] = s.hashes
    old_cap:    i32      = s.cap

    new_cap: i32 = old_cap * 2
    s.cap = new_cap
    s.count = 0
    s.keys   = alloc(cast_int(new_cap) * 8)
    s.states = alloc(cast_int(new_cap))
    s.hashes = alloc(cast_int(new_cap) * 4)
    for i in range(new_cap):
        s.states[i] = EMPTY

    for i in range(old_cap):
        if old_states[i] == OCCUPIED:
            strset_add(s, old_keys[i])

    free(old_keys)
    free(old_states)
    free(old_hashes)

def strset_add(s: ptr[StrSet], key: str) -> void:
    """Add a key to the set."""
    if s.count * 4 >= s.cap * 3:
        _strset_grow(s)
    h: u32 = str_hash(key)
    mask: i32 = s.cap - 1
    idx: i32 = cast_int(h) & mask
    for probe in range(s.cap):
        st: u8 = s.states[idx]
        if st == EMPTY or st == TOMBSTONE:
            s.keys[idx]   = key
            s.states[idx] = OCCUPIED
            s.hashes[idx] = h
            s.count = s.count + 1
            return
        if s.hashes[idx] == h:
            if str_eq(s.keys[idx], key):
                return
        idx = (idx + 1) & mask

def strset_has(s: ptr[StrSet], key: str) -> int:
    """Check if a key is in the set. Returns 1 or 0."""
    if s.count == 0:
        return 0
    h: u32 = str_hash(key)
    mask: i32 = s.cap - 1
    idx: i32 = cast_int(h) & mask
    for probe in range(s.cap):
        st: u8 = s.states[idx]
        if st == EMPTY:
            return 0
        if st == OCCUPIED:
            if s.hashes[idx] == h:
                if str_eq(s.keys[idx], key):
                    return 1
        idx = (idx + 1) & mask
    return 0

def strset_delete(s: ptr[StrSet], key: str) -> int:
    """Remove a key. Returns 1 if found, 0 if not."""
    if s.count == 0:
        return 0
    h: u32 = str_hash(key)
    mask: i32 = s.cap - 1
    idx: i32 = cast_int(h) & mask
    for probe in range(s.cap):
        st: u8 = s.states[idx]
        if st == EMPTY:
            return 0
        if st == OCCUPIED:
            if s.hashes[idx] == h:
                if str_eq(s.keys[idx], key):
                    s.states[idx] = TOMBSTONE
                    s.count = s.count - 1
                    return 1
        idx = (idx + 1) & mask
    return 0

# ── Tests ───────────────────────────────────────────────────────────────

def main() -> int:
    # StrMap basic test
    m: StrMap = strmap_new(16)

    a: str = "hello"
    b: str = "world"
    c: str = "foo"

    strmap_set(addr_of(m), a, cast(ptr[void], 42))
    strmap_set(addr_of(m), b, cast(ptr[void], 99))

    assert strmap_has(addr_of(m), a) == 1
    assert strmap_has(addr_of(m), b) == 1
    assert strmap_has(addr_of(m), c) == 0
    assert cast(i64, strmap_get(addr_of(m), a)) == 42
    assert cast(i64, strmap_get(addr_of(m), b)) == 99
    assert m.count == 2

    # Update existing key
    strmap_set(addr_of(m), a, cast(ptr[void], 100))
    assert cast(i64, strmap_get(addr_of(m), a)) == 100
    assert m.count == 2

    # Delete
    assert strmap_delete(addr_of(m), a) == 1
    assert strmap_has(addr_of(m), a) == 0
    assert m.count == 1

    # Grow: insert many keys
    for i in range(100):
        k: str = str_from_int(i)
        strmap_set(addr_of(m), k, cast(ptr[void], i))
    assert m.count == 101

    for i in range(100):
        k2: str = str_from_int(i)
        assert strmap_has(addr_of(m), k2) == 1
        assert cast(i64, strmap_get(addr_of(m), k2)) == i

    strmap_free(addr_of(m))

    # StrSet basic test
    s: StrSet = strset_new(16)
    x: str = "alpha"
    y: str = "beta"
    z: str = "gamma"

    strset_add(addr_of(s), x)
    strset_add(addr_of(s), y)
    assert strset_has(addr_of(s), x) == 1
    assert strset_has(addr_of(s), y) == 1
    assert strset_has(addr_of(s), z) == 0
    assert s.count == 2

    # Duplicate add
    strset_add(addr_of(s), x)
    assert s.count == 2

    # Delete
    assert strset_delete(addr_of(s), x) == 1
    assert strset_has(addr_of(s), x) == 0
    assert s.count == 1

    # Grow: insert many
    for i in range(200):
        k3: str = str_from_int(i)
        strset_add(addr_of(s), k3)
    assert s.count >= 200

    strset_free(addr_of(s))

    ok: str = "PASS: strmap + strset"
    print(ok)
    return 0
