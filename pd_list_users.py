#!/usr/bin/env python3
"""List all PagerDuty users (flat directory export for CLI/CSV pipelines)."""

import argparse
import csv
import json
import sys

from prettytable import PrettyTable

from pd_common import add_token_arguments, get_pd_api_token, paginate


def fetch_users(token, text_filter=None):
    print("Fetching users...", end="", flush=True)
    users = list(paginate("users", token))
    print(f" Found {len(users)}.")
    if text_filter:
        needle = text_filter.lower()
        users = [
            u
            for u in users
            if needle in (u.get("name") or "").lower()
            or needle in (u.get("email") or "").lower()
        ]
        print(f"After filter '{text_filter}': {len(users)} users.", file=sys.stderr)
    return users


def user_row(u):
    return {
        "id": u.get("id") or "",
        "name": u.get("name") or "",
        "email": u.get("email") or "",
        "role": u.get("role") or "",
        "job_title": u.get("job_title") or "",
    }


def output_table(rows, outfile):
    t = PrettyTable()
    t.field_names = ["id", "name", "email", "role", "job_title"]
    for r in rows:
        t.add_row([r["id"], r["name"], r["email"], r["role"], r["job_title"]])
    s = t.get_string()
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(s + "\n")
    else:
        print(s)


def output_csv(rows, outfile):
    out = open(outfile, "w", encoding="utf-8", newline="") if outfile else sys.stdout
    try:
        w = csv.DictWriter(out, fieldnames=["id", "name", "email", "role", "job_title"])
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
        description="List PagerDuty users with id, name, email, role, and job title."
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
        help="Substring match on name or email (case-insensitive)",
    )
    return p.parse_args()


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    users = fetch_users(token, text_filter=args.text_filter)
    rows = [user_row(u) for u in users]
    if args.format == "table":
        output_table(rows, args.output)
    elif args.format == "csv":
        output_csv(rows, args.output)
    else:
        output_json(rows, args.output)


if __name__ == "__main__":
    main()
