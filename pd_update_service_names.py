#!/usr/bin/env python3
"""
PagerDuty Service Name Update Script

This script connects to PagerDuty API and updates service names by appending "SVC" 
to the end of each service name if it doesn't already end with "SVC".
"""

import requests
import os
import sys
import json
import argparse
import getpass
import dotenv
dotenv.load_dotenv()

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update PagerDuty service names by appending "SVC".')
    parser.add_argument('-t', '--token', help='PagerDuty API token')
    parser.add_argument('-d', '--dry-run', action='store_true', 
                        help='Perform a dry run (show what would change without making changes)')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List services without making changes')
    parser.add_argument('-f', '--filter', 
                        help='Filter services by name (only update services containing this string)')
    return parser.parse_args()

def get_pd_api_token():
    """Get PagerDuty API token from environment variable or user input."""
    token = os.environ.get('PD_API_TOKEN')
    if not token:
        token = getpass.getpass("Enter your PagerDuty API token: ")
    return token

def make_api_request(endpoint, token, method='GET', data=None, params=None):
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
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data, timeout=30)
        else:
            print(f"Error: Unsupported method {method}")
            return None
        
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: API request failed - {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None

    try:
        return response.json()
    except Exception as e:
        print(f"Error decoding JSON: {e}")
        return None

def get_all_services(token, name_filter=None):
    """Get all services from PagerDuty with optional name filtering."""
    print(f"Fetching services...", end="", flush=True)
    services = []
    offset = 0
    limit = 100
    while True:
        params = {"limit": limit, "offset": offset}
        data = make_api_request("services", token, params=params)
        if not data or "services" not in data:
            break
        
        # Apply name filter if provided
        if name_filter:
            filtered_services = [s for s in data["services"] if name_filter.lower() in s.get("name", "").lower()]
            services.extend(filtered_services)
        else:
            services.extend(data["services"])
            
        if not data.get("more"):
            break
        offset += limit
    
    print(f" Found {len(services)} services.")
    return services

def update_service_name(token, service_id, new_name, dry_run=False):
    """Update the name of a service."""
    if dry_run:
        print(f"Would update service {service_id} to name: {new_name}")
        return True
    
    data = {
        "service": {
            "name": new_name
        }
    }
    
    result = make_api_request(f"services/{service_id}", token, method='PUT', data=data)
    if result:
        print(f"Successfully updated service {service_id} to: {new_name}")
        return True
    else:
        print(f"Failed to update service {service_id}")
        return False

def main():
    """Main function to run the script."""
    args = parse_arguments()

    # Get API token
    token = args.token if args.token else get_pd_api_token()
    if not token:
        print("Error: No API token provided.")
        sys.exit(1)

    # Get all services from PagerDuty
    services = get_all_services(token, args.filter)
    
    if args.list:
        # Just list the services
        print("\nCurrent Services:")
        print("----------------")
        for service in services:
            print(f"ID: {service.get('id')}, Name: {service.get('name')}")
        return

    # Count of services that need updating
    to_update = [s for s in services if not s.get('name', '').strip().endswith('SVC')]
    print(f"\nFound {len(to_update)} services that need 'SVC' appended to their name.")
    
    if not to_update:
        print("No services need updating.")
        return
    
    # Confirm before proceeding
    if not args.dry_run:
        confirm = input("\nDo you want to proceed with updating these service names? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return
    
    # Update service names
    updated_count = 0
    failed_count = 0
    
    for service in to_update:
        service_id = service.get('id')
        current_name = service.get('name', '')
        
        # Skip if it already ends with SVC
        if current_name.strip().endswith('SVC'):
            continue
            
        new_name = f"{current_name.strip()} SVC"
        
        # Update the service name
        success = update_service_name(token, service_id, new_name, args.dry_run)
        if success:
            updated_count += 1
        else:
            failed_count += 1
    
    # Print summary
    if args.dry_run:
        print(f"\nDry run complete. {updated_count} services would be updated.")
    else:
        print(f"\nUpdate complete. {updated_count} services updated, {failed_count} failed.")

if __name__ == "__main__":
    main()
