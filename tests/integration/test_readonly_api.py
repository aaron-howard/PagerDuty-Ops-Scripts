"""Integration tests against the real PagerDuty API. Read-only, opt-in.

Skipped unless PD_TEST_TOKEN is set (use a READ-ONLY token from a sandbox
account; never a production full-access token):

    PD_TEST_TOKEN=... python -m pytest tests/integration -v
"""

import os

import pytest

from pagerduty_ops.api import paginate, request

TOKEN = os.environ.get("PD_TEST_TOKEN")

pytestmark = pytest.mark.skipif(
    not TOKEN, reason="PD_TEST_TOKEN not set (read-only sandbox token required)"
)


def test_abilities_endpoint_responds():
    data = request("abilities", TOKEN)
    assert isinstance(data.get("abilities"), list)


def test_users_pagination_first_page():
    users = []
    for user in paginate("users", TOKEN, page_size=5):
        users.append(user)
        if len(users) >= 5:
            break
    assert all("id" in u for u in users)


def test_auth_error_raises_typed_error():
    from pagerduty_ops.api import PDApiError

    with pytest.raises(PDApiError) as exc:
        request("users", "definitely-not-a-valid-token")
    assert exc.value.is_auth_error
