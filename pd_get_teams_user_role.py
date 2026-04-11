import os

from tabulate import tabulate
import dotenv

from pagerduty import PagerDutyAPIClient
from pagerduty.resources import TeamsResource

dotenv.load_dotenv()


def main():
    api_key = os.environ.get("PD_API_TOKEN")
    team_id = os.environ.get("PD_TEAM_ID")

    if not api_key:
        api_key = input("Enter your PagerDuty API key: ")

    if not team_id:
        team_id = input("Enter your PagerDuty team ID: ")

    client = PagerDutyAPIClient(api_token=api_key)
    try:
        teams = TeamsResource(client)
        members = teams.get_members(team_id.strip())

        table_data = []
        for member in members:
            user = member.get("user", {})
            user_id = user.get("id", "")
            user_type = user.get("type", "")
            user_summary = user.get("summary", "")
            user_role = member.get("role", "")
            table_data.append([user_id, user_type, user_summary, user_role])

        print(tabulate(table_data, headers=["ID", "Type", "Summary", "Role"], tablefmt="github"))
    finally:
        client.close()


if __name__ == "__main__":
    main()
