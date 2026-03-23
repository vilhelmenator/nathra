"""Example codegen hook module for testing."""


def wrap_with_banner(banner="DEFAULT"):
    """Hook that wraps the function with a banner comment."""
    def hook(func_name, params, return_type, c_body):
        return f"/* === {banner}: {func_name} === */\n{c_body}\n/* === end {func_name} === */"
    return hook


def noop():
    """Hook that does nothing — function emits normally."""
    def hook(func_name, params, return_type, c_body):
        return None
    return hook


def add_entry_point(name="main_entry"):
    """Hook that appends a platform entry point after the function."""
    def hook(func_name, params, return_type, c_body):
        param_str = ", ".join(f"{ctype} {pname}" for pname, ctype in params)
        call_args = ", ".join(pname for pname, _ in params)
        return f"""{c_body}

void {name}(void) {{
    {func_name}({call_args});
}}"""
    return hook
