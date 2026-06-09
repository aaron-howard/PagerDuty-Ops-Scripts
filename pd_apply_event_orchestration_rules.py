#!/usr/bin/env python3
"""Apply Event Orchestration router/global rules from JSON files (git-export format).

Reads the same layout written by pd_event_orchestration_rules.py:

    {"orchestration": {...}, "router": <orchestration_path>|null, "global": <orchestration_path>|null}

Safety model:
  * Step 1 — diff only: run without --apply (optionally pass --dry-run; same behavior).
    Fetches live router + global, prints unified diffs — no writes.
  * Step 2 — apply: --apply must be used with -y/--yes (no interactive apply).
    PUTs only paths that differ. Incompatible with --dry-run.
  * Never use --apply -y until Step 1 output has been reviewed (ideally in CI from a PR).

PUTs use the same bodies as the REST API: {"orchestration_path": <object>}.
"""

import argparse
import difflib
import json
import os
import sys

from pd_common import add_token_arguments, get_pd_api_token, make_api_request

# Keys removed only for diff comparison (live payloads include timestamps/version noise).
_STRIP_FOR_DIFF = frozenset(
    {
        "version",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    }
)


def parse_arguments():
    p = argparse.ArgumentParser(
        description=(
            "Diff or apply Event Orchestration router/global rules from a directory of JSON files "
            "(export format from pd_event_orchestration_rules.py)."
        )
    )
    add_token_arguments(p)
    p.add_argument(
        "-d",
        "--input-dir",
        required=True,
        help="Directory containing *.json exports (one orchestration per file).",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to PagerDuty (requires -y/--yes after a diff-only run). Mutually exclusive with --dry-run.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Explicit diff-only run (same as default). Cannot be combined with --apply.",
    )
    p.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Required with --apply: affirms you reviewed a prior diff-only run.",
    )
    return p.parse_args()


def _strip_for_diff(obj):
    if isinstance(obj, dict):
        return {
            k: _strip_for_diff(v)
            for k, v in obj.items()
            if k not in _STRIP_FOR_DIFF
        }
    if isinstance(obj, list):
        return [_strip_for_diff(x) for x in obj]
    return obj


def _canonical_json(obj):
    return json.dumps(_strip_for_diff(obj), sort_keys=True, indent=2).splitlines(keepends=True)


def _orch_id_from_filename(path):
    base = os.path.basename(path)
    if "__" in base:
        return base.split("__", 1)[0]
    return None


def _load_export(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_live_path(token, orch_id, subpath):
    """Return orchestration_path dict or None if missing/404."""
    data = make_api_request(f"event_orchestrations/{orch_id}/{subpath}", token)
    if not data:
        return None
    return data.get("orchestration_path")


def _print_diff(label, path, live, desired):
    live_lines = _canonical_json(live if live is not None else {})
    want_lines = _canonical_json(desired if desired is not None else {})
    if live_lines == want_lines:
        return False
    print(f"\n--- {label} ({os.path.basename(path)}) ---", file=sys.stderr)
    for line in difflib.unified_diff(
        live_lines,
        want_lines,
        fromfile=f"live/{label}",
        tofile=f"file/{label}",
        lineterm="",
    ):
        print(line, file=sys.stderr)
    return True


def _put_path(token, orch_id, subpath, orchestration_path):
    body = {"orchestration_path": orchestration_path}
    return make_api_request(
        f"event_orchestrations/{orch_id}/{subpath}",
        token,
        method="PUT",
        data=body,
    )


def _process_file(token, path, *, apply_writes):
    data = _load_export(path)
    orch = data.get("orchestration") or {}
    orch_id = orch.get("id") or _orch_id_from_filename(path)
    if not orch_id:
        print(f"Error: could not determine orchestration id for {path}", file=sys.stderr)
        return 2

    fn_id = _orch_id_from_filename(path)
    if fn_id and fn_id != orch_id:
        print(
            f"Warning: filename id {fn_id!r} != orchestration.id {orch_id!r} in {path}",
            file=sys.stderr,
        )

    router_desired = data.get("router")
    global_desired = data.get("global")

    live_router = _get_live_path(token, orch_id, "router")
    live_global = _get_live_path(token, orch_id, "global")

    router_diff = (
        _print_diff("router", path, live_router, router_desired)
        if router_desired is not None
        else False
    )
    global_diff = (
        _print_diff("global", path, live_global, global_desired)
        if global_desired is not None
        else False
    )
    changed = router_diff or global_diff

    if not apply_writes:
        if not changed:
            print(f"OK (no diff): {path}", file=sys.stderr)
        return 0

    if not changed:
        print(f"Skip apply (no diff): {path}", file=sys.stderr)
        return 0

    ok = True
    if router_desired is not None and router_diff:
        r = _put_path(token, orch_id, "router", router_desired)
        if r is None:
            print(f"PUT router failed for {orch_id}", file=sys.stderr)
            ok = False
        else:
            print(f"Updated router for {orch_id}", file=sys.stderr)
    if ok and global_desired is not None and global_diff:
        r = _put_path(token, orch_id, "global", global_desired)
        if r is None:
            print(f"PUT global failed for {orch_id}", file=sys.stderr)
            ok = False
        else:
            print(f"Updated global for {orch_id}", file=sys.stderr)
    return 0 if ok else 1


def main():
    args = parse_arguments()
    if args.apply and args.dry_run:
        print("Error: use either --apply or --dry-run, not both.", file=sys.stderr)
        sys.exit(2)
    if args.apply and not args.yes:
        print(
            "Error: --apply requires -y/--yes. Run a diff first (omit --apply, or use --dry-run), "
            "review unified diffs on stderr, then re-run with --apply -y.",
            file=sys.stderr,
        )
        sys.exit(2)

    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    input_dir = args.input_dir
    if not os.path.isdir(input_dir):
        print(f"Error: not a directory: {input_dir}", file=sys.stderr)
        sys.exit(2)

    json_files = sorted(
        f for f in os.listdir(input_dir) if f.endswith(".json") and not f.startswith(".")
    )
    if not json_files:
        print(f"No .json files in {input_dir}", file=sys.stderr)
        sys.exit(2)

    apply_writes = bool(args.apply)
    if apply_writes:
        print("Applying changes (--apply -y): writing only paths that differed in diff.", file=sys.stderr)

    exit_code = 0
    for name in json_files:
        path = os.path.join(input_dir, name)
        rc = _process_file(token, path, apply_writes=apply_writes)
        if rc > exit_code:
            exit_code = rc

    if not apply_writes:
        print(
            "\nThis was a diff-only run (no writes). "
            "Review output above, then use --apply -y after verification.",
            file=sys.stderr,
        )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
