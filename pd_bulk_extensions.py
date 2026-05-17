#!/usr/bin/env python3
"""Bulk-attach a PagerDuty extension to many services.

Looks up the extension schema by partial name match, then creates one
extension per service in the input list (filtered or from CSV).

Common use cases:
  - Add a generic webhook extension to every service in a team
  - Standardize Slack/Teams notification posting URLs across services

Examples:
  # Attach a Generic Webhook extension matching --filter, posting to URL
  python pd_bulk_extensions.py \
      --schema "Generic Webhook" \
      --name "DataDog hook" \
      --endpoint-url https://example.com/hook \
      --service-filter "prod"

  # Attach to a specific list of service IDs from a CSV (column: service_id)
  python pd_bulk_extensions.py --schema "Generic Webhook" \
      --name "DataDog hook" --endpoint-url ... --services-csv services.csv
"""

import argparse
import csv
import sys

from pd_common import fetch_all, add_token_arguments, get_pd_api_token, make_api_request


def parse_arguments():
    parser = argparse.ArgumentParser(description="Bulk-attach a PagerDuty extension to many services.")
    add_token_arguments(parser)
    parser.add_argument("--schema", required=True, help="Extension schema name (substring match).")
    parser.add_argument("--name", required=True, help="Display name for the new extension.")
    parser.add_argument(
        "--endpoint-url",
        required=True,
        help="Endpoint URL the extension will POST to.",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--service-filter", help="Only attach to services whose name contains this string.")
    target.add_argument("--services-csv", help="CSV with a 'service_id' column listing target services.")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating extensions.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip the confirmation prompt.")
    return parser.parse_args()


def find_schema(token, name_substring):
    schemas = fetch_all("extension_schemas", token, label="extension_schemas")
    needle = name_substring.lower()
    matches = [s for s in schemas if needle in (s.get("label") or s.get("name") or "").lower()]
    if not matches:
        print(f"Error: no extension_schema matches '{name_substring}'.", file=sys.stderr)
        sys.exit(2)
    if len(matches) > 1:
        print(f"Error: '{name_substring}' matches {len(matches)} schemas:", file=sys.stderr)
        for m in matches:
            print(f"  {m.get('id')}: {m.get('label') or m.get('name')}", file=sys.stderr)
        print("Refine the --schema argument.", file=sys.stderr)
        sys.exit(2)
    return matches[0]


def load_service_ids_from_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "service_id" not in (reader.fieldnames or []):
            print("Error: CSV must have a 'service_id' column.", file=sys.stderr)
            sys.exit(2)
        return [row["service_id"].strip() for row in reader if row.get("service_id")]


def resolve_services(token, args):
    if args.services_csv:
        ids = load_service_ids_from_csv(args.services_csv)
        return [{"id": sid, "name": sid} for sid in ids]
    return fetch_all("services", token, name_filter=args.service_filter, label="services")


def create_extension(token, schema, service, args):
    body = {
        "extension": {
            "type": "extension",
            "name": args.name,
            "endpoint_url": args.endpoint_url,
            "extension_schema": {"id": schema["id"], "type": "extension_schema_reference"},
            "extension_objects": [{"id": service["id"], "type": "service_reference"}],
        }
    }
    if args.dry_run:
        print(f"[dry-run] would attach to {service.get('name', service['id'])} ({service['id']})")
        return True
    result = make_api_request("extensions", token, method="POST", data=body)
    if result and "extension" in result:
        ext = result["extension"]
        print(f"Attached extension {ext.get('id')} to {service.get('name', service['id'])}")
        return True
    print(f"Failed on service {service['id']}")
    return False


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    schema = find_schema(token, args.schema)
    print(f"Using extension schema {schema.get('id')}: {schema.get('label') or schema.get('name')}")

    services = resolve_services(token, args)
    if not services:
        print("No matching services.")
        return
    print(f"{len(services)} services targeted.")

    if not args.dry_run and not args.yes:
        answer = input(f"Attach '{args.name}' to {len(services)} services? (y/n): ").strip().lower()
        if answer != "y":
            print("Operation cancelled.")
            return

    succeeded = 0
    failed = 0
    for service in services:
        if create_extension(token, schema, service, args):
            succeeded += 1
        else:
            failed += 1

    verb = "Would attach" if args.dry_run else "Attached"
    print(f"\nSummary: {verb} {succeeded} extensions, {failed} failed.")


if __name__ == "__main__":
    main()
