import requests
import os
import dotenv

dotenv.load_dotenv()

API_KEY = os.environ.get("PD_API_TOKEN")
USER_ID = os.environ.get("PD_USER_ID")  # Optionally set in .env, or prompt

if not API_KEY:
    API_KEY = input("Enter your PagerDuty API key: ")
if not USER_ID:
    USER_ID = input("Enter the PagerDuty user ID: ")

URL = f"https://api.pagerduty.com/users/{USER_ID}/permissions"

headers = {
    "Authorization": f"Token token={API_KEY}",
    "Accept": "application/json"
}

def get_user_permissions():
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return f"Error: {e}"

if __name__ == "__main__":
    permissions = get_user_permissions()
    print(permissions)
