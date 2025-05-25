import requests

API_TOKEN = 'u+jXY4zuU5iesV9veNLg'
HEADERS = {
    'Authorization': f'Token token={API_TOKEN}',
    'Accept': 'application/vnd.pagerduty+json;version=2',
    'Content-Type': 'application/json'
}

# 1. List users
def get_all_users():
    users = []
    offset = 0
    while True:
        resp = requests.get(
            'https://api.pagerduty.com/users',
            headers=HEADERS,
            params={'limit': 100, 'offset': offset}
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"API Error: {resp.status_code} - {resp.text}")
            break
        try:
            data = resp.json()
        except Exception as e:
            print(f"JSON decode error: {e}")
            print(resp.text)
            break
        users.extend(data['users'])
        if not data.get('more'):
            break
        offset += 100
    return users

# 2. Filter for observers
users = get_all_users()
observer_users = [u for u in users if u['role'] == 'user']

# 3 & 4. Update each observer user (example: promote to 'user' role)
for user in observer_users:
    user_id = user['id']
    resp = requests.patch(
        f'https://api.pagerduty.com/users/{user_id}',
        headers=HEADERS,
        json={'user': {'role': 'observer'}}
    )
    print(f"Updated user {user['name']}: {resp.status_code}")