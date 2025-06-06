import requests
import os
from tabulate import tabulate
import dotenv

dotenv.load_dotenv()

API_KEY = os.environ.get("PD_API_TOKEN")
TEAM_ID = "PSGAUN6"  # Replace with your actual team ID

if not API_KEY:
    API_KEY = input("Enter your PagerDuty API key: ")

headers = {
    "Authorization": f"Token token={API_KEY}",
    "Accept": "application/vnd.pagerduty+json;version=2"
}

# Fetch team members
team_members_url = f"https://api.pagerduty.com/teams/{TEAM_ID}/members"
response = requests.get(team_members_url, headers=headers)
response.raise_for_status()
members = response.json().get("members", [])

# Fetch team schedules (correct endpoint)
schedules_url = f"https://api.pagerduty.com/schedules?team_ids[]={TEAM_ID.strip()}"
schedules_resp = requests.get(schedules_url, headers=headers)
schedules_resp.raise_for_status()
schedules = schedules_resp.json().get("schedules", [])

# Build a set of user IDs on any schedule
scheduled_user_ids = set()
for schedule in schedules:
    schedule_id = schedule.get("id")
    users_url = f"https://api.pagerduty.com/schedules/{schedule_id}/users"
    users_resp = requests.get(users_url, headers=headers)
    users_resp.raise_for_status()
    users = users_resp.json().get("users", [])
    for user in users:
        scheduled_user_ids.add(user.get("id"))

table_data = []
for idx, member in enumerate(members):
    user = member.get("user", {})
    user_id = user.get("id", "")
    user_summary = user.get("summary", "")
    on_schedule = "Yes" if user_id in scheduled_user_ids else "No"
    table_data.append([idx, user_id, user_summary, on_schedule])

print(tabulate(table_data, headers=["#", "User ID", "Summary", "On Schedule"], tablefmt="github"))

# Prompt to remove users not on a schedule
for idx, member in enumerate(members):
    user = member.get("user", {})
    user_id = user.get("id", "")
    user_summary = user.get("summary", "")
    if user_id in scheduled_user_ids:
        print(f"Skipping {user_summary} (on a schedule).")
        continue
    remove = input(f"Remove {user_summary} from team? (y/N): ").strip().lower()
    if remove == "y":
        remove_url = f"https://api.pagerduty.com/teams/{TEAM_ID}/members/{user_id}"
        del_resp = requests.delete(remove_url, headers=headers)
        if del_resp.status_code == 204:
            print(f"Removed {user_summary} from team.")
        else:
            print(f"Failed to remove {user_summary}: {del_resp.text}")
    else:
        print(f"Skipped {user_summary}.")

print("Done.")