"""Unit tests for translating raw kapitan CLI errors into actionable codes."""

from __future__ import annotations

import pytest

from kapitan_mcp.errors import KapitanCliError, classify_kapitan_error, enrich


@pytest.mark.parametrize(
    ("stderr", "expected_code"),
    [
        (
            "Inventory reclass error: Class does.not.exist not found under yaml_fs://",
            "CLASS_NOT_FOUND",
        ),
        ("Cannot resolve ${nonexistent:key}, at broken, in yaml_fs://...", "INTERPOLATION_ERROR"),
        ("helm binary not found in PATH", "HELM_BINARY_MISSING"),
        ("RUNTIME ERROR: jsonnet: import error: file not found", "JSONNET_IMPORT_ERROR"),
        ("something totally unexpected happened", "KAPITAN_CLI_ERROR"),
    ],
)
def test_classify__maps_known_stderr_to_code(stderr: str, expected_code: str) -> None:
    code, remediation = classify_kapitan_error(stderr)

    assert code == expected_code
    assert remediation  # every classification carries a hint


def test_enrich__upgrades_error_code_and_remediation_in_place() -> None:
    err = KapitanCliError(
        "compile failed", exit_code=1, stderr="Class foo.bar not found under yaml_fs://"
    )

    enrich(err)

    assert err.code == "CLASS_NOT_FOUND"
    assert err.remediation


_CROSS_TARGET_STDERR = (
    "example: could not render due to error Class t not found\n"
    "gitlab-runner-test: could not render due to error dictionary changed size during iteration\n"
)


def test_enrich__other_target_failed__flags_the_real_culprit() -> None:
    err = KapitanCliError("inventory failed", exit_code=1, stderr=_CROSS_TARGET_STDERR)

    enrich(err, target="airgap-bundle")

    assert err.code == "OTHER_TARGET_FAILED"
    assert "example" in err.remediation
    assert "gitlab-runner-test" in err.remediation


def test_enrich__requested_target_is_the_broken_one__classifies_normally() -> None:
    err = KapitanCliError(
        "inventory failed",
        exit_code=1,
        stderr="example: could not render due to error Class t not found under yaml_fs://",
    )

    enrich(err, target="example")

    assert err.code == "CLASS_NOT_FOUND"
