#!/usr/bin/env python3
"""Interactively (or in bulk) update PagerDuty team member roles.

Rewrite of pd_update_team_roles.py fixing:
- module-level execution (now main()-guarded and importable/testable)
- missing pagination on /teams/{id}/members (API default limit is 25)
- no role validation (any typo was PATCHed to the API)
- no --dry-run, no exit codes, raw response.text echoed on error
"""

import argparse
import sys

from tabulate import tabulate

from pd_common import (
    add_token_arguments,
    get_pd_api_token,
    get_pd_team_id,
    make_api_request,
    paginate,
)

VALID_TEAM_ROLES = {"manager", "responder", "observer"}


def parse_arguments():
    parser = argparse.ArgumentParser(description="Update PagerDuty team member roles.")
    add_token_arguments(parser)
    parser.add_argument("--team-id", help="PagerDuty team ID (or set PD_TEAM_ID)")
    parser.add_argument(
        "--set-role",
        choices=sorted(VALID_TEAM_ROLES),
        help="Non-interactive: set this role for ALL members (use with --dry-run first).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing.")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation (bulk mode).")
    return parser.parse_args()


def fetch_members(token, team_id):
    return list(paginate(f"teams/{team_id}/members", token, items_key="members"))


def set_member_role(token, team_id, user_id, role, dry_run=False):
    if dry_run:
        return True
    result = make_api_request(
        f"teams/{team_id}/members/{user_id}", token, method="PUT", data={"role": role}
    )
    return result is not None


def prompt_role(user_summary, current_role):
    while True:
        raw = input(
            f"{user_summary} (current: {current_role}) — new role "
            f"[{'/'.join(sorted(VALID_TEAM_ROLES))}] or Enter to skip: "
        ).strip().lower()
        if not raw:
            return None
        if raw in VALID_TEAM_ROLES:
            return raw
        print(f"  Invalid role {raw!r}.", file=sys.stderr)


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    team_id = get_pd_team_id(args.team_id)

    members = fetch_members(token, team_id)
    rows = [
        [i, m.get("user", {}).get("id", ""), m.get("user", {}).get("summary", ""), m.get("role", "")]
        for i, m in enumerate(members)
    ]
    print(tabulate(rows, headers=["#", "ID", "Name", "Role"], tablefmt="github"))
    print(f"\n{len(members)} members on team {team_id}.")

    updated = failed = 0
    if args.set_role:
        targets = [m for m in members if m.get("role") != args.set_role]
        if not targets:
            print("All members already have that role.")
            return 0
        if not args.dry_run and not args.yes:
            if input(f"Set {len(targets)} members to '{args.set_role}'? (y/n): ").strip().lower() != "y":
                print("Cancelled.")
                return 0
        for m in targets:
            user = m.get("user", {})
            ok = set_member_role(token, team_id, user.get("id"), args.set_role, args.dry_run)
            verb = "Would set" if args.dry_run else ("Set" if ok else "FAILED")
            print(f"{verb} {user.get('summary')} -> {args.set_role}")
            updated, failed = updated + ok, failed + (not ok)
    else:
        for m in members:
            user = m.get("user", {})
            new_role = prompt_role(user.get("summary", user.get("id", "?")), m.get("role", ""))
            if not new_role or new_role == m.get("role"):
                continue
            ok = set_member_role(token, team_id, user.get("id"), new_role, args.dry_run)
            verb = "Would set" if args.dry_run else ("Set" if ok else "FAILED")
            print(f"{verb} {user.get('summary')} -> {new_role}")
            updated, failed = updated + ok, failed + (not ok)

    print(f"\nSummary: {'would update' if args.dry_run else 'updated'} {updated}, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
