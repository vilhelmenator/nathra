# micropy

A Python-syntax compiler that targets C. Write systems code in a clean, typed Python dialect — get fast, portable C out the other side.

The compiler includes a bootstrapped native backend — written in micropy itself — that compiles orders of magnitude faster than the Python implementation. See [Bootstrap performance](#bootstrap-performance) for benchmarks.

```python
struct Vec2:
    x: float
    y: float

    def __init__(self, x: float, y: float) -> void:
        self.x = x
        self.y = y

    def length(self) -> float:
        return sqrt(self.x * self.x + self.y * self.y)


def main() -> void:
    v: Vec2 = Vec2(3.0, 4.0)
    print(v.length())   # 5.0
```

## Quick start

```sh
make                                                      # build the native compiler (~2 sec)
python3 cli/mpy.py program.mpy                            # compile + link
python3 cli/mpy.py program.mpy --run                      # compile, link, run
python3 cli/mpy.py program.mpy --emit-c                   # emit C only
python3 cli/mpy.py program.mpy --shared                   # compile to shared library (.so/.dylib/.dll)
python3 cli/mpy.py build.mpy                              # run a project build script
python3 cli/mpy.py program.mpy --watch                    # rebuild on save
python3 cli/mpy.py program.mpy --flags="-O2 -march=native"   # extra compiler/linker flags
python3 cli/mpy.py program.mpy --flags="-lssl -lz"           # link extra libraries
python3 cli/mpy.py program.mpy --no-line-directives           # omit #line directives from C output
python3 cli/snekc.py                                          # interactive REPL
```

## Language reference

### Types

| micropy       | C                  | Notes                              |
|---------------|--------------------|------------------------------------|
| `int`         | `int64_t`          |                                    |
| `float`       | `double`           |                                    |
| `bool`        | `int`              |                                    |
| `byte`        | `uint8_t`          |                                    |
| `str`         | `MpStr*`           | heap-allocated, ref-counted string |
| `cstr`        | `char*`            | raw C string pointer               |
| `void`        | `void`             |                                    |
| `ptr[T]`      | `T*`               |                                    |
| `const[T]`    | `const T`          |                                    |
| `volatile[T]` | `volatile T`       |                                    |
| `atomic[T]`   | `volatile T`       | use with `atomic_load/store/add/sub/cas` |
| `thread_local[T]` | `MP_TLS T`     | per-thread storage (global or static local) |
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

`list[T]` gives you a typed, resizable list with Python-style methods:

```python
nums: list[int] = list_new()
nums.append(10)
nums.append(20)
nums.append(30)

print(len(nums))    # 3
print(nums[0])      # 10
nums[1] = 99        # set by index
v: int = nums.pop() # removes and returns last element
```

Float and string element types work the same way:

```python
fs: list[float] = list_new()
fs.append(1.5)
fs.append(2.5)
print(fs[0])   # 1.5
```

Methods: `append(x)`, `pop()`, `len()`. Subscript read (`lst[i]`) and write (`lst[i] = x`) auto-box/unbox based on the declared element type.

### List comprehensions

```python
squares: list[int] = [i * i for i in range(10)]
doubled: list[int] = [x * 2 for x in my_array]
evens:   list[int] = [x for x in my_array if x % 2 == 0]
pos_sq:  list[int] = [x * x for x in vals if x > 0]
```

Works with `range(...)`, `array[T, N]`, and typed lists. Use `list[T]` annotation for typed access via `lst[i]`; or plain `list` with `as_int(list_get(lst, i))` / `as_float(...)`.

### Strings

```python
s: str = str_new("hello")
t: str = s + str_new(" world")
if s == str_new("hello"):
    print(s.upper())        # HELLO
    print(s.contains("ell")) # 1
    print(s.find("ll"))     # 2
    print(s.slice(1, 3))    # el
```

Methods: `upper`, `lower`, `len`, `find`, `contains`, `starts_with`, `ends_with`, `slice`, `repeat`, `concat`, `strip`, `lstrip`, `rstrip`, `split(sep)`.

```python
words: list = str_new("a,b,c").split(str_new(","))   # 3-element list
clean: str  = str_new("  hi  ").strip()               # "hi"
msg:   str  = str_format("x=%d, y=%.2f", 3, 1.5)     # printf-style → str
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

micropy has no garbage collector. Heap-allocated types — `str`, `list[T]`, `dict` — are owned by you and must be freed explicitly.

**`defer`** — runs a cleanup call at the end of the enclosing function, in reverse order, even on early return. This is the idiomatic way to pair allocation with cleanup:

```python
def process() -> void:
    nums: list[int] = list_new()
    defer(list_free(nums))          # freed when process() returns

    s: str = str_new("hello")
    defer(str_free(s))              # freed after nums (reverse order)

    # ... use nums and s freely
```

Free functions: `list_free(l)`, `str_free(s)`, `dict_free(d)`.

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

The loop is split evenly across `threads` worker threads using `mp_parallel_for`. The function signature must take a pointer and a count; the loop variable must be the index.

### Platform-specific functions

```python
@platform("windows")
def sep() -> str:
    return str_new("\\")

@platform("linux", "macos")
def sep() -> str:
    return str_new("/")
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
# math_utils.mpy
def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

# main.mpy
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

When a `str` variable is passed to `f.write()`, it calls `mp_file_write_str` automatically. String literals and `cstr` go through the raw C write path.

```python
exists: int = file_exists("data.bin")
size:   int = file_size("data.bin")
remove_file("tmp.txt")
rename_file("old.txt", "new.txt")
```

### Directories and paths

```python
dir_create("/tmp/mydir")
dir_remove("/tmp/mydir")
ok:  int = dir_exists("/tmp/mydir")
cwd: str = dir_cwd()
entries: list = dir_list(".")   # list of MpStr* names
```

```python
base: str = path_basename("/home/user/file.txt")   # "file.txt"
ext:  str = path_ext("photo.jpg")                  # ".jpg"
dir:  str = path_dirname("/home/user/file.txt")    # "/home/user"
p:    str = path_join("/tmp", "output.c")
```

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
w: ptr[MpWriter] = writer_new(256)
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

The compiler walks the object graph depth-first, deduplicates shared pointers, serializes leaves first, and writes pointer fields as indices. On load, all objects are allocated and pointer references are reconstructed. The `.mpy` source is the schema.

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

`MpWriter`/`MpReader` are general-purpose binary I/O primitives — usable directly for network protocols, binary file formats, or custom serialization:

```python
w: ptr[MpWriter] = writer_new(64)
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
# game_logic.mpy  →  compiled with --shared
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
python3 cli/mpy.py game_logic.mpy --shared   # → game_logic.so / .dylib / .dll
```

The compiler auto-generates a `MpApi` vtable struct and a `get_api()` entry point:

```c
// generated in game_logic.c
typedef struct {
    void    (*init)(int64_t);
    void    (*update)(double);
    int64_t (*get_state)(void);
} MpApi;

MpApi* get_api(void);
```

Host (can also be micropy):

```python
# host.mpy
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

`snekc` is a live REPL that compiles each line through micropy → C → native code:

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

`build.mpy` is a build script interpreted by micropy's build runner:

```python
exe("hello",   sources=["hello.mpy"],         run=False)
exe("tests",   sources=["tests/test_foo.mpy"], run=True)
exe("release", sources=["main.mpy"],           flags=["-O2", "-march=native"])
lib("mylib",   sources=["mylib.mpy"],          kind="static")
lib("plugin",  sources=["plugin.mpy"],         kind="shared")
```

Run with `python3 cli/mpy.py build.mpy`.

**Incremental builds** — the compiler embeds the source mtime as `/* mpy_stamp: ... */` in every generated `.c` file, including the max mtime of all transitively imported modules. The build runner reads this stamp and skips recompilation when the source is unchanged, without relying on filesystem timestamps.

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

### Error messages

Compiler errors point directly to the `.mpy` source line via `#line` directives:

```
tests/my_prog.mpy:12:5: error: use of undeclared identifier 'typo'
```

## Compiler optimizations

The compiler performs a set of automatic analyses and rewrites at compile time. All are zero-cost in the sense that nothing is added at runtime that wasn't already implied by the source.

### `restrict` inference

When a function takes two or more `ptr[T]` parameters and none of them is ever assigned from another within the function body, the compiler emits `restrict` on each parameter. This is the single highest-value qualifier for loop vectorization — the C compiler cannot insert it on its own.

```python
def copy_bytes(dst: ptr[byte], src: ptr[byte], n: int) -> void:
    ...
# emits: void copy_bytes(uint8_t * restrict dst, uint8_t * restrict src, int64_t n)
```

If any pointer is assigned from another (`a = b`), neither receives `restrict`.

### Branch-free select

An `if/else` that assigns the same variable in both arms using only pure expressions (literals, locals, arithmetic — no calls, no pointer derefs with side effects) is emitted as a C ternary `?:`. The C compiler sometimes converts `if/else` to a `cmov` instruction but only when it can prove both arms are side-effect-free; micropy knows this from the AST.

```python
result: int = 0
if x < 0:
    result = -x
else:
    result = x
# emits: result = ((x < 0) ? (-x) : (x));
```

### Loop unroll hints

`for i in range(N)` where `N` is a small compile-time constant (≤ 8) emits `#pragma GCC unroll N` immediately before the loop, giving the C compiler a reliable unroll hint without manual `@unroll` annotation.

```python
for i in range(4):
    total = total + arr[i]
# emits: #pragma GCC unroll 4
#        for (int64_t i = 0; i < 4; i++) { ... }
```

### Stack variable lifetime narrowing

Large local variables are wrapped in a `{ }` block scope sized to their actual first/last use, so the C compiler knows the stack slot can be reused for a non-overlapping local. micropy can guarantee this safely because it tracks whether `&var` is ever taken; C compilers must conservatively assume it might be.

### Hot/cold splitting

When an `if` arm contains only error handling (a `raise`, a call to a `@cold` function, or another cold `if`) the arm is extracted into a separate `static __attribute__((cold))` helper and the branch is wrapped in `MP_UNLIKELY(...)`. This keeps the hot path's instruction footprint tight for I-cache utilisation.

```python
def safe_divide(a: int, b: int) -> int:
    if b == 0:
        raise "division by zero"
    return a / b
# The raise arm becomes a separate cold helper; the hot path is just the division.
```

Functions whose every code path ends in `raise` or `abort()` are automatically annotated `__attribute__((cold, noreturn))` — no annotation required.

### Constant specialization for `@hot` functions

When a `@hot` function calls a callee with a compile-time constant argument, the compiler emits a specialized copy of the callee with that constant folded in. The constant enables the C compiler to vectorize, strength-reduce, and eliminate branches in ways it cannot with a variable argument.

```python
@hot
def process(arr: ptr[int], n: int) -> int:
    return scaled_sum(arr, n, 4)   # stride=4 is constant → specialized copy emitted
```

**Threshold:** up to 3 distinct constant combinations per callee are specialized freely (one copy each, negligible code size). Beyond 3 distinct combinations, specialization proceeds only for callees with ≤ 30 statements. Functions inside `@hot` or `@unroll` contexts are always eligible.

## Benchmark

### Python vs micropy

`bench/bench.mpy` is a dual-mode file that runs as plain Python and compiles with micropy. `bench/run.py` builds the binary with `-O2`, runs both, and prints a comparison:

```
benchmark             python ms   micropy ms   speedup
--------------------  ----------  ----------  --------
float_sum                   1373           8      171x
leibniz_pi                  2451          14      175x
int_sum                     1215           7      173x
fib_36                      4868         112       43x
```

```sh
cd bench
python3 run.py
```

### Compiler optimizations vs naive C

`bench/run_opts.py` builds three versions of the same algorithms — Python, hand-written idiomatic C, and micropy — and prints a side-by-side comparison. It demonstrates seven automatic micropy optimizations:

```
benchmark              python ms  naive C ms  micropy ms   speedup  optimization
--------------------  ----------  ----------  ----------  --------  ----------------------------------------
saxpy                      23200         134         134      1.0x  restrict → no aliasing-check prelude
strided_sum                 5080          94          94      1.0x  constant specialisation (stride=4 folded in)
small_alloc                49000         198          38      5.2x  alloca substitution (no malloc/free per call)
soa_sum                    32600         123          30      4.1x  @soa → 8B/elem read vs 64B/elem AoS (8-field struct, extract one field)
restrict_short                 —         542         548      1.0x  restrict → no overlap-check preamble (N=64, cost is large fraction of call)
hot_cold                       —          72          74      1.0x  hot/cold split → 3 error paths outlined, hot loop fits in fewer cache lines
linked_list                    —         943         962      1.0x  prefetch(next->next) → hides L3 miss latency on pointer-chase traversal
```

- **small_alloc** — `alloca` substitution is a real win everywhere: stack allocation costs ~1 ns (one `sub rsp` instruction) vs 30–100 ns for `malloc/free` on typical allocators. 5.2× with 5 M calls to a 512-byte scratch-buffer function.
- **soa_sum** — the `@soa` benchmark extracts one field from a particle array (8 fields, 64 B/particle). AoS loads a full 64-byte cache line to get 8 B of `.x`; SoA reads only the `particles_x[]` stream (8 B/element). 4.1× speedup at 5 M particles, `@noinline` on both sides to prevent the optimizer from collapsing the rep loop.
- **saxpy / strided_sum / restrict_short** — Apple Clang at `-O2 -march=native` on Apple Silicon already applies vectorization strategies that match micropy's `restrict` and constant-specialisation output on this target; speedup is architecture-dependent and more visible on x86 toolchains where the overlap-check preamble is costlier.
- **hot_cold** — micropy outlines all three `raise` branches into `static __attribute__((cold, noreturn))` helpers, keeping the hot loop in fewer I-cache lines. The benefit is measurable under I-cache pressure from a larger surrounding binary; Apple Silicon's large L1-I cache absorbs the inline cold paths on this isolated benchmark.
- **linked_list** — micropy inserts `MP_PREFETCH(head->next->next, 0, 1)` before each pointer-chase load. The list is built with a stride-permuted layout (~12 MB hops) to defeat hardware prefetchers. Apple Silicon's stream-detection hardware is unusually aggressive and partially covers irregular pointer-chase patterns; the prefetch benefit is larger on Intel/AMD where L3-miss latency is higher relative to core speed.

```sh
cd bench
python3 run_opts.py
```

## Bootstrap performance

The native compiler is written in micropy and compiles itself. Self-compilation benchmark — the native compiler compiling its own 8 source modules (3,380 lines) to C:

| Module | Python | Native | Speedup |
|--------|--------|--------|---------|
| native_analysis.mpy | 117.9 ms | 0.20 ms | 595x |
| native_compile_file.mpy | 459.1 ms | 0.78 ms | 587x |
| native_infer.mpy | 124.2 ms | 0.26 ms | 478x |
| native_type_map.mpy | 124.0 ms | 0.28 ms | 438x |
| native_codegen_stmt.mpy | 347.6 ms | 1.01 ms | 344x |
| native_codegen_call.mpy | 247.2 ms | 0.85 ms | 290x |
| native_codegen_expr.mpy | 190.5 ms | 0.66 ms | 289x |
| native_compiler_state.mpy | 35.5 ms | 0.14 ms | 253x |
| **Total** | **1,646 ms** | **4.18 ms** | **394x** |

The native compiler compiles all 3,380 lines of its own source in under 5 milliseconds. Total compile time becomes dominated by `gcc`, which is the correct steady state — the compiler should never be slower than the C compiler it feeds.

See [BOOTSTRAP.md](BOOTSTRAP.md) for the full bootstrap roadmap and architecture.

## Generated header rules

Generated `.h` files include only `micropy_types.h` — a minimal header containing forward declarations, `stdint.h`, and `stddef.h`. They never include `micropy_rt.h`, `stdio.h`, `pthread.h`, or any other heavy header.

The full runtime is included exactly once, in the generated `.c` file. Each `.c` includes its own `.h`, which transitively brings in any project module dependencies.

This means including a micropy module header in C++ or C code never silently pulls in platform headers. Compile times stay flat as the project grows.

## Project structure

```
micropy/
  Makefile                          Build the native compiler dylib
  compiler/                         Python compiler (stage 0)
    compiler.py                       Front-end: parse, first-pass, emit glue
    codegen_stmts.py                  Statement code generation
    codegen_exprs.py                  Expression code generation
    type_map.py                       Type annotation → C type mapping
    ast_serial.py                     Binary AST serializer
  cli/                              User-facing tools
    mpy.py                            CLI entry point
    snekc.py                          Interactive REPL shell
    micropy.py                        IDE stubs (from micropy import *)
  runtime/                          C headers shipped with the project
    micropy_rt.h                      Full runtime: strings, lists, dicts, I/O, concurrency
    micropy_types.h                   Forward declarations — safe to include from any header
    micropy_test.h                    Test runner infrastructure
  native/                           Bootstrap native compiler (394x faster)
    src/                              .mpy source for the native compiler
    generated/                        Pre-generated .c/.h — just run make
  lib/
    build.py                          Build script interpreter
  scripts/
    regenerate.py                     Regenerate native/generated/ from .mpy sources
    bootstrap_test.py                 Bootstrap verification
  build/                            Build artifacts (gitignored)
    compiler_native.dylib             Native compiler shared library
  tests/                            Test suite (43 tests)
  bench/                            Benchmarks
  examples/                         Example programs
```

### Build targets

```sh
make                    # build native compiler from pre-generated C (~2 sec)
make regenerate         # regenerate C from .mpy sources (needs Python compiler)
make test               # run the test suite
make bootstrap          # run bootstrap verification
make clean              # remove build artifacts
```