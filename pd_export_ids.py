#!/usr/bin/env python3
"""
PagerDuty ID Export Script

This script connects to PagerDuty API and exports team IDs/names along with associated
schedules, escalation policies, services, and webhook subscriptions in table format.
"""

import requests
import os
import sys
import json
import prettytable
from prettytable import PrettyTable
import argparse
from datetime import datetime

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
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code != 200:
        print(f"Error: API request failed with status code {response.status_code}")
        print(f"Response: {response.text}")
        return None
        
    return response.json()

def get_all_teams(token):
    """Get all teams from PagerDuty."""
    print("Fetching teams...", end="", flush=True)
    teams_data = make_api_request("teams", token, {"limit": 100})
    teams = []
    
    if teams_data and "teams" in teams_data:
        teams = teams_data["teams"]
        
        # Handle pagination if necessary
        while teams_data.get("more") and teams_data.get("more") is True:
            teams_data = make_api_request("teams", token, {
                "limit": 100,
                "offset": teams_data.get("offset") + teams_data.get("limit")
            })
            if teams_data and "teams" in teams_data:
                teams.extend(teams_data["teams"])
            else:
                break
    
    print(f" Found {len(teams)} teams.")
    return teams

def get_all_schedules(token):
    """Get all schedules from PagerDuty."""
    print("Fetching schedules...", end="", flush=True)
    schedules_data = make_api_request("schedules", token, {"limit": 100})
    schedules = []
    
    if schedules_data and "schedules" in schedules_data:
        schedules = schedules_data["schedules"]
        
        # Handle pagination
        while schedules_data.get("more") and schedules_data.get("more") is True:
            schedules_data = make_api_request("schedules", token, {
                "limit": 100,
                "offset": schedules_data.get("offset") + schedules_data.get("limit")
            })
            if schedules_data and "schedules" in schedules_data:
                schedules.extend(schedules_data["schedules"])
            else:
                break
    
    print(f" Found {len(schedules)} schedules.")
    return schedules

def get_all_escalation_policies(token):
    """Get all escalation policies from PagerDuty."""
    print("Fetching escalation policies...", end="", flush=True)
    ep_data = make_api_request("escalation_policies", token, {"limit": 100})
    policies = []
    
    if ep_data and "escalation_policies" in ep_data:
        policies = ep_data["escalation_policies"]
        
        # Handle pagination
        while ep_data.get("more") and ep_data.get("more") is True:
            ep_data = make_api_request("escalation_policies", token, {
                "limit": 100,
                "offset": ep_data.get("offset") + ep_data.get("limit")
            })
            if ep_data and "escalation_policies" in ep_data:
                policies.extend(ep_data["escalation_policies"])
            else:
                break
    
    print(f" Found {len(policies)} escalation policies.")
    return policies

def get_all_services(token):
    """Get all services from PagerDuty."""
    print("Fetching services...", end="", flush=True)
    services_data = make_api_request("services", token, {"limit": 100})
    services = []
    
    if services_data and "services" in services_data:
        services = services_data["services"]
        
        # Handle pagination
        while services_data.get("more") and services_data.get("more") is True:
            services_data = make_api_request("services", token, {
                "limit": 100,
                "offset": services_data.get("offset") + services_data.get("limit")
            })
            if services_data and "services" in services_data:
                services.extend(services_data["services"])
            else:
                break
    
    print(f" Found {len(services)} services.")
    return services

def get_all_webhook_subscriptions(token):
    """Get all webhook subscriptions from PagerDuty."""
    print("Fetching webhook subscriptions...", end="", flush=True)
    webhook_data = make_api_request("webhook_subscriptions", token, {"limit": 100})
    webhooks = []
    
    if webhook_data and "webhook_subscriptions" in webhook_data:
        webhooks = webhook_data["webhook_subscriptions"]
        
        # Handle pagination
        while webhook_data.get("more") and webhook_data.get("more") is True:
            webhook_data = make_api_request("webhook_subscriptions", token, {
                "limit": 100,
                "offset": webhook_data.get("offset") + webhook_data.get("limit")
            })
            if webhook_data and "webhook_subscriptions" in webhook_data:
                webhooks.extend(webhook_data["webhook_subscriptions"])
            else:
                break
    
    print(f" Found {len(webhooks)} webhook subscriptions.")
    return webhooks

def generate_output(teams, schedules, escalation_policies, services, webhooks, format_type):
    """Generate output based on the specified format."""
    result = []
    
    # Create a table to store all data
    table = PrettyTable()
    table.field_names = ["Team ID", "Team Name", "Schedule ID", "Schedule Name", 
                         "Escalation Policy ID", "Escalation Policy Name", 
                         "Service ID", "Service Name", 
                         "Webhook ID", "Webhook Name"]
    
    # Map items by team_id for easier lookup
    team_schedules = {}
    team_policies = {}
    team_services = {}
    team_webhooks = {}
    
    for schedule in schedules:
        teams_list = schedule.get("teams", [])
        for team in teams_list:
            team_id = team.get("id")
            if team_id not in team_schedules:
                team_schedules[team_id] = []
            team_schedules[team_id].append({
                "id": schedule.get("id"),
                "name": schedule.get("name")
            })
    
    for policy in escalation_policies:
        teams_list = policy.get("teams", [])
        for team in teams_list:
            team_id = team.get("id")
            if team_id not in team_policies:
                team_policies[team_id] = []
            team_policies[team_id].append({
                "id": policy.get("id"),
                "name": policy.get("name")
            })
    
    for service in services:
        teams_list = service.get("teams", [])
        for team in teams_list:
            team_id = team.get("id")
            if team_id not in team_services:
                team_services[team_id] = []
            team_services[team_id].append({
                "id": service.get("id"),
                "name": service.get("name")
            })
    
    # Webhooks typically don't have team associations directly in the API
    # Assuming they might be associated with services, which are associated with teams
    for webhook in webhooks:
        delivery_method = webhook.get("delivery_method", {})
        if "connection" in delivery_method:
            connection = delivery_method["connection"]
            if "service" in connection:
                service_id = connection["service"]["id"]
                # Find teams associated with this service
                for service in services:
                    if service["id"] == service_id:
                        teams_list = service.get("teams", [])
                        for team in teams_list:
                            team_id = team.get("id")
                            if team_id not in team_webhooks:
                                team_webhooks[team_id] = []
                            team_webhooks[team_id].append({
                                "id": webhook.get("id"),
                                "name": webhook.get("description", "No description")
                            })
    
    # Populate the table
    for team in teams:
        team_id = team.get("id")
        team_name = team.get("name")
        
        schedules_for_team = team_schedules.get(team_id, [{"id": "", "name": ""}])
        policies_for_team = team_policies.get(team_id, [{"id": "", "name": ""}])
        services_for_team = team_services.get(team_id, [{"id": "", "name": ""}])
        webhooks_for_team = team_webhooks.get(team_id, [{"id": "", "name": ""}])
        
        # Get the maximum number of items in any category
        max_items = max(
            len(schedules_for_team),
            len(policies_for_team),
            len(services_for_team),
            len(webhooks_for_team)
        )
        
        # Add rows ensuring we have an entry for each team with the maximum number of items
        for i in range(max_items):
            schedule_id = schedules_for_team[i]["id"] if i < len(schedules_for_team) else ""
            schedule_name = schedules_for_team[i]["name"] if i < len(schedules_for_team) else ""
            
            policy_id = policies_for_team[i]["id"] if i < len(policies_for_team) else ""
            policy_name = policies_for_team[i]["name"] if i < len(policies_for_team) else ""
            
            service_id = services_for_team[i]["id"] if i < len(services_for_team) else ""
            service_name = services_for_team[i]["name"] if i < len(services_for_team) else ""
            
            webhook_id = webhooks_for_team[i]["id"] if i < len(webhooks_for_team) else ""
            webhook_name = webhooks_for_team[i]["name"] if i < len(webhooks_for_team) else ""
            
            # Only show team info in the first row for each team
            if i == 0:
                row = [team_id, team_name, schedule_id, schedule_name, policy_id, policy_name,
                       service_id, service_name, webhook_id, webhook_name]
            else:
                row = ["", "", schedule_id, schedule_name, policy_id, policy_name,
                       service_id, service_name, webhook_id, webhook_name]
            
            table.add_row(row)
            
            # Also store in a structured format for JSON output
            result.append({
                "team_id": team_id if i == 0 else "",
                "team_name": team_name if i == 0 else "",
                "schedule_id": schedule_id,
                "schedule_name": schedule_name,
                "escalation_policy_id": policy_id,
                "escalation_policy_name": policy_name,
                "service_id": service_id,
                "service_name": service_name,
                "webhook_id": webhook_id,
                "webhook_name": webhook_name
            })
    
    if format_type == 'table':
        return table
    elif format_type == 'json':
        return json.dumps(result, indent=2)
    elif format_type == 'csv':
        csv_output = ",".join(table.field_names) + "\n"
        for row in result:
            csv_output += ",".join([
                f'"{row["team_id"]}"',
                f'"{row["team_name"]}"',
                f'"{row["schedule_id"]}"',
                f'"{row["schedule_name"]}"',
                f'"{row["escalation_policy_id"]}"',
                f'"{row["escalation_policy_name"]}"',
                f'"{row["service_id"]}"',
                f'"{row["service_name"]}"',
                f'"{row["webhook_id"]}"',
                f'"{row["webhook_name"]}"'
            ]) + "\n"
        return csv_output

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
    if args.output:
        with open(args.output, 'w') as f:
            f.write(str(output))
        print(f"Results written to {args.output}")
    else:
        print(output)

if __name__ == "__main__":
    main()