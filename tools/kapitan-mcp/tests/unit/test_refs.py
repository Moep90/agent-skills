"""Unit tests for kapitan_refs_list.

The one hard rule: this tool reports ref metadata only. It must never return a value.
"""

from __future__ import annotations

from pathlib import Path

from kapitan_mcp.tools.refs import refs_list


def test_refs_list__finds_ref_tokens_with_backend(mini_inventory: Path) -> None:
    result = refs_list(mini_inventory)

    backends = {r.backend for r in result.refs}
    assert backends == {"gpg"}
    tokens = {r.token for r in result.refs}
    assert "?{gpg:targets/prod/tls_key}" in tokens


def test_refs_list__reports_existence_of_ref_file(mini_inventory: Path) -> None:
    result = refs_list(mini_inventory)

    by_path = {r.path: r.exists for r in result.refs}
    assert by_path["targets/prod/tls_key"] is True
    # interpolated path has no concrete ref file
    assert by_path["targets/${target_name}/mysql_password"] is False


def test_refs_list__never_returns_a_value(mini_inventory: Path) -> None:
    result = refs_list(mini_inventory)

    dumped = result.model_dump()
    assert "value" not in str(dumped)
    for ref in result.refs:
        assert not hasattr(ref, "value")
