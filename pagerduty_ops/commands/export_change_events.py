"""Export PagerDuty change events to CSV/JSON for compliance / change correlation.

Account-wide, per-service, or per-incident (related change events).
"""

from __future__ import annotations

from ..api import paginate
from ..cli import init, standard_parser
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("export_change_events")

FIELDNAMES = ["id", "type", "summary", "timestamp", "source", "service_ids"]


def build_parser():
    p = standard_parser(
        "Export PagerDuty change events to CSV or JSON (read-only).", formats=("csv", "json")
    )
    p.set_defaults(format="csv")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--service-id", help="Change events for this service only.")
    group.add_argument("--incident-id", help="Change events related to this incident only.")
    p.add_argument("--since", help="ISO 8601 lower bound.")
    p.add_argument("--until", help="ISO 8601 upper bound.")
    p.add_argument("--team-id", action="append", dest="team_ids", metavar="ID",
                   help="Account-wide mode only (repeatable).")
    p.add_argument("--integration-id", action="append", dest="integration_ids", metavar="ID",
                   help="Account-wide mode only (repeatable).")
    return p


def build_params(args) -> dict:
    params = {}
    if args.since:
        params["since"] = args.since
    if args.until:
        params["until"] = args.until
    if args.service_id or args.incident_id:
        return params
    if args.team_ids:
        params["team_ids[]"] = args.team_ids
    if args.integration_ids:
        params["integration_ids[]"] = args.integration_ids
    return params


def flatten(ce: dict) -> dict:
    services = ce.get("services") or []
    return {
        "id": ce.get("id", ""),
        "type": ce.get("type", ""),
        "summary": ce.get("summary", ""),
        "timestamp": ce.get("timestamp") or ce.get("created_at", ""),
        "source": ce.get("source", ""),
        "service_ids": ",".join(s.get("id", "") for s in services if isinstance(s, dict)),
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    if args.incident_id:
        resource = f"incidents/{args.incident_id}/related_change_events"
        items_key = "change_events"
    elif args.service_id:
        resource, items_key = f"services/{args.service_id}/change_events", None
    else:
        resource, items_key = "change_events", None
    log.info("Fetching %s...", resource)
    events = list(paginate(resource, token, params=build_params(args) or None,
                           items_key=items_key))
    log.info("Got %d change events.", len(events))
    rows = [flatten(ce) for ce in events]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=events), args.output)
    return 0
