#!/usr/bin/env python3
"""
Update PagerDuty user roles script.

Promotes every account whose role is `observer` to the `user` role.
API token must be set via the PD_API_TOKEN environment variable.
"""

import os

import dotenv

from pagerduty import PagerDutyAPIClient
from pagerduty.resources import UsersResource

dotenv.load_dotenv()

API_TOKEN = os.environ.get("PD_API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("Please set the PD_API_TOKEN environment variable.")


def update_user_role(client: PagerDutyAPIClient, user_id: str, new_role: str) -> None:
    """Update the role of a PagerDuty user."""
    try:
        client.patch(f"users/{user_id}", json_data={"user": {"role": new_role}})
        print(f"Updated user {user_id} to role '{new_role}'.")
    except Exception as e:
        print(f"Exception updating user {user_id}: {e}")


def main():
    client = PagerDutyAPIClient(api_token=API_TOKEN)
    try:
        users_api = UsersResource(client)
        users = users_api.list()
        observers = [u for u in users if u.get("role") == "observer"]
        for user in observers:
            user_id = user["id"]
            update_user_role(client, user_id, "user")
    finally:
        client.close()


if __name__ == "__main__":
    main()
