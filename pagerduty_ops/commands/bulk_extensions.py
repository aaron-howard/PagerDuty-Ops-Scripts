"""Bulk-attach a PagerDuty extension (webhook, Slack, etc.) to many services.

Schema resolved by unique substring match against /extension_schemas; targets
from --service-filter or a services CSV. Idempotent-ish: services that already
have an extension with the same name + endpoint URL are skipped.
"""

from __future__ import annotations

import sys
from urllib.parse import urlparse

from ..api import PDApiError, fetch_all, request
from ..bulkops import load_csv_rows
from ..cli import confirm, finish_bulk, init, standard_parser
from ..log import get_logger

log = get_logger("bulk_extensions")


def build_parser():
    p = standard_parser(
        "Bulk-attach a PagerDuty extension to many services.", write_guards=True
    )
    p.add_argument("--schema", required=True, help="Extension schema name (substring match).")
    p.add_argument("--name", required=True, help="Display name for the new extension.")
    p.add_argument("--endpoint-url", required=True, help="HTTPS endpoint the extension POSTs to.")
    target = p.add_mutually_exclusive_group(required=True)
    target.add_argument("--service-filter", help="Services whose name contains this string.")
    target.add_argument("--services-csv", help="CSV with a 'service_id' column.")
    return p


def validate_endpoint_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        print(f"Error: --endpoint-url must be a valid https:// URL (got {url!r}).",
              file=sys.stderr)
        raise SystemExit(2)


def find_schema(token, name_substring) -> dict:
    schemas = fetch_all("extension_schemas", token, label="extension_schemas")
    needle = name_substring.lower()
    matches = [s for s in schemas if needle in (s.get("label") or s.get("name") or "").lower()]
    if not matches:
        print(f"Error: no extension_schema matches {name_substring!r}.", file=sys.stderr)
        raise SystemExit(2)
    if len(matches) > 1:
        print(f"Error: {name_substring!r} matches {len(matches)} schemas:", file=sys.stderr)
        for m in matches:
            print(f"  {m.get('id')}: {m.get('label') or m.get('name')}", file=sys.stderr)
        raise SystemExit(2)
    return matches[0]


def resolve_services(token, args) -> list[dict]:
    if args.services_csv:
        rows = load_csv_rows(args.services_csv, {"service_id"}, skip_if_missing=("service_id",))
        return [{"id": r["service_id"], "name": r["service_id"]} for r in rows]
    return fetch_all("services", token, name_filter=args.service_filter, label="services")


def existing_extension_keys(token) -> set[tuple]:
    """(service_id, name, endpoint_url) for every existing extension."""
    keys = set()
    for ext in fetch_all("extensions", token, label="extensions"):
        for obj in ext.get("extension_objects") or []:
            keys.add((obj.get("id"), ext.get("name"), ext.get("endpoint_url")))
    return keys


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    validate_endpoint_url(args.endpoint_url)
    token = init(args)
    schema = find_schema(token, args.schema)
    log.info("Using extension schema %s: %s", schema.get("id"),
             schema.get("label") or schema.get("name"))

    services = resolve_services(token, args)
    if not services:
        log.info("No matching services.")
        return 0

    existing = existing_extension_keys(token)
    todo = [s for s in services
            if (s["id"], args.name, args.endpoint_url) not in existing]
    skipped = len(services) - len(todo)
    log.info("%d services targeted (%d already have this extension).", len(todo), skipped)
    if not todo:
        return 0

    if not confirm(f"Attach '{args.name}' to {len(todo)} services?",
                   assume_yes=args.yes, dry_run=args.dry_run):
        return 0

    succeeded = failed = 0
    for service in todo:
        if args.dry_run:
            print(f"[dry-run] would attach to {service.get('name', service['id'])} "
                  f"({service['id']})", file=sys.stderr)
            succeeded += 1
            continue
        body = {
            "extension": {
                "type": "extension",
                "name": args.name,
                "endpoint_url": args.endpoint_url,
                "extension_schema": {"id": schema["id"], "type": "extension_schema_reference"},
                "extension_objects": [{"id": service["id"], "type": "service_reference"}],
            }
        }
        try:
            result = request("extensions", token, method="POST", data=body)
            ext_id = (result.get("extension") or {}).get("id")
            log.info("Attached extension %s to %s", ext_id, service.get("name", service["id"]))
            succeeded += 1
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("Failed on service %s: %s", service["id"], e)
            failed += 1

    return finish_bulk(succeeded, failed, dry_run=args.dry_run, label="extensions")
