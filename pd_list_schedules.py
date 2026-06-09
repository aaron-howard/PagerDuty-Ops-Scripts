#!/usr/bin/env python3
"""List PagerDuty schedules (REST API v2: GET /schedules).

Read-only inventory of legacy v2 schedules (schedule_layers, overrides, etc. as
embedded fields). For the separate v3 “flexible schedules” Early Access API,
use pd_v3_schedules_list.py instead.
"""

import argparse
import csv
import io
import json
import sys

from pd_common import add_token_arguments, get_pd_api_token, paginate


def parse_arguments():
    parser = argparse.ArgumentParser(description="List PagerDuty schedules (API v2 /schedules).")
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
        "--name-filter",
        help="Substring match (case-insensitive) against schedule name.",
    )
    return parser.parse_args()


def fetch_schedules(token, name_filter):
    print("Fetching schedules...", end="", flush=True, file=sys.stderr)
    schedules = list(paginate("schedules", token))
    if name_filter:
        needle = name_filter.lower()
        schedules = [s for s in schedules if needle in (s.get("name") or "").lower()]
    print(f" {len(schedules)} found.", file=sys.stderr)
    return schedules


def render_list(schedules, fmt):
    if fmt == "json":
        return json.dumps(schedules, indent=2)
    rows = []
    for s in schedules:
        rows.append(
            {
                "id": s.get("id", ""),
                "name": s.get("name") or s.get("summary", ""),
                "time_zone": s.get("time_zone", ""),
                "html_url": s.get("html_url", ""),
            }
        )
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "name", "time_zone", "html_url"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()
    try:
        from tabulate import tabulate
    except ImportError:
        return "\n".join(f"{r['id']}\t{r['name']}\t{r['time_zone']}" for r in rows) + "\n"
    return (
        tabulate(
            [[r["id"], r["name"], r["time_zone"], r["html_url"]] for r in rows],
            headers=["ID", "Name", "Time zone", "URL"],
            tablefmt="github",
        )
        + f"\n\nTotal: {len(rows)} schedules\n"
    )


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    schedules = fetch_schedules(token, args.name_filter)
    payload = render_list(schedules, args.format)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        print(f"Wrote output to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
