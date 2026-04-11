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
from pagerduty.resources import TeamsResource


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List members of a PagerDuty team and their roles."
    )
    add_standard_cli_options(parser)
    add_deprecated_token_argument(parser)
    add_no_progress_argument(parser)
    parser.add_argument(
        "--team-id",
        help="Team ID (default: PD_TEAM_ID environment variable, else prompt)",
    )
    return parser.parse_args(parse_argv(argv))


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
        teams = TeamsResource(client)
        with progress_wait(args, "Fetching team members..."):
            members = teams.get_members(team_id.strip())

        table_data = []
        for member in members:
            user = member.get("user", {})
            user_id = user.get("id", "")
            user_type = user.get("type", "")
            user_summary = user.get("summary", "")
            user_role = member.get("role", "")
            table_data.append([user_id, user_type, user_summary, user_role])

        print(tabulate(table_data, headers=["ID", "Type", "Summary", "Role"], tablefmt="github"))
    finally:
        client.close()


if __name__ == "__main__":
    main()
