"""Typed errors surfaced to the agent as structured tool responses.

Each error carries a stable ``code`` and an actionable ``remediation`` string so the
model can recover instead of seeing a raw stack trace.
"""

from __future__ import annotations

import re


class KapitanMcpError(Exception):
    """Base class for all errors this server raises deliberately."""

    code: str = "UNKNOWN"
    remediation: str = ""

    def __init__(self, message: str, *, remediation: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if remediation is not None:
            self.remediation = remediation


class ProjectNotFoundError(KapitanMcpError):
    code = "PROJECT_NOT_FOUND"
    remediation = (
        "Run the client from inside a Kapitan repo (one containing .kapitan or "
        "inventory/), or start the server with --project-root pointing at one."
    )


class PathOutsideProjectError(KapitanMcpError):
    code = "PATH_OUTSIDE_PROJECT"
    remediation = (
        "Only paths inside the project root are allowed. Remove any '..' segments "
        "or absolute paths that escape the root."
    )


def error_response(exc: KapitanMcpError) -> dict[str, dict[str, str]]:
    """Serialize a typed error into the ``{error: {code, message, remediation}}`` contract."""
    return {
        "error": {
            "code": exc.code,
            "message": exc.message,
            "remediation": exc.remediation,
        }
    }


class InvalidInventoryError(KapitanMcpError):
    code = "INVALID_INVENTORY"
    remediation = "The YAML failed to parse. Fix the syntax in the reported file, then retry."


class UnknownTargetError(KapitanMcpError):
    code = "UNKNOWN_TARGET"
    remediation = "No target file by that name. Call kapitan_list_targets to see valid names."


class KapitanCliError(KapitanMcpError):
    """A subprocess invocation of the kapitan CLI exited non-zero."""

    code = "KAPITAN_CLI_ERROR"

    def __init__(
        self,
        message: str,
        *,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        remediation: str | None = None,
    ) -> None:
        super().__init__(message, remediation=remediation)
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


# Ordered (substring, code, remediation). First match wins, so put specific before generic.
_ERROR_TABLE: list[tuple[str, str, str]] = [
    (
        "not found under yaml_fs",
        "CLASS_NOT_FOUND",
        "A class in a classes: list does not exist. Check the dotted name against the "
        "files under inventory/classes, or remove the include.",
    ),
    (
        "Cannot resolve",
        "INTERPOLATION_ERROR",
        "An ${...} reference points at a key that is missing after the merge. Use "
        "kapitan_search_inventory to find where that key should be defined.",
    ),
    (
        "helm",
        "HELM_BINARY_MISSING",
        "The helm input type needs the helm binary on PATH. Install helm, or run the "
        "server where the real CLI is available.",
    ),
    (
        "jsonnet",
        "JSONNET_IMPORT_ERROR",
        "A jsonnet import could not be resolved. Check the import path and that the "
        "library exists under the project.",
    ),
]


def classify_kapitan_error(stderr: str) -> tuple[str, str]:
    """Map a raw kapitan stderr string to a specific error code and remediation hint."""
    for needle, code, remediation in _ERROR_TABLE:
        if needle.lower() in stderr.lower():
            return code, remediation
    return "KAPITAN_CLI_ERROR", "The kapitan CLI failed. Read the stderr for the cause."


# kapitan reports a per-target render failure as "<target>: could not render due to error ...".
_RENDER_FAILURE_RE = re.compile(r"^(\S+): could not render due to error", re.MULTILINE)


def failed_render_targets(stderr: str) -> set[str]:
    """Target names kapitan reported as failing to render, parsed from its stderr."""
    return set(_RENDER_FAILURE_RE.findall(stderr))


def enrich(err: KapitanCliError, *, target: str | None = None) -> KapitanCliError:
    """Upgrade a raw CLI error's code and remediation from its stderr, in place.

    When ``target`` is given and the failures come from *other* targets (the omegaconf
    backend renders the whole inventory, so one broken target fails the command for all),
    flag that instead of blaming the requested target.
    """
    culprits = failed_render_targets(err.stderr)
    if target is not None and culprits and target not in culprits:
        others = ", ".join(sorted(culprits))
        err.code = "OTHER_TARGET_FAILED"
        err.remediation = (
            f"Target {target!r} was requested, but the inventory backend renders every "
            f"target and these other target(s) failed: {others}. Fix those targets (or "
            f"remove them) so the whole inventory parses, then retry."
        )
        return err
    err.code, err.remediation = classify_kapitan_error(err.stderr)
    return err
