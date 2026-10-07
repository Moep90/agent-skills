"""kapitan-mcp-server: an MCP server for inspecting and compiling Kapitan projects."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("kapitan-mcp-server")
except PackageNotFoundError:  # pragma: no cover - only when not installed as a package
    __version__ = "0.0.0"
