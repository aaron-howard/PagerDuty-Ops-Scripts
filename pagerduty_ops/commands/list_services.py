"""List all PagerDuty services (flat directory export for pipelines and audits)."""

from __future__ import annotations

from ..api import fetch_all
from ..cli import init, standard_parser
from ..output import render_rows, write_payload
from .list_incidents import parse_multi

FIELDNAMES = [
    "id",
    "name",
    "status",
    "description",
    "escalation_policy_id",
    "escalation_policy_name",
    "team_ids",
    "team_names",
    "html_url",
]


def build_parser():
    p = standard_parser(
        "List PagerDuty services (id, name, status, escalation policy, teams).",
        formats=("table", "csv", "json"),
    )
    p.add_argument(
        "--filter",
        dest="text_filter",
        metavar="TEXT",
        help="Substring match on service name (server-side query, case-insensitive).",
    )
    p.add_argument(
        "--team-id",
        dest="team_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Only services linked to this team; repeat or comma-separate.",
    )
    return p


def build_query_params(args) -> dict:
    params = {"include[]": ["teams"]}
    if args.text_filter:
        params["query"] = args.text_filter
    team_ids = parse_multi(args.team_ids)
    if team_ids:
        params["team_ids[]"] = team_ids
    return params


def _join_team_field(teams, key: str) -> str:
    parts = []
    for team in teams or []:
        val = (team.get(key) or "").strip()
        if val:
            parts.append(val)
    return ", ".join(parts)


def service_row(service: dict) -> dict:
    policy = service.get("escalation_policy") or {}
    teams = service.get("teams") or []
    return {
        "id": service.get("id") or "",
        "name": service.get("name") or "",
        "status": service.get("status") or "",
        "description": service.get("description") or "",
        "escalation_policy_id": policy.get("id") or "",
        "escalation_policy_name": policy.get("summary") or "",
        "team_ids": _join_team_field(teams, "id"),
        "team_names": _join_team_field(teams, "summary"),
        "html_url": service.get("html_url") or "",
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    params = build_query_params(args)
    services = fetch_all(
        "services",
        token,
        params=params,
        name_filter=args.text_filter,
        label="services",
    )
    rows = [service_row(s) for s in services]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=services), args.output)
    return 0
