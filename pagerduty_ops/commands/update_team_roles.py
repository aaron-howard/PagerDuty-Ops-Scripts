"""Update PagerDuty team member roles — interactively, or in bulk with --set-role."""

from __future__ import annotations

import sys

from ..api import PDApiError, request
from ..cli import confirm, finish_bulk, init, standard_parser
from ..config import get_team_id
from ..log import get_logger
from ..output import render_rows
from .team_members import fetch_members, member_row

log = get_logger("update_team_roles")

VALID_TEAM_ROLES = {"manager", "responder", "observer"}


def build_parser():
    p = standard_parser("Update PagerDuty team member roles.", write_guards=True)
    p.add_argument("--team-id", help="PagerDuty team ID (or set PD_TEAM_ID).")
    p.add_argument("--set-role", choices=sorted(VALID_TEAM_ROLES),
                   help="Non-interactive: set this role for ALL members "
                        "(review with --dry-run first).")
    return p


def set_member_role(token, team_id, user_id, role, dry_run=False) -> bool:
    if dry_run:
        return True
    try:
        request(f"teams/{team_id}/members/{user_id}", token, method="PUT",
                data={"role": role})
        return True
    except PDApiError as e:
        if e.is_auth_error:
            raise
        log.error("Failed to set role for %s: %s", user_id, e)
        return False


def prompt_role(name, current_role):
    while True:
        raw = input(
            f"{name} (current: {current_role}) — new role "
            f"[{'/'.join(sorted(VALID_TEAM_ROLES))}] or Enter to skip: "
        ).strip().lower()
        if not raw:
            return None
        if raw in VALID_TEAM_ROLES:
            return raw
        print(f"  Invalid role {raw!r}.", file=sys.stderr)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    team_id = get_team_id(args.team_id)

    members = fetch_members(token, team_id)
    rows = [member_row(m) for m in members]
    print(render_rows(rows, ["user_id", "type", "name", "role"], "table"), file=sys.stderr)
    log.info("%d members on team %s.", len(members), team_id)

    updated = failed = 0
    if args.set_role:
        targets = [m for m in members if m.get("role") != args.set_role]
        if not targets:
            log.info("All members already have role %r.", args.set_role)
            return 0
        if not confirm(f"Set {len(targets)} members to '{args.set_role}'?",
                       assume_yes=args.yes, dry_run=args.dry_run):
            return 0
        for m in targets:
            user = m.get("user", {})
            ok = set_member_role(token, team_id, user.get("id"), args.set_role, args.dry_run)
            verb = "[dry-run] would set" if args.dry_run else ("Set" if ok else "FAILED")
            print(f"{verb} {user.get('summary')} -> {args.set_role}", file=sys.stderr)
            updated, failed = updated + ok, failed + (not ok)
    else:
        if not sys.stdin.isatty():
            log.error("Interactive mode needs a TTY. Use --set-role for non-interactive runs.")
            return 2
        for m in members:
            user = m.get("user", {})
            new_role = prompt_role(user.get("summary", user.get("id", "?")), m.get("role", ""))
            if not new_role or new_role == m.get("role"):
                continue
            ok = set_member_role(token, team_id, user.get("id"), new_role, args.dry_run)
            verb = "[dry-run] would set" if args.dry_run else ("Set" if ok else "FAILED")
            print(f"{verb} {user.get('summary')} -> {new_role}", file=sys.stderr)
            updated, failed = updated + ok, failed + (not ok)

    return finish_bulk(updated, failed, dry_run=args.dry_run, label="members")
