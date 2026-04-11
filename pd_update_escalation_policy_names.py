#!/usr/bin/env python3
"""
PagerDuty Escalation Policy Name Update Script

This script connects to PagerDuty API, gets all escalation policies, and appends 'EP'
to the end of escalation policy names that don't already have it.
"""

import argparse
from collections.abc import Sequence

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
    status_line,
)
from pagerduty.resources import EscalationPoliciesResource


def parse_arguments(argv: Sequence[str] | None = None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Update PagerDuty escalation policy names by appending "EP".'
    )
    add_standard_cli_options(parser)
    add_deprecated_token_argument(parser)
    add_no_progress_argument(parser)
    parser.add_argument(
        "-l", "--list", action="store_true", help="List escalation policies without making changes"
    )
    parser.add_argument(
        "-f", "--filter", help="Only process escalation policies containing this text in their name"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    return parser.parse_args(parse_argv(argv))


def get_all_escalation_policies(
    policies_api: EscalationPoliciesResource, name_filter, args: argparse.Namespace
):
    """Get all escalation policies from PagerDuty, with optional filtering by name."""
    with progress_wait(args, "Fetching escalation policies..."):
        all_policies = policies_api.list()
    if name_filter:
        nf = name_filter.lower()
        policies = [p for p in all_policies if nf in p.get("name", "").lower()]
        status_line(
            args,
            f"Found {len(policies)} escalation policies matching filter "
            f"'{name_filter}' (of {len(all_policies)} total).",
        )
    else:
        policies = all_policies
        status_line(args, f"Found {len(policies)} escalation policies.")
    return policies


def update_escalation_policy_name(
    policies_api: EscalationPoliciesResource, policy_id, current_name, dry_run=False
):
    """Update an escalation policy's name by appending 'EP' if not already present."""
    if current_name.strip().endswith(" EP"):
        print(
            f"Escalation Policy '{current_name}' (ID: {policy_id}) already has 'EP' suffix. Skipping."
        )
        return False

    new_name = f"{current_name.strip()} EP"

    if dry_run:
        print(f"Would rename escalation policy '{current_name}' to '{new_name}' (ID: {policy_id})")
        return True

    print(
        f"Renaming escalation policy '{current_name}' to '{new_name}' (ID: {policy_id})...",
        end="",
        flush=True,
    )
    result = policies_api.update(policy_id, {"name": new_name})
    if result and "escalation_policy" in result:
        print(" Success!")
        return True
    print(" Failed.")
    return False


def main(argv: Sequence[str] | None = None):
    """Main function to run the script."""
    init_cli_env()
    args = parse_arguments(argv)
    apply_cli_config_path(args)
    apply_log_level_from_args(args)
    token = resolve_api_token_or_exit(args.token)

    client = PagerDutyAPIClient(api_token=token)
    try:
        policies_api = EscalationPoliciesResource(client)
        policies = get_all_escalation_policies(policies_api, args.filter, args)

        if args.list:
            print("\nCurrent Escalation Policies:")
            print("-" * 80)
            for policy in policies:
                print(f"ID: {policy['id']}, Name: '{policy['name']}'")
            print("-" * 80)
            print(f"Total: {len(policies)} escalation policies")
            return

        if not args.dry_run and policies:
            confirm = input(
                f"\nThis will update {len(policies)} escalation policy names. Do you want to proceed? (y/n): "
            )
            if confirm.lower() != "y":
                print("Operation cancelled.")
                return

        updated_count = 0
        skipped_count = 0

        print("\nProcessing escalation policies...")
        for policy in policies:
            try:
                if update_escalation_policy_name(
                    policies_api, policy["id"], policy["name"], args.dry_run
                ):
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"Error updating policy {policy.get('id')}: {e}")
                skipped_count += 1

        action_verb = "Would update" if args.dry_run else "Updated"
        print(
            f"\nSummary: {action_verb} {updated_count} escalation policies, skipped {skipped_count} escalation policies."
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
