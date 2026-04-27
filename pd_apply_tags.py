#!/usr/bin/env python3
"""Bulk-apply or remove PagerDuty tags from a CSV.

CSV columns (header row required): entity_type, entity_id, tag_label, action

- entity_type: one of users, teams, services, escalation_policies
- entity_id: the PagerDuty ID of the entity
- tag_label: the tag string. Created if it does not already exist.
- action: 'add' or 'remove'

Rows are grouped per entity and submitted via /{entity_type}/{id}/change_tags
in one call per entity, which is the correct atomic shape for tag changes.
"""

import argparse
import csv
import sys
from collections import defaultdict

from pd_common import fetch_all, get_pd_api_token, make_api_request

VALID_ENTITY_TYPES = {"users", "teams", "services", "escalation_policies"}


def parse_arguments():
    parser = argparse.ArgumentParser(description="Bulk add/remove PagerDuty tags from a CSV.")
    parser.add_argument("csv_file", help="CSV with columns: entity_type, entity_id, tag_label, action")
    parser.add_argument("-t", "--token", help="PagerDuty API token")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changing tags.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip the confirmation prompt.")
    return parser.parse_args()


def load_rows(path):
    required = {"entity_type", "entity_id", "tag_label", "action"}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"Error: CSV missing required columns: {sorted(missing)}", file=sys.stderr)
            sys.exit(2)
        rows = []
        for line_no, row in enumerate(reader, start=2):
            if not row.get("entity_id") or not row.get("tag_label"):
                continue
            entity_type = row["entity_type"].strip()
            action = row["action"].strip().lower()
            if entity_type not in VALID_ENTITY_TYPES:
                print(
                    f"line {line_no}: skipping unknown entity_type '{entity_type}'",
                    file=sys.stderr,
                )
                continue
            if action not in {"add", "remove"}:
                print(f"line {line_no}: skipping unknown action '{action}'", file=sys.stderr)
                continue
            rows.append({
                "entity_type": entity_type,
                "entity_id": row["entity_id"].strip(),
                "tag_label": row["tag_label"].strip(),
                "action": action,
                "_line": line_no,
            })
        return rows


def build_tag_index(token):
    """Map tag label -> tag id for existing tags."""
    print("Fetching existing tags...", end="", flush=True)
    tags = fetch_all("tags", token, label="tags")
    return {t["label"]: t["id"] for t in tags if t.get("label") and t.get("id")}


def ensure_tag(token, label, index, dry_run):
    """Return the tag ID for `label`, creating the tag if needed."""
    if label in index:
        return index[label]
    if dry_run:
        print(f"[dry-run] would create tag '{label}'")
        index[label] = f"<new:{label}>"
        return index[label]
    result = make_api_request("tags", token, method="POST", data={"tag": {"label": label, "type": "tag"}})
    if not result or "tag" not in result:
        print(f"Failed to create tag '{label}'")
        return None
    tag_id = result["tag"]["id"]
    index[label] = tag_id
    print(f"Created tag '{label}' ({tag_id})")
    return tag_id


def apply_changes(token, entity_type, entity_id, add_ids, remove_ids, dry_run):
    body = {
        "add": [{"id": tid, "type": "tag_reference"} for tid in add_ids],
        "remove": [{"id": tid, "type": "tag_reference"} for tid in remove_ids],
    }
    if dry_run:
        print(
            f"[dry-run] {entity_type}/{entity_id}: +{len(add_ids)} tags, -{len(remove_ids)} tags"
        )
        return True
    result = make_api_request(
        f"{entity_type}/{entity_id}/change_tags",
        token,
        method="POST",
        data=body,
    )
    if result is None:
        print(f"{entity_type}/{entity_id}: failed")
        return False
    print(f"{entity_type}/{entity_id}: +{len(add_ids)} tags, -{len(remove_ids)} tags")
    return True


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token)
    rows = load_rows(args.csv_file)
    if not rows:
        print("No usable rows in CSV.")
        return

    # Group by (entity_type, entity_id)
    grouped = defaultdict(lambda: {"add": set(), "remove": set()})
    for row in rows:
        key = (row["entity_type"], row["entity_id"])
        grouped[key][row["action"]].add(row["tag_label"])

    print(f"Loaded {len(rows)} rows targeting {len(grouped)} entities.")

    if not args.dry_run and not args.yes:
        answer = input(f"Apply tag changes to {len(grouped)} entities? (y/n): ").strip().lower()
        if answer != "y":
            print("Operation cancelled.")
            return

    tag_index = build_tag_index(token)

    succeeded = 0
    failed = 0
    for (entity_type, entity_id), changes in grouped.items():
        add_ids = []
        for label in sorted(changes["add"]):
            tag_id = ensure_tag(token, label, tag_index, args.dry_run)
            if tag_id:
                add_ids.append(tag_id)
        remove_ids = []
        for label in sorted(changes["remove"]):
            if label not in tag_index:
                print(
                    f"{entity_type}/{entity_id}: cannot remove tag '{label}' (no such tag); skipping"
                )
                continue
            remove_ids.append(tag_index[label])
        if not add_ids and not remove_ids:
            continue
        if apply_changes(token, entity_type, entity_id, add_ids, remove_ids, args.dry_run):
            succeeded += 1
        else:
            failed += 1

    verb = "Would update" if args.dry_run else "Updated"
    print(f"\nSummary: {verb} {succeeded} entities, {failed} failed.")


if __name__ == "__main__":
    main()
