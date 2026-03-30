"nathra"
# Test with statement using file_open/file_close from runtime

@test
def test_with_file_write() -> void:
    # Write a file using with — file_close called automatically
    with file_open("/tmp/nathra_with_test.txt", "w") as f:
        file_write(f, "hello nathra\n")
    # File exists after the with block
    test_assert(file_exists("/tmp/nathra_with_test.txt") == 1)


@test
def test_with_write_read() -> void:
    with file_open("/tmp/nathra_with2.txt", "w") as wf:
        file_write(wf, "test")
    # Read it back
    rf: file = file_open("/tmp/nathra_with2.txt", "r")
    content: str = file_read_all(rf)
    file_close(rf)
    test_assert(str_len(content) == 4)


@test
def test_with_nested() -> void:
    with file_open("/tmp/nathra_with_a.txt", "w") as fa:
        file_write(fa, "a\n")
        with file_open("/tmp/nathra_with_b.txt", "w") as fb:
            file_write(fb, "b\n")
    test_assert(file_exists("/tmp/nathra_with_a.txt") == 1)
    test_assert(file_exists("/tmp/nathra_with_b.txt") == 1)