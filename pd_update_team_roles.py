import requests
import os
from tabulate import tabulate
import dotenv

dotenv.load_dotenv()

API_KEY = os.environ.get("PD_API_TOKEN")
TEAM_ID = "P8Y1SIT"  # Replace with your actual team ID

if not API_KEY:
    API_KEY = input("Enter your PagerDuty API key: ")

headers = {
    "Authorization": f"Token token={API_KEY}",
    "Accept": "application/vnd.pagerduty+json;version=2",
    "Content-Type": "application/json"
}

# Fetch team members
team_members_url = f"https://api.pagerduty.com/teams/{TEAM_ID}/members"
response = requests.get(team_members_url, headers=headers)
response.raise_for_status()
members = response.json().get("members", [])

table_data = []
for idx, member in enumerate(members):
    user = member.get("user", {})
    user_id = user.get("id", "")
    user_type = user.get("type", "")
    user_summary = user.get("summary", "")
    user_role = member.get("role", "")
    table_data.append([idx, user_id, user_type, user_summary, user_role])

print(tabulate(table_data, headers=["#", "ID", "Type", "Summary", "Role"], tablefmt="github"))

# Prompt user to update roles
for idx, member in enumerate(members):
    user = member.get("user", {})
    user_id = user.get("id", "")
    user_summary = user.get("summary", "")
    current_role = member.get("role", "")
    print(f"\nUser: {user_summary} (Current Role: {current_role})")
    new_role = input("Enter new role (manager, responder, observer) or press Enter to skip: ").strip()
    if new_role and new_role != current_role:
        patch_url = f"https://api.pagerduty.com/teams/{TEAM_ID}/members/{user_id}"
        payload = {"role": new_role}
        patch_resp = requests.patch(patch_url, headers=headers, json=payload)
        if patch_resp.status_code == 200:
            print(f"Updated {user_summary} to role '{new_role}'.")
        else:
            print(f"Failed to update {user_summary}: {patch_resp.text}")
    else:
        print("Skipped.")

print("Done.")