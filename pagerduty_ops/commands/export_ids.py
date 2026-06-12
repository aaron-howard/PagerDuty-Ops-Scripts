"""Export team IDs/names with associated schedules, escalation policies,
services, and webhook subscriptions (table/CSV/JSON)."""

from __future__ import annotations

from ..api import fetch_all
from ..cli import init, standard_parser
from ..output import render_rows, write_payload

FIELDNAMES = [
    "team_id", "team_name", "schedule_id", "schedule_name",
    "escalation_policy_id", "escalation_policy_name",
    "service_id", "service_name", "webhook_id", "webhook_name",
]


def build_parser():
    return standard_parser(
        "Export PagerDuty teams with associated schedules, escalation policies, "
        "services, and webhook subscriptions.",
        formats=("table", "csv", "json"),
    )


def map_by_team(items) -> dict:
    mapping: dict = {}
    for item in items:
        for team in item.get("teams", []):
            mapping.setdefault(team.get("id"), []).append(
                {"id": item.get("id"), "name": item.get("name")}
            )
    return mapping


def webhook_service_id(webhook: dict):
    """Service a webhook subscription points at, across known payload shapes."""
    flt = webhook.get("filter")
    if flt and flt.get("type") == "service_reference":
        return flt.get("id")
    svc = webhook.get("service")
    if svc and svc.get("id"):
        return svc["id"]
    conn = (webhook.get("delivery_method") or {}).get("connection") or {}
    return (conn.get("service") or {}).get("id")


def build_rows(teams, schedules, policies, services, webhooks) -> list[dict]:
    team_schedules = map_by_team(schedules)
    team_policies = map_by_team(policies)
    team_services = map_by_team(services)

    service_team_map = {s["id"]: s.get("teams", []) for s in services if s.get("id")}
    team_webhooks: dict = {}
    for webhook in webhooks:
        sid = webhook_service_id(webhook)
        for team in service_team_map.get(sid, []):
            team_webhooks.setdefault(team.get("id"), []).append(
                {"id": webhook.get("id", ""), "name": webhook.get("description", "No description")}
            )

    blank = [{"id": "", "name": ""}]
    rows = []
    for team in teams:
        tid, tname = team.get("id"), team.get("name")
        cols = {
            "schedule": team_schedules.get(tid, blank),
            "escalation_policy": team_policies.get(tid, blank),
            "service": team_services.get(tid, blank),
            "webhook": team_webhooks.get(tid, blank),
        }
        for i in range(max(len(v) for v in cols.values())):
            row = {"team_id": tid if i == 0 else "", "team_name": tname if i == 0 else ""}
            for kind, items in cols.items():
                item = items[i] if i < len(items) else {"id": "", "name": ""}
                row[f"{kind}_id"] = item["id"] or ""
                row[f"{kind}_name"] = item["name"] or ""
            rows.append(row)
    return rows


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    teams = fetch_all("teams", token)
    schedules = fetch_all("schedules", token)
    policies = fetch_all("escalation_policies", token)
    services = fetch_all("services", token)
    webhooks = fetch_all("webhook_subscriptions", token)
    rows = build_rows(teams, schedules, policies, services, webhooks)
    write_payload(render_rows(rows, FIELDNAMES, args.format), args.output)
    return 0
