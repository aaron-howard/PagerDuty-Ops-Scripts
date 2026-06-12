"""Interactively remove users from a PagerDuty team.

For each member: walk through removal from schedule layers, escalation policy
rule targets, and finally the team itself. Fully paginated (the previous
version silently truncated members/schedules/policies at the API default of
25 — dangerous, since a user could be removed from the team while still on an
unseen schedule). --dry-run previews every API call.
"""

from __future__ import annotations

import sys

from ..api import PDApiError, paginate, request
from ..cli import init, standard_parser
from ..config import get_team_id
from ..log import get_logger
from ..output import render_rows

log = get_logger("remove_team_members")


def build_parser():
    p = standard_parser("Interactively remove users from a PagerDuty team.")
    p.add_argument("--team-id", help="PagerDuty team ID (or set PD_TEAM_ID).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would be done without modifying anything.")
    return p


def get_schedule(token, schedule_id) -> dict:
    return request(f"schedules/{schedule_id}", token).get("schedule", {})


def get_policy(token, policy_id) -> dict:
    return request(f"escalation_policies/{policy_id}", token).get("escalation_policy", {})


def remove_user_from_schedule(token, schedule_id, user_id, user_name, dry_run=False) -> bool:
    schedule = get_schedule(token, schedule_id)
    schedule_name = schedule.get("summary", "Unknown Schedule")
    modified = False
    for idx, layer in enumerate(schedule.get("schedule_layers") or []):
        users = layer.get("users")
        if users and any(u.get("id") == user_id for u in users):
            layer["users"] = [u for u in users if u.get("id") != user_id]
            modified = True
            log.info("Removing %s from layer %d in schedule %r", user_name, idx + 1, schedule_name)
    if not modified:
        log.info("%s not found in any layer of schedule %r", user_name, schedule_name)
        return False
    if dry_run:
        print(f"[dry-run] would update schedule {schedule_name!r} to remove {user_name}",
              file=sys.stderr)
        return True
    try:
        request(f"schedules/{schedule_id}", token, method="PUT", data={
            "schedule": {
                "name": schedule.get("name"),
                "schedule_layers": schedule.get("schedule_layers", []),
            }
        })
        log.info("Removed %s from schedule %r", user_name, schedule_name)
        return True
    except PDApiError as e:
        if e.is_auth_error:
            raise
        log.error("Failed to update schedule %r: %s", schedule_name, e)
        return False


def remove_user_from_policy(token, policy_id, user_id, user_name, *, policy=None,
                            dry_run=False) -> bool:
    policy = policy or get_policy(token, policy_id)
    policy_name = policy.get("summary", "Unknown Policy")
    modified = False
    for idx, rule in enumerate(policy.get("escalation_rules") or []):
        targets = rule.get("targets")
        if not targets:
            continue
        kept = [t for t in targets if not (t.get("type") == "user" and t.get("id") == user_id)]
        if len(kept) < len(targets):
            rule["targets"] = kept
            modified = True
            log.info("Removing %s from rule %d in policy %r", user_name, idx + 1, policy_name)
    if not modified:
        log.info("%s not found in any rule of policy %r", user_name, policy_name)
        return False
    if dry_run:
        print(f"[dry-run] would update policy {policy_name!r} to remove {user_name}",
              file=sys.stderr)
        return True
    try:
        request(f"escalation_policies/{policy_id}", token, method="PUT", data={
            "escalation_policy": {
                "name": policy.get("name"),
                "escalation_rules": policy.get("escalation_rules", []),
            }
        })
        log.info("Removed %s from policy %r", user_name, policy_name)
        return True
    except PDApiError as e:
        if e.is_auth_error:
            raise
        log.error("Failed to update policy %r: %s", policy_name, e)
        return False


def build_assignment_maps(token, team_id):
    """user_id -> [schedule refs], user_id -> [policy refs]; fully paginated."""
    schedules = list(paginate("schedules", token, params={"team_ids[]": [team_id]}))
    policies = list(paginate("escalation_policies", token, params={"team_ids[]": [team_id]}))

    user_schedules: dict = {}
    for schedule in schedules:
        sid = schedule.get("id")
        sname = schedule.get("summary", "Unknown")
        for user in paginate(f"schedules/{sid}/users", token, items_key="users"):
            user_schedules.setdefault(user.get("id"), []).append({"id": sid, "name": sname})

    user_policies: dict = {}
    policy_details: dict = {}
    for policy in policies:
        pid = policy.get("id")
        pname = policy.get("summary", "Unknown")
        detail = get_policy(token, pid)
        policy_details[pid] = detail
        for rule in detail.get("escalation_rules", []):
            for target in rule.get("targets", []):
                if target.get("type") == "user":
                    bucket = user_policies.setdefault(target.get("id"), [])
                    if not any(p["id"] == pid for p in bucket):
                        bucket.append({"id": pid, "name": pname})
    return user_schedules, user_policies, policy_details


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    team_id = get_team_id(args.team_id)
    dry_run = args.dry_run

    if not sys.stdin.isatty() and not dry_run:
        log.error("This command is interactive and needs a TTY (or use --dry-run).")
        return 2
    if dry_run:
        log.info("[dry-run] No schedules, policies, or memberships will be modified.")

    members = list(paginate(f"teams/{team_id}/members", token, items_key="members"))
    user_schedules, user_policies, policy_details = build_assignment_maps(token, team_id)

    rows = []
    for idx, member in enumerate(members):
        user = member.get("user", {})
        uid = user.get("id", "")
        rows.append({
            "#": idx,
            "user_id": uid,
            "name": user.get("summary", ""),
            "on_schedule": ", ".join(s["name"] for s in user_schedules.get(uid, [])) or "No",
            "in_policy": ", ".join(p["name"] for p in user_policies.get(uid, [])) or "No",
        })
    print("\n=== Team Members and Their Assignments ===", file=sys.stderr)
    print(render_rows(rows, ["#", "user_id", "name", "on_schedule", "in_policy"], "table"),
          file=sys.stderr)

    failures = 0
    for member in members:
        user = member.get("user", {})
        uid = user.get("id", "")
        name = user.get("summary", "")
        print(f"\n--- Processing {name} ---", file=sys.stderr)

        if sys.stdin.isatty():
            if input(f"Remove {name} from team? (y/N): ").strip().lower() != "y":
                print(f"Skipped {name}.", file=sys.stderr)
                continue
        else:  # dry-run on non-TTY: preview everyone
            print(f"[dry-run] previewing removal of {name}", file=sys.stderr)

        for schedule in user_schedules.get(uid, []):
            if not sys.stdin.isatty() or input(
                f"Remove {name} from schedule '{schedule['name']}'? (y/N): "
            ).strip().lower() == "y":
                remove_user_from_schedule(token, schedule["id"], uid, name, dry_run=dry_run)

        for policy in user_policies.get(uid, []):
            if not sys.stdin.isatty() or input(
                f"Remove {name} from escalation policy '{policy['name']}'? (y/N): "
            ).strip().lower() == "y":
                remove_user_from_policy(token, policy["id"], uid, name,
                                        policy=policy_details.get(policy["id"]),
                                        dry_run=dry_run)

        if dry_run:
            print(f"[dry-run] would DELETE /teams/{team_id}/members/{uid} for {name}",
                  file=sys.stderr)
            continue
        try:
            request(f"teams/{team_id}/members/{uid}", token, method="DELETE")
            log.info("Removed %s from team.", name)
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("Failed to remove %s from team: %s", name, e)
            failures += 1

    log.info("Done. All requested user removals processed (%d failures).", failures)
    return 1 if failures else 0
