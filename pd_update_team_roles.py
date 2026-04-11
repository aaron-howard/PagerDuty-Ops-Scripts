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

    team_id = team_id.strip()
    client = PagerDutyAPIClient(api_token=api_key)
    try:
        teams = TeamsResource(client)
        members = teams.get_members(team_id)

        table_data = []
        for idx, member in enumerate(members):
            user = member.get("user", {})
            user_id = user.get("id", "")
            user_type = user.get("type", "")
            user_summary = user.get("summary", "")
            user_role = member.get("role", "")
            table_data.append([idx, user_id, user_type, user_summary, user_role])

        print(tabulate(table_data, headers=["#", "ID", "Type", "Summary", "Role"], tablefmt="github"))

        for idx, member in enumerate(members):
            user = member.get("user", {})
            user_id = user.get("id", "")
            user_summary = user.get("summary", "")
            current_role = member.get("role", "")
            print(f"\nUser: {user_summary} (Current Role: {current_role})")
            new_role = input("Enter new role (manager, responder, observer) or press Enter to skip: ").strip()
            if new_role and new_role != current_role:
                try:
                    teams.update_member_role(team_id, user_id, new_role)
                    print(f"Updated {user_summary} to role '{new_role}'.")
                except Exception as e:
                    print(f"Failed to update {user_summary}: {e}")
            else:
                print("Skipped.")

        print("Done.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
