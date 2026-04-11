"""
Live PagerDuty API checks (opt-in).

Set ``PAGERDUTY_INTEGRATION_TESTS=1`` (or ``true``) and ``PD_API_TOKEN`` to run.
CI does not provide a token; these tests are skipped by default.
"""

from __future__ import annotations

import os

import pytest

from pagerduty import PagerDutyAPIClient

_INTEGRATION_FLAG = os.environ.get("PAGERDUTY_INTEGRATION_TESTS", "").strip().lower()
_ENABLED = _INTEGRATION_FLAG in ("1", "true", "yes")
_TOKEN = os.environ.get("PD_API_TOKEN", "").strip()

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not _ENABLED or not _TOKEN,
    reason="Set PAGERDUTY_INTEGRATION_TESTS=1 and PD_API_TOKEN for live API tests",
)
def test_live_get_paginated_teams() -> None:
    client = PagerDutyAPIClient(api_token=_TOKEN)
    try:
        teams = client.get_paginated("teams", {"limit": 5})
        assert isinstance(teams, list)
        for item in teams:
            assert "id" in item
    finally:
        client.close()
