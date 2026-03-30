# Writing Sierra Chart Studies with Nathra

Write your indicator logic in Python syntax, compile to a Sierra Chart ACSIL
DLL. Nathra handles the C codegen; a small hook file handles the Sierra
boilerplate.

## Setup

You need two files in your project directory:

```
my_studies/
├── codegen_hooks.py   ← Sierra Chart wrapper (copy once, edit as needed)
├── sma_study.py      ← your indicator logic
└── nathra_rt.h       ← symlink or copy from nathra repo
```

Copy `nathra_rt.h` (and `nathra_types.h` if used) into your project dir,
or symlink them.

## Step 1: The hook file

Create `codegen_hooks.py` — this is plain Python, runs at compile time:

```python
# codegen_hooks.py

def sierra_study(name, subgraphs):
    """Wrap a function as a Sierra Chart ACSIL study."""
    def hook(func_name, params, return_type, c_body):
        sg_setup = ""
        for i, sg in enumerate(subgraphs):
            sg_setup += f'        sc.Subgraph[{i}].Name = "{sg}";\n'
            sg_setup += f'        sc.Subgraph[{i}].DrawStyle = DRAWSTYLE_LINE;\n'

        return f"""
#include "sierrachart.h"
SCDLLName("{name}")

{c_body}

SCSFExport scsf_{func_name}(SCStudyInterfaceRef sc)
{{
    if (sc.SetDefaults)
    {{
        sc.GraphName = "{name}";
{sg_setup}        sc.AutoLoop = 0;
        return;
    }}

    {func_name}(sc.BaseData[SC_LAST], sc.ArraySize, sc.Subgraph[0].Data);
}}
"""
    return hook
```

You write this once. Adjust the `scsf_` entry point to match how you want
to pass data from Sierra Chart into your function.

## Step 2: Write your study

Create `sma_study.py`:

```python
from codegen_hooks import sierra_study

@sierra_study(name="My SMA", subgraphs=["SMA Line"])
def sma(close: ptr[f32], count: i32, output: ptr[f32]) -> void:
    period: i32 = 20
    for i in range(period - 1, count):
        total: f32 = 0.0
        for j in range(period):
            total += close[i - j]
        output[i] = total / cast(f32, period)
```

That's it. Pure math, no Sierra boilerplate in your `.py` file.

## Step 3: Compile

```bash
python nathra.py sma_study.py --shared
```

This produces `sma_study.c` and compiles it to a shared library
(`.dll` on Windows, `.dylib` on macOS). The generated C looks like:

```c
#include "sierrachart.h"
SCDLLName("My SMA")

void sma(float* close, int32_t count, float* output) {
    int32_t period = 20;
    for (int32_t i = period - 1; i < count; i++) {
        float total = 0.0f;
        for (int32_t j = 0; j < period; j++) {
            total += close[i - j];
        }
        output[i] = total / ((float)(period));
    }
}

SCSFExport scsf_sma(SCStudyInterfaceRef sc)
{
    if (sc.SetDefaults)
    {
        sc.GraphName = "My SMA";
        sc.Subgraph[0].Name = "SMA Line";
        sc.Subgraph[0].DrawStyle = DRAWSTYLE_LINE;
        sc.AutoLoop = 0;
        return;
    }

    sma(sc.BaseData[SC_LAST], sc.ArraySize, sc.Subgraph[0].Data);
}
```

Copy the DLL into Sierra Chart's `Data/` folder and add it as a study.

## Multiple studies in one file

You can have multiple studies in a single `.py` file:

```python
from codegen_hooks import sierra_study

@sierra_study(name="My SMA", subgraphs=["SMA Line"])
def sma(close: ptr[f32], count: i32, output: ptr[f32]) -> void:
    ...

@sierra_study(name="My EMA", subgraphs=["EMA Line"])
def ema(close: ptr[f32], count: i32, output: ptr[f32]) -> void:
    ...
```

Each gets its own `scsf_` entry point in the generated C.

## Customizing the hook

The hook receives four arguments:

| Argument | Type | What |
|----------|------|------|
| `func_name` | `str` | Function name (e.g. `"sma"`) |
| `params` | `list[tuple[str, str]]` | Parameter names and C types: `[("close", "float*"), ...]` |
| `return_type` | `str` | C return type (e.g. `"void"`) |
| `c_body` | `str` | The complete generated C function including signature |

Return a string with the full C output for this function, or `None` to
emit the function unchanged.

You can use `params` to auto-generate the call site instead of hardcoding it:

```python
def sierra_study(name, subgraphs):
    def hook(func_name, params, return_type, c_body):
        # Build call args from params
        call_args = ", ".join(pname for pname, _ in params)
        ...
    return hook
```
