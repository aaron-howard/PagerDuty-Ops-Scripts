#!/usr/bin/env python3
"""
PagerDuty Service Name Update Script

This script connects to PagerDuty API and updates service names by appending "SVC"
to the end of each service name if it doesn't already end with "SVC".
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
from pagerduty.resources import ServicesResource


def parse_arguments(argv: Sequence[str] | None = None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Update PagerDuty service names by appending "SVC".'
    )
    add_standard_cli_options(parser)
    add_deprecated_token_argument(parser)
    add_no_progress_argument(parser)
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Perform a dry run (show what would change without making changes)",
    )
    parser.add_argument(
        "-l", "--list", action="store_true", help="List services without making changes"
    )
    parser.add_argument(
        "-f",
        "--filter",
        help="Filter services by name (only update services containing this string)",
    )
    return parser.parse_args(parse_argv(argv))


def get_all_services(services_api: ServicesResource, name_filter, args: argparse.Namespace):
    """Get all services from PagerDuty with optional name filtering."""
    with progress_wait(args, "Fetching services..."):
        all_svcs = services_api.list()
    if name_filter:
        nf = name_filter.lower()
        services = [s for s in all_svcs if nf in s.get("name", "").lower()]
        status_line(
            args,
            f"Found {len(services)} services matching filter (of {len(all_svcs)} total).",
        )
    else:
        services = all_svcs
        status_line(args, f"Found {len(services)} services.")
    return services


def update_service_name(services_api: ServicesResource, service_id, new_name, dry_run=False):
    """Update the name of a service."""
    if dry_run:
        print(f"Would update service {service_id} to name: {new_name}")
        return True

    services_api.update(service_id, {"name": new_name})
    print(f"Successfully updated service {service_id} to: {new_name}")
    return True


def main(argv: Sequence[str] | None = None):
    """Main function to run the script."""
    init_cli_env()
    args = parse_arguments(argv)
    apply_cli_config_path(args)
    apply_log_level_from_args(args)
    token = resolve_api_token_or_exit(args.token)

    client = PagerDutyAPIClient(api_token=token)
    try:
        services_api = ServicesResource(client)
        services = get_all_services(services_api, args.filter, args)

        if args.list:
            print("\nCurrent Services:")
            print("----------------")
            for service in services:
                print(f"ID: {service.get('id')}, Name: {service.get('name')}")
            return

        to_update = [s for s in services if not s.get("name", "").strip().endswith("SVC")]
        print(f"\nFound {len(to_update)} services that need 'SVC' appended to their name.")

        if not to_update:
            print("No services need updating.")
            return

        if not args.dry_run:
            confirm = input("\nDo you want to proceed with updating these service names? (y/n): ")
            if confirm.lower() != "y":
                print("Operation cancelled.")
                return

        updated_count = 0
        failed_count = 0

        for service in to_update:
            service_id = service.get("id")
            current_name = service.get("name", "")
            if current_name.strip().endswith("SVC"):
                continue
            new_name = f"{current_name.strip()} SVC"
            try:
                if update_service_name(services_api, service_id, new_name, args.dry_run):
                    updated_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"Failed to update {current_name}: {e}")
                failed_count += 1

        if args.dry_run:
            print(f"\nDry run complete. {updated_count} services would be updated.")
        else:
            print(f"\nUpdate complete. {updated_count} services updated, {failed_count} failed.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
