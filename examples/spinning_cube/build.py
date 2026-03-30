
exe("cube",
    sources=["cube.py"],
    c_modules={
        "glut": {
            "macos": ["<GLUT/glut.h>", "<OpenGL/gl.h>"],
            "linux": ["<GL/glut.h>", "<GL/gl.h>"],
        },
    },
    flags={
        "macos": ["-framework", "OpenGL", "-framework", "GLUT", "-framework", "Cocoa",
                  "-Wno-deprecated-declarations"],
        "linux": ["-lGL", "-lglut", "-lm"],
    },
    run=True
)
