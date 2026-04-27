#!/usr/bin/env python3
"""Bulk-configure PagerDuty Alert Grouping Settings.

Lists existing alert grouping settings or attaches services to a named
setting. Two modes:

  --list                   : print all settings + the services each covers
  --attach NAME --services-csv FILE
                           : add services from CSV (column: service_id) to
                             the setting whose name matches NAME

Why this exists: AIOps grouping config drifts when teams add new services.
This script lets you enforce coverage from a CSV produced by a query against
your service catalog.
"""

import argparse
import csv
import sys

from pd_common import fetch_all, get_pd_api_token, make_api_request

ENDPOINT = "alert_grouping_settings"


def parse_arguments():
    parser = argparse.ArgumentParser(description="Manage PagerDuty Alert Grouping Settings in bulk.")
    parser.add_argument("-t", "--token", help="PagerDuty API token")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="List all alert grouping settings.")
    mode.add_argument(
        "--attach",
        metavar="NAME",
        help="Substring match for the alert grouping setting to attach services to.",
    )
    parser.add_argument(
        "--services-csv",
        help="CSV with a 'service_id' column. Required with --attach.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip the confirmation prompt.")
    return parser.parse_args()


def list_settings(token):
    settings = fetch_all(ENDPOINT, token, label=ENDPOINT)
    for s in settings:
        services = s.get("services") or []
        names = ", ".join((svc.get("summary") or svc.get("id")) for svc in services) or "(none)"
        print(f"{s.get('id')}  {s.get('name')}  type={s.get('type')}  services=[{names}]")
    print(f"\nTotal: {len(settings)} alert grouping settings.")


def find_setting(token, name_substring):
    settings = fetch_all(ENDPOINT, token, label=ENDPOINT)
    needle = name_substring.lower()
    matches = [s for s in settings if needle in (s.get("name") or "").lower()]
    if not matches:
        print(f"Error: no alert grouping setting matches '{name_substring}'.", file=sys.stderr)
        sys.exit(2)
    if len(matches) > 1:
        print(f"Error: '{name_substring}' matches {len(matches)} settings:", file=sys.stderr)
        for m in matches:
            print(f"  {m.get('id')}: {m.get('name')}", file=sys.stderr)
        sys.exit(2)
    return matches[0]


def load_service_ids(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "service_id" not in (reader.fieldnames or []):
            print("Error: CSV must have a 'service_id' column.", file=sys.stderr)
            sys.exit(2)
        return [row["service_id"].strip() for row in reader if row.get("service_id")]


def attach(token, args):
    if not args.services_csv:
        print("Error: --attach requires --services-csv.", file=sys.stderr)
        sys.exit(2)
    setting = find_setting(token, args.attach)
    new_ids = load_service_ids(args.services_csv)
    existing_ids = {svc.get("id") for svc in setting.get("services") or []}
    to_add = [sid for sid in new_ids if sid not in existing_ids]
    print(
        f"Setting '{setting['name']}' currently covers {len(existing_ids)} services; "
        f"{len(to_add)} new services to add."
    )
    if not to_add:
        return
    if args.dry_run:
        for sid in to_add:
            print(f"[dry-run] would add service {sid}")
        return
    if not args.yes:
        answer = input(f"Add {len(to_add)} services to '{setting['name']}'? (y/n): ").strip().lower()
        if answer != "y":
            print("Operation cancelled.")
            return
    merged = [{"id": sid, "type": "service_reference"} for sid in (existing_ids | set(new_ids))]
    body = {
        "alert_grouping_setting": {
            "name": setting["name"],
            "type": setting["type"],
            "config": setting.get("config") or {},
            "services": merged,
        }
    }
    result = make_api_request(f"{ENDPOINT}/{setting['id']}", token, method="PUT", data=body)
    if result and "alert_grouping_setting" in result:
        print(f"Updated. Setting now covers {len(merged)} services.")
    else:
        print("Update failed.")


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token)
    if args.list:
        list_settings(token)
    else:
        attach(token, args)


if __name__ == "__main__":
    main()
