"""Bulk-create PagerDuty maintenance windows from a CSV.

CSV columns: service_id, start_time, end_time, description
Times must be ISO 8601 with timezone.

Idempotent: before creating, existing windows for the targeted services are
fetched, and rows whose (service, start, end) already exist are skipped — so
re-running a CSV after a partial failure does not create duplicates.
"""

from __future__ import annotations

import sys
from datetime import datetime

from ..api import PDApiError, paginate, request
from ..bulkops import load_csv_rows, parse_iso8601
from ..cli import confirm, finish_bulk, init, standard_parser
from ..config import get_from_email
from ..log import get_logger

log = get_logger("bulk_maintenance_window")


def build_parser():
    p = standard_parser(
        "Bulk-create PagerDuty maintenance windows from a CSV.", write_guards=True
    )
    p.add_argument("csv_file", help="CSV: service_id, start_time, end_time, description")
    p.add_argument("--from-email",
                   help="PagerDuty 'From' header (valid PD user email); "
                        "defaults to PD_FROM_EMAIL.")
    return p


def _norm(dt_str: str) -> str:
    """Normalized comparison key for ISO timestamps (Z == +00:00)."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).isoformat()
    except (ValueError, AttributeError):
        return dt_str or ""


def load_and_validate(path) -> list[dict]:
    rows = load_csv_rows(
        path,
        {"service_id", "start_time", "end_time", "description"},
        skip_if_missing=("service_id",),
    )
    for row in rows:
        start = parse_iso8601(row["start_time"], field="start_time", line=row["_line"])
        end = parse_iso8601(row["end_time"], field="end_time", line=row["_line"])
        if end <= start:
            print(f"Error: line {row['_line']}: end_time must be after start_time.",
                  file=sys.stderr)
            raise SystemExit(2)
    return rows


def existing_window_keys(token, service_ids) -> set[tuple]:
    """(service_id, start, end) for every current/future window on the services."""
    keys = set()
    if not service_ids:
        return keys
    windows = paginate(
        "maintenance_windows", token,
        params={"service_ids[]": sorted(service_ids), "filter": "all"},
    )
    for w in windows:
        for svc in w.get("services") or []:
            keys.add((svc.get("id"), _norm(w.get("start_time", "")), _norm(w.get("end_time", ""))))
    return keys


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    from_email = get_from_email(args.from_email)
    rows = load_and_validate(args.csv_file)
    if not rows:
        log.info("No rows to process.")
        return 0
    log.info("Loaded %d window rows from %s.", len(rows), args.csv_file)

    existing = existing_window_keys(token, {r["service_id"] for r in rows})
    todo, skipped = [], 0
    for row in rows:
        key = (row["service_id"], _norm(row["start_time"]), _norm(row["end_time"]))
        if key in existing:
            log.info("line %d: identical window already exists for %s; skipping.",
                     row["_line"], row["service_id"])
            skipped += 1
        else:
            todo.append(row)
    if not todo:
        log.info("All %d windows already exist. Nothing to do.", skipped)
        return 0

    if not confirm(f"Create {len(todo)} maintenance windows ({skipped} already exist)?",
                   assume_yes=args.yes, dry_run=args.dry_run):
        return 0

    created = failed = 0
    for row in todo:
        if args.dry_run:
            print(f"[dry-run] line {row['_line']}: would create window for "
                  f"{row['service_id']} {row['start_time']} -> {row['end_time']}",
                  file=sys.stderr)
            created += 1
            continue
        body = {
            "maintenance_window": {
                "type": "maintenance_window",
                "start_time": row["start_time"],
                "end_time": row["end_time"],
                "description": row.get("description", ""),
                "services": [{"id": row["service_id"], "type": "service_reference"}],
            }
        }
        try:
            result = request("maintenance_windows", token, method="POST", data=body,
                             extra_headers={"From": from_email})
            wid = (result.get("maintenance_window") or {}).get("id")
            log.info("line %d: created %s for %s", row["_line"], wid, row["service_id"])
            created += 1
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("line %d: failed - %s", row["_line"], e)
            failed += 1

    return finish_bulk(created, failed, dry_run=args.dry_run, label="windows")
