# micropy

A Python-syntax compiler that targets C. Write systems code in a clean, typed Python dialect — get fast, portable C out the other side.

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
python3 mpy.py program.mpy           # compile + link
python3 mpy.py program.mpy --run     # compile, link, run
python3 mpy.py program.mpy --emit-c  # emit C only
python3 mpy.py program.mpy --shared  # compile to shared library (.so/.dylib/.dll)
python3 mpy.py build.mpy             # run a project build script
python3 mpy.py program.mpy --watch   # rebuild on save
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

Decorators: `@packed`, `@align(N)`.

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
class Color:
    RED   = 0
    GREEN = 1
    BLUE  = 2
```

### Functions

```python
def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if x < lo: return lo
    if x > hi: return hi
    return x
```

Decorators: `@inline`, `@noinline`, `@noreturn`, `@cold`, `@hot`, `@extern`, `@staticmethod`.

`None` is valid as a default value for `ptr[T]` parameters (emits `NULL`):

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

**Arenas** — allocate many objects from a single region; free everything at once when the scope exits. Good for temporary work where individual lifetimes don't matter:

```python
with arena_new() as a:
    lst: list = arena_list_new(a)
    s:   str  = arena_str_new(a, "scratch")
    # a and all its allocations freed here automatically
```

**Raw pointers** — `alloc`/`free` for manual byte-level control:

```python
buf: ptr[byte] = alloc(1024)
free(buf)

p: ptr[int] = addr_of(x)
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

### Generics

```python
@generic(T=[int, float])
def square(x: T) -> T:
    return x * x

# Generates square_int64_t() and square_double()
```

### Traits

```python
@trait
class Printable:
    def print_self(self) -> void: ...

@impl(Printable)
struct MyType:
    value: int
    def print_self(self) -> void:
        print(self.value)
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

### Inline C

```python
c_include("<unistd.h>")

def sleep_sec(n: int) -> void:
    c_code("sleep(n);")
```

### Concurrency

```python
mutex: ptr[MpMutex] = mutex_new()
mutex_lock(mutex)
# critical section
mutex_unlock(mutex)

t: thread = thread_spawn(my_func, arg)
thread_join(t)

ch: ptr[MpChannel] = channel_new(16)
channel_send(ch, val)
channel_recv(ch, addr_of(out))

# Thread-local storage: each thread has its own copy
request_id: thread_local[int] = 0

def handle() -> void:
    call_count: thread_local[int] = 0   # static local, persists per-thread
    call_count += 1
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
python3 mpy.py game_logic.mpy --shared   # → game_logic.so / .dylib / .dll
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

### Build system

`build.mpy` is a build script interpreted by micropy's build runner:

```python
exe("hello",   sources=["hello.mpy"],         run=False)
exe("tests",   sources=["tests/test_foo.mpy"], run=True)
exe("release", sources=["main.mpy"],           flags=["-O2", "-march=native"])
lib("mylib",   sources=["mylib.mpy"],          kind="static")
lib("plugin",  sources=["plugin.mpy"],         kind="shared")
```

Run with `python3 mpy.py build.mpy`.

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

## Project structure

| File               | Purpose                                  |
|--------------------|------------------------------------------|
| `mpy.py`           | CLI entry point                          |
| `compiler.py`      | Front-end: parse, first-pass, emit glue  |
| `codegen_stmts.py` | Statement code generation                |
| `codegen_exprs.py` | Expression code generation               |
| `type_map.py`      | Type annotation → C type mapping         |
| `build.py`         | Build script interpreter                 |
| `micropy_rt.h`     | Runtime: strings, lists, dicts, I/O, … |
| `micropy_test.h`   | Test runner infrastructure               |