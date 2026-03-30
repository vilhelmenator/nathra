# Language Reference


### Types

| nathra        | C                  | Notes                              |
|---------------|--------------------|------------------------------------|
| `int`         | `int64_t`          |                                    |
| `float`       | `double`           |                                    |
| `bool`        | `int`              |                                    |
| `byte`        | `uint8_t`          |                                    |
| `str`         | `NrStr*`           | heap-allocated, ref-counted string |
| `cstr`        | `char*`            | raw C string pointer               |
| `void`        | `void`             |                                    |
| `ptr[T]`      | `T*`               |                                    |
| `const[T]`    | `const T`          |                                    |
| `volatile[T]` | `volatile T`       |                                    |
| `atomic[T]`   | `volatile T`       | use with `atomic_load/store/add/sub/cas` |
| `thread_local[T]` | `NR_TLS T`     | per-thread storage (global or static local) |
| `static[T]`   | `static T`         | static local — persists across calls        |
| `array[T, N]` | `T[N]`             | fixed-size stack array             |
| `vec[T, N]`   | GCC vector type    | SIMD vector                        |
| `i8/i16/i32/i64` | `int8_t` … `int64_t` | explicit-width integers      |
| `u8/u16/u32/u64` | `uint8_t` …        |                                    |
| `f32/f64`     | `float`/`double`   |                                    |
| `Result[T]`   | generated struct   | typed error-or-value               |

Type aliases:

```python
Scalar = float
Index  = int
```

### Structs

```python
struct Point:
    x: float
    y: float

    def __init__(self, x: float, y: float) -> void:
        self.x = x
        self.y = y

    def distance(self, other: ptr[Point]) -> float:
        dx: float = self.x - other.x
        dy: float = self.y - other.y
        return sqrt(dx*dx + dy*dy)

    @staticmethod
    def origin() -> Point:
        return Point(0.0, 0.0)
```

Named and positional construction both work:

```python
p1: Point = Point(1.0, 2.0)
p2: Point = Point(y=4.0, x=3.0)
```

Decorators: `@packed`, `@align(N)`, `@hot`, `@soa`.

`@soa` (Struct-of-Arrays) — when a struct is annotated `@soa`, any `array[T, N]` of that type is expanded into one flat array per field. Field accesses rewrite automatically:

```python
@soa
class Particle:
    x: float
    y: float
    z: float
    mass: float

particles: array[Particle, 1000]
particles[i].x = 1.0   # emits: particles_x[i] = 1.0
```

Generated C:
```c
double particles_x[1000];
double particles_y[1000];
double particles_z[1000];
double particles_mass[1000];
```

Unsupported patterns (compile error): whole-element read/write (`p = particles[i]`), method calls on element, `ref(particles[i])`, passing a SoA array where `ptr[T]` is expected.

Special methods: `__init__`, `__add__`/`__sub__`/`__mul__`/`__truediv__`, `__neg__`, `__eq__`/`__lt__` etc., `__len__` (called by `len(x)`), `__bool__` (called in `if x:` and `while x:`).

`@property` methods are called transparently on attribute access:

```python
struct Rect:
    _x: float
    _w: float
    _h: float

    @property
    def x(self) -> float:
        return self._x

    @property
    def area(self) -> float:
        return self._w * self._h

r: Rect = Rect(1.0, 10.0, 5.0)
a: float = r.area   # calls Rect_area(&r)
```

Works for both value and pointer types (`rp.area` calls `Rect_area(rp)`).

### Unions and bit fields

```python
@union
class IntFloat:
    i: int
    f: float

struct Flags:
    active:   bitfield[u32, 1]
    mode:     bitfield[u32, 3]
    priority: bitfield[u32, 4]
```

Or with the `union` keyword:

```python
union IntFloat:
    i: int
    f: float
```

### Enums

```python
from enum import Enum

class Color(Enum):
    RED   = 0
    GREEN = 1
    BLUE  = 2
```

Members are accessed as `Color.RED` and emit `Color_RED` in C. The `(Enum)` base is optional but recommended for clarity — plain `class Color:` with integer assignments works identically.

Enum values work naturally in `match`/`case`:

```python
match color:
    case Color.RED:   printf("red\n")
    case Color.GREEN: printf("green\n")
    case _:           printf("other\n")
```

### Functions

```python
def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if x < lo: return lo
    if x > hi: return hi
    return x
```

Decorators: `@inline`, `@noinline`, `@noreturn`, `@cold`, `@hot`, `@stream`, `@extern`, `@export`, `@staticmethod`.

`@stream` — marks a function as a single-pass streaming writer. Subscript writes inside `for` loops emit `__builtin_nontemporal_store` instead of regular stores, bypassing the cache entirely. Use when a loop writes every element exactly once and never re-reads — avoids evicting hot data from L1/L2:

```python
@stream
def fill_zeros(buf: ptr[float], n: int) -> void:
    for i in range(0, n):
        buf[i] = 0.0   # emits: __builtin_nontemporal_store(0.0, &buf[i])
```

`-> None` is equivalent to `-> void`. `None` as a value emits `NULL` and is valid anywhere a pointer is expected:

```python
def find(list: ptr[Node], key: int, out: ptr[int] = None) -> int:
    ...
```

`static[T]` variables persist across calls (initialized once):

```python
def next_id() -> int:
    counter: static[int] = 0
    counter += 1
    return counter
```

### Variadic functions

```python
c_include("<stdarg.h>")

def log(fmt: cstr, *args) -> void:
    ap: va_list
    va_start(ap, fmt)
    vprintf(fmt, ap)
    va_end(ap)

def sum_n(count: int, *args) -> int:
    ap: va_list
    va_start(ap, count)
    total: int = 0
    for i in range(count):
        total += va_arg(ap, int)
    va_end(ap)
    return total
```

`*args` in a function signature emits `...` in C. `va_list`, `va_start`, `va_end`, and `va_arg` map directly. `<stdarg.h>` is included automatically when variadic functions are present.

### Lambda expressions

Lambdas are typed by their annotation and compile to static C functions:

```python
# Assign to a typed func variable
dbl: func[int, int]       = lambda x: x * 2
add: func[int, int, int]  = lambda x, y: x + y

# Pass directly to a function expecting func[int, int]
def apply(fn: func[int, int], x: int) -> int:
    return fn(x)

result: int = apply(lambda x: x * x, 5)   # 25
```

The annotation (`func[Ret, Args...]`) provides the parameter and return types. The compiler emits a static helper function before the enclosing function and substitutes its name at the use site.

### Error handling

```python
def safe_div(a: int, b: int) -> Result[int]:
    if b == 0:
        raise "division by zero"      # sugar for return Err(...)
    return Ok(a // b)

def pipeline(x: int) -> Result[int]:
    a: int = try_unwrap(safe_div(x, 2))   # propagates error automatically
    b: int = try_unwrap(safe_div(a, 3))
    return Ok(b)

# At call site:
r: Result[int] = safe_div(10, 2)
if is_ok(r):
    print(unwrap(r))
else:
    print(err_msg(r))
```

- `Ok(val)` / `Err("message")` — construct a result
- `raise "message"` — return `Err(...)` from a `Result`-returning function
- `try_unwrap(expr)` — unwrap or propagate the error to the caller
- `is_ok(r)` / `is_err(r)` / `unwrap(r)` / `err_msg(r)` — inspect results
- `unwrap` panics with the error message if the result is an error

### Control flow

```python
# if / elif / else, while, for/range, break, continue, pass
for i in range(10):
    if i % 2 == 0:
        continue
    print(i)

# for-in arrays and typed lists
for x in my_array:
    process(x)

# enumerate: index + element
for i, v in enumerate(my_array):
    print(i)

# zip: parallel iteration (uses first sequence's length)
for a, b in zip(arr1, arr2):
    print(a + b)

# match / case  (Python 3.10+)
match status:
    case 200: print("ok")
    case 404: print("not found")
    case _:   print("other")
```

### Lists

`list[T]` gives you a typed, resizable list with Python-style syntax:

```python
nums: list[int] = [10, 20, 30]

print(len(nums))    # 3
print(nums[0])      # 10
nums[1] = 99        # set by index
nums.append(40)
v: int = nums.pop() # removes and returns last element

if 20 in nums:
    print("found")

# slicing and concatenation
first_two: list[int] = nums[0:2]
combined: list[int] = nums + other_list
```

Methods: `append(x)`, `pop()`, `len()`. Subscript, `in` operator, slicing, and `+` concatenation work as expected.

### List comprehensions

```python
squares: list[int] = [i * i for i in range(10)]
doubled: list[int] = [x * 2 for x in my_array]
evens:   list[int] = [x for x in my_array if x % 2 == 0]
pos_sq:  list[int] = [x * x for x in vals if x > 0]
```

Works with `range(...)`, `array[T, N]`, and typed lists. Use `list[T]` annotation for typed access via `lst[i]`; or plain `list` with `as_int(list_get(lst, i))` / `as_float(...)`.

### Dicts

`dict[K, V]` with Python-style literals, subscript access, and iteration:

```python
ages: dict[str, int] = {"alice": 30, "bob": 25}

ages["charlie"] = 35        # subscript write
age: int = ages["alice"]     # subscript read

if "bob" in ages:
    print("found")

for name, age in ages.items():
    print(name)
```

Methods: `keys()`, `values()`, `get(k, default)`. The runtime uses string keys and boxed values — the compiler inserts box/unbox calls automatically based on the `dict[K, V]` annotation.

### Strings

String literals are automatically inferred as `NrStr*` — no `str_new()` needed:

```python
s: str = "hello"
t: str = s + " world"
if s == "hello":
    print(s.upper())         # HELLO
    print(s.contains("ell")) # 1
    print(s.find("ll"))      # 2
    print(s.slice(1, 3))     # el
```

F-strings work as expected:

```python
name: str = "world"
x: int = 42
msg: str = f"hello {name}, x={x}"
pi: float = 3.14159
formatted: str = f"pi={pi:.4f}"
```

Methods: `upper`, `lower`, `len`, `find`, `contains`, `starts_with`, `ends_with`, `slice`, `repeat`, `concat`, `strip`, `lstrip`, `rstrip`, `split(sep)`.

```python
words: list = "a,b,c".split(",")           # 3-element list
clean: str  = "  hi  ".strip()              # "hi"
msg:   str  = str_format("x=%d", 3)        # printf-style → str
```

### Math

```python
import math

x: float = math.sqrt(2.0)
y: float = math.sin(math.atan2(1.0, 1.0))

# Or without the prefix:
z: float = sqrt(9.0)
```

Full set: `sqrt`, `cbrt`, `sin`/`cos`/`tan`, `asin`/`acos`/`atan`/`atan2`, `sinh`/`cosh`/`tanh`, `exp`/`exp2`, `log`/`log2`/`log10`, `pow`, `floor`/`ceil`/`round`/`trunc`, `fabs`, `hypot`, `fmod`, `isnan`, `isinf`.

### Builtins

`print(x)`, `abs(x)`, `min(a,b)`, `max(a,b)`, `int(x)`, `float(x)`, `str(x)`, `len(x)`, `sizeof(T)`, `exit(n)`, `input(prompt?)`.

### Random

```python
rand_seed(42)
n: int   = rand_int(0, 9)     # integer in [lo, hi]
f: float = rand_float()       # float in [0.0, 1.0)
```

### Time

```python
now: int = time_now()   # seconds since Unix epoch
ms:  int = time_ms()    # monotonic milliseconds (for game loops / benchmarks)
```

### Sort

```python
def cmp(a: ptr[int], b: ptr[int]) -> int:
    if deref(a) < deref(b): return -1
    if deref(a) > deref(b): return 1
    return 0

nums: array[int, 5] = {5, 3, 1, 4, 2}
sort(nums, cmp)   # in-place, wraps qsort
```

### Environment

```python
path: ptr[str] = getenv("PATH")    # returns NULL if not set
if path is not None:
    print(path)
```

### Memory management

nathra has no garbage collector. Heap-allocated types — `str`, `list[T]`, `dict` — are owned by you and must be freed explicitly, or use **auto-defer** (see below).

**`defer`** — runs a cleanup call at the end of the enclosing function, in reverse order, even on early return:

```python
def process() -> void:
    nums: list[int] = [1, 2, 3]
    defer(list_free(nums))          # freed when process() returns

    s: str = "hello"
    defer(str_free(s))              # freed after nums (reverse order)

    # ... use nums and s freely
```

**Auto-defer** — the compiler's escape analysis detects local-only `str`, `list[T]`, and `dict` variables and inserts `defer(free(...))` automatically. If a value is returned or passed to a function that takes ownership, it is classified as escaping and left for you to manage. No annotation needed — it just works for the common case.

Free functions: `list_free(l)`, `str_free(s)`, `dict_free(d)`.

**`own[T]`** — opt-in ownership annotation. Marks a variable or parameter as owning its heap allocation. The compiler tracks liveness and enforces that owned values are freed or transferred — use-after-move and forgotten frees are compile errors:

```python
def consume(data: own[list[int]]) -> void:
    defer(list_free(data))
    for x in data:
        print(x)

def main() -> void:
    nums: own[list[int]] = [10, 20, 30]
    consume(nums)       # ownership transferred
    print(len(nums))    # COMPILE ERROR: use of moved value 'nums'
```

Plain `ptr[T]`, `list[T]`, `str` parameters remain borrowed — no ownership transfer. `own[T]` is opt-in for functions that want to express "I take this and I'm responsible for it." Always on, zero runtime cost.

**Arenas** — allocate many objects from a single region; free everything at once. Good for temporary work where individual lifetimes don't matter:

```python
def process() -> void:
    a: arena = arena_new(65536)
    defer(arena_free(a))

    lst: list = arena_list_new(a)
    s:   str  = arena_str_new(a, "scratch")
    list_append(lst, val_int(42))

    arena_reset(a)   # discard all allocations without freeing the arena itself
    # arena_free called on return via defer
```

**Scoped arenas** — `with scope` creates and frees an arena automatically at scope exit:

```python
def process() -> void:
    with scope(arena, 65536):
        s: str = arena_str_new(arena, "temp")
        lst: list = arena_list_new(arena)
        # use freely — no defer needed
    # arena freed here automatically
```

**Raw pointers** — `alloc`/`free` for manual byte-level control:

```python
buf: ptr[byte] = alloc(1024)
free(buf)

p: ptr[int] = addr_of(x)   # ref(x) is an alias
v: int = deref(p)
```

**Stack types never need freeing** — `array[T, N]`, structs, and all scalar types live on the stack.

### SIMD

```python
@simd
def add_vecs(a: array[f32, 1024], b: array[f32, 1024], out: array[f32, 1024]) -> void:
    for i in range(1024):
        out[i] = a[i] + b[i]

# Explicit SIMD vector type
v: vec[f32, 4] = ...
```

### Compile-time evaluation

```python
@compile_time
def gen_lookup() -> list:
    return [i * i for i in range(16)]

TABLE: array[int, 16] = gen_lookup()   # embedded as a C initializer
```

The decorated function runs in Python at compile time. The result must be a list of integers or floats matching the target array type.

### Generics

```python
@generic(T=[int, float])
def square(x: T) -> T:
    return x * x

# Generates square_int() and square_float()
```

### Loop unrolling

```python
@unroll(4)
def sum_array(data: ptr[int], n: int) -> int:
    total: int = 0
    for i in range(0, n):
        total = total + data[i]
    return total
```

The `for`-`range` loop body is replicated `N` times in the emitted C. The loop variable and bounds are adjusted automatically.

### Parallel loops

```python
@parallel(threads=4)
def scale_array(data: ptr[float], n: int) -> void:
    for i in range(0, n):
        data[i] = data[i] * 2.0
```

The loop is split evenly across `threads` worker threads using `nr_parallel_for`. The function signature must take a pointer and a count; the loop variable must be the index.

### Platform-specific functions

```python
@platform("windows")
def sep() -> str:
    return "\\"

@platform("linux", "macos")
def sep() -> str:
    return "/"
```

Only the body matching the current platform is compiled. Multiple platforms can be listed. Valid values: `"windows"`, `"linux"`, `"macos"`.

### Traits

```python
@trait
class Measurable:
    def area(self) -> float: ...
    def perimeter(self) -> float: ...

@impl(Measurable)
struct Circle:
    radius: float
    def area(self) -> float:
        return 3.14159 * self.radius * self.radius
    def perimeter(self) -> float:
        return 2.0 * 3.14159 * self.radius
```


### Modules

```python
# math_utils.py
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

# main.py
import math_utils
from math_utils import lerp

x: float = math_utils.lerp(0.0, 10.0, 0.5)
y: float = lerp(0.0, 10.0, 0.25)
```

### File I/O

Files use Python-style method syntax. `open` and `with open` work as you'd expect:

```python
with open("/tmp/out.txt", "w") as f:
    f.write("hello\n")
    f.write_line("world")     # appends \n automatically
    f.write_int(42)
    f.write_float(3.14)

r: file = open("/tmp/out.txt", "r")
content: str = r.read()        # read entire file
line:    str = r.readline()    # read one line
eof:     int = r.eof()
r.close()
```

When a `str` variable is passed to `f.write()`, it calls `nr_file_write_str` automatically. String literals and `cstr` go through the raw C write path.

```python
import os

exists: int = os.exists("data.bin")
size:   int = os.file_size("data.bin")
os.remove("tmp.txt")
os.rename("old.txt", "new.txt")
```

### Directories and paths

```python
os.mkdir("/tmp/mydir")
os.rmdir("/tmp/mydir")
ok:  int = os.isdir("/tmp/mydir")
cwd: str = os.getcwd()
entries: list = os.listdir(".")   # list of NrStr* names
```

```python
base: str = os.path.basename("/home/user/file.txt")   # "file.txt"
ext:  str = os.path.ext("photo.jpg")                  # ".jpg"
dir:  str = os.path.dirname("/home/user/file.txt")    # "/home/user"
p:    str = os.path.join("/tmp", "output.c")
```

The old function names (`file_exists`, `dir_create`, `path_join`, etc.) still work.

### Serialization

Mark a struct `@serializable` and the compiler generates `serialize_X`/`deserialize_X` functions automatically — no schema files, no runtime reflection:

```python
@serializable
struct Vec3:
    x: f64
    y: f64
    z: f64

@serializable
struct Entity:
    name: str
    position: Vec3
    parent: ptr[Entity]
```

**Inline serialization** — for writing to buffers, network, or custom formats:

```python
w: ptr[NrWriter] = writer_new(256)
v: Vec3 = Vec3(1.0, 2.0, 3.0)
serialize_Vec3(w, addr_of(v))

out_len: i64 = 0
buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))
# ... send buf over network, write to file, etc.
```

**Graph serialization** — for structs with `ptr[T]` fields, the compiler generates `save_X`/`load_X` that handle shared references and file I/O automatically:

```python
save_Entity("scene.bin", root)
root: ptr[Entity] = load_Entity("scene.bin")
```

The compiler walks the object graph depth-first, deduplicates shared pointers, serializes leaves first, and writes pointer fields as indices. On load, all objects are allocated and pointer references are reconstructed. The `.py` source is the schema.

**Cycle handling** — use `backref[T]` on fields that point back up the tree (e.g. parent pointers). These are skipped during graph collection to prevent infinite loops:

```python
@serializable
struct Node:
    value: i32
    children: ptr[Node]
    parent: backref[ptr[Node]]
```

**Schema validation** — every serialized struct includes a 4-byte hash computed from its field names, types, and order. Deserialization aborts with a clear error if the schema has changed.

**Supported field types:** scalars (`int`, `float`, `bool`, fixed-width integers), `str`, nested `@serializable` structs (by value), `ptr[T]` to `@serializable` structs, `array[T, N]` with scalar or struct elements.

`NrWriter`/`NrReader` are general-purpose binary I/O primitives — usable directly for network protocols, binary file formats, or custom serialization:

```python
w: ptr[NrWriter] = writer_new(64)
write_i32(w, 42)
write_f64(w, 3.14)
write_str(w, my_string)
```

### Inline C

```python
c_include("<unistd.h>")

def sleep_sec(n: int) -> void:
    c_code("sleep(n);")
```

### C library integration

`import` a C library by name — the build system maps it to the right headers for your platform. The compiler runs `gcc -E` at compile time to extract all function signatures and `#define` constants automatically:

```python
import glut

def main() -> int:
    glutInitDisplayMode(GLUT_DOUBLE + GLUT_RGB + GLUT_DEPTH)
    glutCreateWindow("nathra - spinning cube")
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(display)
    glutMainLoop()
    return 0
```

No `@extern` declarations, no constant blocks — `import glut` gives you every function and `#define` from the headers.

Map module names to headers via the CLI or `build.py`:

```sh
python3 cli/nathra.py program.py --c-module "glut=<GLUT/glut.h>,<OpenGL/gl.h>"
```

```python
# build.py
exe("cube",
    sources=["cube.py"],
    c_modules={
        "glut": {
            "macos": ["<GLUT/glut.h>", "<OpenGL/gl.h>"],
            "linux": ["<GL/glut.h>", "<GL/gl.h>"],
        },
    },
    flags={
        "macos": ["-framework OpenGL", "-framework GLUT"],
        "linux": ["-lGL", "-lglut", "-lm"],
    },
)
```

Platform-keyed dicts resolve automatically based on the build machine. A `.pyi` stub file is auto-generated for IDE autocomplete and linting (gitignored).

Functions with `...` body are automatically treated as extern — no `@extern` decorator needed:

```python
def custom_lib_func(x: int, y: float) -> int: ...
```

See [examples/spinning_cube/](examples/spinning_cube/) for a complete working demo.

### Concurrency

**Threads** — `thread_spawn` wraps arguments automatically; no `c_code` needed:

```python
def worker(data: ptr[int], index: int, value: int) -> void:
    data[index] = value * value

def main() -> void:
    results: array[int, 4] = {0}
    t0: thread = thread_spawn(worker, results, 0, 3)
    t1: thread = thread_spawn(worker, results, 1, 5)
    thread_join(t0)
    thread_join(t1)
    # results[0] == 9, results[1] == 25
```

**Mutex**:

```python
m: mutex = mutex_new()
defer(mutex_free(m))
mutex_lock(m)
# critical section
mutex_unlock(m)
```

**Channels** — bounded MPMC queue:

```python
ch: channel = channel_new(32)
channel_send(ch, val_int(42))
v: int = as_int(channel_recv_val(ch))
channel_close(ch)
results: list = channel_drain(ch)   # blocks until closed, collects all values
channel_free(ch)
```

**Condition variables**:

```python
c: cond  = cond_new()
m: mutex = mutex_new()
cond_wait(c, m)       # atomically unlock m and sleep
cond_signal(c)        # wake one waiter
cond_broadcast(c)     # wake all waiters
```

**Atomics** — lock-free operations on `volatile int64_t`:

```python
counter: array[int, 1] = {0}
atomic_add(counter, 1)
atomic_sub(counter, 1)
v:   int = atomic_load(counter)
atomic_store(counter, 99)
old: int = atomic_cas(counter, 99, 0)   # compare-and-swap; returns previous value
```

**Thread-local storage** — each thread has its own copy:

```python
request_id: thread_local[int] = 0

def handle() -> void:
    call_count: thread_local[int] = 0   # static local, persists per-thread
    call_count += 1
```

**Thread pool**:

```python
pool: threadpool = pool_new(4, 64)     # 4 threads, queue capacity 64
pool_submit(pool, my_task, arg)
pool_shutdown(pool)                    # waits for all tasks, then frees
```

### Hot-reloading

Mark functions with `@export` and compile to a shared library. The host loads it with `hotreload_open`, calls `get_api()` to get a vtable of function pointers, and can swap the library at runtime without restarting.

```python
# game_logic.py  →  compiled with --shared
state: int = 0

@export
def init(n: int) -> void:
    state = n

@export
def update(dt: float) -> void:
    state += int(dt * 100.0)

@export
def get_state() -> int:
    return state
```

```sh
python3 cli/nathra.py game_logic.py --shared   # → game_logic.so / .dylib / .dll
```

The compiler auto-generates a `NrApi` vtable struct and a `get_api()` entry point:

```c
// generated in game_logic.c
typedef struct {
    void    (*init)(int64_t);
    void    (*update)(double);
    int64_t (*get_state)(void);
} NrApi;

NrApi* get_api(void);
```

Host (can also be nathra):

```python
# host.py
c_include("<dlfcn.h>")

def main() -> void:
    lib: ptr[void] = hotreload_open("./game_logic.dylib")

    init_fn:      func[int, void]   = hotreload_sym(lib, "init")
    update_fn:    func[float, void] = hotreload_sym(lib, "update")
    get_state_fn: func[int]         = hotreload_sym(lib, "get_state")

    init_fn(0)
    update_fn(1.0)
    print(get_state_fn())   # 100

    # Reload after recompile:
    hotreload_close(lib)
    lib = hotreload_open("./game_logic.dylib")
    update_fn = hotreload_sym(lib, "update")
    get_state_fn = hotreload_sym(lib, "get_state")
```

`hotreload_open/sym/close` wrap `dlopen`/`dlsym`/`dlclose` on POSIX and `LoadLibrary`/`GetProcAddress`/`FreeLibrary` on Windows.

### Interactive shell

`snekc` is a live REPL that compiles each line through nathra → C → native code:

```sh
python3 cli/snekc.py
```

```
>>> x: int = 42
>>> y: int = x + 8
>>> print(y)
50
>>> struct Vec2:
...     x: float
...     y: float
...
>>> v: Vec2 = Vec2(3.0, 4.0)
>>> print(v.x)
3.000000
```

Variables become C globals that persist between evaluations. State is transferred via `ctypes` between compilations. Structs and functions can be redefined — the new definition replaces the old one. Failed compilations roll back without corrupting state.

### Build system

`build.py` is a build script interpreted by nathra's build runner:

```python
exe("hello",   sources=["hello.py"],         run=False)
exe("tests",   sources=["tests/test_foo.py"], run=True)
exe("release", sources=["main.py"],           flags=["-O2", "-march=native"])
lib("mylib",   sources=["mylib.py"],          kind="static")
lib("plugin",  sources=["plugin.py"],         kind="shared")
```

Run with `python3 cli/nathra.py build.py`.

**Incremental builds** — the compiler embeds the source mtime as `/* nth_stamp: ... */` in every generated `.c` file, including the max mtime of all transitively imported modules. The build runner reads this stamp and skips recompilation when the source is unchanged, without relying on filesystem timestamps.

### Testing

```python
@test
def test_addition() -> void:
    test_assert(1 + 1 == 2)
    test_assert(abs(-5) == 5)
```

Any file with `@test` functions gets a generated test runner main. Output is Google Test-style:

```
[ RUN      ] test_addition
[       OK ] test_addition (42 nano sec)
[==========] 1 tests, 0 failures
```

**Heap assertions** — verify that code paths don't leak, under `--safe` or `--track-alloc`:

```python
@test
def test_no_leak() -> void:
    snap: int = heap_allocated()
    nums: list[int] = [10, 20, 30]
    list_free(nums)
    heap_assert(snap)              # all memory returned

@test
def test_delta() -> void:
    snap: int = heap_allocated()
    s: str = str_new("hello")
    str_free(s)
    heap_assert_delta(snap, 0)     # zero net change
```

In release builds, heap tracking compiles out — zero overhead.

### Error messages

Compiler errors point directly to the `.py` source line via `#line` directives:

```
tests/my_prog.py:12:5: error: use of undeclared identifier 'typo'
```

