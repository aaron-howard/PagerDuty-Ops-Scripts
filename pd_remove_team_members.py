#!/usr/bin/env python3
"""Interactively remove users from a PagerDuty team.

For each member, walk through removal from schedule layers, escalation policy
rule targets, and finally the team itself. Use --dry-run to preview every API
call without mutating PagerDuty state.
"""

import argparse

import requests
from tabulate import tabulate

from pd_common import build_headers, get_pd_api_token, get_pd_team_id


def parse_arguments():
    parser = argparse.ArgumentParser(description="Interactively remove users from a PagerDuty team.")
    parser.add_argument("-t", "--token", help="PagerDuty API token")
    parser.add_argument("--team-id", help="PagerDuty team ID")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without modifying schedules, policies, or team membership.",
    )
    return parser.parse_args()


def get_schedule_details(headers, schedule_id):
    url = f"https://api.pagerduty.com/schedules/{schedule_id}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("schedule", {})


def remove_user_from_schedule(headers, schedule_id, user_id, user_name, dry_run=False):
    schedule = get_schedule_details(headers, schedule_id)
    schedule_name = schedule.get("summary", "Unknown Schedule")

    modified = False
    if "schedule_layers" in schedule:
        for idx, layer in enumerate(schedule.get("schedule_layers", [])):
            if "users" not in layer:
                continue
            user_in_layer = any(u.get("id") == user_id for u in layer["users"])
            if user_in_layer:
                layer["users"] = [u for u in layer["users"] if u.get("id") != user_id]
                modified = True
                print(f"Removing {user_name} from layer {idx+1} in schedule '{schedule_name}'")

    if not modified:
        print(f"User {user_name} not found in any layers of schedule '{schedule_name}'")
        return False

    if dry_run:
        print(f"[dry-run] Would update schedule '{schedule_name}' to remove {user_name}")
        return True

    update_url = f"https://api.pagerduty.com/schedules/{schedule_id}"
    update_data = {
        "schedule": {
            "name": schedule.get("name"),
            "schedule_layers": schedule.get("schedule_layers", []),
        }
    }

    try:
        put_resp = requests.put(update_url, headers=headers, json=update_data, timeout=30)
        put_resp.raise_for_status()
        print(f"Successfully removed {user_name} from schedule '{schedule_name}'")
        return True
    except Exception as e:
        print(f"Failed to update schedule '{schedule_name}': {e}")
        return False


def get_escalation_policy_details(headers, policy_id):
    url = f"https://api.pagerduty.com/escalation_policies/{policy_id}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("escalation_policy", {})


def remove_user_from_escalation_policy(headers, policy_id, user_id, user_name, dry_run=False):
    policy = get_escalation_policy_details(headers, policy_id)
    policy_name = policy.get("summary", "Unknown Policy")

    modified = False
    if "escalation_rules" in policy:
        for idx, rule in enumerate(policy.get("escalation_rules", [])):
            if "targets" in rule:
                original_length = len(rule["targets"])
                rule["targets"] = [
                    t for t in rule["targets"]
                    if not (t.get("type") == "user" and t.get("id") == user_id)
                ]
                if len(rule["targets"]) < original_length:
                    modified = True
                    print(f"Removing {user_name} from rule {idx+1} in policy '{policy_name}'")

    if not modified:
        print(f"User {user_name} not found in any rules of policy '{policy_name}'")
        return False

    if dry_run:
        print(f"[dry-run] Would update policy '{policy_name}' to remove {user_name}")
        return True

    update_url = f"https://api.pagerduty.com/escalation_policies/{policy_id}"
    update_data = {
        "escalation_policy": {
            "name": policy.get("name"),
            "escalation_rules": policy.get("escalation_rules", []),
        }
    }

    try:
        put_resp = requests.put(update_url, headers=headers, json=update_data, timeout=30)
        put_resp.raise_for_status()
        print(f"Successfully removed {user_name} from policy '{policy_name}'")
        return True
    except Exception as e:
        print(f"Failed to update policy '{policy_name}': {e}")
        return False


def main():
    args = parse_arguments()
    api_key = get_pd_api_token(args.token)
    team_id = get_pd_team_id(args.team_id)
    headers = build_headers(api_key)
    dry_run = args.dry_run

    if dry_run:
        print("[dry-run] No schedules, policies, or team memberships will be modified.\n")

    team_members_url = f"https://api.pagerduty.com/teams/{team_id}/members"
    response = requests.get(team_members_url, headers=headers, timeout=30)
    response.raise_for_status()
    members = response.json().get("members", [])

    schedules_url = f"https://api.pagerduty.com/schedules?team_ids[]={team_id}"
    schedules_resp = requests.get(schedules_url, headers=headers, timeout=30)
    schedules_resp.raise_for_status()
    schedules = schedules_resp.json().get("schedules", [])

    escalation_policies_url = f"https://api.pagerduty.com/escalation_policies?team_ids[]={team_id}"
    escalation_policies_resp = requests.get(escalation_policies_url, headers=headers, timeout=30)
    escalation_policies_resp.raise_for_status()
    escalation_policies = escalation_policies_resp.json().get("escalation_policies", [])

    user_schedules = {}
    user_policies = {}

    for schedule in schedules:
        schedule_id = schedule.get("id")
        schedule_name = schedule.get("summary", "Unknown")
        users_url = f"https://api.pagerduty.com/schedules/{schedule_id}/users"
        users_resp = requests.get(users_url, headers=headers, timeout=30)
        users_resp.raise_for_status()
        users = users_resp.json().get("users", [])
        for user in users:
            user_id = user.get("id")
            user_schedules.setdefault(user_id, []).append({"id": schedule_id, "name": schedule_name})

    for policy in escalation_policies:
        policy_id = policy.get("id")
        policy_name = policy.get("summary", "Unknown")
        policy_detail = get_escalation_policy_details(headers, policy_id)
        for rule in policy_detail.get("escalation_rules", []):
            for target in rule.get("targets", []):
                if target.get("type") == "user":
                    user_id = target.get("id")
                    bucket = user_policies.setdefault(user_id, [])
                    if not any(p["id"] == policy_id for p in bucket):
                        bucket.append({"id": policy_id, "name": policy_name})

    table_data = []
    for idx, member in enumerate(members):
        user = member.get("user", {})
        user_id = user.get("id", "")
        user_summary = user.get("summary", "")
        on_schedule = "No"
        if user_id in user_schedules:
            on_schedule = f"Yes ({', '.join(s['name'] for s in user_schedules[user_id])})"
        in_policy = "No"
        if user_id in user_policies:
            in_policy = f"Yes ({', '.join(p['name'] for p in user_policies[user_id])})"
        table_data.append([idx, user_id, user_summary, on_schedule, in_policy])

    print("\n=== Team Members and Their Assignments ===")
    print(tabulate(
        table_data,
        headers=["#", "User ID", "Name", "On Schedule", "In Escalation Policy"],
        tablefmt="github",
    ))
    print("\n")

    for member in members:
        user = member.get("user", {})
        user_id = user.get("id", "")
        user_summary = user.get("summary", "")

        print(f"\n--- Processing {user_summary} ---")

        if user_id in user_schedules:
            print(f"On schedules: {', '.join(s['name'] for s in user_schedules[user_id])}")
        if user_id in user_policies:
            print(f"In escalation policies: {', '.join(p['name'] for p in user_policies[user_id])}")
        if user_id not in user_schedules and user_id not in user_policies:
            print("Not on any schedules or in any escalation policies.")

        remove = input(f"Remove {user_summary} from team? (y/N): ").strip().lower()
        if remove != "y":
            print(f"Skipped {user_summary}.")
            continue

        if user_id in user_schedules:
            print(f"\nRemoving {user_summary} from schedules first:")
            for schedule in user_schedules[user_id]:
                confirm = input(f"Remove {user_summary} from schedule '{schedule['name']}'? (y/N): ").strip().lower()
                if confirm == "y":
                    remove_user_from_schedule(headers, schedule["id"], user_id, user_summary, dry_run=dry_run)
                else:
                    print(f"Skipped removing from schedule '{schedule['name']}'")

        if user_id in user_policies:
            print(f"\nRemoving {user_summary} from escalation policies:")
            for policy in user_policies[user_id]:
                confirm = input(f"Remove {user_summary} from escalation policy '{policy['name']}'? (y/N): ").strip().lower()
                if confirm == "y":
                    remove_user_from_escalation_policy(headers, policy["id"], user_id, user_summary, dry_run=dry_run)
                else:
                    print(f"Skipped removing from escalation policy '{policy['name']}'")

        print(f"\nRemoving {user_summary} from team...")
        if dry_run:
            print(f"[dry-run] Would DELETE /teams/{team_id}/members/{user_id} for {user_summary}")
            continue
        remove_url = f"https://api.pagerduty.com/teams/{team_id}/members/{user_id}"
        del_resp = requests.delete(remove_url, headers=headers, timeout=30)
        if del_resp.status_code == 204:
            print(f"Successfully removed {user_summary} from team.")
        else:
            print(f"Failed to remove {user_summary} from team: {del_resp.text}")

    print("\nDone. All requested user removals have been processed.")


if __name__ == "__main__":
    main()
