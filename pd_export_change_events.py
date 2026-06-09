#!/usr/bin/env python3
"""Export PagerDuty change events to CSV or JSON for compliance / change correlation.

Uses one of:

- ``GET /change_events`` (account-wide, default)
- ``GET /services/{id}/change_events`` when ``--service-id`` is set
- ``GET /incidents/{id}/related_change_events`` when ``--incident-id`` is set

Read-only; offset pagination like other list endpoints.
"""

import argparse
import csv
import io
import json
import sys

from pd_common import add_token_arguments, get_pd_api_token, paginate


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Export PagerDuty change events to CSV or JSON (read-only)."
    )
    add_token_arguments(parser)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--service-id",
        help="List change events for this service only.",
    )
    group.add_argument(
        "--incident-id",
        help="List change events related to this incident only.",
    )
    parser.add_argument("--since", help="ISO 8601 lower bound on event time")
    parser.add_argument("--until", help="ISO 8601 upper bound on event time")
    parser.add_argument(
        "--team-id",
        action="append",
        dest="team_ids",
        metavar="ID",
        help="Filter by team ID (repeatable). Account-wide mode only.",
    )
    parser.add_argument(
        "--integration-id",
        action="append",
        dest="integration_ids",
        metavar="ID",
        help="Filter by integration ID (repeatable). Account-wide mode only.",
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
    if args.service_id or args.incident_id:
        return params
    if args.team_ids:
        params["team_ids[]"] = args.team_ids
    if args.integration_ids:
        params["integration_ids[]"] = args.integration_ids
    return params


CSV_FIELDS = [
    "id",
    "type",
    "summary",
    "timestamp",
    "source",
    "service_ids",
]


def flatten_change_event(ce):
    services = ce.get("services") or []
    svc_ids = ",".join(s.get("id", "") for s in services if isinstance(s, dict))
    return {
        "id": ce.get("id", ""),
        "type": ce.get("type", ""),
        "summary": ce.get("summary", ""),
        "timestamp": ce.get("timestamp") or ce.get("created_at", ""),
        "source": ce.get("source", ""),
        "service_ids": svc_ids,
    }


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    params = build_params(args)

    if args.incident_id:
        resource = f"incidents/{args.incident_id}/related_change_events"
        items_key = "change_events"
        label = f"related change_events for incident {args.incident_id}"
    elif args.service_id:
        resource = f"services/{args.service_id}/change_events"
        items_key = None
        label = f"change_events for service {args.service_id}"
    else:
        resource = "change_events"
        items_key = None
        label = "change_events"

    print(f"Fetching {label}...", end="", flush=True, file=sys.stderr)
    events = list(paginate(resource, token, params=params or None, items_key=items_key))
    print(f" got {len(events)}.", file=sys.stderr)

    if args.format == "json":
        payload = json.dumps(events, indent=2)
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for ce in events:
            writer.writerow(flatten_change_event(ce))
        payload = buf.getvalue()

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        print(f"Wrote {len(events)} rows to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
