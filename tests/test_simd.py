"nathra"
@test
def test_vec_add() -> void:
    a: vec[f32, 4] = {1.0, 2.0, 3.0, 4.0}
    b: vec[f32, 4] = {10.0, 20.0, 30.0, 40.0}
    c: vec[f32, 4] = a + b
    test_assert(c[0] == 11.0)
    test_assert(c[1] == 22.0)
    test_assert(c[2] == 33.0)
    test_assert(c[3] == 44.0)


@test
def test_vec_mul() -> void:
    a: vec[f32, 4] = {1.0, 2.0, 3.0, 4.0}
    b: vec[f32, 4] = {2.0, 2.0, 2.0, 2.0}
    c: vec[f32, 4] = a * b
    test_assert(c[0] == 2.0)
    test_assert(c[1] == 4.0)
    test_assert(c[2] == 6.0)
    test_assert(c[3] == 8.0)


@test
def test_vec_sub() -> void:
    a: vec[f32, 4] = {5.0, 6.0, 7.0, 8.0}
    b: vec[f32, 4] = {1.0, 2.0, 3.0, 4.0}
    c: vec[f32, 4] = a - b
    test_assert(c[0] == 4.0)
    test_assert(c[1] == 4.0)
    test_assert(c[2] == 4.0)
    test_assert(c[3] == 4.0)


@simd
@test
def test_simd_loop() -> void:
    data: array[f32, 8] = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0}
    total: f32 = 0.0
    for i in range(8):
        total += data[i]
    test_assert(total == 36.0)