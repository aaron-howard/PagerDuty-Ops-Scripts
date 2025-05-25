import requests
import os
from tabulate import tabulate
import dotenv

dotenv.load_dotenv()

API_KEY = os.environ.get("PD_API_TOKEN")  # Use .env or environment variable
TEAM_ID = "PDMGZ7E"  # Replace with your actual team ID

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

table_data = []

for member in members:
    user = member.get("user", {})
    user_id = user.get("id", "")
    user_type = user.get("type", "")
    user_summary = user.get("summary", "")
    user_role = member.get("role", "")  # Role is included in the member object

    table_data.append([user_id, user_type, user_summary, user_role])

print(tabulate(table_data, headers=["ID", "Type", "Summary", "Role"], tablefmt="github"))