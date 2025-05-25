#!/usr/bin/env python3
"""
Update PagerDuty user roles script.

Lists all users and updates their roles as needed.
API token should be set via the PD_API_TOKEN environment variable.
"""

import requests
import os

API_TOKEN = os.environ.get('PD_API_TOKEN')
if not API_TOKEN:
    raise RuntimeError("Please set the PD_API_TOKEN environment variable.")

HEADERS = {
    'Authorization': f'Token token={API_TOKEN}',
    'Accept': 'application/vnd.pagerduty+json;version=2',
    'Content-Type': 'application/json'
}

def get_all_users():
    """Fetch all PagerDuty users with pagination and error handling."""
    users = []
    offset = 0
    limit = 100
    while True:
        try:
            resp = requests.get(
                'https://api.pagerduty.com/users',
                headers=HEADERS,
                params={'limit': limit, 'offset': offset}
            )
            print(f"Status: {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"API or JSON error: {e}")
            break
        users.extend(data.get('users', []))
        if not data.get('more'):
            break
        offset += limit
    return users

def update_user_role(user_id, new_role):
    """Update the role of a PagerDuty user."""
    try:
        resp = requests.patch(
            f'https://api.pagerduty.com/users/{user_id}',
            headers=HEADERS,
            json={'user': {'role': new_role}}
        )
        if resp.status_code == 200:
            print(f"Updated user {user_id} to role '{new_role}'.")
        else:
            print(f"Failed to update user {user_id}: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Exception updating user {user_id}: {e}")

def main():
    users = get_all_users()
    # Example: promote all 'observer' users to 'user'
    observer_users = [u for u in users if u.get('role') == 'observer']
    for user in observer_users:
        user_id = user['id']
        update_user_role(user_id, 'user')

if __name__ == "__main__":
    main()