# Spinning Cube — OpenGL + GLUT

A minimal 3D demo: a colored cube rotating in a window. No external dependencies — uses system OpenGL/GLUT frameworks.

## Build and run

```sh
# From the repo root:
cd examples/spinning_cube
PYTHONPATH=../.. python3 ../../cli/nathra.py build.py
```

Or directly:

```sh
# macOS:
PYTHONPATH=. python3 cli/nathra.py examples/spinning_cube/cube.py \
    --c-module "glut=<GLUT/glut.h>,<OpenGL/gl.h>" \
    --flags="-framework OpenGL -framework GLUT -framework Cocoa -Wno-deprecated-declarations" \
    --run

# Linux:
PYTHONPATH=. python3 cli/nathra.py examples/spinning_cube/cube.py \
    --c-module "glut=<GL/glut.h>,<GL/gl.h>" \
    --flags="-lGL -lglut -lm" \
    --run
```

## How it works

The source is pure nathra — no `#include`, no `#ifdef`, no C boilerplate:

```python
import glut

def draw_cube() -> void:
    glBegin(GL_QUADS)
    face(1.0, 0.0, 0.0, -0.5,-0.5, 0.5, ...)
    glEnd()

def main() -> int:
    glutInitDisplayMode(GLUT_DOUBLE + GLUT_RGB + GLUT_DEPTH)
    glutCreateWindow("nathra - spinning cube")
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(display)
    glutMainLoop()
    return 0
```

`import glut` is mapped to C headers by the build system. The compiler runs `gcc -E` at compile time to extract all function signatures and `#define` constants from the headers — no manual declarations needed.

The `build.py` handles platform differences:

```python
exe("cube",
    sources=["cube.py"],
    c_modules={
        "glut": {
            "macos": ["<GLUT/glut.h>", "<OpenGL/gl.h>"],
            "linux": ["<GL/glut.h>", "<GL/gl.h>"],
        },
    },
    flags={
        "macos": ["-framework OpenGL", "-framework GLUT", "-framework Cocoa"],
        "linux": ["-lGL", "-lglut", "-lm"],
    },
    run=True
)
```

A `glut.pyi` stub file is auto-generated for IDE support (gitignored).
