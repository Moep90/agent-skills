"""Structural guards for the security invariants.

These are cheap structural checks, not behaviour tests. They fail loudly if a future
change ever wires up secret reveal or drops the env allowlist.

Path sandboxing (../ traversal, absolute escape, symlink escape) is already covered by
test_project.py::test_resolve_within__* and is not duplicated here. Fetch-off-by-default
is covered by test_compile.py::test_compile__fetch_*. AWS_/GOOGLE_ scrubbing and the
run() argv/cwd/timeout contract are covered by test_runner.py. This file adds the
remaining SECURITY.md claims those files don't already prove: the VAULT_ credential
case and the argv-not-shell injection claim.
"""

from __future__ import annotations

import sys
from pathlib import Path

import kapitan_mcp
from kapitan_mcp.runner import run, scrub_env

SRC = Path(kapitan_mcp.__file__).parent


def test_no_reveal_flag_anywhere_in_src() -> None:
    offenders = [
        py.relative_to(SRC).as_posix() for py in SRC.rglob("*.py") if "--reveal" in py.read_text()
    ]
    assert offenders == [], f"secret-reveal flag must never appear in src: {offenders}"


def test_no_refs_reveal_tool_is_registered() -> None:
    import asyncio

    from kapitan_mcp.server import create_server

    server = create_server(SRC)  # any dir; we only inspect tool names
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert not any("reveal" in n for n in names)


def test_scrub_env__drops_vault_token() -> None:
    # SECURITY.md names AWS_*, GOOGLE_*, VAULT_* together; test_runner.py already proves
    # AWS_ and GOOGLE_, this closes the VAULT_ case.
    result = scrub_env({"PATH": "/usr/bin", "VAULT_TOKEN": "shh"})

    assert "VAULT_TOKEN" not in result
    assert result["PATH"] == "/usr/bin"


def test_run__shell_metacharacters_in_argv_are_not_interpreted(tmp_path: Path) -> None:
    # SECURITY.md: "All tool string params are data: argv lists, never a shell." Prove it
    # behaviourally: a value containing shell metacharacters must reach the child process
    # as a single literal argv element, never split or expanded by a shell.
    payload = "a; rm -rf /tmp/should-not-run && echo pwned"

    result = run([sys.executable, "-c", "import sys; print(sys.argv[1])", payload], cwd=tmp_path)

    assert result.stdout.strip() == payload
