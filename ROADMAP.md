# Nathra Compiler Roadmap


## Automatic Build Topology from Compiler Analysis

The compiler should synthesize a default dynamic-link topology from dependency, thermal, and lifecycle analysis. Developers intervene only to express semantic constraints the compiler cannot safely infer.

### Core Idea

Nathra's compiler already performs `@hot`/`@cold` analysis and builds a full AST and call graph. This information is sufficient to produce a strong default partitioning of the binary into shared libraries — refined by safety and lifecycle analysis — without requiring manual build file annotations.

The topology is a compiler output, not a compiler input. This eliminates duplicated truth between the build system and the code, which is where build systems rot.

### Partitioning Inputs

The compiler uses the following to derive `.so` boundaries:

- **Call graph + thermal map**: tightly coupled hot code clusters together; cold stable code forms a base library that is never swapped
- **Ownership and lifecycle analysis**: `own[T]`, arena boundaries, and resource lifetimes inform which modules can be safely unloaded
- **Header/interface boundaries**: already enforced by the compiler, these are treated as constraints on valid cut points, not evidence that a cut is natural
- **Optimization objective**: minimize cross-DSO calls subject to hot-swap granularity and reload blast radius

`build.nth` handles only exceptions and overrides rather than describing the full topology:

```python
# build.nth - only needed for exceptions
pin_together("renderer.mesh", "renderer.draw")  # force same .so despite analysis
keep_alive("net.socket_manager")                # never hot-swap this
```

### Reloadability Model

"Swappable or not" must be a first-class semantic property, not a loose annotation. The compiler infers a reloadability category for each module:

| Category | Description |
|---|---|
| `pure` | Stateless, freely reloadable |
| `process-local` | Owns in-process state; reloadable if state can be migrated |
| `resource-owner` | Owns external handles, sockets, file descriptors; non-swappable |
| `abi-anchor` | Defines interfaces others depend on; version-controlled reload only |
| `indirection-only` | Reloadable only behind a stable vtable or function pointer boundary |

Modules inferred as `resource-owner` or `abi-anchor` are pinned automatically. The developer only overrides when the inference is wrong.

### State and Code Separation

The key to hot reload being real rather than theatrical is separating *durable state* from *reloadable code*. A module that mixes long-lived state with logic that changes frequently cannot be cleanly swapped.

`@persistent_state` marks data or subsystems whose state must survive reloads. The compiler uses this to:

- hoist durable state into stable anchor partitions outside reloadable clusters
- warn when reloadable code directly owns persistent state
- generate state handoff points between reload generations where schema is compatible

Without this separation, hot reload works in demos and breaks in production.

### Build Modes

- **Dev**: fine-grained `.so` per hot cluster, enabling isolated hot-swap of individual modules without restarting the host process
- **Release**: clusters merged according to graph analysis, with full LTO across the combined result; automatic topology matters primarily for dev and service modes
- **Service**: non-swappable modules are pinned; the rest can be reloaded live without taking down the process

### Safety in Hot-Reload Builds

Dev builds targeting hot-swap apply stricter compilation automatically. The cost of a bad reload is a downed host process, so the bar is higher than a normal debug build:

- Warnings as errors
- Null guards and bounds checks on slices
- Reload-safe ABI discipline: layout stability across boundaries, vtable/interface version checks, safe destructor and shutdown ordering
- Allocator domain awareness: cross-module ownership of heap memory is flagged

Note: the hard part of hot reload is not graph partitioning. It is preserving correctness when code, state, and resource ownership change under a live process. Stricter compilation is necessary but not sufficient — reload-safe state discipline is the deeper requirement.

### Non-Goal

The developer should not need to think about `.so` boundaries in the common case. The topology is a compiler output, not a compiler input.
