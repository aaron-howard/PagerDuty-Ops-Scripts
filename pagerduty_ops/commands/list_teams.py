"""List all PagerDuty teams (flat directory export for pipelines and audits)."""

from __future__ import annotations

from ..api import fetch_all
from ..cli import init, standard_parser
from ..output import render_rows, write_payload

FIELDNAMES = ["id", "name", "description"]


def build_parser():
    p = standard_parser(
        "List PagerDuty teams (id, name, description).", formats=("table", "csv", "json")
    )
    p.add_argument(
        "--filter",
        dest="text_filter",
        metavar="TEXT",
        help="Substring match on team name or description (case-insensitive).",
    )
    return p


def team_row(t: dict) -> dict:
    return {f: (t.get(f) or "") for f in FIELDNAMES}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    params = {"query": args.text_filter} if args.text_filter else None
    teams = fetch_all("teams", token, params=params, label="teams")
    if args.text_filter:
        needle = args.text_filter.lower()
        teams = [
            t for t in teams
            if needle in (t.get("name") or "").lower()
            or needle in (t.get("description") or "").lower()
        ]
    rows = [team_row(t) for t in teams]
    write_payload(render_rows(rows, FIELDNAMES, args.format), args.output)
    return 0
