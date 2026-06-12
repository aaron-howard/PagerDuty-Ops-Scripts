"""Bulk-update PagerDuty user roles: everyone in --from-role moves to --to-role."""

from __future__ import annotations

import sys

from ..api import PDApiError, fetch_all, request
from ..cli import confirm, finish_bulk, init, standard_parser
from ..log import get_logger

log = get_logger("patch_role")

VALID_ROLES = {
    "admin", "limited_user", "observer", "owner", "read_only_user",
    "read_only_limited_user", "restricted_access", "user",
}


def build_parser():
    p = standard_parser("Bulk-update PagerDuty user roles.", write_guards=True)
    p.add_argument("--from-role", required=True,
                   help="Only update users currently in this role. One of: "
                        + ", ".join(sorted(VALID_ROLES)))
    p.add_argument("--to-role", required=True, help="The role to assign.")
    return p


def validate_roles(from_role, to_role) -> None:
    if from_role == to_role:
        print("Error: --from-role and --to-role are identical; nothing to do.", file=sys.stderr)
        raise SystemExit(2)
    for label, role in (("--from-role", from_role), ("--to-role", to_role)):
        if role not in VALID_ROLES:
            print(f"Error: {label}={role!r} is not a valid PagerDuty role. "
                  f"Valid: {', '.join(sorted(VALID_ROLES))}", file=sys.stderr)
            raise SystemExit(2)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    validate_roles(args.from_role, args.to_role)
    token = init(args)

    users = fetch_all("users", token, label="users")
    targets = [u for u in users if u.get("role") == args.from_role]
    log.info("%d users currently have role %r.", len(targets), args.from_role)
    if not targets:
        return 0

    if not confirm(
        f"Update {len(targets)} users from '{args.from_role}' to '{args.to_role}'?",
        assume_yes=args.yes, dry_run=args.dry_run,
    ):
        return 0

    updated = failed = 0
    for user in targets:
        user_id = user.get("id")
        name = user.get("name") or user.get("email") or user_id
        if args.dry_run:
            print(f"[dry-run] would update {name} ({user_id}) -> {args.to_role!r}",
                  file=sys.stderr)
            updated += 1
            continue
        try:
            request(f"users/{user_id}", token, method="PATCH",
                    data={"user": {"role": args.to_role}})
            log.info("Updated %s (%s) -> %r", name, user_id, args.to_role)
            updated += 1
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("Failed to update %s (%s): %s", name, user_id, e)
            failed += 1

    return finish_bulk(updated, failed, dry_run=args.dry_run, label="users")
