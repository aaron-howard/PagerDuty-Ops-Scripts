"""Bulk-apply or remove PagerDuty tags from a CSV.

CSV columns: entity_type, entity_id, tag_label, action
- entity_type: users | teams | services | escalation_policies
- action: add | remove

Rows are grouped per entity and submitted via one atomic change_tags call each.
"""

from __future__ import annotations

import sys
from collections import defaultdict

from ..api import PDApiError, fetch_all, request
from ..bulkops import load_csv_rows
from ..cli import confirm, finish_bulk, init, standard_parser
from ..log import get_logger

log = get_logger("apply_tags")

VALID_ENTITY_TYPES = {"users", "teams", "services", "escalation_policies"}
VALID_ACTIONS = {"add", "remove"}


def build_parser():
    p = standard_parser("Bulk add/remove PagerDuty tags from a CSV.", write_guards=True)
    p.add_argument("csv_file", help="CSV: entity_type, entity_id, tag_label, action")
    return p


def load_rows(path) -> list[dict]:
    rows = load_csv_rows(
        path,
        {"entity_type", "entity_id", "tag_label", "action"},
        skip_if_missing=("entity_id", "tag_label"),
    )
    valid = []
    for row in rows:
        entity_type = row["entity_type"]
        action = row["action"].lower()
        if entity_type not in VALID_ENTITY_TYPES:
            log.warning("line %d: skipping unknown entity_type %r", row["_line"], entity_type)
            continue
        if action not in VALID_ACTIONS:
            log.warning("line %d: skipping unknown action %r", row["_line"], action)
            continue
        valid.append({**row, "action": action})
    return valid


def build_tag_index(token) -> dict:
    tags = fetch_all("tags", token, label="tags")
    return {t["label"]: t["id"] for t in tags if t.get("label") and t.get("id")}


def ensure_tag(token, label, index, dry_run):
    if label in index:
        return index[label]
    if dry_run:
        index[label] = f"<new:{label}>"
        print(f"[dry-run] would create tag {label!r}", file=sys.stderr)
        return index[label]
    try:
        result = request("tags", token, method="POST",
                         data={"tag": {"label": label, "type": "tag"}})
    except PDApiError as e:
        if e.is_auth_error:
            raise
        log.error("Failed to create tag %r: %s", label, e)
        return None
    tag_id = (result.get("tag") or {}).get("id")
    if tag_id:
        index[label] = tag_id
        log.info("Created tag %r (%s)", label, tag_id)
    return tag_id


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    rows = load_rows(args.csv_file)
    if not rows:
        log.info("No usable rows in CSV.")
        return 0

    grouped: dict = defaultdict(lambda: {"add": set(), "remove": set()})
    for row in rows:
        grouped[(row["entity_type"], row["entity_id"])][row["action"]].add(row["tag_label"])
    log.info("Loaded %d rows targeting %d entities.", len(rows), len(grouped))

    if not confirm(f"Apply tag changes to {len(grouped)} entities?",
                   assume_yes=args.yes, dry_run=args.dry_run):
        return 0

    tag_index = build_tag_index(token)
    succeeded = failed = 0
    for (entity_type, entity_id), changes in grouped.items():
        add_ids = [tid for label in sorted(changes["add"])
                   if (tid := ensure_tag(token, label, tag_index, args.dry_run))]
        remove_ids = []
        for label in sorted(changes["remove"]):
            if label not in tag_index:
                log.warning("%s/%s: cannot remove unknown tag %r; skipping.",
                            entity_type, entity_id, label)
                continue
            remove_ids.append(tag_index[label])
        if not add_ids and not remove_ids:
            continue
        if args.dry_run:
            print(f"[dry-run] {entity_type}/{entity_id}: +{len(add_ids)} -{len(remove_ids)} tags",
                  file=sys.stderr)
            succeeded += 1
            continue
        body = {
            "add": [{"id": t, "type": "tag_reference"} for t in add_ids],
            "remove": [{"id": t, "type": "tag_reference"} for t in remove_ids],
        }
        try:
            request(f"{entity_type}/{entity_id}/change_tags", token, method="POST", data=body)
            log.info("%s/%s: +%d -%d tags", entity_type, entity_id, len(add_ids), len(remove_ids))
            succeeded += 1
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("%s/%s: failed - %s", entity_type, entity_id, e)
            failed += 1

    return finish_bulk(succeeded, failed, dry_run=args.dry_run, label="entities")
