#!/usr/bin/env python3
"""List PagerDuty Schedules v3 (Early Access).

Reads /v3/schedules with the required X-EARLY-ACCESS header. Read-only
inventory script for orgs experimenting with the v3 (flexible) schedules
API. v3 and legacy v2 schedules coexist; this script does not touch v2.

Important: PagerDuty marks the v3 API as Early Access and explicitly says
"Do not use this endpoint in production, as it may change." Use this
script for inventory/visibility only — the existing v2 scripts in this
repo remain the right tool for production schedule operations until v3
is generally available.

Optional --get SCHEDULE_ID fetches a single schedule's full detail
(rotations, escalation policies, teams) instead of the list view.
"""

import argparse
import csv
import io
import json
import sys

from pd_common import add_token_arguments, get_pd_api_token, make_api_request, paginate

V3_RESOURCE = "v3/schedules"
EARLY_ACCESS_HEADERS = {"X-EARLY-ACCESS": "flexible-schedules-early-access"}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="List PagerDuty Schedules v3 (Early Access). Read-only inventory."
    )
    add_token_arguments(parser)
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table).",
    )
    parser.add_argument("-o", "--output", help="Output file (default stdout).")
    parser.add_argument(
        "--get",
        metavar="SCHEDULE_ID",
        help="Fetch a single v3 schedule's full detail instead of the list view.",
    )
    parser.add_argument(
        "--include-users",
        action="store_true",
        help="With --get, include the users array in the response.",
    )
    return parser.parse_args()


def list_schedules(token):
    return list(paginate(V3_RESOURCE, token, extra_headers=EARLY_ACCESS_HEADERS))


def get_schedule(token, schedule_id, include_users):
    params = {}
    includes = []
    if include_users:
        includes.append("users")
    if includes:
        params["include[]"] = includes
    return make_api_request(
        f"{V3_RESOURCE}/{schedule_id}",
        token,
        params=params or None,
        extra_headers=EARLY_ACCESS_HEADERS,
    )


def render_list(schedules, fmt):
    if fmt == "json":
        return json.dumps(schedules, indent=2)
    rows = [
        {
            "id": s.get("id", ""),
            "name": s.get("name") or s.get("summary", ""),
            "type": s.get("type", ""),
            "self": s.get("self", ""),
        }
        for s in schedules
    ]
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "name", "type", "self"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()
    try:
        from tabulate import tabulate
    except ImportError:
        return "\n".join(f"{r['id']}\t{r['name']}\t{r['type']}" for r in rows) + "\n"
    return (
        tabulate(
            [[r["id"], r["name"], r["type"]] for r in rows],
            headers=["ID", "Name", "Type"],
            tablefmt="github",
        )
        + f"\n\nTotal: {len(rows)} v3 schedules\n"
    )


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)

    if args.get:
        result = get_schedule(token, args.get, args.include_users)
        if not result:
            print("No schedule returned.", file=sys.stderr)
            sys.exit(1)
        payload = json.dumps(result, indent=2)
    else:
        print("Fetching v3 schedules...", end="", flush=True, file=sys.stderr)
        schedules = list_schedules(token)
        print(f" got {len(schedules)}.", file=sys.stderr)
        payload = render_list(schedules, args.format)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        print(f"Wrote output to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
