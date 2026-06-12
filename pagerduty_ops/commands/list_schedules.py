"""List PagerDuty v2 schedules (GET /schedules). Read-only.

For v3 'flexible schedules' (Early Access), use the v3-schedules command.
"""

from __future__ import annotations

from ..api import fetch_all
from ..cli import init, standard_parser
from ..output import render_rows, write_payload

FIELDNAMES = ["id", "name", "time_zone", "html_url"]


def build_parser():
    p = standard_parser(
        "List PagerDuty schedules (API v2 /schedules).", formats=("table", "csv", "json")
    )
    p.add_argument("--name-filter", help="Substring match (case-insensitive) on schedule name.")
    return p


def schedule_row(s: dict) -> dict:
    return {
        "id": s.get("id", ""),
        "name": s.get("name") or s.get("summary", ""),
        "time_zone": s.get("time_zone", ""),
        "html_url": s.get("html_url", ""),
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    params = {"query": args.name_filter} if args.name_filter else None
    schedules = fetch_all(
        "schedules", token, params=params, name_filter=args.name_filter, label="schedules"
    )
    rows = [schedule_row(s) for s in schedules]
    # json keeps full API objects (raw=) for fidelity, matching prior behavior
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=schedules), args.output)
    return 0
