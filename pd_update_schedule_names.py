#!/usr/bin/env python3
"""
PagerDuty Schedule Name Update Script

This script connects to PagerDuty API, gets all schedules, and appends 'SCH' 
to the end of schedule names that don't already have it.
"""

import requests
import os
import sys
import argparse
import json
import dotenv
dotenv.load_dotenv()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update PagerDuty schedule names by appending "SCH".')
    parser.add_argument('-t', '--token', help='PagerDuty API token')
    parser.add_argument('-l', '--list', action='store_true', help='List schedules without making changes')
    parser.add_argument('-f', '--filter', help='Only process schedules containing this text in their name')
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

def get_all_schedules(token, name_filter=None):
    """Get all schedules from PagerDuty, with optional filtering by name."""
    print("Fetching schedules...", end="", flush=True)
    schedules = []
    offset = 0
    limit = 100
    total = 0
    
    while True:
        params = {"limit": limit, "offset": offset}
        data = make_api_request("schedules", token, params=params)
        if not data or "schedules" not in data:
            break
        
        # Filter schedules by name if filter is provided
        if name_filter:
            filtered_schedules = [s for s in data["schedules"] if name_filter.lower() in s["name"].lower()]
            schedules.extend(filtered_schedules)
        else:
            schedules.extend(data["schedules"])
        
        if not data.get("more"):
            break
        offset += limit
        total = data.get("total", 0)
    
    print(f" Found {len(schedules)} schedules" + 
          (f" matching filter '{name_filter}'" if name_filter else "") + 
          f" out of {total} total.")
    return schedules

def update_schedule_name(token, schedule_id, current_name, dry_run=False):
    """Update a schedule's name by appending 'SCH' if not already present."""
    if current_name.endswith(" SCH"):
        print(f"Schedule '{current_name}' (ID: {schedule_id}) already has 'SCH' suffix. Skipping.")
        return False
    
    new_name = f"{current_name} SCH"
    
    if dry_run:
        print(f"Would rename schedule '{current_name}' to '{new_name}' (ID: {schedule_id})")
        return True
    
    print(f"Renaming schedule '{current_name}' to '{new_name}' (ID: {schedule_id})...", end="", flush=True)
    
    # Create the update data
    update_data = {
        "schedule": {
            "name": new_name
        }
    }
    
    # Make the API request to update the schedule
    result = make_api_request(f"schedules/{schedule_id}", token, method='PUT', data=update_data)
    
    if result and "schedule" in result:
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

    # Get all schedules from PagerDuty
    schedules = get_all_schedules(token, args.filter)
    
    if args.list:
        # Just list the schedules without making changes
        print("\nCurrent Schedules:")
        print("-" * 80)
        for schedule in schedules:
            print(f"ID: {schedule['id']}, Name: '{schedule['name']}'")
        print("-" * 80)
        print(f"Total: {len(schedules)} schedules")
        return
    
    # Process schedules
    updated_count = 0
    skipped_count = 0
    
    print("\nProcessing schedules...")
    for schedule in schedules:
        if update_schedule_name(token, schedule['id'], schedule['name'], args.dry_run):
            updated_count += 1
        else:
            skipped_count += 1
    
    action_verb = "Would update" if args.dry_run else "Updated"
    print(f"\nSummary: {action_verb} {updated_count} schedules, skipped {skipped_count} schedules.")

if __name__ == "__main__":
    main()
