"""Smoke test: every CLI script must support --help and exit 0.

Catches what py_compile cannot: scripts that execute API calls or sys.exit
at import time (currently pd_get_teams_user_role.py and pd_update_team_roles.py
fail this — they run network calls at module level).
"""

import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = sorted(
    p for p in REPO_ROOT.glob("pd_*.py") if p.name != "pd_common.py"
) + [REPO_ROOT / "update_service_notifications.py"]

# Module-level-execution scripts: remove entries as they are fixed (A1).
KNOWN_BROKEN = {"pd_get_teams_user_role.py", "pd_update_team_roles.py"}


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_help_exits_zero(script):
    if script.name in KNOWN_BROKEN:
        pytest.xfail("executes at import time; see audit finding A1")
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=REPO_ROOT,
        env={"PATH": "", "PD_API_TOKEN": "smoke-test-not-a-real-token"},
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
