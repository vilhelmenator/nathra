"nathra"
c_include("<stdarg.h>")


def sum_n(count: int, *args) -> int:
    ap: va_list
    va_start(ap, count)
    total: int = 0
    for i in range(count):
        total += va_arg(ap, int)
    va_end(ap)
    return total


def vlog(fmt: cstr, *args) -> void:
    ap: va_list
    va_start(ap, fmt)
    vprintf(fmt, ap)
    va_end(ap)


@test
def test_variadic_sum() -> void:
    result: int = sum_n(3, 10, 20, 30)
    test_assert(result == 60)


@test
def test_variadic_two() -> void:
    result: int = sum_n(2, 100, 200)
    test_assert(result == 300)