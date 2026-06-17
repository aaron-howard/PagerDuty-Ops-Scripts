"""List all PagerDuty escalation policies (flat directory export)."""

from __future__ import annotations

from ..api import fetch_all
from ..cli import init, standard_parser
from ..output import render_rows, write_payload
from .list_incidents import parse_multi

FIELDNAMES = [
    "id",
    "name",
    "description",
    "num_loops",
    "team_ids",
    "team_names",
    "html_url",
]


def build_parser():
    p = standard_parser(
        "List PagerDuty escalation policies (id, name, teams).",
        formats=("table", "csv", "json"),
    )
    p.add_argument(
        "--filter",
        dest="text_filter",
        metavar="TEXT",
        help="Substring match on policy name (server-side query, case-insensitive).",
    )
    p.add_argument(
        "--team-id",
        dest="team_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Only policies linked to this team; repeat or comma-separate.",
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


def policy_row(policy: dict) -> dict:
    teams = policy.get("teams") or []
    num_loops = policy.get("num_loops")
    return {
        "id": policy.get("id") or "",
        "name": policy.get("name") or "",
        "description": policy.get("description") or "",
        "num_loops": "" if num_loops is None else str(num_loops),
        "team_ids": _join_team_field(teams, "id"),
        "team_names": _join_team_field(teams, "summary"),
        "html_url": policy.get("html_url") or "",
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    params = build_query_params(args)
    policies = fetch_all(
        "escalation_policies",
        token,
        params=params,
        name_filter=args.text_filter,
        label="escalation policies",
    )
    rows = [policy_row(p) for p in policies]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=policies), args.output)
    return 0
