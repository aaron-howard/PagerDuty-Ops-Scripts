"""Export and diff/apply PagerDuty Event Orchestration router/global rules.

export_main: one JSON file per orchestration (metadata + router + global),
suitable for committing to git so rule changes show up as reviewable diffs.

apply_main: compares each JSON file to the live API and prints a unified
diff. --apply -y (plus a From email) pushes router/global orchestration_path
trees from disk to PagerDuty. Never creates/deletes orchestrations.
"""

from __future__ import annotations

import difflib
import json
import os
import re
import sys

from ..api import PDApiError, fetch_all, request
from ..cli import init, standard_parser
from ..config import get_from_email
from ..log import get_logger

log = get_logger("event_orchestration")


# ---------------- export ----------------

def build_export_parser():
    p = standard_parser("Export PagerDuty Event Orchestration rules to JSON files.")
    p.add_argument("-o", "--output-dir", default="event_orchestrations",
                   help="Directory for JSON files (default: event_orchestrations).")
    return p


def slugify(name) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", name or "").strip("-").lower()
    return slug or "unnamed"


def export_main(argv=None) -> int:
    args = build_export_parser().parse_args(argv)
    token = init(args)

    orchestrations = fetch_all("event_orchestrations", token, label="event_orchestrations")
    os.makedirs(args.output_dir, exist_ok=True)

    written = failed = 0
    for orch in orchestrations:
        orch_id = orch.get("id")
        if not orch_id:
            continue
        try:
            router = request(f"event_orchestrations/{orch_id}/router", token)
            global_rules = request(f"event_orchestrations/{orch_id}/global", token)
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("Failed to export %s: %s", orch_id, e)
            failed += 1
            continue
        payload = {
            "orchestration": orch,
            "router": router.get("orchestration_path"),
            "global": global_rules.get("orchestration_path"),
        }
        path = os.path.join(args.output_dir, f"{orch_id}__{slugify(orch.get('name'))}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.write("\n")
        written += 1
        log.info("Wrote %s", path)

    log.info("Exported %d orchestrations to %s/ (%d failed).", written, args.output_dir, failed)
    return 1 if failed else 0


# ---------------- diff / apply ----------------

def build_apply_parser():
    p = standard_parser(
        "Diff or apply Event Orchestration router/global from export JSON files."
    )
    p.add_argument("-i", "--input-dir", default="event_orchestrations",
                   help="Directory containing export JSON files.")
    p.add_argument("--apply", action="store_true",
                   help="Write changes to PagerDuty (requires -y and a From email).")
    p.add_argument("-y", "--yes", action="store_true", help="Acknowledge apply.")
    p.add_argument("--from-email",
                   help="PagerDuty 'From' header; defaults to PD_FROM_EMAIL.")
    return p


def stable_lines(obj) -> list[str]:
    return (json.dumps(obj, indent=2, sort_keys=True) if obj is not None else "null").splitlines()


def _diff(live, desired, orch_id, kind, filename) -> list[str]:
    return list(difflib.unified_diff(
        stable_lines(live), stable_lines(desired),
        fromfile=f"{orch_id}/{kind} (live)",
        tofile=f"{orch_id}/{kind} (file {filename})",
    ))


def apply_main(argv=None) -> int:
    args = build_apply_parser().parse_args(argv)
    token = init(args)

    if args.apply and not args.yes:
        print("Error: --apply requires -y/--yes.", file=sys.stderr)
        return 2
    from_email = get_from_email(args.from_email, required=args.apply) if args.apply else None
    extra_headers = {"From": from_email} if args.apply else None

    if not os.path.isdir(args.input_dir):
        print(f"Error: not a directory: {args.input_dir}", file=sys.stderr)
        return 2
    paths = [os.path.join(args.input_dir, n) for n in sorted(os.listdir(args.input_dir))
             if n.endswith(".json")]
    if not paths:
        log.warning("No .json files under %s", args.input_dir)
        return 0

    any_diff = False
    failures = 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, ValueError) as e:
            log.error("%s: failed to read JSON: %s", path, e)
            failures += 1
            continue

        orch = doc.get("orchestration") or {}
        orch_id = orch.get("id")
        if not orch_id:
            log.error("%s: missing orchestration.id", path)
            failures += 1
            continue

        try:
            live_router = request(f"event_orchestrations/{orch_id}/router", token).get(
                "orchestration_path")
            live_global = request(f"event_orchestrations/{orch_id}/global", token).get(
                "orchestration_path")
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("%s: GET failed for %s: %s", path, orch_id, e)
            failures += 1
            continue

        filename = os.path.basename(path)
        router_diff = _diff(live_router, doc.get("router"), orch_id, "router", filename)
        global_diff = _diff(live_global, doc.get("global"), orch_id, "global", filename)

        for d in (router_diff, global_diff):
            if d:
                any_diff = True
                print("\n".join(d))
                print()
        if not router_diff and not global_diff:
            log.info("%s (%s): in sync", filename, orch.get("name") or orch_id)
            continue
        if not args.apply:
            continue

        for kind, diff_lines, desired in (
            ("router", router_diff, doc.get("router")),
            ("global", global_diff, doc.get("global")),
        ):
            if not diff_lines:
                continue
            try:
                request(f"event_orchestrations/{orch_id}/{kind}", token, method="PUT",
                        data={"orchestration_path": desired}, extra_headers=extra_headers)
                log.info("%s: updated %s for %s", path, kind, orch_id)
            except PDApiError as e:
                if e.is_auth_error:
                    raise
                log.error("%s: PUT %s failed: %s", path, kind, e)
                failures += 1

    if failures:
        return 1
    if any_diff and not args.apply:
        log.info("Differences shown above. Re-run with --apply -y --from-email you@org.com "
                 "to push.")
    return 0
