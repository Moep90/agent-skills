# kapitan-mcp-server

A local, read-first [MCP](https://modelcontextprotocol.io) server that lets AI coding
agents inspect, compile, and diff [Kapitan](https://kapitan.dev) projects without
guessing at the inventory or leaking secrets.

Run it with:

```bash
uvx kapitan-mcp-server --project-root /path/to/your/kapitan/repo
```

It ships with the `kapitan-core` plugin; see the [repository root](../../README.md) for installation.
