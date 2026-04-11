#!/usr/bin/env python3
"""
PagerDuty ID Export Script

This script connects to PagerDuty API and exports team IDs/names along with associated
schedules, escalation policies, services, and webhook subscriptions in table, CSV, or JSON format.
"""

import argparse
import csv
import getpass
import io
import json
import os
import sys

import dotenv
from prettytable import PrettyTable

from pagerduty import PagerDutyAPIClient
from pagerduty.resources import (
    EscalationPoliciesResource,
    SchedulesResource,
    ServicesResource,
    TeamsResource,
    WebhooksResource,
)

dotenv.load_dotenv()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Export PagerDuty IDs and names for various objects."
    )
    parser.add_argument("-t", "--token", help="PagerDuty API token")
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
    return parser.parse_args()


def get_pd_api_token():
    """Get PagerDuty API token from environment variable or user input."""
    token = os.environ.get("PD_API_TOKEN")
    if not token:
        token = getpass.getpass("Enter your PagerDuty API token: ")
    return token


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


def main():
    """Main function to run the script."""
    args = parse_arguments()

    # Get API token
    token = args.token if args.token else get_pd_api_token()
    if not token:
        print("Error: No API token provided.")
        sys.exit(1)

    client = PagerDutyAPIClient(api_token=token)
    try:
        print("Fetching teams...", end="", flush=True)
        teams = TeamsResource(client).list()
        print(f" Found {len(teams)} teams.")
        print("Fetching schedules...", end="", flush=True)
        schedules = SchedulesResource(client).list()
        print(f" Found {len(schedules)} schedules.")
        print("Fetching escalation_policies...", end="", flush=True)
        escalation_policies = EscalationPoliciesResource(client).list()
        print(f" Found {len(escalation_policies)} escalation_policies.")
        print("Fetching services...", end="", flush=True)
        services = ServicesResource(client).list()
        print(f" Found {len(services)} services.")
        print("Fetching webhook_subscriptions...", end="", flush=True)
        webhooks = WebhooksResource(client).list()
        print(f" Found {len(webhooks)} webhook_subscriptions.")
    finally:
        client.close()

    # Generate output
    output = generate_output(teams, schedules, escalation_policies, services, webhooks, args.format)

    # Output to file or stdout
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
