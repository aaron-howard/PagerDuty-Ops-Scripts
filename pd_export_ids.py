#!/usr/bin/env python3
"""
PagerDuty ID Export Script

This script connects to PagerDuty API and exports team IDs/names along with associated
schedules, escalation policies, services, and webhook subscriptions in table, CSV, or JSON format.
"""

import argparse
import csv
import io
import json
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed

from prettytable import PrettyTable

from pagerduty import PagerDutyAPIClient
from pagerduty.cli_common import (
    EXIT_USAGE,
    add_deprecated_token_argument,
    add_no_progress_argument,
    add_standard_cli_options,
    apply_cli_config_path,
    apply_log_level_from_args,
    init_cli_env,
    parse_argv,
    progress_wait,
    resolve_api_token_or_exit,
    show_progress,
    status_line,
)
from pagerduty.resources import (
    EscalationPoliciesResource,
    SchedulesResource,
    ServicesResource,
    TeamsResource,
    WebhooksResource,
)

_SKIP_RESOURCES = (
    "schedules",
    "escalation_policies",
    "services",
    "webhooks",
)


def parse_arguments(argv: Sequence[str] | None = None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Export PagerDuty IDs and names for various objects."
    )
    add_standard_cli_options(parser)
    add_deprecated_token_argument(parser)
    add_no_progress_argument(parser)
    parser.add_argument(
        "-o", "--output", help="Output file for results (default is to display on screen)"
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--without",
        nargs="+",
        choices=_SKIP_RESOURCES,
        default=None,
        metavar="RESOURCE",
        help=(
            "Skip fetching these resources to reduce API calls (teams are always fetched). "
            f"One or more of: {', '.join(_SKIP_RESOURCES)}."
        ),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        metavar="N",
        help=(
            "Parallel fetches for list endpoints when N>1 (separate HTTP session per worker). "
            "Ignored when only one resource is fetched."
        ),
    )
    return parser.parse_args(parse_argv(argv))


def _fetch_resource_list(resource: str, token: str) -> tuple[str, list[dict]]:
    """One list() call with its own client (thread-safe)."""
    client = PagerDutyAPIClient(api_token=token)
    try:
        if resource == "teams":
            return resource, TeamsResource(client).list()
        if resource == "schedules":
            return resource, SchedulesResource(client).list()
        if resource == "escalation_policies":
            return resource, EscalationPoliciesResource(client).list()
        if resource == "services":
            return resource, ServicesResource(client).list()
        if resource == "webhooks":
            return resource, WebhooksResource(client).list()
        raise ValueError(f"unknown resource: {resource}")
    finally:
        client.close()


def generate_output(teams, schedules, escalation_policies, services, webhooks, format_type):
    """Generate output based on the specified format."""
    result = []
    table = PrettyTable()
    table.field_names = [
        "Team ID",
        "Team Name",
        "Schedule ID",
        "Schedule Name",
        "Escalation Policy ID",
        "Escalation Policy Name",
        "Service ID",
        "Service Name",
        "Webhook ID",
        "Webhook Name",
    ]

    # Map items by team_id for easier lookup
    def map_by_team(items, key):
        mapping = {}
        for item in items:
            for team in item.get("teams", []):
                team_id = team.get("id")
                if team_id not in mapping:
                    mapping[team_id] = []
                mapping[team_id].append({"id": item.get("id"), "name": item.get("name")})
        return mapping

    team_schedules = map_by_team(schedules, "schedules")
    team_policies = map_by_team(escalation_policies, "escalation_policies")
    team_services = map_by_team(services, "services")

    # Map webhooks to teams via services
    team_webhooks = {}
    service_team_map = {service["id"]: service.get("teams", []) for service in services}
    for webhook in webhooks:
        # Extract service ID from webhook data structure
        service_id = None

        # Check for filter with service_reference type
        if (
            "filter" in webhook
            and webhook["filter"]
            and webhook["filter"].get("type") == "service_reference"
        ):
            service_id = webhook["filter"].get("id")
        # Fallback to direct service reference if available
        elif "service" in webhook and webhook["service"] and "id" in webhook["service"]:
            service_id = webhook["service"]["id"]
        # Legacy structure fallback
        elif "delivery_method" in webhook:
            delivery_method = webhook.get("delivery_method", {})
            if "connection" in delivery_method and "service" in delivery_method["connection"]:
                service_id = delivery_method["connection"]["service"]["id"]

        if service_id and service_id in service_team_map:
            for team in service_team_map[service_id]:
                team_id = team.get("id")
                if team_id not in team_webhooks:
                    team_webhooks[team_id] = []
                team_webhooks[team_id].append(
                    {
                        "id": webhook.get("id", ""),
                        "name": webhook.get("description", "No description"),
                    }
                )
    for team in teams:
        team_id = team.get("id")
        team_name = team.get("name")

        schedules_for_team = team_schedules.get(team_id, [{"id": "", "name": ""}])
        policies_for_team = team_policies.get(team_id, [{"id": "", "name": ""}])
        services_for_team = team_services.get(team_id, [{"id": "", "name": ""}])
        webhooks_for_team = team_webhooks.get(team_id, [{"id": "", "name": ""}])

        max_items = max(
            len(schedules_for_team),
            len(policies_for_team),
            len(services_for_team),
            len(webhooks_for_team),
        )

        for i in range(max_items):
            row = [
                team_id if i == 0 else "",
                team_name if i == 0 else "",
                schedules_for_team[i]["id"] if i < len(schedules_for_team) else "",
                schedules_for_team[i]["name"] if i < len(schedules_for_team) else "",
                policies_for_team[i]["id"] if i < len(policies_for_team) else "",
                policies_for_team[i]["name"] if i < len(policies_for_team) else "",
                services_for_team[i]["id"] if i < len(services_for_team) else "",
                services_for_team[i]["name"] if i < len(services_for_team) else "",
                webhooks_for_team[i]["id"] if i < len(webhooks_for_team) else "",
                webhooks_for_team[i]["name"] if i < len(webhooks_for_team) else "",
            ]
            table.add_row(row)
            result.append(
                {
                    "team_id": row[0],
                    "team_name": row[1],
                    "schedule_id": row[2],
                    "schedule_name": row[3],
                    "escalation_policy_id": row[4],
                    "escalation_policy_name": row[5],
                    "service_id": row[6],
                    "service_name": row[7],
                    "webhook_id": row[8],
                    "webhook_name": row[9],
                }
            )

    if format_type == "table":
        return table
    elif format_type == "json":
        return json.dumps(result, indent=2)
    elif format_type == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=table.field_names)
        writer.writeheader()
        for row in result:
            writer.writerow(
                {
                    "Team ID": row["team_id"],
                    "Team Name": row["team_name"],
                    "Schedule ID": row["schedule_id"],
                    "Schedule Name": row["schedule_name"],
                    "Escalation Policy ID": row["escalation_policy_id"],
                    "Escalation Policy Name": row["escalation_policy_name"],
                    "Service ID": row["service_id"],
                    "Service Name": row["service_name"],
                    "Webhook ID": row["webhook_id"],
                    "Webhook Name": row["webhook_name"],
                }
            )
        return output.getvalue()


def main(argv: Sequence[str] | None = None):
    """Main function to run the script."""
    init_cli_env()
    args = parse_arguments(argv)
    apply_cli_config_path(args)
    apply_log_level_from_args(args)
    token = resolve_api_token_or_exit(args.token)

    if args.concurrency < 1:
        print("Error: --concurrency must be >= 1.", file=sys.stderr)
        sys.exit(EXIT_USAGE)

    skip = set(args.without or [])

    fetch_order = ["teams"]
    for name in _SKIP_RESOURCES:
        if name not in skip:
            fetch_order.append(name)

    if len(fetch_order) > 1 and args.concurrency > 1:
        workers = min(args.concurrency, len(fetch_order))
        results: dict[str, list] = {}
        with progress_wait(
            args,
            f"Fetching {len(fetch_order)} resources ({workers} parallel workers)...",
        ):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_fetch_resource_list, name, token): name for name in fetch_order
                }
                for fut in as_completed(futures):
                    key, items = fut.result()
                    results[key] = items
        if show_progress(args):
            for name in fetch_order:
                print(f"  {name}: {len(results[name])}")
        teams = results["teams"]
        schedules = results.get("schedules", [])
        escalation_policies = results.get("escalation_policies", [])
        services = results.get("services", [])
        webhooks = results.get("webhooks", [])
    else:
        client = PagerDutyAPIClient(api_token=token)
        try:
            with progress_wait(args, "Fetching teams..."):
                teams = TeamsResource(client).list()
            status_line(args, f"Found {len(teams)} teams.")

            if "schedules" in skip:
                schedules = []
                status_line(args, "Skipping schedules fetch (--without schedules).")
            else:
                with progress_wait(args, "Fetching schedules..."):
                    schedules = SchedulesResource(client).list()
                status_line(args, f"Found {len(schedules)} schedules.")

            if "escalation_policies" in skip:
                escalation_policies = []
                status_line(
                    args, "Skipping escalation_policies fetch (--without escalation_policies)."
                )
            else:
                with progress_wait(args, "Fetching escalation_policies..."):
                    escalation_policies = EscalationPoliciesResource(client).list()
                status_line(args, f"Found {len(escalation_policies)} escalation_policies.")

            if "services" in skip:
                services = []
                status_line(args, "Skipping services fetch (--without services).")
            else:
                with progress_wait(args, "Fetching services..."):
                    services = ServicesResource(client).list()
                status_line(args, f"Found {len(services)} services.")

            if "webhooks" in skip:
                webhooks = []
                status_line(args, "Skipping webhook_subscriptions fetch (--without webhooks).")
            else:
                with progress_wait(args, "Fetching webhook_subscriptions..."):
                    webhooks = WebhooksResource(client).list()
                status_line(args, f"Found {len(webhooks)} webhook_subscriptions.")
        finally:
            client.close()

    output = generate_output(teams, schedules, escalation_policies, services, webhooks, args.format)

    try:
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(str(output))
            print(f"Results written to {args.output}")
        else:
            print(output)
    except Exception as e:
        print(f"Error writing output: {e}")


if __name__ == "__main__":
    main()
