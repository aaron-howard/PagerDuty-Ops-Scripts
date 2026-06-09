#!/usr/bin/env python3
"""Apply PagerDuty Event Orchestration router/global JSON exported by pd_event_orchestration_rules.py.

Compares each JSON file under the input directory to the live API (GET router and
GET global). By default prints a unified diff and does not write. Use ``--apply``
together with ``-y`` and ``--from-email`` (or ``PD_FROM_EMAIL``) to push router and
global ``orchestration_path`` values from disk to PagerDuty.

This script does not create or delete orchestrations and does not modify the
``orchestration`` metadata object—only the router and global rule trees.
"""

import argparse
import difflib
import json
import os
import sys

from pd_common import add_token_arguments, get_pd_api_token, make_api_request


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Diff or apply Event Orchestration router/global from export JSON files."
    )
    add_token_arguments(parser)
    parser.add_argument(
        "-i",
        "--input-dir",
        default="event_orchestrations",
        help="Directory containing export JSON files (default: event_orchestrations).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to PagerDuty (requires -y and From email).",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Acknowledge apply (required with --apply).",
    )
    parser.add_argument(
        "--from-email",
        help="PagerDuty 'From' header (valid user email). Defaults to PD_FROM_EMAIL when set.",
    )
    return parser.parse_args()


def stable_lines(obj):
    text = json.dumps(obj, indent=2, sort_keys=True) if obj is not None else "null"
    return text.splitlines()


def load_export_files(input_dir):
    if not os.path.isdir(input_dir):
        print(f"Error: not a directory: {input_dir}", file=sys.stderr)
        sys.exit(2)
    paths = []
    for name in sorted(os.listdir(input_dir)):
        if not name.endswith(".json"):
            continue
        paths.append(os.path.join(input_dir, name))
    return paths


def read_export(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)

    if args.apply and not args.yes:
        print("Error: --apply requires -y/--yes.", file=sys.stderr)
        sys.exit(2)

    from_email = args.from_email or os.environ.get("PD_FROM_EMAIL")
    if args.apply and not from_email:
        print(
            "Error: --apply requires --from-email or PD_FROM_EMAIL (PagerDuty From header).",
            file=sys.stderr,
        )
        sys.exit(2)

    extra_headers = {"From": from_email} if args.apply else None

    paths = load_export_files(args.input_dir)
    if not paths:
        print(f"No .json files under {args.input_dir}", file=sys.stderr)
        sys.exit(0)

    any_diff = False
    failures = 0

    for path in paths:
        try:
            doc = read_export(path)
        except (OSError, ValueError) as e:
            print(f"{path}: failed to read JSON: {e}", file=sys.stderr)
            failures += 1
            continue

        orch = doc.get("orchestration") or {}
        orch_id = orch.get("id")
        orch_name = orch.get("name") or orch_id
        if not orch_id:
            print(f"{path}: missing orchestration.id", file=sys.stderr)
            failures += 1
            continue

        desired_router = doc.get("router")
        desired_global = doc.get("global")

        router_resp = make_api_request(f"event_orchestrations/{orch_id}/router", token)
        global_resp = make_api_request(f"event_orchestrations/{orch_id}/global", token)
        if router_resp is None:
            print(f"{path}: GET router failed for {orch_id}", file=sys.stderr)
            failures += 1
            continue
        if global_resp is None:
            print(f"{path}: GET global failed for {orch_id}", file=sys.stderr)
            failures += 1
            continue
        live_router = router_resp.get("orchestration_path")
        live_global = global_resp.get("orchestration_path")

        router_diff = list(
            difflib.unified_diff(
                stable_lines(live_router),
                stable_lines(desired_router),
                fromfile=f"{orch_id}/router (live)",
                tofile=f"{orch_id}/router (file {os.path.basename(path)})",
            )
        )
        global_diff = list(
            difflib.unified_diff(
                stable_lines(live_global),
                stable_lines(desired_global),
                fromfile=f"{orch_id}/global (live)",
                tofile=f"{orch_id}/global (file {os.path.basename(path)})",
            )
        )

        if router_diff:
            any_diff = True
            print("\n".join(router_diff))
            print()
        if global_diff:
            any_diff = True
            print("\n".join(global_diff))
            print()

        if not router_diff and not global_diff:
            print(f"{os.path.basename(path)} ({orch_name}): in sync", file=sys.stderr)
            continue

        if not args.apply:
            continue

        if router_diff:
            body = {"orchestration_path": desired_router}
            out = make_api_request(
                f"event_orchestrations/{orch_id}/router",
                token,
                method="PUT",
                data=body,
                extra_headers=extra_headers,
            )
            if not out:
                print(f"{path}: PUT router failed", file=sys.stderr)
                failures += 1
            else:
                print(f"{path}: updated router for {orch_id}", file=sys.stderr)

        if global_diff:
            body = {"orchestration_path": desired_global}
            out = make_api_request(
                f"event_orchestrations/{orch_id}/global",
                token,
                method="PUT",
                data=body,
                extra_headers=extra_headers,
            )
            if not out:
                print(f"{path}: PUT global failed", file=sys.stderr)
                failures += 1
            else:
                print(f"{path}: updated global for {orch_id}", file=sys.stderr)

    if failures:
        sys.exit(1)
    if any_diff and not args.apply:
        print(
            "\nDifferences shown above. Re-run with --apply -y --from-email you@org.com to push.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
