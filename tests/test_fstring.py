"nathra"
@extern
def strcmp(a: cstr, b: cstr) -> int: ...


@test
def test_fstring_int() -> void:
    x: int = 42
    s: cstr = f"val={x}"
    test_assert(strcmp(s, "val=42") == 0)


@test
def test_fstring_negative() -> void:
    x: int = -7
    s: cstr = f"x={x}"
    test_assert(strcmp(s, "x=-7") == 0)


@test
def test_fstring_float_spec() -> void:
    pi: float = 3.14159
    s: cstr = f"pi={pi:.4f}"
    test_assert(strcmp(s, "pi=3.1416") == 0)


@test
def test_fstring_mixed() -> void:
    n: int = 5
    v: float = 2.5
    s: cstr = f"n={n} v={v:.1f}"
    test_assert(strcmp(s, "n=5 v=2.5") == 0)


@test
def test_fstring_literal_only() -> void:
    s: cstr = f"hello world"
    test_assert(strcmp(s, "hello world") == 0)


@test
def test_fstring_expr() -> void:
    a: int = 3
    b: int = 4
    s: cstr = f"sum={a + b}"
    test_assert(strcmp(s, "sum=7") == 0)


@test
def test_fstring_hex() -> void:
    x: int = 255
    s: cstr = f"x={x:x}"
    test_assert(strcmp(s, "x=ff") == 0)


@test
def test_fstring_in_print() -> void:
    x: int = 10
    y: int = 20
    print(f"x={x} y={y} sum={x + y}")
    test_assert(1 == 1)