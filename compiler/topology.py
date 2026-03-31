"""
topology.py — Build topology analyzer for nathra.

Consumes the compiler's call graph, module info, allocation tags, and
decorator metadata to produce a partitioning plan for shared libraries.

Phase 1: Pure analysis — classify modules, cluster functions, detect violations.
Phase 2: Build plan — map clusters to .so targets, generate ABI boundaries.

Usage:
    from compiler.topology import TopologyAnalyzer

    analyzer = TopologyAnalyzer()
    analyzer.add_module("renderer", compiler_instance)
    analyzer.add_module("physics", compiler_instance)
    report = analyzer.analyze()
    report.print()
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import sys


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class Reloadability(Enum):
    """Module reloadability category — inferred from code analysis."""
    PURE = "pure"                       # stateless, freely reloadable
    PROCESS_LOCAL = "process-local"     # owns in-process state, reloadable with migration
    RESOURCE_OWNER = "resource-owner"   # owns external handles, non-swappable
    ABI_ANCHOR = "abi-anchor"           # defines interfaces others depend on


class BuildMode(Enum):
    """Build mode — controls how topology maps to link strategy."""
    DEV = "dev"           # fine-grained .so per cluster, hot-swap enabled
    RELEASE = "release"   # all clusters merged, static link, full LTO
    SERVICE = "service"   # pinned modules static, swappable modules as .so


@dataclass
class FunctionInfo:
    """Metadata for a single function, collected from the compiler."""
    name: str
    module: str
    is_hot: bool = False
    is_cold: bool = False
    is_export: bool = False
    is_test: bool = False
    alloc_tags: frozenset = field(default_factory=frozenset)
    # Resources this function acquires (file_open, mutex_new, etc.)
    acquires_resources: list = field(default_factory=list)
    # Resources this function releases (file_close, mutex_free, etc.)
    releases_resources: list = field(default_factory=list)


@dataclass
class ModuleData:
    """All topology-relevant data for one compiled module."""
    name: str
    functions: dict = field(default_factory=dict)      # fname → FunctionInfo
    imports: list = field(default_factory=list)         # module names imported
    from_imports: dict = field(default_factory=dict)    # local_name → (module, original)
    exports: set = field(default_factory=set)           # @export function names
    has_globals: bool = False                           # module-level mutable state
    has_thread_locals: bool = False
    reloadability: Reloadability = Reloadability.PURE


@dataclass
class CallEdge:
    """Weighted edge between two functions (possibly cross-module)."""
    caller: str        # "module.func"
    callee: str        # "module.func"
    weight: float = 1.0


@dataclass
class Cluster:
    """A group of functions that will be linked into the same .so."""
    id: int
    functions: list = field(default_factory=list)  # ["module.func", ...]
    modules: set = field(default_factory=set)       # module names represented
    reloadability: Reloadability = Reloadability.PURE
    total_weight: float = 0.0                       # sum of internal edge weights


@dataclass
class TopologyReport:
    """The output of topology analysis."""
    modules: dict = field(default_factory=dict)       # name → ModuleData
    clusters: list = field(default_factory=list)       # [Cluster, ...]
    cross_cluster_edges: list = field(default_factory=list)  # [CallEdge, ...]
    warnings: list = field(default_factory=list)       # diagnostic strings
    heap_violations: list = field(default_factory=list)  # cross-module ownership issues

    def print(self, file=sys.stderr):
        """Print a human-readable topology report."""
        p = lambda *a, **kw: print(*a, **kw, file=file)

        p("=" * 60)
        p("  TOPOLOGY ANALYSIS")
        p("=" * 60)
        p()

        # Module classifications
        p("Module classifications:")
        for name, mod in sorted(self.modules.items()):
            funcs = len(mod.functions)
            exports = len(mod.exports)
            p(f"  {name:<30} {mod.reloadability.value:<18} "
              f"({funcs} funcs, {exports} exports)")
        p()

        # Clusters
        p(f"Clusters ({len(self.clusters)}):")
        for cl in self.clusters:
            reload_str = cl.reloadability.value
            p(f"  cluster {cl.id}: [{reload_str}] "
              f"weight={cl.total_weight:.0f}")
            for fn in cl.functions[:10]:
                p(f"    {fn}")
            if len(cl.functions) > 10:
                p(f"    ... and {len(cl.functions) - 10} more")
        p()

        # Cross-cluster edges
        if self.cross_cluster_edges:
            p(f"Cross-cluster edges ({len(self.cross_cluster_edges)}):")
            sorted_edges = sorted(self.cross_cluster_edges,
                                  key=lambda e: -e.weight)
            for edge in sorted_edges[:15]:
                p(f"  {edge.caller} → {edge.callee}  "
                  f"weight={edge.weight:.0f}")
            if len(sorted_edges) > 15:
                p(f"  ... and {len(sorted_edges) - 15} more")
            p()

        # Warnings
        if self.warnings:
            p(f"Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                p(f"  {w}")
            p()

        # Heap violations
        if self.heap_violations:
            p(f"Cross-module heap ownership violations "
              f"({len(self.heap_violations)}):")
            for v in self.heap_violations:
                p(f"  {v}")
            p()

        p("=" * 60)


# ---------------------------------------------------------------------------
# Build plan (Phase 2)
# ---------------------------------------------------------------------------

@dataclass
class SharedLibTarget:
    """A shared library derived from a cluster."""
    name: str                                      # e.g. "cluster_0" or "renderer"
    cluster_id: int
    modules: list = field(default_factory=list)     # module names in this .so
    c_files: list = field(default_factory=list)     # .c files to compile
    reloadability: Reloadability = Reloadability.PURE
    # Functions called FROM this .so INTO other .so's (need dispatch stubs)
    outgoing_calls: list = field(default_factory=list)  # [(local_func, remote_func), ...]
    # Functions called INTO this .so FROM other .so's (need to be exported)
    incoming_calls: list = field(default_factory=list)  # [func_name, ...]
    abi_hash: int = 0                               # FNV-1a hash of exported ABI


@dataclass
class DispatchEntry:
    """A function pointer entry in the indirection table."""
    name: str                   # fully qualified: "module.func"
    ret_type: str               # C return type
    param_types: list           # [(name, ctype), ...]
    source_cluster: int         # cluster that owns the implementation
    callers: list = field(default_factory=list)  # cluster IDs that call this


@dataclass
class BuildPlan:
    """Complete build plan derived from topology analysis."""
    shared_libs: list = field(default_factory=list)    # [SharedLibTarget, ...]
    host_exe: str = ""                                  # main executable name
    host_c_files: list = field(default_factory=list)   # .c files for the host
    dispatch_table: list = field(default_factory=list) # [DispatchEntry, ...]
    # The pinned (non-swappable) cluster, linked statically into the host
    pinned_cluster: int = -1
    mode: BuildMode = BuildMode.DEV
    lto: bool = False                                   # release mode: link with LTO

    def print(self, file=sys.stderr):
        """Print a human-readable build plan."""
        p = lambda *a, **kw: print(*a, **kw, file=file)

        p("=" * 60)
        p(f"  BUILD PLAN  [{self.mode.value}]")
        p("=" * 60)
        p()

        if self.lto:
            p("Link-time optimization: enabled")
            p()

        if self.host_exe:
            p(f"Host executable: {self.host_exe}")
            if self.host_c_files:
                p(f"  Static .c files: {', '.join(self.host_c_files)}")
            p()

        p(f"Shared libraries ({len(self.shared_libs)}):")
        for lib in self.shared_libs:
            swappable = lib.reloadability in (Reloadability.PURE,
                                               Reloadability.PROCESS_LOCAL)
            swap_str = "swappable" if swappable else "pinned"
            p(f"  lib{lib.name}.so  [{lib.reloadability.value}] ({swap_str})")
            for mod in lib.modules:
                p(f"    module: {mod}")
            if lib.incoming_calls:
                p(f"    exports: {len(lib.incoming_calls)} functions")
            if lib.outgoing_calls:
                p(f"    imports: {len(lib.outgoing_calls)} cross-cluster calls")
        p()

        if self.dispatch_table:
            p(f"Dispatch table ({len(self.dispatch_table)} entries):")
            for entry in self.dispatch_table:
                callers = ", ".join(f"cluster_{c}" for c in entry.callers)
                p(f"  {entry.name}  (owned by cluster_{entry.source_cluster}"
                  f", called from {callers})")
            p()

        p("=" * 60)

    def generate_dispatch_header(self) -> str:
        """Generate the C dispatch header for cross-cluster calls.

        This header defines:
        - A struct of function pointers (the dispatch table)
        - A global instance of the table
        - Inline wrapper functions that call through the table

        Each .so loads its function pointers into the table at init time.
        The host exe initializes the table before calling any .so code.
        """
        if not self.dispatch_table:
            return ""

        lines = [
            "/* Auto-generated by nathra topology — do not edit */",
            "#ifndef NATHRA_DISPATCH_H",
            "#define NATHRA_DISPATCH_H",
            "",
            '#include "nathra_rt.h"',
            "",
            "/* Dispatch table struct */",
            "typedef struct {",
        ]

        for entry in self.dispatch_table:
            params = ", ".join(f"{ct} {cn}" for cn, ct in entry.param_types)
            if not params:
                params = "void"
            lines.append(f"    {entry.ret_type} (*{_mangle(entry.name)})({params});")

        lines += [
            "} NrDispatchTable;",
            "",
            "/* Global dispatch table */",
            "extern NrDispatchTable nr_dispatch;",
            "",
            "/* Inline wrappers — call these from application code */",
        ]

        for entry in self.dispatch_table:
            params = ", ".join(f"{ct} {cn}" for cn, ct in entry.param_types)
            args = ", ".join(cn for cn, _ in entry.param_types)
            mangled = _mangle(entry.name)
            if not params:
                params = "void"
                args = ""

            if entry.ret_type == "void":
                lines.append(f"static inline void {mangled}({params}) {{")
                lines.append(f"    nr_dispatch.{mangled}({args});")
            else:
                lines.append(
                    f"static inline {entry.ret_type} {mangled}({params}) {{")
                lines.append(f"    return nr_dispatch.{mangled}({args});")
            lines.append("}")
            lines.append("")

        lines += [
            "/* Registration — each .so calls this at load time */",
        ]

        # Group entries by source cluster for per-cluster init functions
        by_cluster = {}
        for entry in self.dispatch_table:
            by_cluster.setdefault(entry.source_cluster, []).append(entry)

        for cid, entries in sorted(by_cluster.items()):
            lines.append(
                f"static inline void nr_dispatch_register_cluster_{cid}"
                f"(void) {{")
            for entry in entries:
                mangled = _mangle(entry.name)
                # The actual function symbol (defined in the .so)
                impl_name = _mangle(entry.name) + "_impl"
                lines.append(f"    nr_dispatch.{mangled} = {impl_name};")
            lines.append("}")
            lines.append("")

        lines += [
            "#endif /* NATHRA_DISPATCH_H */",
            "",
        ]

        return "\n".join(lines)

    def generate_dispatch_impl(self) -> str:
        """Generate the C file that defines the global dispatch table."""
        if not self.dispatch_table:
            return ""

        return "\n".join([
            "/* Auto-generated by nathra topology — do not edit */",
            '#include "nathra_dispatch.h"',
            "",
            "NrDispatchTable nr_dispatch = {0};",
            "",
        ])

    def generate_reload_init(self) -> str:
        """Generate the C init function that sets up the reload manager.

        Called by the host executable at startup. Registers all clusters,
        loads each .so, and populates the dispatch table.
        """
        lines = [
            "/* Auto-generated by nathra topology — do not edit */",
            '#include "nathra_rt.h"',
        ]

        if self.dispatch_table:
            lines.append('#include "nathra_dispatch.h"')

        lines += [
            "",
            "static NrReloadManager _nr_rm;",
            "",
            "void nr_topology_init(void) {",
            f"    _nr_rm = nr_reload_manager_new({len(self.shared_libs)});",
        ]

        for lib in self.shared_libs:
            is_pinned = lib.cluster_id == self.pinned_cluster
            reloadable = 0 if is_pinned else 1
            # Determine .so path based on platform
            lines.append(f"    nr_reload_register(&_nr_rm, "
                         f'"{lib.name}", '
                         f'"lib{lib.name}.so", '
                         f'{reloadable});  '
                         f'/* {"pinned" if is_pinned else "swappable"} */')

        lines.append("")

        # Load all clusters
        for i, lib in enumerate(self.shared_libs):
            if lib.cluster_id == self.pinned_cluster:
                lines.append(f"    /* cluster {i} ({lib.name}) is pinned"
                             f" — linked statically */")
            else:
                lines.append(f"    nr_reload_load(&_nr_rm, {i});  "
                             f"/* {lib.name} */")

        lines += [
            "}",
            "",
            "void nr_topology_shutdown(void) {",
            "    nr_reload_manager_free(&_nr_rm);",
            "}",
            "",
            "int32_t nr_topology_reload(const char* name) {",
            "    return nr_reload_by_name(&_nr_rm, name);",
            "}",
            "",
            "int32_t nr_topology_reload_all(void) {",
            "    return nr_reload_all(&_nr_rm);",
            "}",
            "",
        ]

        return "\n".join(lines)

    def generate_state_migration_stubs(self) -> str:
        """Generate save/load state stubs for process-local clusters.

        For each process-local module, generates:
        - nr_state_save_<module>(NrWriter* w) — serialize globals
        - nr_state_load_<module>(NrReader* r) — deserialize globals

        These are called before/after a reload to migrate state.
        The stubs are empty by default — the developer fills them in
        for modules with non-trivial state.
        """
        lines = [
            "/* Auto-generated state migration stubs — edit as needed */",
            '#include "nathra_rt.h"',
            "",
        ]

        has_stubs = False
        for lib in self.shared_libs:
            if lib.reloadability != Reloadability.PROCESS_LOCAL:
                continue
            for mod in lib.modules:
                has_stubs = True
                lines += [
                    f"/* State migration for module '{mod}' */",
                    f"void nr_state_save_{mod}(NrWriter* w) {{",
                    f"    /* TODO: serialize {mod}'s globals into w */",
                    f"    (void)w;",
                    f"}}",
                    f"",
                    f"void nr_state_load_{mod}(NrReader* r) {{",
                    f"    /* TODO: deserialize {mod}'s globals from r */",
                    f"    (void)r;",
                    f"}}",
                    f"",
                ]

        if not has_stubs:
            return ""

        return "\n".join(lines)


def _mangle(qualified_name: str) -> str:
    """Convert 'module.func' to 'module_func' for C identifiers."""
    return qualified_name.replace(".", "_")


# ---------------------------------------------------------------------------
# Resource detection
# ---------------------------------------------------------------------------

# Functions that acquire external resources (file handles, threads, etc.)
_RESOURCE_ACQUIRE = {
    "file_open", "file_open_safe", "nr_file_open", "nr_file_open_safe",
    "thread_spawn", "nr_thread_spawn",
    "mutex_new", "nr_mutex_new",
    "cond_new", "nr_cond_new",
    "channel_new", "nr_channel_new",
    "pool_new", "nr_pool_new",
}

# Functions that release external resources
_RESOURCE_RELEASE = {
    "file_close", "nr_file_close",
    "thread_join", "nr_thread_join",
    "mutex_free", "nr_mutex_free",
    "cond_free", "nr_cond_free",
    "channel_free", "nr_channel_free",
    "pool_free", "nr_pool_free",
}

# Allocation functions (heap, not resources)
_ALLOC_FUNCS = {
    "alloc", "alloc_safe", "nr_alloc",
    "list_new", "dict_new", "str_new",
    "nr_list_new", "nr_dict_new", "nr_str_new",
    "writer_new", "nr_writer_new",
    "arena_new", "nr_arena_new",
}

_FREE_FUNCS = {
    "free", "nr_free",
    "list_free", "dict_free", "str_free",
    "nr_list_free", "nr_dict_free", "nr_str_free",
    "writer_free", "nr_writer_free",
    "arena_free", "nr_arena_free",
}


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

class TopologyAnalyzer:
    """Analyzes compiled modules and produces a build topology."""

    def __init__(self):
        self.modules: dict = {}           # name → ModuleData
        self.call_edges: list = []        # [CallEdge, ...]
        self._func_to_module: dict = {}   # "module.func" → module_name
        self._overrides_pin: dict = {}    # "module.func" → "module.func" (pin_together)
        self._overrides_keep: set = set() # module names to keep_alive

    def add_module(self, name: str, compiler) -> None:
        """Extract topology-relevant data from a compiled module.

        Args:
            name: Module name
            compiler: A Compiler instance that has already compiled this module
        """
        import ast

        mod = ModuleData(name=name)

        # Extract function info
        for func in getattr(compiler, '_all_func_defs', {}).values():
            if not isinstance(func, ast.FunctionDef):
                continue
            decs = compiler.get_decorators(func)
            fi = FunctionInfo(
                name=func.name,
                module=name,
                is_hot="hot" in decs,
                is_cold=(func.name in getattr(compiler, '_cold_funcs', set())
                         or "cold" in decs),
                is_export="export" in decs,
                is_test="test" in decs,
                alloc_tags=getattr(compiler, 'func_alloc_tags', {}).get(
                    func.name, frozenset()),
            )

            # Scan for resource acquire/release
            for nd in ast.walk(func):
                if (isinstance(nd, ast.Call)
                        and isinstance(nd.func, ast.Name)):
                    fname = nd.func.id
                    if fname in _RESOURCE_ACQUIRE:
                        fi.acquires_resources.append(fname)
                    elif fname in _RESOURCE_RELEASE:
                        fi.releases_resources.append(fname)

            mod.functions[func.name] = fi
            self._func_to_module[f"{name}.{func.name}"] = name

            if fi.is_export:
                mod.exports.add(func.name)

        # Module-level state detection
        mod.imports = list(getattr(compiler, 'imports', []))
        mod.from_imports = dict(getattr(compiler, 'from_imports', {}))

        # Check for module-level globals (mutable state)
        for g in getattr(compiler, 'globals', []):
            mod.has_globals = True
            break

        # Check for thread-local storage
        # (detected by the presence of thread_local annotations in the AST)
        for fi in mod.functions.values():
            if fi.acquires_resources:
                # Any function that acquires resources marks the module
                break

        self.modules[name] = mod

    def add_call_edges(self, compiler, module_name: str) -> None:
        """Extract weighted call edges from a compiled module.

        Uses the compiler's existing _build_weighted_call_graph for
        intra-module edges, and scans for cross-module calls.
        """
        import ast

        funcs = list(getattr(compiler, '_all_func_defs', {}).values())

        # Intra-module edges (reuse existing infrastructure)
        intra_edges = compiler._build_weighted_call_graph(funcs)
        for (a, b), weight in intra_edges.items():
            self.call_edges.append(CallEdge(
                caller=f"{module_name}.{a}",
                callee=f"{module_name}.{b}",
                weight=weight,
            ))

        # Cross-module edges
        from_imports = getattr(compiler, 'from_imports', {})
        imports = set(getattr(compiler, 'imports', []))
        mod_funcs = {f.name for f in funcs if isinstance(f, ast.FunctionDef)}

        for func in funcs:
            if not isinstance(func, ast.FunctionDef):
                continue
            for nd in ast.walk(func):
                if not (isinstance(nd, ast.Call)
                        and isinstance(nd.func, ast.Name)):
                    continue
                callee_name = nd.func.id
                # Skip intra-module calls (already handled)
                if callee_name in mod_funcs:
                    continue
                # Check if this is an imported function
                if callee_name in from_imports:
                    src_mod, orig_name = from_imports[callee_name]
                    self.call_edges.append(CallEdge(
                        caller=f"{module_name}.{func.name}",
                        callee=f"{src_mod}.{orig_name}",
                        weight=1.0,
                    ))

    def pin_together(self, *qualified_names: str) -> None:
        """Force functions/modules into the same cluster."""
        anchor = qualified_names[0]
        for name in qualified_names[1:]:
            self._overrides_pin[name] = anchor

    def keep_alive(self, module_name: str) -> None:
        """Mark a module as non-swappable."""
        self._overrides_keep.add(module_name)

    def analyze(self) -> TopologyReport:
        """Run the full topology analysis pipeline."""
        report = TopologyReport(modules=dict(self.modules))

        # Step 1: Classify module reloadability
        self._classify_modules(report)

        # Step 2: Detect cross-module heap ownership violations
        self._detect_heap_violations(report)

        # Step 3: Build clusters
        self._build_clusters(report)

        # Step 4: Apply overrides
        self._apply_overrides(report)

        # Step 5: Compute cross-cluster edges
        self._compute_cross_cluster_edges(report)

        return report

    # ------------------------------------------------------------------
    # Step 1: Module classification
    # ------------------------------------------------------------------

    def _classify_modules(self, report: TopologyReport) -> None:
        """Classify each module's reloadability based on code analysis."""
        for name, mod in self.modules.items():
            # Check for resource acquisition
            has_resources = any(
                fi.acquires_resources
                for fi in mod.functions.values()
                if not all(r in fi.releases_resources
                           for r in fi.acquires_resources)
            )

            # Check if other modules depend on this module's exports
            is_depended_on = any(
                name in other.imports or
                any(src == name for src, _ in other.from_imports.values())
                for other_name, other in self.modules.items()
                if other_name != name
            )

            # Classify
            if name in self._overrides_keep:
                mod.reloadability = Reloadability.RESOURCE_OWNER
                report.warnings.append(
                    f"{name}: pinned as resource-owner by keep_alive()")
            elif has_resources:
                mod.reloadability = Reloadability.RESOURCE_OWNER
            elif mod.has_globals:
                mod.reloadability = Reloadability.PROCESS_LOCAL
            elif is_depended_on and mod.exports:
                mod.reloadability = Reloadability.ABI_ANCHOR
            else:
                mod.reloadability = Reloadability.PURE

        report.modules = dict(self.modules)

    # ------------------------------------------------------------------
    # Step 2: Heap ownership violations
    # ------------------------------------------------------------------

    def _detect_heap_violations(self, report: TopologyReport) -> None:
        """Detect cross-module heap ownership issues.

        Flags cases where module A allocates (Producer) and module B
        frees (Consumer) without an explicit ownership transfer.
        """
        # Build producer/consumer maps per module
        producers = {}  # "module.func" → module
        consumers = {}  # "module.func" → module

        for name, mod in self.modules.items():
            for fi in mod.functions.values():
                qname = f"{name}.{fi.name}"
                if "producer" in fi.alloc_tags:
                    producers[qname] = name
                if "consumer" in fi.alloc_tags:
                    consumers[qname] = name

        # Check cross-module edges where a producer's output flows to
        # a consumer in a different module
        for edge in self.call_edges:
            if edge.callee in consumers and edge.caller in producers:
                caller_mod = self._func_to_module.get(edge.caller, "?")
                callee_mod = self._func_to_module.get(edge.callee, "?")
                if caller_mod != callee_mod:
                    report.heap_violations.append(
                        f"{edge.caller} (producer in {caller_mod}) → "
                        f"{edge.callee} (consumer in {callee_mod}): "
                        f"cross-module ownership transfer")

    # ------------------------------------------------------------------
    # Step 3: Clustering
    # ------------------------------------------------------------------

    def _build_clusters(self, report: TopologyReport) -> None:
        """Cluster functions to minimize cross-cluster edge weight.

        Uses a greedy agglomerative approach:
        1. Start with each module as its own cluster
        2. Merge the two clusters with the heaviest inter-cluster edge
        3. Stop when merging would combine clusters with incompatible
           reloadability categories
        """
        # Start: one cluster per module
        clusters = {}
        cluster_id = 0
        func_to_cluster = {}  # "module.func" → cluster_id

        for name, mod in self.modules.items():
            cl = Cluster(
                id=cluster_id,
                functions=[f"{name}.{fn}" for fn in mod.functions],
                modules={name},
                reloadability=mod.reloadability,
            )
            # Compute internal weight (sum of intra-module edges)
            mod_funcs = {f"{name}.{fn}" for fn in mod.functions}
            for edge in self.call_edges:
                if edge.caller in mod_funcs and edge.callee in mod_funcs:
                    cl.total_weight += edge.weight
            for fn in mod.functions:
                func_to_cluster[f"{name}.{fn}"] = cluster_id
            clusters[cluster_id] = cl
            cluster_id += 1

        # Build inter-cluster edge weights
        def _inter_cluster_weight(c1_id, c2_id):
            total = 0.0
            for edge in self.call_edges:
                ec = func_to_cluster.get(edge.caller)
                ee = func_to_cluster.get(edge.callee)
                if ec is None or ee is None:
                    continue
                if (ec == c1_id and ee == c2_id) or \
                   (ec == c2_id and ee == c1_id):
                    total += edge.weight
            return total

        # Reloadability compatibility: can these two categories be merged?
        def _compatible(r1: Reloadability, r2: Reloadability) -> bool:
            # Only merge clusters with matching reloadability
            # Exception: PURE can merge with anything
            if r1 == Reloadability.PURE or r2 == Reloadability.PURE:
                return True
            return r1 == r2

        # Greedy merge
        max_merges = len(clusters) * 2  # safety cap
        for _ in range(max_merges):
            best_pair = None
            best_weight = 0.0

            active = [cid for cid, cl in clusters.items() if cl.functions]
            for i, c1 in enumerate(active):
                for c2 in active[i + 1:]:
                    if not _compatible(clusters[c1].reloadability,
                                       clusters[c2].reloadability):
                        continue
                    w = _inter_cluster_weight(c1, c2)
                    if w > best_weight:
                        best_weight = w
                        best_pair = (c1, c2)

            # Stop if no beneficial merge exists
            if best_pair is None or best_weight <= 0:
                break

            # Merge c2 into c1
            c1_id, c2_id = best_pair
            c1, c2 = clusters[c1_id], clusters[c2_id]
            c1.functions.extend(c2.functions)
            c1.modules |= c2.modules
            c1.total_weight += c2.total_weight + best_weight

            # Merged reloadability: most restrictive wins
            priority = [Reloadability.RESOURCE_OWNER, Reloadability.ABI_ANCHOR,
                        Reloadability.PROCESS_LOCAL, Reloadability.PURE]
            for r in priority:
                if c1.reloadability == r or c2.reloadability == r:
                    c1.reloadability = r
                    break

            # Update function → cluster mapping
            for fn in c2.functions:
                func_to_cluster[fn] = c1_id
            c2.functions = []
            c2.modules = set()

        # Collect active clusters
        report.clusters = [cl for cl in clusters.values() if cl.functions]

        # Renumber
        for i, cl in enumerate(report.clusters):
            cl.id = i

    # ------------------------------------------------------------------
    # Step 4: Apply overrides
    # ------------------------------------------------------------------

    def _apply_overrides(self, report: TopologyReport) -> None:
        """Apply pin_together and keep_alive overrides."""
        if not self._overrides_pin:
            return

        # Build function → cluster index
        func_to_ci = {}
        for i, cl in enumerate(report.clusters):
            for fn in cl.functions:
                func_to_ci[fn] = i

        # For each pin_together pair, merge clusters
        for fn, anchor in self._overrides_pin.items():
            ci_fn = func_to_ci.get(fn)
            ci_anchor = func_to_ci.get(anchor)
            if ci_fn is None or ci_anchor is None:
                report.warnings.append(
                    f"pin_together: could not find '{fn}' or '{anchor}'")
                continue
            if ci_fn == ci_anchor:
                continue  # already together

            # Merge fn's cluster into anchor's cluster
            src = report.clusters[ci_fn]
            dst = report.clusters[ci_anchor]
            dst.functions.extend(src.functions)
            dst.modules |= src.modules
            for f in src.functions:
                func_to_ci[f] = ci_anchor
            src.functions = []
            src.modules = set()

        # Remove empty clusters and renumber
        report.clusters = [cl for cl in report.clusters if cl.functions]
        for i, cl in enumerate(report.clusters):
            cl.id = i

    # ------------------------------------------------------------------
    # Step 5: Cross-cluster edges
    # ------------------------------------------------------------------

    def _compute_cross_cluster_edges(self, report: TopologyReport) -> None:
        """Compute edges that cross cluster boundaries."""
        func_to_ci = {}
        for i, cl in enumerate(report.clusters):
            for fn in cl.functions:
                func_to_ci[fn] = i

        for edge in self.call_edges:
            ci_caller = func_to_ci.get(edge.caller)
            ci_callee = func_to_ci.get(edge.callee)
            if ci_caller is not None and ci_callee is not None:
                if ci_caller != ci_callee:
                    report.cross_cluster_edges.append(edge)

    # ------------------------------------------------------------------
    # Phase 2: Build plan generation
    # ------------------------------------------------------------------

    def generate_build_plan(self, report: TopologyReport,
                            source_dir: str = ".",
                            host_name: str = "app",
                            mode: BuildMode = BuildMode.DEV) -> BuildPlan:
        """Generate a concrete build plan from the topology report.

        Args:
            report: A completed TopologyReport from analyze()
            source_dir: Directory containing the .c source files
            host_name: Name for the host executable
            mode: Build mode — dev (hot-swap), release (static LTO),
                  or service (selective hot-swap)
        """
        import os

        plan = BuildPlan(host_exe=host_name, mode=mode)

        # -----------------------------------------------------------
        # RELEASE: everything goes into one static binary with LTO
        # -----------------------------------------------------------
        if mode == BuildMode.RELEASE:
            all_modules = set()
            for cl in report.clusters:
                all_modules |= cl.modules

            # Single "cluster" — the whole program
            lib = SharedLibTarget(
                name=host_name,
                cluster_id=0,
                modules=sorted(all_modules),
                reloadability=Reloadability.PURE,  # irrelevant in release
            )
            for mod in all_modules:
                lib.c_files.append(os.path.join(source_dir, f"{mod}.c"))
            plan.shared_libs.append(lib)

            # Everything is statically linked — no .so, no dispatch table
            plan.pinned_cluster = 0
            plan.host_c_files = list(lib.c_files)
            plan.lto = True
            return plan

        # -----------------------------------------------------------
        # DEV and SERVICE: cluster into .so targets
        # -----------------------------------------------------------

        # Build function → cluster index mapping
        func_to_ci = {}
        for i, cl in enumerate(report.clusters):
            for fn in cl.functions:
                func_to_ci[fn] = i

        # Identify pinned clusters
        for i, cl in enumerate(report.clusters):
            is_pinned = cl.reloadability in (Reloadability.RESOURCE_OWNER,
                                              Reloadability.ABI_ANCHOR)
            # In SERVICE mode, only pin resource-owner and abi-anchor
            # In DEV mode, also pin resource-owner (can't hot-swap handles)
            if is_pinned:
                # Pick the largest pinned cluster as the primary
                if plan.pinned_cluster < 0 or \
                   len(cl.functions) > len(report.clusters[plan.pinned_cluster].functions):
                    plan.pinned_cluster = i

        # SERVICE mode: pure and process-local are swappable,
        # resource-owner and abi-anchor are pinned
        # DEV mode: everything except resource-owner is swappable

        # Create SharedLibTarget per cluster
        for i, cl in enumerate(report.clusters):
            if len(cl.modules) == 1:
                lib_name = next(iter(cl.modules))
            else:
                lib_name = f"cluster_{i}"

            lib = SharedLibTarget(
                name=lib_name,
                cluster_id=i,
                modules=sorted(cl.modules),
                reloadability=cl.reloadability,
            )
            for mod in cl.modules:
                lib.c_files.append(os.path.join(source_dir, f"{mod}.c"))
            plan.shared_libs.append(lib)

        # Identify cross-cluster calls for dispatch table
        seen_dispatch = set()
        for edge in report.cross_cluster_edges:
            ci_caller = func_to_ci.get(edge.caller)
            ci_callee = func_to_ci.get(edge.callee)
            if ci_caller is None or ci_callee is None:
                continue

            if edge.callee not in seen_dispatch:
                seen_dispatch.add(edge.callee)
                entry = DispatchEntry(
                    name=edge.callee,
                    ret_type="void",
                    param_types=[],
                    source_cluster=ci_callee,
                    callers=[ci_caller],
                )
                plan.dispatch_table.append(entry)
            else:
                for entry in plan.dispatch_table:
                    if entry.name == edge.callee:
                        if ci_caller not in entry.callers:
                            entry.callers.append(ci_caller)
                        break

            caller_lib = plan.shared_libs[ci_caller]
            callee_lib = plan.shared_libs[ci_callee]
            pair = (edge.caller, edge.callee)
            if pair not in caller_lib.outgoing_calls:
                caller_lib.outgoing_calls.append(pair)
            if edge.callee not in callee_lib.incoming_calls:
                callee_lib.incoming_calls.append(edge.callee)

        # Host .c files
        if plan.pinned_cluster >= 0:
            pinned_lib = plan.shared_libs[plan.pinned_cluster]
            plan.host_c_files = list(pinned_lib.c_files)

        # SERVICE mode: generate abi-anchor version hashes
        if mode == BuildMode.SERVICE:
            self._generate_abi_hashes(report, plan)

        return plan

    def _generate_abi_hashes(self, report: TopologyReport,
                              plan: BuildPlan) -> None:
        """Generate layout hashes for abi-anchor clusters.

        Before reloading an abi-anchor module, the reload manager
        compares the new .so's hash against the running version.
        Mismatch → reject the reload (ABI break).

        The hash is computed from:
        - Exported function names (sorted)
        - Struct layouts exported in headers
        """
        for lib in plan.shared_libs:
            if lib.reloadability != Reloadability.ABI_ANCHOR:
                continue

            # Collect all exported function names from this cluster's modules
            export_names = []
            for mod_name in lib.modules:
                if mod_name in self.modules:
                    mod = self.modules[mod_name]
                    export_names.extend(sorted(mod.exports))

            # Simple hash: FNV-1a over sorted export names
            h = 0x811c9dc5  # FNV offset basis (32-bit)
            for name in sorted(export_names):
                for ch in name.encode("utf-8"):
                    h ^= ch
                    h = (h * 0x01000193) & 0xFFFFFFFF

            lib.abi_hash = h
