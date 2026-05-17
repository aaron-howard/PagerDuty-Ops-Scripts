#!/usr/bin/env python3
"""Export PagerDuty audit records to CSV or JSON.

Pulls /audit/records with cursor pagination, optionally filtered by date
range, actor, action prefix, or root resource. Designed for compliance
reporting and change-history audits.
"""

import argparse
import csv
import io
import json
import sys

from pd_common import add_token_arguments, get_pd_api_token, paginate_cursor


def parse_arguments():
    parser = argparse.ArgumentParser(description="Export PagerDuty audit records to CSV or JSON.")
    add_token_arguments(parser)
    parser.add_argument("--since", help="ISO 8601 lower bound (e.g. 2026-04-01T00:00:00Z)")
    parser.add_argument("--until", help="ISO 8601 upper bound")
    parser.add_argument(
        "--actor-id",
        action="append",
        help="Filter by actor user/team ID. May be repeated.",
    )
    parser.add_argument(
        "--actor-type",
        choices=["user", "team", "system"],
        help="Filter by actor type.",
    )
    parser.add_argument(
        "--action",
        action="append",
        help="Filter by action prefix (e.g. 'create', 'update', 'delete'). May be repeated.",
    )
    parser.add_argument(
        "--root-resource-type",
        help="Filter by root resource type (e.g. services, schedules, escalation_policies).",
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
    if args.actor_id:
        params["actor_id"] = args.actor_id
    if args.actor_type:
        params["actor_type"] = args.actor_type
    if args.action:
        params["action"] = args.action
    if args.root_resource_type:
        params["root_resource_type"] = args.root_resource_type
    return params


CSV_FIELDS = [
    "id",
    "execution_time",
    "action",
    "actor_id",
    "actor_type",
    "actor_summary",
    "root_resource_id",
    "root_resource_type",
    "root_resource_summary",
    "method_type",
]


def flatten(record):
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


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    params = build_params(args)

    print("Fetching audit records...", end="", flush=True, file=sys.stderr)
    records = list(paginate_cursor("audit/records", token, items_key="records", params=params))
    print(f" got {len(records)} records.", file=sys.stderr)

    if args.format == "json":
        payload = json.dumps(records, indent=2)
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for r in records:
            writer.writerow(flatten(r))
        payload = buf.getvalue()

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        print(f"Wrote {len(records)} records to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
