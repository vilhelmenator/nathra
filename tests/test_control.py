"nathra"
@test
def test_if_else() -> void:
    x: int = 10
    result: int = 0
    if x > 5:
        result = 1
    else:
        result = 2
    test_assert(result == 1)


@test
def test_elif() -> void:
    x: int = 5
    result: int = 0
    if x > 10:
        result = 1
    elif x > 3:
        result = 2
    else:
        result = 3
    test_assert(result == 2)


@test
def test_nested_if() -> void:
    x: int = 7
    y: int = 3
    result: int = 0
    if x > 5:
        if y > 5:
            result = 1
        else:
            result = 2
    test_assert(result == 2)


@test
def test_for_range_1arg() -> void:
    total: int = 0
    for i in range(5):
        total = total + i
    test_assert(total == 10)


@test
def test_for_range_2arg() -> void:
    total: int = 0
    for i in range(2, 6):
        total = total + i
    test_assert(total == 14)


@test
def test_for_range_step() -> void:
    total: int = 0
    for i in range(0, 10, 2):
        total = total + i
    test_assert(total == 20)


@test
def test_while() -> void:
    n: int = 1
    while n < 32:
        n = n * 2
    test_assert(n == 32)


@test
def test_break() -> void:
    found: int = -1
    for i in range(10):
        if i == 6:
            found = i
            break
    test_assert(found == 6)


@test
def test_continue() -> void:
    total: int = 0
    for i in range(10):
        if i % 2 == 0:
            continue
        total = total + i
    test_assert(total == 25)


@test
def test_nested_loops() -> void:
    count: int = 0
    for i in range(3):
        for j in range(4):
            count = count + 1
    test_assert(count == 12)


@test
def test_while_break() -> void:
    x: int = 0
    while True:
        x = x + 1
        if x == 5:
            break
    test_assert(x == 5)
