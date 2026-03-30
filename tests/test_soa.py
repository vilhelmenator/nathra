"nathra"
from nathra_stubs import *

@soa
class Particle:
    x: float
    y: float
    z: float
    mass: float

@test
def test_soa_basic() -> void:
    particles: array[Particle, 4]
    particles[0].x = 1.0
    particles[0].y = 2.0
    particles[0].z = 3.0
    particles[0].mass = 0.5
    particles[1].x = 4.0
    particles[1].mass = 1.0
    test_assert(particles[0].x == 1.0)
    test_assert(particles[0].y == 2.0)
    test_assert(particles[0].z == 3.0)
    test_assert(particles[0].mass == 0.5)
    test_assert(particles[1].x == 4.0)

@test
def test_soa_loop() -> void:
    n: int = 8
    pos: array[Particle, 8]
    i: int = 0
    while i < n:
        pos[i].x = cast_float(i)
        pos[i].y = cast_float(i * 2)
        pos[i].z = 0.0
        pos[i].mass = 1.0
        i = i + 1
    total: float = 0.0
    i = 0
    while i < n:
        total = total + pos[i].x
        i = i + 1
    test_assert(total == 28.0)
