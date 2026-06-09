#!/usr/bin/env python3
"""Configure PagerDuty Alert Grouping Settings (list, attach, CRUD).

Modes (pick one):

  --list                   : print all settings + the services each covers
  --attach NAME --services-csv FILE
                           : add services from CSV (column: service_id) to the
                             setting whose name matches NAME uniquely
  --get-json ID            : print one setting as JSON (API document)
  --create-json FILE       : POST a new setting from JSON (see README)
  --update-json FILE       : PUT an existing setting (must include id)
  --delete ID              : DELETE a setting by id

Why this exists: AIOps grouping config drifts when teams add new services.
This script lets you enforce coverage from a CSV or manage settings from JSON.
"""

import argparse
import csv
import json
import sys

from pd_common import fetch_all, add_token_arguments, get_pd_api_token, make_api_request

ENDPOINT = "alert_grouping_settings"


def _service_refs_from_setting(setting):
    """Normalize services to API reference list."""
    out = []
    for svc in setting.get("services") or []:
        if isinstance(svc, str):
            out.append({"id": svc, "type": "service_reference"})
        else:
            sid = svc.get("id")
            if sid:
                out.append({"id": sid, "type": "service_reference"})
    return out


def parse_arguments():
    parser = argparse.ArgumentParser(description="Manage PagerDuty Alert Grouping Settings.")
    add_token_arguments(parser)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="List all alert grouping settings.")
    mode.add_argument(
        "--attach",
        metavar="NAME",
        help="Substring match for the alert grouping setting to attach services to.",
    )
    mode.add_argument(
        "--get-json",
        metavar="ID",
        help="Print one alert grouping setting as JSON.",
    )
    mode.add_argument(
        "--create-json",
        metavar="FILE",
        help="Create a setting from a JSON file (inner object or wrapped in alert_grouping_setting).",
    )
    mode.add_argument(
        "--update-json",
        metavar="FILE",
        help="Update a setting from JSON (must include id).",
    )
    mode.add_argument(
        "--delete",
        metavar="ID",
        help="Delete an alert grouping setting by id.",
    )
    parser.add_argument(
        "--services-csv",
        help="CSV with a 'service_id' column. Required with --attach.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts.")
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="With --get-json, write JSON to this file instead of stdout.",
    )
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


def get_json(token, args):
    data = make_api_request(f"{ENDPOINT}/{args.get_json}", token)
    if not data:
        sys.exit(1)
    text = json.dumps(data.get("alert_grouping_setting", data), indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(text, end="")


def _load_setting_body(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    if "alert_grouping_setting" in raw:
        return raw["alert_grouping_setting"]
    return raw


def create_from_json(token, args):
    body_inner = _load_setting_body(args.create_json)
    body_inner.pop("id", None)
    if "name" not in body_inner or "type" not in body_inner:
        print("Error: JSON must include name and type.", file=sys.stderr)
        sys.exit(2)
    if "services" not in body_inner:
        print("Error: JSON must include services array.", file=sys.stderr)
        sys.exit(2)
    body_inner["services"] = _service_refs_from_setting(body_inner)
    payload = {"alert_grouping_setting": body_inner}
    if args.dry_run:
        print("[dry-run] would POST /alert_grouping_settings with:")
        print(json.dumps(payload, indent=2))
        return
    if not args.yes:
        ans = input("Create this alert grouping setting? (y/n): ").strip().lower()
        if ans != "y":
            print("Cancelled.")
            return
    result = make_api_request(ENDPOINT, token, method="POST", data=payload)
    if result and "alert_grouping_setting" in result:
        sid = result["alert_grouping_setting"].get("id")
        print(f"Created alert grouping setting id={sid}")
    else:
        print("Create failed.", file=sys.stderr)
        sys.exit(1)


def update_from_json(token, args):
    body_inner = _load_setting_body(args.update_json)
    sid = body_inner.get("id")
    if not sid:
        print("Error: JSON must include id for update.", file=sys.stderr)
        sys.exit(2)
    body_inner["services"] = _service_refs_from_setting(body_inner)
    payload = {"alert_grouping_setting": body_inner}
    if args.dry_run:
        print(f"[dry-run] would PUT /{ENDPOINT}/{sid} with:")
        print(json.dumps(payload, indent=2))
        return
    if not args.yes:
        ans = input(f"Update alert grouping setting {sid}? (y/n): ").strip().lower()
        if ans != "y":
            print("Cancelled.")
            return
    result = make_api_request(f"{ENDPOINT}/{sid}", token, method="PUT", data=payload)
    if result and "alert_grouping_setting" in result:
        print(f"Updated alert grouping setting id={sid}")
    else:
        print("Update failed.", file=sys.stderr)
        sys.exit(1)


def delete_setting(token, args):
    sid = args.delete
    if args.dry_run:
        print(f"[dry-run] would DELETE /{ENDPOINT}/{sid}")
        return
    if not args.yes:
        ans = input(f"Delete alert grouping setting {sid}? (y/n): ").strip().lower()
        if ans != "y":
            print("Cancelled.")
            return
    result = make_api_request(f"{ENDPOINT}/{sid}", token, method="DELETE")
    if result is not None:
        print(f"Deleted {sid}.")
    else:
        print("Delete failed.", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    if args.list:
        list_settings(token)
    elif args.attach:
        attach(token, args)
    elif args.get_json:
        get_json(token, args)
    elif args.create_json:
        create_from_json(token, args)
    elif args.update_json:
        update_from_json(token, args)
    elif args.delete:
        delete_setting(token, args)


if __name__ == "__main__":
    main()
