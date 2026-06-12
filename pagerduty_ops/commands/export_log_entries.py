"""Export PagerDuty log entries to CSV/JSON for compliance and forensics.

Account-wide (GET /log_entries) or per-incident (GET /incidents/{id}/log_entries).
Pass explicit --since/--until for reproducible exports.
"""

from __future__ import annotations

from ..api import paginate
from ..cli import init, standard_parser
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("export_log_entries")

FIELDNAMES = [
    "id", "created_at", "resource_type", "summary", "agent_id", "agent_summary",
    "service_id", "service_summary", "incident_id", "incident_number",
]


def build_parser():
    p = standard_parser(
        "Export PagerDuty log entries to CSV or JSON (read-only).", formats=("csv", "json")
    )
    p.set_defaults(format="csv")
    p.add_argument("--incident-id", help="Only log entries for this incident.")
    p.add_argument("--since", help="ISO 8601 lower bound.")
    p.add_argument("--until", help="ISO 8601 upper bound.")
    p.add_argument("--time-zone", help="IANA time zone for rendering (e.g. America/Chicago).")
    p.add_argument("--is-overview", action="store_true",
                   help="Only high-level incident changes (less verbose).")
    p.add_argument("--include", action="append", dest="includes", metavar="FRAGMENT",
                   help="include[] query fragment (repeatable), e.g. --include channels.")
    p.add_argument("--team-id", action="append", dest="team_ids", metavar="ID")
    p.add_argument("--service-id", action="append", dest="service_ids", metavar="ID")
    return p


def build_params(args) -> dict:
    params = {}
    if args.since:
        params["since"] = args.since
    if args.until:
        params["until"] = args.until
    if args.time_zone:
        params["time_zone"] = args.time_zone
    if args.is_overview:
        params["is_overview"] = True
    if args.includes:
        params["include[]"] = args.includes
    if args.team_ids:
        params["team_ids[]"] = args.team_ids
    if args.service_ids:
        params["service_ids[]"] = args.service_ids
    return params


def flatten(le: dict) -> dict:
    agent = le.get("agent") or {}
    service = le.get("service") or {}
    incident = le.get("incident") or {}
    return {
        "id": le.get("id", ""),
        "created_at": le.get("created_at", ""),
        "resource_type": le.get("type", ""),
        "summary": le.get("summary", ""),
        "agent_id": agent.get("id", ""),
        "agent_summary": agent.get("summary", ""),
        "service_id": service.get("id", ""),
        "service_summary": service.get("summary", ""),
        "incident_id": incident.get("id", ""),
        "incident_number": str(incident.get("incident_number", "") or ""),
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    resource = f"incidents/{args.incident_id}/log_entries" if args.incident_id else "log_entries"
    log.info("Fetching %s...", resource)
    entries = list(paginate(resource, token, params=build_params(args) or None))
    log.info("Got %d log entries.", len(entries))
    rows = [flatten(le) for le in entries]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=entries), args.output)
    return 0
