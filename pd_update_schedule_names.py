#!/usr/bin/env python3
"""
PagerDuty Schedule Name Update Script

This script connects to PagerDuty API, gets all schedules, and appends 'SCH'
to the end of schedule names that don't already have it.
"""

import argparse
import getpass
import os
import sys

import dotenv

from pagerduty import PagerDutyAPIClient
from pagerduty.resources import SchedulesResource

dotenv.load_dotenv()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Update PagerDuty schedule names by appending "SCH".'
    )
    parser.add_argument("-t", "--token", help="PagerDuty API token")
    parser.add_argument(
        "-l", "--list", action="store_true", help="List schedules without making changes"
    )
    parser.add_argument(
        "-f", "--filter", help="Only process schedules containing this text in their name"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without making changes"
    )
    return parser.parse_args()


def get_pd_api_token():
    """Get PagerDuty API token from environment variable or user input."""
    token = os.environ.get("PD_API_TOKEN")
    if not token:
        token = getpass.getpass("Enter your PagerDuty API token: ")
    return token


def get_all_schedules(schedules_api: SchedulesResource, name_filter=None):
    """Get all schedules from PagerDuty, with optional filtering by name."""
    print("Fetching schedules...", end="", flush=True)
    all_schedules = schedules_api.list()
    if name_filter:
        nf = name_filter.lower()
        schedules = [s for s in all_schedules if nf in s.get("name", "").lower()]
        print(
            f" Found {len(schedules)} schedules matching filter '{name_filter}' "
            f"(of {len(all_schedules)} total)."
        )
    else:
        schedules = all_schedules
        print(f" Found {len(schedules)} schedules.")
    return schedules


def update_schedule_name(
    schedules_api: SchedulesResource, schedule_id, current_name, dry_run=False
):
    """Update a schedule's name by appending 'SCH' if not already present."""
    if current_name.endswith(" SCH"):
        print(f"Schedule '{current_name}' (ID: {schedule_id}) already has 'SCH' suffix. Skipping.")
        return False

    new_name = f"{current_name} SCH"

    if dry_run:
        print(f"Would rename schedule '{current_name}' to '{new_name}' (ID: {schedule_id})")
        return True

    print(
        f"Renaming schedule '{current_name}' to '{new_name}' (ID: {schedule_id})...",
        end="",
        flush=True,
    )
    result = schedules_api.update(schedule_id, {"name": new_name})
    if result and "schedule" in result:
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
        schedules_api = SchedulesResource(client)
        schedules = get_all_schedules(schedules_api, args.filter)

        if args.list:
            print("\nCurrent Schedules:")
            print("-" * 80)
            for schedule in schedules:
                print(f"ID: {schedule['id']}, Name: '{schedule['name']}'")
            print("-" * 80)
            print(f"Total: {len(schedules)} schedules")
            return

        updated_count = 0
        skipped_count = 0

        print("\nProcessing schedules...")
        for schedule in schedules:
            try:
                if update_schedule_name(
                    schedules_api, schedule["id"], schedule["name"], args.dry_run
                ):
                    updated_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"Error updating schedule {schedule.get('id')}: {e}")
                skipped_count += 1

        action_verb = "Would update" if args.dry_run else "Updated"
        print(
            f"\nSummary: {action_verb} {updated_count} schedules, skipped {skipped_count} schedules."
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
