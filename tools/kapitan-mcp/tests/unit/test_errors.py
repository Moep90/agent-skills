"""Unit tests for structured error responses."""

from __future__ import annotations

from kapitan_mcp.errors import KapitanCliError, PathOutsideProjectError, error_response


def test_error_response__carries_code_message_remediation() -> None:
    exc = PathOutsideProjectError("bad path")

    payload = error_response(exc)

    assert payload["error"]["code"] == "PATH_OUTSIDE_PROJECT"
    assert payload["error"]["message"] == "bad path"
    assert payload["error"]["remediation"]  # non-empty default


def test_error_response__cli_error_includes_default_remediation_when_absent() -> None:
    exc = KapitanCliError("compile blew up", exit_code=1, stderr="ClassNotFound")

    payload = error_response(exc)

    assert payload["error"]["code"] == "KAPITAN_CLI_ERROR"
    assert "compile blew up" in payload["error"]["message"]
