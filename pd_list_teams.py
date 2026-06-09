#!/usr/bin/env python3
"""List all PagerDuty teams (flat directory export for CLI/CSV pipelines)."""

import argparse
import csv
import json
import sys

from prettytable import PrettyTable

from pd_common import add_token_arguments, get_pd_api_token, paginate


def fetch_teams(token, text_filter=None):
    print("Fetching teams...", end="", flush=True)
    teams = list(paginate("teams", token))
    print(f" Found {len(teams)}.")
    if text_filter:
        needle = text_filter.lower()
        teams = [
            t
            for t in teams
            if needle in (t.get("name") or "").lower()
            or needle in (t.get("description") or "").lower()
        ]
        print(f"After filter '{text_filter}': {len(teams)} teams.", file=sys.stderr)
    return teams


def team_row(t):
    return {
        "id": t.get("id") or "",
        "name": t.get("name") or "",
        "description": t.get("description") or "",
    }


def output_table(rows, outfile):
    t = PrettyTable()
    t.field_names = ["id", "name", "description"]
    for r in rows:
        t.add_row([r["id"], r["name"], r["description"]])
    s = t.get_string()
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(s + "\n")
    else:
        print(s)


def output_csv(rows, outfile):
    out = open(outfile, "w", encoding="utf-8", newline="") if outfile else sys.stdout
    try:
        w = csv.DictWriter(out, fieldnames=["id", "name", "description"])
        w.writeheader()
        w.writerows(rows)
    finally:
        if outfile:
            out.close()


def output_json(rows, outfile):
    payload = json.dumps(rows, indent=2)
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    else:
        print(payload)


def parse_arguments():
    p = argparse.ArgumentParser(
        description="List PagerDuty teams with id, name, and description."
    )
    add_token_arguments(p)
    p.add_argument(
        "-f",
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)",
    )
    p.add_argument("-o", "--output", help="Write to this file instead of stdout")
    p.add_argument(
        "--filter",
        dest="text_filter",
        metavar="TEXT",
        help="Substring match on team name or description (case-insensitive)",
    )
    return p.parse_args()


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    teams = fetch_teams(token, text_filter=args.text_filter)
    rows = [team_row(t) for t in teams]
    if args.format == "table":
        output_table(rows, args.output)
    elif args.format == "csv":
        output_csv(rows, args.output)
    else:
        output_json(rows, args.output)


if __name__ == "__main__":
    main()
