import argparse
import os
from collections.abc import Sequence

from tabulate import tabulate

from pagerduty import PagerDutyAPIClient
from pagerduty.cli_common import (
    add_deprecated_token_argument,
    add_no_progress_argument,
    add_standard_cli_options,
    apply_cli_config_path,
    apply_log_level_from_args,
    init_cli_env,
    parse_argv,
    progress_wait,
    resolve_api_token_or_exit,
)
from pagerduty.resources import SchedulesResource, TeamsResource


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactively remove members from a PagerDuty team (and related assignments)."
    )
    add_standard_cli_options(parser)
    add_deprecated_token_argument(parser)
    add_no_progress_argument(parser)
    parser.add_argument(
        "--team-id",
        help="Team ID (default: PD_TEAM_ID environment variable, else prompt)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show members and schedule/policy assignments only; no removal prompts or API writes",
    )
    return parser.parse_args(parse_argv(argv))


def get_schedule_details(client: PagerDutyAPIClient, schedule_id: str) -> dict:
    data = client.get(f"schedules/{schedule_id}")
    return data.get("schedule", {}) if isinstance(data, dict) else {}


def remove_user_from_schedule(
    client: PagerDutyAPIClient, schedule_id: str, user_id: str, user_name: str
) -> bool:
    schedule = get_schedule_details(client, schedule_id)
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
                print(f"Removing {user_name} from layer {idx + 1} in schedule '{schedule_name}'")

    if not modified:
        print(f"User {user_name} not found in any layers of schedule '{schedule_name}'")
        return False

    update_data = {
        "schedule": {
            "name": schedule.get("name"),
            "schedule_layers": schedule.get("schedule_layers", []),
        }
    }
    try:
        client.put(f"schedules/{schedule_id}", json_data=update_data)
        print(f"Successfully removed {user_name} from schedule '{schedule_name}'")
        return True
    except Exception as e:
        print(f"Failed to update schedule '{schedule_name}': {str(e)}")
        return False


def get_escalation_policy_details(client: PagerDutyAPIClient, policy_id: str) -> dict:
    data = client.get(f"escalation_policies/{policy_id}")
    return data.get("escalation_policy", {}) if isinstance(data, dict) else {}


def remove_user_from_escalation_policy(
    client: PagerDutyAPIClient, policy_id: str, user_id: str, user_name: str
) -> bool:
    policy = get_escalation_policy_details(client, policy_id)
    policy_name = policy.get("summary", "Unknown Policy")

    modified = False
    if "escalation_rules" in policy:
        for idx, rule in enumerate(policy.get("escalation_rules", [])):
            if "targets" in rule:
                original_length = len(rule["targets"])
                rule["targets"] = [
                    t
                    for t in rule["targets"]
                    if not (t.get("type") == "user" and t.get("id") == user_id)
                ]
                if len(rule["targets"]) < original_length:
                    modified = True
                    print(f"Removing {user_name} from rule {idx + 1} in policy '{policy_name}'")

    if not modified:
        print(f"User {user_name} not found in any rules of policy '{policy_name}'")
        return False

    update_data = {
        "escalation_policy": {
            "name": policy.get("name"),
            "escalation_rules": policy.get("escalation_rules", []),
        }
    }
    try:
        client.put(f"escalation_policies/{policy_id}", json_data=update_data)
        print(f"Successfully removed {user_name} from policy '{policy_name}'")
        return True
    except Exception as e:
        print(f"Failed to update policy '{policy_name}': {str(e)}")
        return False


def main(argv: Sequence[str] | None = None):
    init_cli_env()
    args = parse_arguments(argv)
    apply_cli_config_path(args)
    apply_log_level_from_args(args)
    token = resolve_api_token_or_exit(args.token)
    team_id = (args.team_id or os.environ.get("PD_TEAM_ID") or "").strip()
    if not team_id:
        team_id = input("Enter your PagerDuty team ID: ").strip()

    client = PagerDutyAPIClient(api_token=token)
    try:
        teams_api = TeamsResource(client)
        schedules_api = SchedulesResource(client)

        with progress_wait(
            args,
            "Loading team members, schedules, and escalation assignments...",
        ):
            members = teams_api.get_members(team_id)
            schedules = teams_api.get_schedules(team_id)
            escalation_policies = teams_api.get_escalation_policies(team_id)

            user_schedules: dict[str, list[dict[str, str]]] = {}
            user_policies: dict[str, list[dict[str, str]]] = {}

            for schedule in schedules:
                schedule_id = schedule.get("id")
                if not schedule_id:
                    continue
                schedule_name = schedule.get("summary", "Unknown")
                users = schedules_api.get_users(schedule_id)
                for user in users:
                    uid = user.get("id")
                    if not uid:
                        continue
                    if uid not in user_schedules:
                        user_schedules[uid] = []
                    user_schedules[uid].append({"id": schedule_id, "name": schedule_name})

            for policy in escalation_policies:
                policy_id = policy.get("id")
                if not policy_id:
                    continue
                policy_name = policy.get("summary", "Unknown")
                policy_detail = get_escalation_policy_details(client, policy_id)
                for rule in policy_detail.get("escalation_rules", []):
                    for target in rule.get("targets", []):
                        if target.get("type") == "user":
                            uid = target.get("id")
                            if not uid:
                                continue
                            if uid not in user_policies:
                                user_policies[uid] = []
                            if not any(p["id"] == policy_id for p in user_policies.get(uid, [])):
                                user_policies[uid].append({"id": policy_id, "name": policy_name})

        table_data = []
        for idx, member in enumerate(members):
            user = member.get("user", {})
            user_id = user.get("id", "")
            user_summary = user.get("summary", "")

            on_schedule = "No"
            if user_id in user_schedules:
                schedules_list = [s["name"] for s in user_schedules[user_id]]
                on_schedule = f"Yes ({', '.join(schedules_list)})"

            in_policy = "No"
            if user_id in user_policies:
                policies_list = [p["name"] for p in user_policies[user_id]]
                in_policy = f"Yes ({', '.join(policies_list)})"

            table_data.append([idx, user_id, user_summary, on_schedule, in_policy])

        print("\n=== Team Members and Their Assignments ===")
        print(
            tabulate(
                table_data,
                headers=["#", "User ID", "Name", "On Schedule", "In Escalation Policy"],
                tablefmt="github",
            )
        )
        print("\n")

        if args.dry_run:
            print(
                "Dry run: no removal prompts or API changes. "
                "Re-run without --dry-run to remove members interactively."
            )
            return

        for idx, member in enumerate(members):
            user = member.get("user", {})
            user_id = user.get("id", "")
            user_summary = user.get("summary", "")

            print(f"\n--- Processing {user_summary} ---")

            if user_id in user_schedules:
                print(f"On schedules: {', '.join(s['name'] for s in user_schedules[user_id])}")
            if user_id in user_policies:
                print(
                    f"In escalation policies: {', '.join(p['name'] for p in user_policies[user_id])}"
                )
            if user_id not in user_schedules and user_id not in user_policies:
                print("Not on any schedules or in any escalation policies.")

            remove = input(f"Remove {user_summary} from team? (y/N): ").strip().lower()

            if remove == "y":
                if user_id in user_schedules:
                    print(f"\nRemoving {user_summary} from schedules first:")
                    for schedule in user_schedules[user_id]:
                        confirm = (
                            input(
                                f"Remove {user_summary} from schedule '{schedule['name']}'? (y/N): "
                            )
                            .strip()
                            .lower()
                        )
                        if confirm == "y":
                            remove_user_from_schedule(client, schedule["id"], user_id, user_summary)
                        else:
                            print(f"Skipped removing from schedule '{schedule['name']}'")

                if user_id in user_policies:
                    print(f"\nRemoving {user_summary} from escalation policies:")
                    for policy in user_policies[user_id]:
                        confirm = (
                            input(
                                f"Remove {user_summary} from escalation policy '{policy['name']}'? (y/N): "
                            )
                            .strip()
                            .lower()
                        )
                        if confirm == "y":
                            remove_user_from_escalation_policy(
                                client, policy["id"], user_id, user_summary
                            )
                        else:
                            print(f"Skipped removing from escalation policy '{policy['name']}'")

                print(f"\nRemoving {user_summary} from team...")
                try:
                    teams_api.remove_member(team_id, user_id)
                    print(f"Successfully removed {user_summary} from team.")
                except Exception as e:
                    print(f"Failed to remove {user_summary} from team: {e}")
            else:
                print(f"Skipped {user_summary}.")

        print("\nDone. All requested user removals have been processed.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
