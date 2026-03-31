# Build Topology

Nathra's compiler derives shared library boundaries from code analysis. The topology is a compiler output, not a compiler input.

## How it works

The compiler builds a whole-program call graph with weighted edges during its normal AST walk. It then:

1. **Classifies** each module's reloadability based on resource ownership
2. **Clusters** functions to minimize cross-cluster call weight
3. **Generates** a build plan: which clusters become `.so`s, which are statically linked

## Module classification

| Category | Meaning | Swappable? |
|---|---|---|
| `pure` | Stateless functions, no globals | Yes |
| `process-local` | Owns in-process state (globals) | Yes, with state migration |
| `resource-owner` | Owns file handles, sockets, threads | No — pinned into host |
| `abi-anchor` | Defines interfaces others depend on | Version-controlled only |

Classification is inferred from code analysis. A module that calls `thread_spawn` or `file_open` (without matching cleanup in the same scope) is a `resource-owner`. A module with mutable globals is `process-local`. Everything else is `pure`.

## Build modes

### Dev

Fine-grained `.so` per cluster. Hot-swap enabled for swappable modules. Swappable `.so`s are compiled with stricter flags (`-DNR_SAFE -Wall -Werror`) because the cost of a bad reload is a downed host process.

```sh
python3 cli/nathra.py build.py --topology=dev
```

### Release

All clusters merged into a single static binary with full LTO (`-flto -O2`). No `.so` files, no dispatch table, no reload overhead. This is what you ship.

```sh
python3 cli/nathra.py build.py --topology=release
```

### Service

Non-swappable modules (`resource-owner`, `abi-anchor`) are pinned into the host binary. Swappable modules are `.so`s that can be reloaded live without restarting the process. ABI-anchor modules embed a layout hash — reload is rejected if the hash changes.

```sh
python3 cli/nathra.py build.py --topology=service
```

## Overrides

The build file handles only exceptions:

```python
pin_together("renderer.mesh", "renderer.draw")  # force same .so
keep_alive("net.socket_manager")                # never hot-swap
```

## Dispatch table

Cross-cluster calls go through a function pointer dispatch table. Each `.so` registers its function pointers at load time. The host initializes the table before calling any `.so` code. Inline wrappers make the indirection invisible to callers.

## Hot-swap at runtime

```c
// From nathra code or C:
nr_topology_reload("renderer");    // reload one module
nr_topology_reload_all();          // reload all swappable modules
```

The reload manager:
- Calls `dlclose` on the old `.so`
- Calls `dlopen` on the new `.so`
- Re-registers the dispatch table entries
- Increments the generation counter

For `process-local` modules, state migration stubs (`nr_state_save_<module>` / `nr_state_load_<module>`) are called before/after the reload.

## State and code separation

The key to hot reload being real rather than theatrical is separating durable state from reloadable code. If a module mixes long-lived state with frequently-changing logic, it cannot be cleanly swapped.

Modules inferred as `resource-owner` are automatically pinned. For `process-local` modules, the compiler generates empty state migration stubs that the developer fills in for modules with non-trivial state.

## Architecture

```
compiler/topology.py    — analysis + build plan (pure Python, no codegen)
runtime/nathra_rt.h     — NrReloadManager, dlopen/dlsym wrappers
lib/build.py            — build_with_topology() links .so's and host
```

The topology module consumes the compiler's existing call graph, allocation tags, and decorator metadata. It does not modify the compiler or the generated C.
