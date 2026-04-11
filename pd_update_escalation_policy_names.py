#!/usr/bin/env python3
"""
PagerDuty Escalation Policy Name Update Script

This script connects to PagerDuty API, gets all escalation policies, and appends 'EP'
to the end of escalation policy names that don't already have it.
"""

import os
import sys
import argparse
import getpass

import dotenv
from pagerduty import PagerDutyAPIClient
from pagerduty.resources import EscalationPoliciesResource

dotenv.load_dotenv()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update PagerDuty escalation policy names by appending "EP".')
    parser.add_argument('-t', '--token', help='PagerDuty API token')
    parser.add_argument('-l', '--list', action='store_true', help='List escalation policies without making changes')
    parser.add_argument('-f', '--filter', help='Only process escalation policies containing this text in their name')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    return parser.parse_args()


def get_pd_api_token():
    """Get PagerDuty API token from environment variable or user input."""
    token = os.environ.get('PD_API_TOKEN')
    if not token:
        token = getpass.getpass("Enter your PagerDuty API token: ")
    return token


def get_all_escalation_policies(policies_api: EscalationPoliciesResource, name_filter=None):
    """Get all escalation policies from PagerDuty, with optional filtering by name."""
    print("Fetching escalation policies...", end="", flush=True)
    all_policies = policies_api.list()
    if name_filter:
        nf = name_filter.lower()
        policies = [p for p in all_policies if nf in p.get("name", "").lower()]
        print(
            f" Found {len(policies)} escalation policies matching filter "
            f"'{name_filter}' (of {len(all_policies)} total)."
        )
    else:
        policies = all_policies
        print(f" Found {len(policies)} escalation policies.")
    return policies


def update_escalation_policy_name(
    policies_api: EscalationPoliciesResource, policy_id, current_name, dry_run=False
):
    """Update an escalation policy's name by appending 'EP' if not already present."""
    if current_name.strip().endswith(" EP"):
        print(f"Escalation Policy '{current_name}' (ID: {policy_id}) already has 'EP' suffix. Skipping.")
        return False

    new_name = f"{current_name.strip()} EP"

    if dry_run:
        print(f"Would rename escalation policy '{current_name}' to '{new_name}' (ID: {policy_id})")
        return True

    print(f"Renaming escalation policy '{current_name}' to '{new_name}' (ID: {policy_id})...", end="", flush=True)
    result = policies_api.update(policy_id, {"name": new_name})
    if result and "escalation_policy" in result:
        print(" Success!")
        return True
    print(" Failed.")
    return False


def main():
    """Main function to run the script."""
    args = parse_arguments()

    token = args.token if args.token else get_pd_api_token()
    if not token:
        print("Error: No API token provided.")
        sys.exit(1)

    client = PagerDutyAPIClient(api_token=token)
    try:
        policies_api = EscalationPoliciesResource(client)
        policies = get_all_escalation_policies(policies_api, args.filter)

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
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                return

        updated_count = 0
        skipped_count = 0

        print("\nProcessing escalation policies...")
        for policy in policies:
            try:
                if update_escalation_policy_name(policies_api, policy['id'], policy['name'], args.dry_run):
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"Error updating policy {policy.get('id')}: {e}")
                skipped_count += 1

        action_verb = "Would update" if args.dry_run else "Updated"
        print(f"\nSummary: {action_verb} {updated_count} escalation policies, skipped {skipped_count} escalation policies.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
