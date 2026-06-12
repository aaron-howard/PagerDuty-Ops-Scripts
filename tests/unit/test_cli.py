"""Tests for pagerduty_ops.cli (confirm, run)."""

import sys
from types import SimpleNamespace

import pytest

from pagerduty_ops.api import PDApiError
from pagerduty_ops.cli import EXIT_AUTH, EXIT_FAILURES, EXIT_USAGE, confirm, run


def test_confirm_non_interactive_exits_2(monkeypatch):
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: False))
    with pytest.raises(SystemExit) as exc:
        confirm("Proceed?", assume_yes=False, dry_run=False)
    assert exc.value.code == EXIT_USAGE


def test_confirm_non_interactive_dry_run_ok(monkeypatch):
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert confirm("Proceed?", assume_yes=False, dry_run=True) is True


def test_confirm_non_interactive_assume_yes_ok(monkeypatch):
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert confirm("Proceed?", assume_yes=True, dry_run=False) is True


def test_run_maps_auth_pd_api_error_to_exit_3():
    def boom(argv=None):
        raise PDApiError("unauthorized", status_code=401)

    with pytest.raises(SystemExit) as exc:
        run(boom)
    assert exc.value.code == EXIT_AUTH


def test_run_maps_other_pd_api_error_to_exit_1():
    def boom(argv=None):
        raise PDApiError("server error", status_code=500)

    with pytest.raises(SystemExit) as exc:
        run(boom)
    assert exc.value.code == EXIT_FAILURES
