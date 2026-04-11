"""Tests for lazy configuration and safe package import."""

import os
import subprocess
import sys
from pathlib import Path

from pagerduty.config import Config, config, load_config


def test_import_package_without_pd_api_token():
    """Importing pagerduty must not require PD_API_TOKEN (subprocess, clean env)."""
    root = Path(__file__).resolve().parents[1]
    code = """
import pagerduty
assert pagerduty.__version__
from pagerduty import PagerDutyAPIClient
from pagerduty.errors import AuthError
try:
    PagerDutyAPIClient(api_token=None)
except AuthError:
    pass
else:
    raise SystemExit("expected AuthError")
"""
    # Drop PD_* so lazy config does not pick up a token from the parent shell.
    env = {k: v for k, v in os.environ.items() if not k.startswith("PD_")}
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_load_config_instance():
    """load_config() returns a usable Config (separate from the lazy module proxy)."""
    cfg = load_config()
    assert isinstance(cfg, Config)
    token = cfg.get("api_token")
    assert token is None or isinstance(token, str)


def test_lazy_module_config_get_set():
    """Lazy `config` proxy loads on first use and supports set/get."""
    prior = config.get("api_token")
    try:
        config.set("api_token", "test-token-hygiene")
        assert config.get("api_token") == "test-token-hygiene"
    finally:
        config.set("api_token", prior)


def test_load_config_returns_fresh_instance():
    """load_config() returns an isolated Config, not the lazy singleton."""
    a = load_config()
    b = load_config()
    assert a is not b
