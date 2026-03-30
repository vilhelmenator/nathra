"nathra"
from nathra_stubs import *
c_include("<dlfcn.h>")


def main() -> void:
    lib: ptr[void] = hotreload_open("./tests/game_logic.dylib")

    init_fn:      func[int, void]   = hotreload_sym(lib, "init")
    update_fn:    func[float, void] = hotreload_sym(lib, "update")
    get_state_fn: func[int]         = hotreload_sym(lib, "get_state")

    init_fn(0)
    update_fn(1.0)
    update_fn(2.0)
    s: int = get_state_fn()
    print(s)   # 300  (100 + 200)

    hotreload_close(lib)