"""Tests for pagerduty.cli_common token resolution."""

import argparse
import os
import sys
from unittest.mock import patch

import pytest

from pagerduty.cli_common import progress_wait, resolve_api_token
from pagerduty.config import reset_default_config_for_testing


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    reset_default_config_for_testing()
    yield
    reset_default_config_for_testing()


def test_resolve_cli_token_warns_and_returns_value(capsys):
    with patch.dict(os.environ, {}, clear=True):
        tok = resolve_api_token("  secret  ", allow_prompt=False)
    assert tok == "secret"
    err = capsys.readouterr().err
    assert "shell history" in err.lower()


def test_resolve_prefers_env_over_config(tmp_path, monkeypatch):
    cfg = tmp_path / "pagerduty.yaml"
    cfg.write_text("api_token: from-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PD_API_TOKEN", raising=False)
    monkeypatch.setenv("PD_API_TOKEN", "from-env")
    reset_default_config_for_testing()
    tok = resolve_api_token(None, allow_prompt=False)
    assert tok == "from-env"


def test_resolve_config_file_when_no_env(tmp_path, monkeypatch):
    """Default config search includes ``pagerduty.yaml`` in the current directory."""
    cfg = tmp_path / "pagerduty.yaml"
    cfg.write_text("api_token: from-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PD_API_TOKEN", raising=False)
    reset_default_config_for_testing()
    tok = resolve_api_token(None, allow_prompt=False)
    assert tok == "from-file"


def test_progress_wait_skipped_when_no_progress():
    args = argparse.Namespace(no_progress=True)
    with progress_wait(args, "Working..."):
        pass


def test_progress_wait_non_tty_prints_label_once(capsys, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    args = argparse.Namespace(no_progress=False)
    with progress_wait(args, "Fetching..."):
        pass
    out = capsys.readouterr().out
    assert "Fetching" in out
