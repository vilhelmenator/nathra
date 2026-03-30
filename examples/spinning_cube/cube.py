"nathra"
from glut import *
from nathra_stubs import addr_of, cstr, f32, i32
# ── State ──────────────────────────────────────────────────────────────
angle: f32 = 0.0

# ── Cube face helper ───────────────────────────────────────────────────
def face(r: f32, g: f32, b: f32,
         x0: f32, y0: f32, z0: f32,
         x1: f32, y1: f32, z1: f32,
         x2: f32, y2: f32, z2: f32,
         x3: f32, y3: f32, z3: f32) -> None:
    glColor3f(r, g, b)
    glVertex3f(x0, y0, z0)
    glVertex3f(x1, y1, z1)
    glVertex3f(x2, y2, z2)
    glVertex3f(x3, y3, z3)

# ── Draw ───────────────────────────────────────────────────────────────
def draw_cube() -> None:
    glBegin(GL_QUADS)
    face(1.0, 0.0, 0.0, -0.5,-0.5, 0.5,  0.5,-0.5, 0.5,  0.5, 0.5, 0.5, -0.5, 0.5, 0.5)
    face(0.0, 1.0, 0.0, -0.5,-0.5,-0.5, -0.5, 0.5,-0.5,  0.5, 0.5,-0.5,  0.5,-0.5,-0.5)
    face(0.0, 0.0, 1.0, -0.5, 0.5,-0.5, -0.5, 0.5, 0.5,  0.5, 0.5, 0.5,  0.5, 0.5,-0.5)
    face(1.0, 1.0, 0.0, -0.5,-0.5,-0.5,  0.5,-0.5,-0.5,  0.5,-0.5, 0.5, -0.5,-0.5, 0.5)
    face(1.0, 0.0, 1.0,  0.5,-0.5,-0.5,  0.5, 0.5,-0.5,  0.5, 0.5, 0.5,  0.5,-0.5, 0.5)
    face(0.0, 1.0, 1.0, -0.5,-0.5,-0.5, -0.5,-0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.5,-0.5)
    glEnd()

# ── GLUT callbacks ─────────────────────────────────────────────────────
def display() -> None:
    glClear(GL_COLOR_BUFFER_BIT + GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -3.0)
    glRotatef(angle, 1.0, 0.7, 0.3)
    draw_cube()
    glutSwapBuffers()

def idle() -> None:
    global angle
    angle = angle + 0.5
    if angle > 360.0:
        angle = angle - 360.0
    glutPostRedisplay()

def reshape(w: i32, h: i32) -> None:
    if h == 0:
        h = 1
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, float(w) / float(h), 0.1, 100.0)

# ── Entry point ────────────────────────────────────────────────────────
def main() -> int:
    argc: i32 = 1
    argv_str: cstr = "cube"
    glutInit(addr_of(argc), addr_of(argv_str))
    glutInitDisplayMode(GLUT_DOUBLE + GLUT_RGB + GLUT_DEPTH)
    glutInitWindowSize(640, 480)
    glutCreateWindow("nathra - spinning cube")
    glClearColor(0.1, 0.1, 0.1, 1.0)
    glEnable(GL_DEPTH_TEST)
    glutDisplayFunc(display)
    glutIdleFunc(idle)
    glutReshapeFunc(reshape)
    glutMainLoop()
    return 0
