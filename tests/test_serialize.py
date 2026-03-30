"nathra"
from nathra_stubs import *


# ---- Phase 1: NrWriter / NrReader round-trip ----

@test
def test_writer_reader_scalars() -> void:
    w: ptr[NrWriter] = writer_new(64)

    write_i8(w, 42)
    write_i16(w, 1000)
    write_i32(w, 100000)
    write_i64(w, 9999999999)
    write_u8(w, 255)
    write_u16(w, 60000)
    write_u32(w, 3000000000)
    write_f32(w, 3.14)
    write_f64(w, 2.718281828)
    write_bool(w, True)
    write_bool(w, False)

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))
    test_assert(out_len > 0)

    r: ptr[NrReader] = reader_new(buf, out_len)

    test_assert(read_i8(r) == 42)
    test_assert(read_i16(r) == 1000)
    test_assert(read_i32(r) == 100000)
    test_assert(read_i64(r) == 9999999999)
    test_assert(read_u8(r) == 255)
    test_assert(read_u16(r) == 60000)
    test_assert(read_u32(r) == 3000000000)
    v32: f32 = read_f32(r)
    test_assert(v32 > 3.13)
    test_assert(v32 < 3.15)
    v64: f64 = read_f64(r)
    test_assert(v64 > 2.71)
    test_assert(v64 < 2.72)
    test_assert(read_bool(r) == True)
    test_assert(read_bool(r) == False)

    reader_free(r)
    free(buf)
    writer_free(w)


@test
def test_writer_reader_str() -> void:
    w: ptr[NrWriter] = writer_new(64)
    s: str = "hello, world"
    write_str(w, s)

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    s2: str = read_str(r)
    test_assert(str_eq(s, s2))

    str_free(s2)
    reader_free(r)
    free(buf)
    writer_free(w)


@test
def test_writer_pos() -> void:
    w: ptr[NrWriter] = writer_new(64)
    test_assert(writer_pos(w) == 0)
    write_i32(w, 42)
    test_assert(writer_pos(w) == 4)
    write_i64(w, 100)
    test_assert(writer_pos(w) == 12)
    writer_free(w)


# ---- Phase 2: @serializable flat structs ----

@serializable
struct Vec3:
    x: f64
    y: f64
    z: f64


@serializable
struct Transform:
    pos: Vec3
    scale: f64


@test
def test_serialize_flat_struct() -> void:
    w: ptr[NrWriter] = writer_new(256)

    v: Vec3 = Vec3(1.0, 2.0, 3.0)
    serialize_Vec3(w, addr_of(v))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))
    test_assert(out_len > 0)

    r: ptr[NrReader] = reader_new(buf, out_len)
    v2: Vec3 = Vec3(0.0, 0.0, 0.0)
    deserialize_Vec3(r, addr_of(v2))

    test_assert(v2.x == 1.0)
    test_assert(v2.y == 2.0)
    test_assert(v2.z == 3.0)

    reader_free(r)
    free(buf)
    writer_free(w)


@test
def test_serialize_nested_flat() -> void:
    w: ptr[NrWriter] = writer_new(256)

    t: Transform = Transform(Vec3(10.0, 20.0, 30.0), 2.5)
    serialize_Transform(w, addr_of(t))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    t2: Transform = Transform(Vec3(0.0, 0.0, 0.0), 0.0)
    deserialize_Transform(r, addr_of(t2))

    test_assert(t2.pos.x == 10.0)
    test_assert(t2.pos.y == 20.0)
    test_assert(t2.pos.z == 30.0)
    test_assert(t2.scale == 2.5)

    reader_free(r)
    free(buf)
    writer_free(w)


@test
def test_serialize_multiple_round_trips() -> void:
    w: ptr[NrWriter] = writer_new(256)

    v1: Vec3 = Vec3(1.0, 2.0, 3.0)
    v2: Vec3 = Vec3(4.0, 5.0, 6.0)
    serialize_Vec3(w, addr_of(v1))
    serialize_Vec3(w, addr_of(v2))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    r1: Vec3 = Vec3(0.0, 0.0, 0.0)
    r2: Vec3 = Vec3(0.0, 0.0, 0.0)
    deserialize_Vec3(r, addr_of(r1))
    deserialize_Vec3(r, addr_of(r2))

    test_assert(r1.x == 1.0)
    test_assert(r1.y == 2.0)
    test_assert(r1.z == 3.0)
    test_assert(r2.x == 4.0)
    test_assert(r2.y == 5.0)
    test_assert(r2.z == 6.0)

    reader_free(r)
    free(buf)
    writer_free(w)


# ---- Phase 3: strings, pointers, arrays ----

@serializable
struct Named:
    name: str
    value: f64


@test
def test_serialize_str_field() -> void:
    w: ptr[NrWriter] = writer_new(256)

    n: Named = Named(str_new("hello"), 3.14)
    serialize_Named(w, addr_of(n))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    n2: Named = Named(str_new(""), 0.0)
    deserialize_Named(r, addr_of(n2))

    test_assert(str_eq(n2.name, n.name))
    test_assert(n2.value > 3.13)
    test_assert(n2.value < 3.15)

    str_free(n.name)
    str_free(n2.name)
    reader_free(r)
    free(buf)
    writer_free(w)


@serializable
struct TreeNode:
    value: i32
    left: ptr[TreeNode]
    right: ptr[TreeNode]


@test
def test_serialize_ptr_field() -> void:
    w: ptr[NrWriter] = writer_new(256)

    left: ptr[TreeNode] = alloc(sizeof(TreeNode))
    left.value = 10
    left.left = NULL
    left.right = NULL

    right: ptr[TreeNode] = alloc(sizeof(TreeNode))
    right.value = 30
    right.left = NULL
    right.right = NULL

    root: TreeNode = TreeNode(20, left, right)
    serialize_TreeNode(w, addr_of(root))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    root2: TreeNode = TreeNode(0, NULL, NULL)
    deserialize_TreeNode(r, addr_of(root2))

    test_assert(root2.value == 20)
    test_assert(root2.left != NULL)
    test_assert(root2.left.value == 10)
    test_assert(root2.left.left == NULL)
    test_assert(root2.right != NULL)
    test_assert(root2.right.value == 30)

    free(root2.left)
    free(root2.right)
    free(left)
    free(right)
    reader_free(r)
    free(buf)
    writer_free(w)


@test
def test_serialize_null_ptr() -> void:
    w: ptr[NrWriter] = writer_new(256)

    leaf: TreeNode = TreeNode(42, NULL, NULL)
    serialize_TreeNode(w, addr_of(leaf))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    leaf2: TreeNode = TreeNode(0, NULL, NULL)
    deserialize_TreeNode(r, addr_of(leaf2))

    test_assert(leaf2.value == 42)
    test_assert(leaf2.left == NULL)
    test_assert(leaf2.right == NULL)

    reader_free(r)
    free(buf)
    writer_free(w)


@serializable
struct Polygon:
    vertices: array[f64, 6]
    color: i32


@test
def test_serialize_array_field() -> void:
    w: ptr[NrWriter] = writer_new(256)

    p: Polygon = Polygon(0.0, 0)
    p.vertices[0] = 1.0
    p.vertices[1] = 2.0
    p.vertices[2] = 3.0
    p.vertices[3] = 4.0
    p.vertices[4] = 5.0
    p.vertices[5] = 6.0
    p.color = 255

    serialize_Polygon(w, addr_of(p))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    p2: Polygon = Polygon(0.0, 0)
    deserialize_Polygon(r, addr_of(p2))

    test_assert(p2.vertices[0] == 1.0)
    test_assert(p2.vertices[1] == 2.0)
    test_assert(p2.vertices[2] == 3.0)
    test_assert(p2.vertices[3] == 4.0)
    test_assert(p2.vertices[4] == 5.0)
    test_assert(p2.vertices[5] == 6.0)
    test_assert(p2.color == 255)

    reader_free(r)
    free(buf)
    writer_free(w)


@serializable
struct Mesh:
    points: array[Vec3, 3]
    id: i32


@test
def test_serialize_struct_array_field() -> void:
    w: ptr[NrWriter] = writer_new(512)

    m: Mesh = Mesh(0)
    m.id = 99
    m.points[0] = Vec3(1.0, 0.0, 0.0)
    m.points[1] = Vec3(0.0, 1.0, 0.0)
    m.points[2] = Vec3(0.0, 0.0, 1.0)

    serialize_Mesh(w, addr_of(m))

    out_len: i64 = 0
    buf: ptr[u8] = writer_to_bytes(w, addr_of(out_len))

    r: ptr[NrReader] = reader_new(buf, out_len)
    m2: Mesh = Mesh(0)
    deserialize_Mesh(r, addr_of(m2))

    test_assert(m2.points[0].x == 1.0)
    test_assert(m2.points[1].y == 1.0)
    test_assert(m2.points[2].z == 1.0)
    test_assert(m2.id == 99)

    reader_free(r)
    free(buf)
    writer_free(w)


# ---- Phase 4: graph serialization (save/load) ----

@test
def test_save_load_tree() -> void:
    # Build a small tree
    left: ptr[TreeNode] = alloc(sizeof(TreeNode))
    left.value = 10
    left.left = NULL
    left.right = NULL

    right: ptr[TreeNode] = alloc(sizeof(TreeNode))
    right.value = 30
    right.left = NULL
    right.right = NULL

    root: ptr[TreeNode] = alloc(sizeof(TreeNode))
    root.value = 20
    root.left = left
    root.right = right

    save_TreeNode("/tmp/test_tree.mpyg", root)

    root2: ptr[TreeNode] = load_TreeNode("/tmp/test_tree.mpyg")

    test_assert(root2.value == 20)
    test_assert(root2.left != NULL)
    test_assert(root2.left.value == 10)
    test_assert(root2.left.left == NULL)
    test_assert(root2.right != NULL)
    test_assert(root2.right.value == 30)

    # Cleanup
    free(root2.left)
    free(root2.right)
    free(root2)
    free(left)
    free(right)
    free(root)


@serializable
struct Material:
    roughness: f64
    metallic: f64


@serializable
struct Entity:
    id: i32
    mat: ptr[Material]


@test
def test_save_load_shared_ref() -> void:
    # Two entities share the same material
    shared_mat: ptr[Material] = alloc(sizeof(Material))
    shared_mat.roughness = 0.5
    shared_mat.metallic = 1.0

    e1: ptr[Entity] = alloc(sizeof(Entity))
    e1.id = 1
    e1.mat = shared_mat

    e2: ptr[Entity] = alloc(sizeof(Entity))
    e2.id = 2
    e2.mat = shared_mat

    # Save e1 — shared_mat will be collected once
    save_Entity("/tmp/test_entity.mpyg", e1)

    e1_loaded: ptr[Entity] = load_Entity("/tmp/test_entity.mpyg")

    test_assert(e1_loaded.id == 1)
    test_assert(e1_loaded.mat != NULL)
    test_assert(e1_loaded.mat.roughness == 0.5)
    test_assert(e1_loaded.mat.metallic == 1.0)

    free(e1_loaded.mat)
    free(e1_loaded)
    free(shared_mat)
    free(e1)
    free(e2)
