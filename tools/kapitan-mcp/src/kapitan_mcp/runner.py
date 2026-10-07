"""Safe subprocess wrapper: the only place this server spawns processes.

Rules enforced here:
- ``shell=False`` with an argv list, never string interpolation (injection surface).
- Explicit ``cwd`` (the sandboxed project root).
- A timeout on every call.
- A scrubbed environment: an allowlist only, so kapitan ref backends cannot pick
  up ``AWS_*`` / ``GOOGLE_*`` / ``VAULT_*`` credentials unless the human opted in.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import structlog

from kapitan_mcp.errors import KapitanCliError

# Audit trail: every subprocess is logged (to stderr, never stdout) before it runs, so an
# operator can see exactly which CLI invocations the agent drove. Only argv and cwd are
# recorded, never the environment, so scrubbed credentials cannot leak into the log.
log = structlog.get_logger()

# Environment variables always passed through to the child.
_ENV_ALLOWLIST = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TERM"})

DEFAULT_TIMEOUT_S = 120.0


def _as_text(value: str | bytes | None) -> str:
    """Coerce a possibly-bytes stream (as TimeoutExpired may carry) to text."""
    if value is None:
        return ""
    return value if isinstance(value, str) else value.decode(errors="replace")


@dataclass(frozen=True)
class CommandResult:
    """Captured output of a completed subprocess."""

    exit_code: int
    stdout: str
    stderr: str


def scrub_env(
    source: Mapping[str, str],
    *,
    forward_prefixes: tuple[str, ...] = (),
) -> dict[str, str]:
    """Return a minimal environment: the allowlist plus any ``forward_prefixes`` matches.

    Everything else (notably cloud credentials) is dropped. ``forward_prefixes`` is the
    escape hatch a human enables with ``--forward-env`` when secrets genuinely need
    revealing during a compile.
    """
    scrubbed: dict[str, str] = {}
    for key, value in source.items():
        if key in _ENV_ALLOWLIST or key.startswith(forward_prefixes):
            scrubbed[key] = value
    # Keep our subprocesses read-only: kapitan imports project python (e.g. omegaconf
    # resolvers.py), which otherwise writes .pyc files into the user's inventory tree.
    scrubbed["PYTHONDONTWRITEBYTECODE"] = "1"
    return scrubbed


def run(
    argv: list[str],
    *,
    cwd: Path,
    timeout: float = DEFAULT_TIMEOUT_S,
    forward_prefixes: tuple[str, ...] = (),
) -> CommandResult:
    """Run ``argv`` in ``cwd`` with a scrubbed env and a timeout.

    Raises :class:`KapitanCliError` on non-zero exit (carrying both streams) or timeout.
    """
    log.info("cli_exec", argv=argv, cwd=str(cwd))
    env = scrub_env(os.environ, forward_prefixes=forward_prefixes)
    try:
        completed = subprocess.run(  # noqa: S603 - argv list, shell=False, scrubbed env
            argv,
            cwd=cwd,
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise KapitanCliError(
            f"Command timed out after {timeout}s: {argv[0]}",
            exit_code=-1,
            stdout=_as_text(exc.stdout),
            stderr=_as_text(exc.stderr),
            remediation=(
                "Increase the timeout, or try the faster reclass-rs backend for large inventories."
            ),
        ) from exc

    if completed.returncode != 0:
        raise KapitanCliError(
            f"Command failed ({completed.returncode}): {' '.join(argv)}",
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    return CommandResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
