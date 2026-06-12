"""Every legacy script must support --help and exit 0 in a subprocess.

Catches import-time breakage (the old pd_get_teams_user_role.py and
pd_update_team_roles.py executed API calls at import) and verifies the
shim -> package wiring.
"""

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS = sorted(p for p in REPO_ROOT.glob("pd_*.py") if p.name != "pd_common.py")
SCRIPTS.append(REPO_ROOT / "update_service_notifications.py")


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_shim_help_exits_zero(script):
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True, text=True, timeout=60, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()


def test_pd_common_legacy_surface():
    """External callers of pd_common keep working (with a DeprecationWarning)."""
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import pd_common

    for name in ("make_api_request", "paginate", "paginate_cursor", "fetch_all",
                 "get_pd_api_token", "get_pd_team_id", "build_headers",
                 "add_token_arguments", "expand_query_params", "PD_API_BASE"):
        assert hasattr(pd_common, name), f"pd_common.{name} missing"


def test_pd_common_make_api_request_returns_none_on_error(token):
    """Legacy contract preserved: None on failure instead of an exception."""
    import warnings

    import responses as resp

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import pd_common

    @resp.activate
    def check():
        resp.get("https://api.pagerduty.com/users", status=500,
                 json={"error": {"message": "boom"}})
        assert pd_common.make_api_request("users", token) is None

    check()
