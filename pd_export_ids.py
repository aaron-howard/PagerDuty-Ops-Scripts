#!/usr/bin/env python3
"""
PagerDuty ID Export Script

This script connects to PagerDuty API and exports team IDs/names along with associated
schedules, escalation policies, services, and webhook subscriptions in table, CSV, or JSON format.
"""

import requests
import os
import sys
import json
import prettytable
from prettytable import PrettyTable
import argparse
from datetime import datetime
import csv
import io

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Export PagerDuty IDs and names for various objects.')
    parser.add_argument('-t', '--token', help='PagerDuty API token')
    parser.add_argument('-o', '--output', help='Output file for results (default is to display on screen)')
    parser.add_argument('-f', '--format', choices=['table', 'csv', 'json'], default='table',
                       help='Output format (default: table)')
    return parser.parse_args()

def get_pd_api_token():
    """Get PagerDuty API token from environment variable or user input."""
    token = os.environ.get('PD_API_TOKEN')
    if not token:
        token = input("Enter your PagerDuty API token: ")
    return token

def make_api_request(endpoint, token, params=None):
    """Make a request to the PagerDuty API."""
    base_url = "https://api.pagerduty.com"
    headers = {
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Authorization": f"Token token={token}",
        "Content-Type": "application/json"
    }

    url = f"{base_url}/{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: API request failed - {e}")
        return None

    try:
        return response.json()
    except Exception as e:
        print(f"Error decoding JSON: {e}")
        return None

def get_all_items(token, resource):
    """Generic function to handle pagination for any resource."""
    print(f"Fetching {resource}...", end="", flush=True)
    items = []
    offset = 0
    limit = 100
    while True:
        params = {"limit": limit, "offset": offset}
        data = make_api_request(resource, token, params)
        if not data or resource not in data:
            break
        items.extend(data[resource])
        if not data.get("more"):
            break
        offset += limit
    print(f" Found {len(items)} {resource}.")
    return items

def get_all_teams(token):
    return get_all_items(token, "teams")

def get_all_schedules(token):
    return get_all_items(token, "schedules")

def get_all_escalation_policies(token):
    return get_all_items(token, "escalation_policies")

def get_all_services(token):
    return get_all_items(token, "services")

def get_all_webhook_subscriptions(token):
    return get_all_items(token, "webhook_subscriptions")

def generate_output(teams, schedules, escalation_policies, services, webhooks, format_type):
    """Generate output based on the specified format."""
    result = []
    table = PrettyTable()
    table.field_names = [
        "Team ID", "Team Name", "Schedule ID", "Schedule Name",
        "Escalation Policy ID", "Escalation Policy Name",
        "Service ID", "Service Name",
        "Webhook ID", "Webhook Name"
    ]

    # Map items by team_id for easier lookup
    def map_by_team(items, key):
        mapping = {}
        for item in items:
            for team in item.get("teams", []):
                team_id = team.get("id")
                if team_id not in mapping:
                    mapping[team_id] = []
                mapping[team_id].append({
                    "id": item.get("id"),
                    "name": item.get("name")
                })
        return mapping

    team_schedules = map_by_team(schedules, "schedules")
    team_policies = map_by_team(escalation_policies, "escalation_policies")
    team_services = map_by_team(services, "services")

    # Map webhooks to teams via services
    team_webhooks = {}
    service_team_map = {service['id']: service.get('teams', []) for service in services}
    for webhook in webhooks:
        delivery_method = webhook.get("delivery_method", {})
        service_id = None
        if "connection" in delivery_method and "service" in delivery_method["connection"]:
            service_id = delivery_method["connection"]["service"]["id"]
        if service_id and service_id in service_team_map:
            for team in service_team_map[service_id]:
                team_id = team.get("id")
                if team_id not in team_webhooks:
                    team_webhooks[team_id] = []
                team_webhooks[team_id].append({
                    "id": webhook.get("id"),
                    "name": webhook.get("description", "No description")
                })

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
            len(webhooks_for_team)
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
            result.append({
                "team_id": row[0],
                "team_name": row[1],
                "schedule_id": row[2],
                "schedule_name": row[3],
                "escalation_policy_id": row[4],
                "escalation_policy_name": row[5],
                "service_id": row[6],
                "service_name": row[7],
                "webhook_id": row[8],
                "webhook_name": row[9]
            })

    if format_type == 'table':
        return table
    elif format_type == 'json':
        return json.dumps(result, indent=2)
    elif format_type == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=table.field_names)
        writer.writeheader()
        for row in result:
            writer.writerow({
                "Team ID": row["team_id"],
                "Team Name": row["team_name"],
                "Schedule ID": row["schedule_id"],
                "Schedule Name": row["schedule_name"],
                "Escalation Policy ID": row["escalation_policy_id"],
                "Escalation Policy Name": row["escalation_policy_name"],
                "Service ID": row["service_id"],
                "Service Name": row["service_name"],
                "Webhook ID": row["webhook_id"],
                "Webhook Name": row["webhook_name"]
            })
        return output.getvalue()

def main():
    """Main function to run the script."""
    args = parse_arguments()

    # Get API token
    token = args.token if args.token else get_pd_api_token()
    if not token:
        print("Error: No API token provided.")
        sys.exit(1)

    # Get all data from PagerDuty
    teams = get_all_teams(token)
    schedules = get_all_schedules(token)
    escalation_policies = get_all_escalation_policies(token)
    services = get_all_services(token)
    webhooks = get_all_webhook_subscriptions(token)

    # Generate output
    output = generate_output(teams, schedules, escalation_policies, services, webhooks, args.format)

    # Output to file or stdout
    try:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(str(output))
            print(f"Results written to {args.output}")
        else:
            print(output)
    except Exception as e:
        print(f"Error writing output: {e}")

if __name__ == "__main__":
    main()