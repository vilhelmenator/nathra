"nathra"
c_include("<math.h>")
c_include("<stdlib.h>")


@extern
def sqrt(x: float) -> float: ...

@extern
def llabs(x: int) -> int: ...

@extern
def fabs(x: float) -> float: ...


@test
def test_extern_sqrt() -> void:
    result: float = sqrt(9.0)
    test_assert(result == 3.0)
    test_assert(sqrt(4.0) == 2.0)
    test_assert(sqrt(0.0) == 0.0)


@test
def test_extern_llabs() -> void:
    test_assert(llabs(-42) == 42)
    test_assert(llabs(7) == 7)
    test_assert(llabs(0) == 0)


@test
def test_extern_fabs() -> void:
    test_assert(fabs(-3.14) == 3.14)
    test_assert(fabs(2.5) == 2.5)
    test_assert(fabs(0.0) == 0.0)