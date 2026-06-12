"""List PagerDuty Schedules v3 (Early Access). Read-only inventory.

PagerDuty marks the v3 API as Early Access ("Do not use this endpoint in
production, as it may change"). Inventory/visibility only; use the v2
schedule commands for production operations until v3 is GA.
"""

from __future__ import annotations

import json

from ..api import paginate, request
from ..cli import init, standard_parser
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("v3_schedules")

V3_RESOURCE = "v3/schedules"
EARLY_ACCESS_HEADERS = {"X-EARLY-ACCESS": "flexible-schedules-early-access"}
FIELDNAMES = ["id", "name", "type", "self"]


def build_parser():
    p = standard_parser(
        "List PagerDuty Schedules v3 (Early Access). Read-only inventory.",
        formats=("table", "csv", "json"),
    )
    p.add_argument("--get", metavar="SCHEDULE_ID", help="Fetch one v3 schedule's full detail.")
    p.add_argument("--include-users", action="store_true",
                   help="With --get, include the users array.")
    return p


def schedule_row(s: dict) -> dict:
    return {
        "id": s.get("id", ""),
        "name": s.get("name") or s.get("summary", ""),
        "type": s.get("type", ""),
        "self": s.get("self", ""),
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)

    if args.get:
        params = {"include[]": ["users"]} if args.include_users else None
        result = request(f"{V3_RESOURCE}/{args.get}", token, params=params,
                         extra_headers=EARLY_ACCESS_HEADERS)
        write_payload(json.dumps(result, indent=2) + "\n", args.output)
        return 0

    log.info("Fetching v3 schedules...")
    schedules = list(paginate(V3_RESOURCE, token, extra_headers=EARLY_ACCESS_HEADERS))
    log.info("Found %d v3 schedules.", len(schedules))
    rows = [schedule_row(s) for s in schedules]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=schedules), args.output)
    return 0
