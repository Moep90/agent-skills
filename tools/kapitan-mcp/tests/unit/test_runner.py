"""Unit tests for the subprocess runner.

These exercise the real subprocess path against the current Python interpreter
instead of mocking, so we verify actual argv/cwd/env/timeout behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from kapitan_mcp.errors import KapitanCliError
from kapitan_mcp.runner import CommandResult, run, scrub_env


def test_scrub_env__drops_cloud_credentials_by_default() -> None:
    source = {"PATH": "/usr/bin", "HOME": "/home/x", "AWS_SECRET_ACCESS_KEY": "shh"}

    result = scrub_env(source)

    assert result["PATH"] == "/usr/bin"
    assert result["HOME"] == "/home/x"
    assert "AWS_SECRET_ACCESS_KEY" not in result


def test_scrub_env__keeps_locale_vars() -> None:
    source = {"PATH": "/usr/bin", "LANG": "en_US.UTF-8", "LC_ALL": "C"}

    result = scrub_env(source)

    assert result["LANG"] == "en_US.UTF-8"
    assert result["LC_ALL"] == "C"


def test_scrub_env__sets_dont_write_bytecode() -> None:
    # kapitan imports project python (e.g. omegaconf resolvers.py); without this the
    # import litters inventory/__pycache__ .pyc files in the user's tree.
    result = scrub_env({"PATH": "/usr/bin"})

    assert result["PYTHONDONTWRITEBYTECODE"] == "1"


def test_scrub_env__forwards_only_explicitly_allowed_prefixes() -> None:
    source = {"PATH": "/usr/bin", "AWS_PROFILE": "dev", "GOOGLE_TOKEN": "g"}

    result = scrub_env(source, forward_prefixes=("AWS_",))

    assert result["AWS_PROFILE"] == "dev"
    assert "GOOGLE_TOKEN" not in result


def test_run__success__returns_stdout_and_zero_exit(tmp_path: Path) -> None:
    result = run([sys.executable, "-c", "print('hello')"], cwd=tmp_path)

    assert isinstance(result, CommandResult)
    assert result.exit_code == 0
    assert result.stdout.strip() == "hello"


def test_run__separates_stdout_and_stderr(tmp_path: Path) -> None:
    code = "import sys; print('out'); print('err', file=sys.stderr)"

    result = run([sys.executable, "-c", code], cwd=tmp_path)

    assert result.stdout.strip() == "out"
    assert result.stderr.strip() == "err"


def test_run__nonzero_exit__raises_typed_error_with_streams(tmp_path: Path) -> None:
    code = "import sys; print('partial'); print('boom', file=sys.stderr); sys.exit(3)"

    with pytest.raises(KapitanCliError) as excinfo:
        run([sys.executable, "-c", code], cwd=tmp_path)

    err = excinfo.value
    assert err.exit_code == 3
    assert "partial" in err.stdout
    assert "boom" in err.stderr


def test_run__scrubs_credentials_from_child_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "leak-me")
    code = "import os; print(os.environ.get('AWS_SECRET_ACCESS_KEY', 'ABSENT'))"

    result = run([sys.executable, "-c", code], cwd=tmp_path)

    assert result.stdout.strip() == "ABSENT"


def test_run__timeout__raises_typed_error(tmp_path: Path) -> None:
    with pytest.raises(KapitanCliError) as excinfo:
        run([sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp_path, timeout=0.2)

    assert "timed out" in str(excinfo.value).lower()


def test_run__emits_audit_record_with_argv_and_cwd(tmp_path: Path) -> None:
    argv = [sys.executable, "-c", "print('x')"]

    with capture_logs() as logs:
        run(argv, cwd=tmp_path)

    audit = [e for e in logs if e["event"] == "cli_exec"]
    assert len(audit) == 1
    assert audit[0]["argv"] == argv
    assert audit[0]["cwd"] == str(tmp_path)


def test_run__audit_record_never_carries_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "leak-me")

    with capture_logs() as logs:
        run([sys.executable, "-c", "print('x')"], cwd=tmp_path)

    blob = repr(logs)
    assert "leak-me" not in blob
    assert "AWS_SECRET_ACCESS_KEY" not in blob


def test_run__emits_audit_record_even_on_timeout(tmp_path: Path) -> None:
    with capture_logs() as logs, pytest.raises(KapitanCliError):
        run([sys.executable, "-c", "import time; time.sleep(5)"], cwd=tmp_path, timeout=0.2)

    assert any(e["event"] == "cli_exec" for e in logs)
