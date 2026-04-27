#!/usr/bin/env python3
"""Bulk-update PagerDuty user roles.

Selects every user with --from-role and patches them to --to-role.
Use --dry-run to preview before applying.
"""

import argparse
import sys

from pd_common import fetch_all, get_pd_api_token, make_api_request

VALID_ROLES = {
    "admin",
    "limited_user",
    "observer",
    "owner",
    "read_only_user",
    "read_only_limited_user",
    "restricted_access",
    "user",
}


def parse_arguments():
    parser = argparse.ArgumentParser(description="Bulk-update PagerDuty user roles.")
    parser.add_argument("-t", "--token", help="PagerDuty API token")
    parser.add_argument(
        "--from-role",
        required=True,
        help="Only update users currently in this role (e.g. 'user').",
    )
    parser.add_argument(
        "--to-role",
        required=True,
        help="The role to assign (e.g. 'observer').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without making any updates.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    return parser.parse_args()


def update_user_role(token, user_id, new_role):
    result = make_api_request(
        f"users/{user_id}",
        token,
        method="PATCH",
        data={"user": {"role": new_role}},
    )
    return result is not None


def main():
    args = parse_arguments()

    if args.from_role == args.to_role:
        print("Error: --from-role and --to-role are identical; nothing to do.")
        sys.exit(2)
    for label, role in (("--from-role", args.from_role), ("--to-role", args.to_role)):
        if role not in VALID_ROLES:
            print(f"Warning: {label}='{role}' is not a recognized PagerDuty role. Proceeding anyway.")

    token = get_pd_api_token(args.token)
    users = fetch_all("users", token, label="users")
    targets = [u for u in users if u.get("role") == args.from_role]
    print(f"\n{len(targets)} users currently have role '{args.from_role}'.")

    if not targets:
        return

    if not args.dry_run and not args.yes:
        answer = input(
            f"Update {len(targets)} users from '{args.from_role}' to '{args.to_role}'? (y/n): "
        ).strip().lower()
        if answer != "y":
            print("Operation cancelled.")
            return

    updated = 0
    failed = 0
    for user in targets:
        user_id = user.get("id")
        name = user.get("name") or user.get("email") or user_id
        if args.dry_run:
            print(f"Would update {name} ({user_id}) -> '{args.to_role}'")
            updated += 1
            continue
        if update_user_role(token, user_id, args.to_role):
            print(f"Updated {name} ({user_id}) -> '{args.to_role}'")
            updated += 1
        else:
            print(f"Failed to update {name} ({user_id})")
            failed += 1

    verb = "Would update" if args.dry_run else "Updated"
    print(f"\nSummary: {verb} {updated} users, {failed} failed.")


if __name__ == "__main__":
    main()
