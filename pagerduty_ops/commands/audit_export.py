"""Export PagerDuty audit records (/audit/records, cursor pagination) to CSV/JSON.

Designed for compliance reporting and change-history audits.
"""

from __future__ import annotations

from ..api import paginate_cursor
from ..cli import init, standard_parser
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("audit_export")

FIELDNAMES = [
    "id", "execution_time", "action", "actor_id", "actor_type", "actor_summary",
    "root_resource_id", "root_resource_type", "root_resource_summary", "method_type",
]


def build_parser():
    p = standard_parser(
        "Export PagerDuty audit records to CSV or JSON.", formats=("csv", "json")
    )
    p.set_defaults(format="csv")
    p.add_argument("--since", help="ISO 8601 lower bound (e.g. 2026-04-01T00:00:00Z).")
    p.add_argument("--until", help="ISO 8601 upper bound.")
    p.add_argument("--actor-id", action="append", help="Filter by actor ID (repeatable).")
    p.add_argument("--actor-type", choices=["user", "team", "system"])
    p.add_argument("--action", action="append",
                   help="Filter by action prefix, e.g. create/update/delete (repeatable).")
    p.add_argument("--root-resource-type",
                   help="e.g. services, schedules, escalation_policies.")
    return p


def build_params(args) -> dict:
    params = {}
    for key in ("since", "until", "actor_id", "actor_type", "action", "root_resource_type"):
        value = getattr(args, key)
        if value:
            params[key] = value
    return params


def flatten(record: dict) -> dict:
    actor = (record.get("actors") or [{}])[0]
    root = record.get("root_resource") or {}
    method = record.get("method") or {}
    return {
        "id": record.get("id", ""),
        "execution_time": record.get("execution_time", ""),
        "action": record.get("action", ""),
        "actor_id": actor.get("id", ""),
        "actor_type": actor.get("type", ""),
        "actor_summary": actor.get("summary", ""),
        "root_resource_id": root.get("id", ""),
        "root_resource_type": root.get("type", ""),
        "root_resource_summary": root.get("summary", ""),
        "method_type": method.get("type", ""),
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    log.info("Fetching audit records...")
    records = list(paginate_cursor("audit/records", token, items_key="records",
                                   params=build_params(args)))
    log.info("Got %d audit records.", len(records))
    rows = [flatten(r) for r in records]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=records), args.output)
    return 0
