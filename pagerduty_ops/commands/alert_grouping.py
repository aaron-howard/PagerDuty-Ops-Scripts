"""Manage PagerDuty Alert Grouping Settings (list, attach from CSV, JSON CRUD)."""

from __future__ import annotations

import json
import sys

from ..api import fetch_all, request
from ..bulkops import load_csv_rows
from ..cli import confirm, init, standard_parser
from ..log import get_logger
from ..output import write_payload

log = get_logger("alert_grouping")

ENDPOINT = "alert_grouping_settings"


def build_parser():
    p = standard_parser("Manage PagerDuty Alert Grouping Settings.", write_guards=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true", help="List all settings.")
    mode.add_argument("--attach", metavar="NAME",
                      help="Add services from --services-csv to the uniquely matched setting.")
    mode.add_argument("--get-json", metavar="ID", help="Print one setting as JSON.")
    mode.add_argument("--create-json", metavar="FILE", help="POST a new setting from JSON.")
    mode.add_argument("--update-json", metavar="FILE", help="PUT a setting (JSON must include id).")
    mode.add_argument("--delete", metavar="ID", help="Delete a setting by id.")
    p.add_argument("--services-csv", help="CSV with a 'service_id' column (for --attach).")
    p.add_argument("-o", "--output", metavar="FILE",
                   help="With --get-json, write JSON here instead of stdout.")
    return p


def _service_refs(setting) -> list[dict]:
    out = []
    for svc in setting.get("services") or []:
        sid = svc if isinstance(svc, str) else svc.get("id")
        if sid:
            out.append({"id": sid, "type": "service_reference"})
    return out


def find_setting(token, name_substring) -> dict:
    settings = fetch_all(ENDPOINT, token, label=ENDPOINT)
    needle = name_substring.lower()
    matches = [s for s in settings if needle in (s.get("name") or "").lower()]
    if not matches:
        print(f"Error: no alert grouping setting matches {name_substring!r}.", file=sys.stderr)
        raise SystemExit(2)
    if len(matches) > 1:
        print(f"Error: {name_substring!r} matches {len(matches)} settings:", file=sys.stderr)
        for m in matches:
            print(f"  {m.get('id')}: {m.get('name')}", file=sys.stderr)
        raise SystemExit(2)
    return matches[0]


def list_settings(token) -> int:
    settings = fetch_all(ENDPOINT, token, label=ENDPOINT)
    for s in settings:
        services = s.get("services") or []
        names = ", ".join((svc.get("summary") or svc.get("id")) for svc in services) or "(none)"
        print(f"{s.get('id')}  {s.get('name')}  type={s.get('type')}  services=[{names}]")
    log.info("Total: %d alert grouping settings.", len(settings))
    return 0


def attach(token, args) -> int:
    if not args.services_csv:
        print("Error: --attach requires --services-csv.", file=sys.stderr)
        raise SystemExit(2)
    setting = find_setting(token, args.attach)
    rows = load_csv_rows(args.services_csv, {"service_id"}, skip_if_missing=("service_id",))
    new_ids = [r["service_id"] for r in rows]
    existing_ids = {svc.get("id") for svc in setting.get("services") or []}
    to_add = [sid for sid in new_ids if sid not in existing_ids]
    log.info("Setting %r covers %d services; %d new to add.",
             setting["name"], len(existing_ids), len(to_add))
    if not to_add:
        return 0
    if args.dry_run:
        for sid in to_add:
            print(f"[dry-run] would add service {sid}", file=sys.stderr)
        return 0
    if not confirm(f"Add {len(to_add)} services to '{setting['name']}'?",
                   assume_yes=args.yes):
        return 0
    merged = [{"id": sid, "type": "service_reference"} for sid in existing_ids | set(new_ids)]
    body = {
        "alert_grouping_setting": {
            "name": setting["name"],
            "type": setting["type"],
            "config": setting.get("config") or {},
            "services": merged,
        }
    }
    request(f"{ENDPOINT}/{setting['id']}", token, method="PUT", data=body)
    log.info("Updated. Setting now covers %d services.", len(merged))
    return 0


def get_json(token, args) -> int:
    data = request(f"{ENDPOINT}/{args.get_json}", token)
    text = json.dumps(data.get("alert_grouping_setting", data), indent=2, sort_keys=True) + "\n"
    write_payload(text, args.output)
    return 0


def _load_setting_body(path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        print(f"Error: cannot read JSON {path}: {e}", file=sys.stderr)
        raise SystemExit(2) from e
    return raw.get("alert_grouping_setting", raw)


def create_from_json(token, args) -> int:
    body_inner = _load_setting_body(args.create_json)
    body_inner.pop("id", None)
    for field in ("name", "type", "services"):
        if field not in body_inner:
            print(f"Error: JSON must include {field}.", file=sys.stderr)
            raise SystemExit(2)
    body_inner["services"] = _service_refs(body_inner)
    payload = {"alert_grouping_setting": body_inner}
    if args.dry_run:
        print("[dry-run] would POST /alert_grouping_settings with:", file=sys.stderr)
        print(json.dumps(payload, indent=2), file=sys.stderr)
        return 0
    if not confirm("Create this alert grouping setting?", assume_yes=args.yes):
        return 0
    result = request(ENDPOINT, token, method="POST", data=payload)
    log.info("Created alert grouping setting id=%s",
             (result.get("alert_grouping_setting") or {}).get("id"))
    return 0


def update_from_json(token, args) -> int:
    body_inner = _load_setting_body(args.update_json)
    sid = body_inner.get("id")
    if not sid:
        print("Error: JSON must include id for update.", file=sys.stderr)
        raise SystemExit(2)
    body_inner["services"] = _service_refs(body_inner)
    payload = {"alert_grouping_setting": body_inner}
    if args.dry_run:
        print(f"[dry-run] would PUT /{ENDPOINT}/{sid} with:", file=sys.stderr)
        print(json.dumps(payload, indent=2), file=sys.stderr)
        return 0
    if not confirm(f"Update alert grouping setting {sid}?", assume_yes=args.yes):
        return 0
    request(f"{ENDPOINT}/{sid}", token, method="PUT", data=payload)
    log.info("Updated alert grouping setting id=%s", sid)
    return 0


def delete_setting(token, args) -> int:
    sid = args.delete
    if args.dry_run:
        print(f"[dry-run] would DELETE /{ENDPOINT}/{sid}", file=sys.stderr)
        return 0
    if not confirm(f"Delete alert grouping setting {sid}?", assume_yes=args.yes):
        return 0
    request(f"{ENDPOINT}/{sid}", token, method="DELETE")
    log.info("Deleted %s.", sid)
    return 0


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    if args.list:
        return list_settings(token)
    if args.attach:
        return attach(token, args)
    if args.get_json:
        return get_json(token, args)
    if args.create_json:
        return create_from_json(token, args)
    if args.update_json:
        return update_from_json(token, args)
    return delete_setting(token, args)
