"""Command-level tests: parser smoke for every command, pure helpers, and
end-to-end runs of representative commands with mocked HTTP."""

import importlib

import pytest
import responses

from pagerduty_ops.api import PD_API_BASE

COMMAND_MODULES = [
    "alert_grouping", "apply_tags", "audit_export", "bulk_extensions",
    "bulk_maintenance_window", "event_orchestration", "export_change_events",
    "export_ids", "export_log_entries", "list_incidents", "list_schedules",
    "list_status_pages", "list_teams", "list_users", "patch_role",
    "remove_team_members", "rename_resources", "scim_user_audit",
    "service_urgency", "standards_report", "team_members",
    "update_team_roles", "v3_schedules",
]


# ---------- --help smoke for every command ----------

@pytest.mark.parametrize("module_name", COMMAND_MODULES)
def test_every_command_help_exits_zero(module_name, capsys):
    module = importlib.import_module(f"pagerduty_ops.commands.{module_name}")
    parsers = []
    if hasattr(module, "build_parser"):
        parsers.append(module.build_parser())
    for extra in ("build_export_parser", "build_apply_parser"):
        if hasattr(module, extra):
            parsers.append(getattr(module, extra)())
    assert parsers, f"{module_name} exposes no parser"
    for parser in parsers:
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--help"])
        assert exc.value.code == 0
        assert "usage:" in capsys.readouterr().out.lower()


# ---------- pure helpers ----------

def test_parse_multi_dedupes_and_splits():
    from pagerduty_ops.commands.list_incidents import parse_multi

    assert parse_multi(["a,b", "b", " c "]) == ["a", "b", "c"]
    assert parse_multi(None) == []


def test_normalize_statuses_rejects_invalid():
    from pagerduty_ops.commands.list_incidents import normalize_statuses

    assert normalize_statuses(["Triggered,RESOLVED"]) == ["triggered", "resolved"]
    with pytest.raises(SystemExit) as exc:
        normalize_statuses(["bogus"])
    assert exc.value.code == 2


def test_patch_role_validation():
    from pagerduty_ops.commands.patch_role import validate_roles

    validate_roles("user", "observer")  # ok
    with pytest.raises(SystemExit):
        validate_roles("user", "user")  # identical
    with pytest.raises(SystemExit):
        validate_roles("user", "superhero")  # invalid role


def test_endpoint_url_validation():
    from pagerduty_ops.commands.bulk_extensions import validate_endpoint_url

    validate_endpoint_url("https://example.com/hook")
    for bad in ("http://example.com/hook", "ftp://x", "example.com", ""):
        with pytest.raises(SystemExit):
            validate_endpoint_url(bad)


def test_scim_diff_buckets():
    from pagerduty_ops.commands.scim_user_audit import diff

    pd_users = [
        {"id": "U1", "email": "a@x.com", "displayName": "A", "active": True},
        {"id": "U2", "email": "b@x.com", "displayName": "B", "active": True},
    ]
    expected = {
        "b@x.com": {"email": "b@x.com", "displayName": "B2", "active": True},
        "c@x.com": {"email": "c@x.com", "displayName": "C", "active": True},
    }
    orphans, missing, drifts = diff(pd_users, expected)
    assert orphans == ["a@x.com"]
    assert missing == ["c@x.com"]
    assert len(drifts) == 1 and drifts[0][0] == "b@x.com" and "displayName" in drifts[0][2]


def test_export_ids_webhook_service_resolution():
    from pagerduty_ops.commands.export_ids import webhook_service_id

    assert webhook_service_id({"filter": {"type": "service_reference", "id": "S1"}}) == "S1"
    assert webhook_service_id({"service": {"id": "S2"}}) == "S2"
    assert webhook_service_id(
        {"delivery_method": {"connection": {"service": {"id": "S3"}}}}
    ) == "S3"
    assert webhook_service_id({}) is None


def test_slugify():
    from pagerduty_ops.commands.event_orchestration import slugify

    assert slugify("Prod / Payments!") == "prod-payments"
    assert slugify(None) == "unnamed"


# ---------- end-to-end with mocked HTTP ----------

@responses.activate
def test_list_users_end_to_end_csv(monkeypatch, capsys, token):
    monkeypatch.setenv("PD_API_TOKEN", token)
    responses.get(
        f"{PD_API_BASE}/users",
        json={"users": [
            {"id": "U1", "name": "Jane", "email": "jane@x.com", "role": "user",
             "job_title": "SRE"},
        ], "more": False},
    )
    from pagerduty_ops.commands.list_users import main

    assert main(["-f", "csv"]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "id,name,email,role,job_title"
    assert "U1,Jane,jane@x.com,user,SRE" in out


@responses.activate
def test_patch_role_dry_run_writes_nothing(monkeypatch, token):
    monkeypatch.setenv("PD_API_TOKEN", token)
    responses.get(
        f"{PD_API_BASE}/users",
        json={"users": [{"id": "U1", "name": "Jane", "role": "user"}], "more": False},
    )
    from pagerduty_ops.commands.patch_role import main

    assert main(["--from-role", "user", "--to-role", "observer", "--dry-run"]) == 0
    assert all(c.request.method == "GET" for c in responses.calls)


@responses.activate
def test_patch_role_partial_failure_exit_code(monkeypatch, token):
    monkeypatch.setenv("PD_API_TOKEN", token)
    responses.get(
        f"{PD_API_BASE}/users",
        json={"users": [
            {"id": "U1", "name": "Jane", "role": "user"},
            {"id": "U2", "name": "Bob", "role": "user"},
        ], "more": False},
    )
    responses.patch(f"{PD_API_BASE}/users/U1", json={"user": {"id": "U1"}})
    responses.patch(f"{PD_API_BASE}/users/U2", status=400,
                    json={"error": {"message": "bad"}})
    from pagerduty_ops.commands.patch_role import main

    assert main(["--from-role", "user", "--to-role", "observer", "-y"]) == 1


@responses.activate
def test_team_members_is_paginated_beyond_25(monkeypatch, capsys, token):
    """Regression for the audit's worst finding: teams >25 members were truncated."""
    monkeypatch.setenv("PD_API_TOKEN", token)
    monkeypatch.setenv("PD_TEAM_ID", "PTEAM")
    page1 = [{"user": {"id": f"U{i}", "summary": f"User {i}"}, "role": "responder"}
             for i in range(100)]
    page2 = [{"user": {"id": "U100", "summary": "User 100"}, "role": "manager"}]
    responses.get(f"{PD_API_BASE}/teams/PTEAM/members",
                  json={"members": page1, "more": True})
    responses.get(f"{PD_API_BASE}/teams/PTEAM/members",
                  json={"members": page2, "more": False})
    from pagerduty_ops.commands.team_members import main

    assert main(["-f", "csv"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 102  # header + 101 members
    assert "U100" in out


@responses.activate
def test_maintenance_window_idempotency_skips_existing(monkeypatch, tmp_path, token):
    monkeypatch.setenv("PD_API_TOKEN", token)
    csv_path = tmp_path / "windows.csv"
    csv_path.write_text(
        "service_id,start_time,end_time,description\n"
        "P1,2026-07-01T02:00:00Z,2026-07-01T04:00:00Z,patching\n",
        encoding="utf-8",
    )
    # identical window already exists (offset notation, same instant)
    responses.get(
        f"{PD_API_BASE}/maintenance_windows",
        json={"maintenance_windows": [{
            "start_time": "2026-07-01T02:00:00+00:00",
            "end_time": "2026-07-01T04:00:00+00:00",
            "services": [{"id": "P1"}],
        }], "more": False},
    )
    from pagerduty_ops.commands.bulk_maintenance_window import main

    assert main([str(csv_path), "--from-email", "ops@x.com", "-y"]) == 0
    assert all(c.request.method == "GET" for c in responses.calls)  # no POST
