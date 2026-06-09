#!/usr/bin/env python3
"""Export PagerDuty log entries to CSV or JSON for compliance / incident forensics.

Uses ``GET /log_entries`` (account-wide) with offset pagination, or
``GET /incidents/{id}/log_entries`` when ``--incident-id`` is set.

PagerDuty defaults the searchable window when ``since`` / ``until`` are omitted;
pass explicit ISO 8601 bounds for reproducible exports.
"""

import argparse
import csv
import io
import json
import sys

from pd_common import add_token_arguments, get_pd_api_token, paginate


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Export PagerDuty log entries to CSV or JSON (read-only)."
    )
    add_token_arguments(parser)
    parser.add_argument(
        "--incident-id",
        help="Fetch log entries for this incident only (GET /incidents/{id}/log_entries).",
    )
    parser.add_argument("--since", help="ISO 8601 lower bound (e.g. 2026-04-01T00:00:00Z)")
    parser.add_argument("--until", help="ISO 8601 upper bound")
    parser.add_argument(
        "--time-zone",
        help="IANA time zone for rendering (e.g. America/Chicago).",
    )
    parser.add_argument(
        "--is-overview",
        action="store_true",
        help="Only return high-level incident changes (less verbose).",
    )
    parser.add_argument(
        "--include",
        action="append",
        dest="includes",
        metavar="FRAGMENT",
        help="Pass include[] query fragment (repeatable). Example: --include channels",
    )
    parser.add_argument(
        "--team-id",
        action="append",
        dest="team_ids",
        metavar="ID",
        help="Restrict to team IDs (repeatable). Account must have teams ability.",
    )
    parser.add_argument(
        "--service-id",
        action="append",
        dest="service_ids",
        metavar="ID",
        help="Restrict to service IDs (repeatable).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default csv).",
    )
    parser.add_argument("-o", "--output", help="Output file (default stdout).")
    return parser.parse_args()


def build_params(args):
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


CSV_FIELDS = [
    "id",
    "created_at",
    "resource_type",
    "summary",
    "agent_id",
    "agent_summary",
    "service_id",
    "service_summary",
    "incident_id",
    "incident_number",
]


def flatten_log_entry(le):
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


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    params = build_params(args)

    if args.incident_id:
        resource = f"incidents/{args.incident_id}/log_entries"
        label = f"log_entries for incident {args.incident_id}"
    else:
        resource = "log_entries"
        label = "log_entries"

    print(f"Fetching {label}...", end="", flush=True, file=sys.stderr)
    entries = list(paginate(resource, token, params=params or None))
    print(f" got {len(entries)}.", file=sys.stderr)

    if args.format == "json":
        payload = json.dumps(entries, indent=2)
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for le in entries:
            writer.writerow(flatten_log_entry(le))
        payload = buf.getvalue()

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        print(f"Wrote {len(entries)} rows to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
