"""DEPRECATED: prefer the PagerDuty MCP server's `list_team_members` tool.

This script lists members of a single PagerDuty team in a table. The same data
is now available via the official PagerDuty MCP server (configured in
`.mcp.json`) through the `list_team_members` tool, which is strictly better for
ad-hoc reads from an MCP-aware client. This script is retained only for users
who need a CLI/CSV-friendly fallback.
"""

import sys
import warnings

import requests
import os
from tabulate import tabulate
import dotenv

dotenv.load_dotenv()

warnings.warn(
    "pd_get_teams_user_role.py is deprecated; use the PagerDuty MCP server's "
    "list_team_members tool. See README.md 'When to use scripts vs MCP'.",
    DeprecationWarning,
    stacklevel=2,
)
print(
    "[deprecated] Prefer the PagerDuty MCP server's list_team_members tool. "
    "See README.md.",
    file=sys.stderr,
)

API_KEY = os.environ.get("PD_API_TOKEN")  # Use .env or environment variable
TEAM_ID = os.environ.get("PD_TEAM_ID")  # Get team ID from environment variable

if not API_KEY:
    API_KEY = input("Enter your PagerDuty API key: ")

if not TEAM_ID:
    TEAM_ID = input("Enter your PagerDuty team ID: ")

headers = {
    "Authorization": f"Token token={API_KEY}",
    "Accept": "application/vnd.pagerduty+json;version=2"
}

# Fetch team members
team_members_url = f"https://api.pagerduty.com/teams/{TEAM_ID}/members"
response = requests.get(team_members_url, headers=headers, timeout=30)
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