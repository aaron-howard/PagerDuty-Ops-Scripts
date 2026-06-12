"""List and export PagerDuty incidents (read-only) for pipelines and ticketing."""

from __future__ import annotations

import sys

from ..api import paginate
from ..cli import init, standard_parser
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("list_incidents")

VALID_STATUSES = frozenset({"triggered", "acknowledged", "resolved"})

FIELDNAMES = [
    "id", "incident_number", "title", "status", "urgency",
    "created_at", "html_url", "service_id", "service_summary", "assignees",
]


def parse_multi(values) -> list[str]:
    """Flatten repeated flags + comma-separated tokens into a unique ordered list."""
    out, seen = [], set()
    for raw in values or []:
        for part in raw.split(","):
            s = part.strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out


def normalize_statuses(status_args) -> list[str]:
    out = []
    for s in parse_multi(status_args):
        low = s.lower()
        if low not in VALID_STATUSES:
            print(
                f"Error: invalid status {s!r}. Use: {', '.join(sorted(VALID_STATUSES))}.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        out.append(low)
    return out


def build_query_params(args) -> dict:
    params = {}
    if args.since:
        params["since"] = args.since
    if args.until:
        params["until"] = args.until
    statuses = normalize_statuses(args.statuses)
    if statuses:
        params["statuses[]"] = statuses
    for flag, key in (("service_ids", "service_ids[]"), ("team_ids", "team_ids[]"),
                      ("user_ids", "user_ids[]")):
        vals = parse_multi(getattr(args, flag))
        if vals:
            params[key] = vals
    return params


def _assignees_str(inc) -> str:
    parts = []
    for a in inc.get("assignments") or []:
        asg = a.get("assignee") or {}
        summ = (asg.get("summary") or "").strip()
        iid = asg.get("id") or ""
        if summ or iid:
            parts.append(f"{summ} ({iid})".strip())
    return " | ".join(parts)


def incident_row(inc: dict) -> dict:
    svc = inc.get("service") or {}
    n = inc.get("incident_number", inc.get("number"))
    return {
        "id": inc.get("id") or "",
        "incident_number": str(n) if n is not None else "",
        "title": inc.get("title") or "",
        "status": inc.get("status") or "",
        "urgency": inc.get("urgency") or "",
        "created_at": inc.get("created_at") or "",
        "html_url": inc.get("html_url") or "",
        "service_id": svc.get("id") or "",
        "service_summary": svc.get("summary") or "",
        "assignees": _assignees_str(inc),
    }


def build_parser():
    p = standard_parser(
        "Export PagerDuty incidents to table, CSV, or JSON. Prefer --since/--until "
        "for bounded, reproducible exports.",
        formats=("table", "csv", "json"),
    )
    p.add_argument("--since", metavar="ISO8601", help="Lower bound (e.g. 2026-01-01T00:00:00Z).")
    p.add_argument("--until", metavar="ISO8601", help="Upper bound.")
    p.add_argument("--status", dest="statuses", action="append", default=[], metavar="STATUS",
                   help="triggered/acknowledged/resolved; repeat or comma-separate.")
    p.add_argument("--service-id", dest="service_ids", action="append", default=[], metavar="ID")
    p.add_argument("--team-id", dest="team_ids", action="append", default=[], metavar="ID")
    p.add_argument("--user-id", dest="user_ids", action="append", default=[], metavar="ID",
                   help="Assigned user; the API omits resolved incidents for this filter.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    params = build_query_params(args)
    if not args.since and not args.until:
        log.warning("No --since/--until bound; export may be large and is capped at "
                    "10,000 records by the API.")
    log.info("Fetching incidents...")
    incidents = list(paginate("incidents", token, params=params))
    log.info("Found %d incidents.", len(incidents))
    rows = [incident_row(i) for i in incidents]
    write_payload(render_rows(rows, FIELDNAMES, args.format), args.output)
    return 0
