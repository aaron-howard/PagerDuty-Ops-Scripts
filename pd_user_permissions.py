import requests

API_KEY = "u+uFYRCsJKzuwAHXtHVA"  # Replace with your actual API ke
USER_ID = "PFV7M6N" # Replace with your actual user ID
URL = f"https://api.pagerduty.com/users/{USER_ID}/permissions"

headers = {
    "Authorization": f"Token token={API_KEY}",
    "Accept": "application/json"
}

def get_user_permissions():
    response = requests.get(URL, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code} - {response.text}"

# Call the function and print the result
permissions = get_user_permissions()
print(permissions)
