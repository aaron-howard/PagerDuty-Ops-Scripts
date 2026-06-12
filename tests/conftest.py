"""Shared fixtures. Run from the repo root: python -m pytest"""

import logging

import pytest

from pagerduty_ops.api import reset_session


@pytest.fixture(autouse=True)
def _fresh_session():
    """Each test gets a fresh requests.Session (responses patches per-test)."""
    reset_session()
    yield
    reset_session()


@pytest.fixture(autouse=True)
def _quiet_logs():
    """Keep pd_ops logging configured but quiet during tests."""
    logger = logging.getLogger("pd_ops")
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.DEBUG)
    yield


@pytest.fixture
def token():
    return "test-token-not-real"
