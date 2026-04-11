#!/usr/bin/env python3
"""
Update PagerDuty user roles script.

Promotes every account whose role is `observer` to the `user` role.
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
)
from pagerduty.resources import UsersResource


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote users with role 'observer' to role 'user'."
    )
    add_standard_cli_options(parser)
    add_deprecated_token_argument(parser)
    add_no_progress_argument(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List observer users that would be promoted without calling the API",
    )
    return parser.parse_args(parse_argv(argv))


def update_user_role(client: PagerDutyAPIClient, user_id: str, new_role: str) -> None:
    """Update the role of a PagerDuty user."""
    try:
        client.patch(f"users/{user_id}", json_data={"user": {"role": new_role}})
        print(f"Updated user {user_id} to role '{new_role}'.")
    except Exception as e:
        print(f"Exception updating user {user_id}: {e}")


def main(argv: Sequence[str] | None = None):
    init_cli_env()
    args = parse_arguments(argv)
    apply_cli_config_path(args)
    apply_log_level_from_args(args)
    token = resolve_api_token_or_exit(args.token)
    client = PagerDutyAPIClient(api_token=token)
    try:
        users_api = UsersResource(client)
        with progress_wait(args, "Fetching users..."):
            users = users_api.list()
        observers = [u for u in users if u.get("role") == "observer"]
        if args.dry_run:
            print(
                f"Dry run: {len(observers)} user(s) with role 'observer' would be promoted to 'user'."
            )
            for user in observers:
                uid = user.get("id", "")
                summary = user.get("summary") or user.get("email") or uid
                print(f"  - {summary} ({uid})")
            return
        for user in observers:
            user_id = user["id"]
            update_user_role(client, user_id, "user")
    finally:
        client.close()


if __name__ == "__main__":
    main()
