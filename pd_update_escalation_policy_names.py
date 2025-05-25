#!/usr/bin/env python3
"""
PagerDuty Escalation Policy Name Update Script

This script connects to PagerDuty API, gets all escalation policies, and appends 'EP' 
to the end of escalation policy names that don't already have it.
"""

import requests
import os
import sys
import argparse
import json

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
        token = input("Enter your PagerDuty API token: ")
    return token

def make_api_request(endpoint, token, method='GET', params=None, data=None):
    """Make a request to the PagerDuty API."""
    base_url = "https://api.pagerduty.com"
    headers = {
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Authorization": f"Token token={token}",
        "Content-Type": "application/json"
    }

    url = f"{base_url}/{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        else:
            print(f"Error: Unsupported method {method}")
            return None
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: API request failed - {e}")
        return None

    try:
        return response.json() if response.text else {}
    except Exception as e:
        print(f"Error decoding JSON: {e}")
        return None

def get_all_escalation_policies(token, name_filter=None):
    """Get all escalation policies from PagerDuty, with optional filtering by name."""
    print("Fetching escalation policies...", end="", flush=True)
    policies = []
    offset = 0
    limit = 100
    total = 0
    
    while True:
        params = {"limit": limit, "offset": offset}
        data = make_api_request("escalation_policies", token, params=params)
        if not data or "escalation_policies" not in data:
            break
        
        # Filter policies by name if filter is provided
        if name_filter:
            filtered_policies = [p for p in data["escalation_policies"] if name_filter.lower() in p["name"].lower()]
            policies.extend(filtered_policies)
        else:
            policies.extend(data["escalation_policies"])
        
        if not data.get("more"):
            break
        offset += limit
        total = data.get("total", 0)
    
    print(f" Found {len(policies)} escalation policies" + 
          (f" matching filter '{name_filter}'" if name_filter else "") + 
          f" out of {total} total.")
    return policies

def update_escalation_policy_name(token, policy_id, current_name, dry_run=False):
    """Update an escalation policy's name by appending 'EP' if not already present."""
    if current_name.strip().endswith(" EP"):
        print(f"Escalation Policy '{current_name}' (ID: {policy_id}) already has 'EP' suffix. Skipping.")
        return False
    
    new_name = f"{current_name.strip()} EP"
    
    if dry_run:
        print(f"Would rename escalation policy '{current_name}' to '{new_name}' (ID: {policy_id})")
        return True
    
    print(f"Renaming escalation policy '{current_name}' to '{new_name}' (ID: {policy_id})...", end="", flush=True)
    
    # Create the update data
    update_data = {
        "escalation_policy": {
            "name": new_name
        }
    }
    
    # Make the API request to update the escalation policy
    result = make_api_request(f"escalation_policies/{policy_id}", token, method='PUT', data=update_data)
    
    if result and "escalation_policy" in result:
        print(" Success!")
        return True
    else:
        print(" Failed.")
        return False

def main():
    """Main function to run the script."""
    args = parse_arguments()

    # Get API token
    token = args.token if args.token else get_pd_api_token()
    if not token:
        print("Error: No API token provided.")
        sys.exit(1)

    # Get all escalation policies from PagerDuty
    policies = get_all_escalation_policies(token, args.filter)
    
    if args.list:
        # Just list the escalation policies without making changes
        print("\nCurrent Escalation Policies:")
        print("-" * 80)
        for policy in policies:
            print(f"ID: {policy['id']}, Name: '{policy['name']}'")
        print("-" * 80)
        print(f"Total: {len(policies)} escalation policies")
        return

    # Confirm before proceeding (if not in dry run mode)
    if not args.dry_run and policies:
        confirm = input(f"\nThis will update {len(policies)} escalation policy names. Do you want to proceed? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
    
    # Process escalation policies
    updated_count = 0
    skipped_count = 0
    
    print("\nProcessing escalation policies...")
    for policy in policies:
        if update_escalation_policy_name(token, policy['id'], policy['name'], args.dry_run):
            updated_count += 1
        else:
            skipped_count += 1
    
    action_verb = "Would update" if args.dry_run else "Updated"
    print(f"\nSummary: {action_verb} {updated_count} escalation policies, skipped {skipped_count} escalation policies.")

if __name__ == "__main__":
    main()
