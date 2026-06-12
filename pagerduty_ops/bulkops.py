"""Reusable bulk-operation logic (idempotent rename, CSV loading helpers)."""

from __future__ import annotations

import csv
import sys
from datetime import datetime

from .api import PDApiError, fetch_all, request
from .cli import confirm, finish_bulk
from .log import get_logger

log = get_logger("bulkops")


def name_has_affix(name, affix, position, *, ignore_case=False) -> bool:
    """True if `name` already carries the affix (idempotency check)."""
    n = (name or "").strip()
    if not affix:
        return True
    if ignore_case:
        n, affix = n.lower(), affix.lower()
    return n.startswith(affix) if position == "prefix" else n.endswith(affix)


def apply_name_affix_update(
    *,
    token,
    resource,
    item_kind,
    position,
    affix,
    name_filter=None,
    list_only=False,
    dry_run=False,
    assume_yes=False,
    ignore_case=False,
) -> int:
    """Add a literal prefix/suffix to names that lack it. Returns an exit code."""
    if position not in ("prefix", "suffix"):
        raise ValueError("position must be 'prefix' or 'suffix'")

    items = fetch_all(resource, token, name_filter=name_filter, label=resource)

    if list_only:
        for item in items:
            print(f"{item.get('id')}\t{item.get('name')}")
        log.info("Total: %d %s", len(items), resource)
        return 0

    needs_update = [
        i for i in items
        if not name_has_affix(i.get("name"), affix, position, ignore_case=ignore_case)
    ]
    log.info("%d %s need %s %r.", len(needs_update), resource, position, affix)
    if not needs_update:
        return 0

    if not confirm(f"Update {len(needs_update)} {resource}?", assume_yes=assume_yes,
                   dry_run=dry_run):
        return 0

    updated = failed = 0
    for item in needs_update:
        item_id = item.get("id")
        current = (item.get("name") or "").strip()
        new_name = f"{affix}{current}" if position == "prefix" else f"{current}{affix}"
        if dry_run:
            print(f"[dry-run] would rename {item_kind} {current!r} -> {new_name!r} ({item_id})",
                  file=sys.stderr)
            updated += 1
            continue
        try:
            request(f"{resource}/{item_id}", token, method="PUT",
                    data={item_kind: {"name": new_name}})
            log.info("Renamed %s %r -> %r (%s)", item_kind, current, new_name, item_id)
            updated += 1
        except PDApiError as e:
            if e.is_auth_error:
                raise  # no point continuing the loop with a rejected token
            log.error("Failed to rename %s (%s): %s", current, item_id, e)
            failed += 1

    return finish_bulk(updated, failed, dry_run=dry_run, label=resource)


def load_csv_rows(path: str, required_columns: set[str], *, skip_if_missing=()) -> list[dict]:
    """Load and validate a CSV. Exits 2 on missing columns; skips rows missing
    any column named in `skip_if_missing`. Adds '_line' for error reporting."""
    try:
        f = open(path, newline="", encoding="utf-8")
    except OSError as e:
        print(f"Error: cannot read CSV {path}: {e}", file=sys.stderr)
        raise SystemExit(2) from e
    with f:
        reader = csv.DictReader(f)
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            print(f"Error: CSV missing required columns: {sorted(missing)}", file=sys.stderr)
            raise SystemExit(2)
        rows = []
        for line_no, row in enumerate(reader, start=2):
            if any(not (row.get(c) or "").strip() for c in skip_if_missing):
                continue
            rows.append({**{k: (v or "").strip() for k, v in row.items()}, "_line": line_no})
        return rows


def parse_iso8601(value: str, *, field: str, line: int) -> datetime:
    """Strict ISO 8601 (timezone required) validation for CSV inputs."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        print(f"Error: line {line}: {field}={value!r} is not valid ISO 8601.", file=sys.stderr)
        raise SystemExit(2) from None
    if dt.tzinfo is None:
        print(f"Error: line {line}: {field}={value!r} must include a timezone "
              "(e.g. 2026-05-01T02:00:00Z).", file=sys.stderr)
        raise SystemExit(2)
    return dt
