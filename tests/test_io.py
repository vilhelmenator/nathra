"nathra"
from nathra_stubs import *

TMP_FILE: cstr = "/tmp/nathra_io_test.txt"
TMP_CSV:  cstr = "/tmp/nathra_io_csv.txt"
TMP_DIR:  cstr = "/tmp/nathra_io_dir"


@test
def test_file_write_and_exists() -> void:
    with open(TMP_FILE, "w") as f:
        f.write_line("line one")
        f.write_line("line two")
    test_assert(file_exists(TMP_FILE) == 1)


@test
def test_file_read_all() -> void:
    with open(TMP_FILE, "w") as f:
        f.write("hello world")

    r: file = open(TMP_FILE, "r")
    content: str = r.read()
    r.close()
    test_assert(str_len(content) == 11)
    test_assert(str_eq(content, str_new("hello world")) == 1)


@test
def test_file_write_int_and_float() -> void:
    with open(TMP_FILE, "w") as f:
        f.write_int(42)
        f.write("\n")
        f.write_float(3.14)
        f.write("\n")
    test_assert(file_exists(TMP_FILE) == 1)
    sz: int = file_size(TMP_FILE)
    test_assert(sz > 0)


@test
def test_file_read_line() -> void:
    with open(TMP_FILE, "w") as f:
        f.write_line("alpha")
        f.write_line("beta")
        f.write_line("gamma")

    r: file = open(TMP_FILE, "r")
    l1: str = r.readline()
    l2: str = r.readline()
    l3: str = r.readline()
    r.close()
    test_assert(str_eq(l1, str_new("alpha")) == 1)
    test_assert(str_eq(l2, str_new("beta")) == 1)
    test_assert(str_eq(l3, str_new("gamma")) == 1)


@test
def test_file_size() -> void:
    with open(TMP_FILE, "w") as f:
        f.write("12345")
    test_assert(file_size(TMP_FILE) == 5)


@test
def test_file_not_exists() -> void:
    test_assert(file_exists("/tmp/nathra_definitely_no_such_file_xyz.txt") == 0)


@test
def test_remove_file() -> void:
    with open(TMP_FILE, "w") as f:
        f.write("bye")
    test_assert(file_exists(TMP_FILE) == 1)
    remove_file(TMP_FILE)
    test_assert(file_exists(TMP_FILE) == 0)


@test
def test_path_basename() -> void:
    b: str = path_basename("/home/user/docs/report.pdf")
    test_assert(str_eq(b, str_new("report.pdf")) == 1)


@test
def test_path_basename_no_dir() -> void:
    b: str = path_basename("file.txt")
    test_assert(str_eq(b, str_new("file.txt")) == 1)


@test
def test_path_ext() -> void:
    e: str = path_ext("photo.jpg")
    test_assert(str_eq(e, str_new(".jpg")) == 1)


@test
def test_path_ext_no_ext() -> void:
    e: str = path_ext("Makefile")
    test_assert(str_len(e) == 0)


@test
def test_path_dirname() -> void:
    d: str = path_dirname("/home/user/docs/report.pdf")
    test_assert(str_eq(d, str_new("/home/user/docs")) == 1)


@test
def test_path_join() -> void:
    j: str = path_join("/tmp", "output.txt")
    test_assert(str_len(j) > 4)


@test
def test_dir_create_and_remove() -> void:
    dir_create(TMP_DIR)
    test_assert(dir_exists(TMP_DIR) == 1)
    dir_remove(TMP_DIR)
    test_assert(dir_exists(TMP_DIR) == 0)


@test
def test_dir_cwd_not_empty() -> void:
    cwd: str = dir_cwd()
    test_assert(str_len(cwd) > 0)