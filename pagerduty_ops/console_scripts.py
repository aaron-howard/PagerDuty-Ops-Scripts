"""Setuptools `console_scripts` targets — each wraps a command `main` with `cli.run()`.

Installed CLIs therefore share the same PDApiError → exit 1/3 mapping and stderr
logging as the legacy `pd_*.py` shims.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib import import_module

from pagerduty_ops.cli import run as _run


def _entry(module: str, attr: str = "main") -> None:
    main_fn: Callable[..., int] = getattr(import_module(f"pagerduty_ops.commands.{module}"), attr)
    _run(main_fn)


def pd_list_users() -> None:
    _entry("list_users")


def pd_list_teams() -> None:
    _entry("list_teams")


def pd_list_schedules() -> None:
    _entry("list_schedules")


def pd_list_incidents() -> None:
    _entry("list_incidents")


def pd_list_status_pages() -> None:
    _entry("list_status_pages")


def pd_v3_schedules() -> None:
    _entry("v3_schedules")


def pd_export_ids() -> None:
    _entry("export_ids")


def pd_audit_export() -> None:
    _entry("audit_export")


def pd_export_log_entries() -> None:
    _entry("export_log_entries")


def pd_export_change_events() -> None:
    _entry("export_change_events")


def pd_scim_user_audit() -> None:
    _entry("scim_user_audit")


def pd_standards_report() -> None:
    _entry("standards_report")


def pd_patch_role() -> None:
    _entry("patch_role")


def pd_rename_resources() -> None:
    _entry("rename_resources")


def pd_team_members() -> None:
    _entry("team_members")


def pd_update_team_roles() -> None:
    _entry("update_team_roles")


def pd_remove_team_members() -> None:
    _entry("remove_team_members")


def pd_service_urgency() -> None:
    _entry("service_urgency")


def pd_bulk_maintenance_window() -> None:
    _entry("bulk_maintenance_window")


def pd_apply_tags() -> None:
    _entry("apply_tags")


def pd_bulk_extensions() -> None:
    _entry("bulk_extensions")


def pd_alert_grouping() -> None:
    _entry("alert_grouping")


def pd_eo_export() -> None:
    _entry("event_orchestration", "export_main")


def pd_eo_apply() -> None:
    _entry("event_orchestration", "apply_main")
