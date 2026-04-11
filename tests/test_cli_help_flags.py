"""Smoke-check that selected CLIs advertise key flags in --help."""

import pytest

import pd_get_teams_user_role
import pd_patch_role
import pd_remove_team_members
import pd_update_team_roles


@pytest.mark.parametrize(
    ("module", "needle"),
    [
        (pd_update_team_roles, "dry-run"),
        (pd_remove_team_members, "dry-run"),
    ],
)
def test_help_lists_dry_run(module, needle: str, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        module.parse_arguments(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out.lower()
    assert needle in out


@pytest.mark.parametrize(
    "module",
    [
        pd_patch_role,
        pd_get_teams_user_role,
        pd_update_team_roles,
        pd_remove_team_members,
    ],
)
def test_help_lists_no_progress(module, capsys) -> None:
    with pytest.raises(SystemExit) as exc:
        module.parse_arguments(["--help"])
    assert exc.value.code == 0
    assert "no-progress" in capsys.readouterr().out.lower()
