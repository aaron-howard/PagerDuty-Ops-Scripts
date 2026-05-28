#!/usr/bin/env python3
"""Bulk-create PagerDuty maintenance windows from a CSV.

CSV columns (header row required): service_id, start_time, end_time, description

Times must be ISO 8601 with timezone (e.g. 2026-05-01T02:00:00Z or
2026-05-01T02:00:00-04:00). One row produces one maintenance window for one
service. To cover multiple services with the same window, repeat the row with
a different service_id.
"""

import argparse
import csv
import sys

import requests

from pd_common import PD_API_BASE, REQUEST_TIMEOUT, build_headers, add_token_arguments, get_pd_api_token


def parse_arguments():
    parser = argparse.ArgumentParser(description="Bulk-create PagerDuty maintenance windows from a CSV.")
    parser.add_argument("csv_file", help="CSV with columns: service_id, start_time, end_time, description")
    add_token_arguments(parser)
    parser.add_argument(
        "--from-email",
        required=True,
        help="Email of the user creating the windows (PagerDuty 'From' header).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating windows.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip the confirmation prompt.")
    return parser.parse_args()


def load_rows(path):
    required = {"service_id", "start_time", "end_time", "description"}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"Error: CSV missing required columns: {sorted(missing)}", file=sys.stderr)
            sys.exit(2)
        rows = []
        for line_no, row in enumerate(reader, start=2):
            if not row.get("service_id"):
                continue
            rows.append({**row, "_line": line_no})
        return rows


def create_window(token, from_email, row, dry_run):
    body = {
        "maintenance_window": {
            "type": "maintenance_window",
            "start_time": row["start_time"],
            "end_time": row["end_time"],
            "description": row.get("description", ""),
            "services": [{"id": row["service_id"], "type": "service_reference"}],
        }
    }
    if dry_run:
        print(
            f"[dry-run] line {row['_line']}: would create window for service "
            f"{row['service_id']} {row['start_time']} -> {row['end_time']}"
        )
        return True
    # Maintenance window creation requires a 'From' header with a valid PD user email.
    headers = build_headers(token)
    headers["From"] = from_email
    try:
        resp = requests.post(
            f"{PD_API_BASE}/maintenance_windows",
            headers=headers,
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        body_text = getattr(e.response, "text", "") if getattr(e, "response", None) is not None else ""
        print(f"line {row['_line']}: failed - {e}. {body_text}")
        return False
    created = resp.json().get("maintenance_window", {})
    print(
        f"line {row['_line']}: created {created.get('id')} for service "
        f"{row['service_id']} {row['start_time']} -> {row['end_time']}"
    )
    return True


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    rows = load_rows(args.csv_file)
    if not rows:
        print("No rows to process.")
        return
    print(f"Loaded {len(rows)} maintenance windows from {args.csv_file}.")

    if not args.dry_run and not args.yes:
        answer = input(f"Create {len(rows)} maintenance windows? (y/n): ").strip().lower()
        if answer != "y":
            print("Operation cancelled.")
            return

    created = 0
    failed = 0
    for row in rows:
        if create_window(token, args.from_email, row, args.dry_run):
            created += 1
        else:
            failed += 1

    verb = "Would create" if args.dry_run else "Created"
    print(f"\nSummary: {verb} {created} windows, {failed} failed.")


if __name__ == "__main__":
    main()
