"""FastMCP application: registers the read-only tools and serves them over stdio.

Design notes:
- The project root comes from ``--project-root`` or CWD auto-detect, never from the
  model, so tools can never be pointed at another project. Without a project the
  server still starts (clients register it globally); tools answer with the
  structured PROJECT_NOT_FOUND error and retry discovery on every call.
- Every tool catches :class:`KapitanMcpError` and returns the structured
  ``{error: {...}}`` contract instead of leaking a stack trace.
- Logging goes to stderr only; stdout belongs to the MCP protocol.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import structlog
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from kapitan_mcp.errors import KapitanMcpError, ProjectNotFoundError, error_response
from kapitan_mcp.project import find_project_root
from kapitan_mcp.tools import compile as compile_tools
from kapitan_mcp.tools import generators, inventory, lint, refs, search

structlog.configure(
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)
log = structlog.get_logger()


def _guard(fn: Any) -> Any:
    """Wrap a tool so typed errors become structured responses, not tracebacks."""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            result = fn(*args, **kwargs)
        except KapitanMcpError as exc:
            log.warning("tool_error", tool=fn.__name__, code=exc.code)
            return error_response(exc)
        return result.model_dump()

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


# Tool hints so clients can tell inspection from mutation. All tools but kapitan_compile
# only read (compile_diff writes to a temp dir, never the project).
_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
_COMPILE = ToolAnnotations(
    readOnlyHint=False,  # writes into compiled/ when apply=True
    destructiveHint=True,  # overwrites existing compiled output
    idempotentHint=True,  # same inventory + templates produce the same output
    openWorldHint=True,  # fetch=true may reach the network
)


def create_server(project_root: Path | None) -> FastMCP:
    """Build a FastMCP app with every read-only tool bound to ``project_root``.

    With ``project_root=None`` the root is discovered lazily from the CWD on each tool
    call, so the server can start before (or without) a Kapitan project existing.
    """
    fixed_root = project_root.resolve() if project_root is not None else None
    mcp = FastMCP("kapitan-mcp-server")

    def _root() -> Path:
        if fixed_root is not None:
            return fixed_root
        return find_project_root(Path.cwd())

    def _tool(fn: Any) -> Any:
        """Like ``_guard``, but resolves the project root inside the error boundary."""

        def call(*args: Any, **kwargs: Any) -> Any:
            try:
                root = _root()
            except KapitanMcpError as exc:
                log.warning("tool_error", tool=fn.__name__, code=exc.code)
                return error_response(exc)
            return _guard(fn)(root, *args, **kwargs)

        return call

    @mcp.tool(name="kapitan_project_info", annotations=_READ_ONLY)
    def kapitan_project_info() -> Any:
        """Detect the kapitan version, inventory backend, and target count for the project.
        Call this first: the backend determines interpolation syntax for other tools."""
        return _tool(inventory.project_info)()

    @mcp.tool(name="kapitan_list_targets", annotations=_READ_ONLY)
    def kapitan_list_targets(pattern: str | None = None) -> Any:
        """List the project's targets (name + path). Optional glob ``pattern`` filters by name."""
        return _tool(inventory.list_targets)(pattern)

    @mcp.tool(name="kapitan_list_classes", annotations=_READ_ONLY)
    def kapitan_list_classes(pattern: str | None = None) -> Any:
        """List classes, mapping dotted names to file paths. Optional glob ``pattern``."""
        return _tool(inventory.list_classes)(pattern)

    @mcp.tool(name="kapitan_inventory_target", annotations=_READ_ONLY)
    def kapitan_inventory_target(target: str, parameter_path: str | None = None) -> Any:
        """Return the fully resolved (merged + interpolated) inventory for one target.
        Prefer this over mentally merging YAML. Pass a dotted ``parameter_path`` (e.g.
        'mysql.image') to fetch just a subtree and keep the response small."""
        return _tool(inventory.inventory_target)(target, parameter_path=parameter_path)

    @mcp.tool(name="kapitan_class_hierarchy", annotations=_READ_ONLY)
    def kapitan_class_hierarchy(target: str) -> Any:
        """Show the ordered class include tree for a target, so you can see which class
        contributes or overrides a value (parameters merge in include order; target wins last)."""
        return _tool(inventory.class_hierarchy)(target)

    @mcp.tool(name="kapitan_search_inventory", annotations=_READ_ONLY)
    def kapitan_search_inventory(query: str, kind: str = "key", scope: str = "all") -> Any:
        """Find where a parameter is defined or overridden across raw inventory YAML.
        ``kind``: key|value|regex. ``scope``: classes|targets|all. Confirm the resolved
        winner with kapitan_inventory_target."""
        return _tool(search.search_inventory)(query, kind=kind, scope=scope)

    @mcp.tool(name="kapitan_refs_list", annotations=_READ_ONLY)
    def kapitan_refs_list() -> Any:
        """List secret refs in the inventory (backend, path, whether a ref file exists).
        Metadata only: this never reveals a ref value, and no reveal tool exists."""
        return _tool(refs.refs_list)()

    @mcp.tool(name="kapitan_compile", annotations=_COMPILE)
    def kapitan_compile(targets: list[str], fetch: bool = False, apply: bool = True) -> Any:
        """Compile the given targets. Writes into the project's compiled/ only when apply
        is true. Remote fetch is off unless you opt in with fetch=true."""
        return _tool(compile_tools.compile_targets)(targets, fetch=fetch, apply=apply)

    @mcp.tool(name="kapitan_compile_diff", annotations=_READ_ONLY)
    def kapitan_compile_diff(targets: list[str]) -> Any:
        """Compile the given targets into a temp dir and return a unified diff against the
        committed compiled/ output. Never writes into compiled/. Run this before finishing
        an inventory or template change to review what it produces."""
        return _tool(compile_tools.compile_diff)(targets)

    @mcp.tool(name="kapitan_generator_trace", annotations=_READ_ONLY)
    def kapitan_generator_trace(targets: list[str] | None = None) -> Any:
        """Flag components/generators blocks that no kadet compile entry consumes: the
        silent no-op where an inventory block emits nothing with no error. Reads the resolved
        inventory (all targets if none given). Run after editing a generator block, before
        kapitan_compile_diff. Catches unwired blocks, not mistyped keys inside a block."""
        return _tool(generators.generator_trace)(targets)

    @mcp.tool(name="kapitan_generator_schema", annotations=_READ_ONLY)
    def kapitan_generator_schema(key: str = "components", targets: list[str] | None = None) -> Any:
        """Report the keys actually used under a generator block (default 'components'),
        learned from the project's own working blocks. Returns each key with how many blocks
        use it and examples; keys used by exactly one block come back in rare_keys as likely
        typos. Use to confirm a field name before adding it, instead of guessing the schema."""
        return _tool(generators.generator_schema)(key, targets)

    @mcp.tool(name="kapitan_lint", annotations=_READ_ONLY)
    def kapitan_lint() -> Any:
        """Run kapitan's built-in lint (yamllint plus orphan-class checks) and return
        whether it passed, with the raw output."""
        return _tool(lint.lint)()

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(prog="kapitan-mcp-server")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help="Kapitan project root. Defaults to auto-detecting from the current directory.",
    )
    args = parser.parse_args()

    root: Path | None = args.project_root
    if root is None:
        try:
            root = find_project_root(Path.cwd())
        except ProjectNotFoundError:
            log.warning(
                "no_project_found",
                cwd=str(Path.cwd()),
                hint="serving anyway; tools return PROJECT_NOT_FOUND until a project exists",
            )
    log.info("starting", project_root=str(root.resolve()) if root else None)
    create_server(root).run(transport="stdio")


if __name__ == "__main__":
    main()
