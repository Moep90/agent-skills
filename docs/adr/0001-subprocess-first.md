# 1. Subprocess-first invocation of Kapitan

- Status: accepted
- Date: 2026-07-02

## Context

The MCP server needs to run Kapitan operations (inventory resolution, compile, lint).
Kapitan is a Python package, so importing its API in-process is possible. But Kapitan's
internal API is not a stable public contract: it changes between minor versions, calls
`sys.exit()` on some error paths, and keeps global state. The `kapitan` CLI, by contrast,
is the interface Kapitan documents and supports.

## Decision

Invoke Kapitan as a subprocess (the `kapitan` CLI) for every operation. Do not import
Kapitan's Python API in the server process. All subprocess spawning goes through a single
module, `runner.py`, which enforces `shell=False`, an argv list, an explicit `cwd`, a
timeout, and a scrubbed environment.

## Consequences

- The server is decoupled from Kapitan's internal API churn; it works against any Kapitan
  version whose CLI honours the flags we pass.
- Kapitan's `sys.exit()` and global state cannot corrupt the server process.
- We pay subprocess startup cost per call, and must parse CLI output instead of getting
  Python objects. For large inventories this is acceptable given the `parameter_path`
  filtering and truncation the tools already apply.
- The `./kapitan` docker-wrapper pattern (a shell script named `kapitan` on PATH) works
  transparently, because we invoke whatever `kapitan` resolves to in the project.
