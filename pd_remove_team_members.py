import requests
import os
from tabulate import tabulate
import dotenv
import json

dotenv.load_dotenv()

API_KEY = os.environ.get("PD_API_TOKEN")
TEAM_ID = os.environ.get("PD_TEAM_ID")  # Get team ID from environment variable

if not API_KEY:
    API_KEY = input("Enter your PagerDuty API key: ")

if not TEAM_ID:
    TEAM_ID = input("Enter your PagerDuty team ID: ")

headers = {
    "Authorization": f"Token token={API_KEY}",
    "Accept": "application/vnd.pagerduty+json;version=2"
}

def get_schedule_details(schedule_id):
    """Get details about a specific schedule including layers and users."""
    url = f"https://api.pagerduty.com/schedules/{schedule_id}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("schedule", {})

def remove_user_from_schedule(schedule_id, user_id, user_name):
    """Remove a user from a schedule."""
    # First get current schedule details
    schedule = get_schedule_details(schedule_id)
    schedule_name = schedule.get("summary", "Unknown Schedule")
    
    # Check if there are layers and remove the user from each layer
    modified = False
    if "schedule_layers" in schedule:
        for idx, layer in enumerate(schedule.get("schedule_layers", [])):
            # Skip if there are no users in this layer
            if "users" not in layer:
                continue
                
            # Check if user is in this layer
            user_in_layer = any(u.get("id") == user_id for u in layer["users"])
            if user_in_layer:
                # Remove user from this layer
                layer["users"] = [u for u in layer["users"] if u.get("id") != user_id]
                modified = True
                print(f"Removing {user_name} from layer {idx+1} in schedule '{schedule_name}'")
    
    if not modified:
        print(f"User {user_name} not found in any layers of schedule '{schedule_name}'")
        return False
        
    # Update the schedule with the user removed
    update_url = f"https://api.pagerduty.com/schedules/{schedule_id}"
    # Create schedule update payload
    update_data = {
        "schedule": {
            "name": schedule.get("name"),
            "schedule_layers": schedule.get("schedule_layers", [])
        }
    }
    
    try:
        put_resp = requests.put(update_url, headers=headers, json=update_data, timeout=30)
        put_resp.raise_for_status()
        print(f"Successfully removed {user_name} from schedule '{schedule_name}'")
        return True
    except Exception as e:
        print(f"Failed to update schedule '{schedule_name}': {str(e)}")
        return False

def get_escalation_policy_details(policy_id):
    """Get details for a specific escalation policy."""
    url = f"https://api.pagerduty.com/escalation_policies/{policy_id}"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("escalation_policy", {})

def remove_user_from_escalation_policy(policy_id, user_id, user_name):
    """Remove a user from an escalation policy."""
    # Get current policy details
    policy = get_escalation_policy_details(policy_id)
    policy_name = policy.get("summary", "Unknown Policy")
    
    # Check each rule for the user
    modified = False
    if "escalation_rules" in policy:
        for idx, rule in enumerate(policy.get("escalation_rules", [])):
            # Check if user is in this rule's targets
            if "targets" in rule:
                original_length = len(rule["targets"])
                rule["targets"] = [t for t in rule["targets"] if not (t.get("type") == "user" and t.get("id") == user_id)]
                
                if len(rule["targets"]) < original_length:
                    modified = True
                    print(f"Removing {user_name} from rule {idx+1} in policy '{policy_name}'")
    
    if not modified:
        print(f"User {user_name} not found in any rules of policy '{policy_name}'")
        return False
        
    # Update the policy with the user removed
    update_url = f"https://api.pagerduty.com/escalation_policies/{policy_id}"
    # Create policy update payload
    update_data = {
        "escalation_policy": {
            "name": policy.get("name"),
            "escalation_rules": policy.get("escalation_rules", [])
        }
    }
    
    try:
        put_resp = requests.put(update_url, headers=headers, json=update_data, timeout=30)
        put_resp.raise_for_status()
        print(f"Successfully removed {user_name} from policy '{policy_name}'")
        return True
    except Exception as e:
        print(f"Failed to update policy '{policy_name}': {str(e)}")
        return False

# Fetch team members
team_members_url = f"https://api.pagerduty.com/teams/{TEAM_ID}/members"
response = requests.get(team_members_url, headers=headers, timeout=30)
response.raise_for_status()
members = response.json().get("members", [])

# Fetch team schedules
schedules_url = f"https://api.pagerduty.com/schedules?team_ids[]={TEAM_ID.strip()}"
schedules_resp = requests.get(schedules_url, headers=headers, timeout=30)
schedules_resp.raise_for_status()
schedules = schedules_resp.json().get("schedules", [])

# Fetch team escalation policies
escalation_policies_url = f"https://api.pagerduty.com/escalation_policies?team_ids[]={TEAM_ID.strip()}"
escalation_policies_resp = requests.get(escalation_policies_url, headers=headers, timeout=30)
escalation_policies_resp.raise_for_status()
escalation_policies = escalation_policies_resp.json().get("escalation_policies", [])

# Build a mapping of users to their schedules and escalation policies
user_schedules = {}
user_policies = {}

# Check users in schedules
for schedule in schedules:
    schedule_id = schedule.get("id")
    schedule_name = schedule.get("summary", "Unknown")
    users_url = f"https://api.pagerduty.com/schedules/{schedule_id}/users"
    users_resp = requests.get(users_url, headers=headers, timeout=30)
    users_resp.raise_for_status()
    users = users_resp.json().get("users", [])
    
    for user in users:
        user_id = user.get("id")
        if user_id not in user_schedules:
            user_schedules[user_id] = []
        user_schedules[user_id].append({"id": schedule_id, "name": schedule_name})

# Check users in escalation policies
for policy in escalation_policies:
    policy_id = policy.get("id")
    policy_name = policy.get("summary", "Unknown")
    
    policy_detail = get_escalation_policy_details(policy_id)
    for rule in policy_detail.get("escalation_rules", []):
        for target in rule.get("targets", []):
            if target.get("type") == "user":
                user_id = target.get("id")
                if user_id not in user_policies:
                    user_policies[user_id] = []
                if not any(p["id"] == policy_id for p in user_policies.get(user_id, [])):
                    user_policies[user_id].append({"id": policy_id, "name": policy_name})

# Create table data with schedule and escalation policy information
table_data = []
for idx, member in enumerate(members):
    user = member.get("user", {})
    user_id = user.get("id", "")
    user_summary = user.get("summary", "")
    
    # Check if user is on any schedule
    on_schedule = "No"
    if user_id in user_schedules:
        schedules_list = [s["name"] for s in user_schedules[user_id]]
        on_schedule = f"Yes ({', '.join(schedules_list)})"
    
    # Check if user is in any escalation policy
    in_policy = "No"
    if user_id in user_policies:
        policies_list = [p["name"] for p in user_policies[user_id]]
        in_policy = f"Yes ({', '.join(policies_list)})"
    
    table_data.append([idx, user_id, user_summary, on_schedule, in_policy])

print("\n=== Team Members and Their Assignments ===")
print(tabulate(table_data, headers=["#", "User ID", "Name", "On Schedule", "In Escalation Policy"], tablefmt="github"))
print("\n")

# Process each team member
for idx, member in enumerate(members):
    user = member.get("user", {})
    user_id = user.get("id", "")
    user_summary = user.get("summary", "")
    
    print(f"\n--- Processing {user_summary} ---")
    
    # Show user's current assignments
    if user_id in user_schedules:
        print(f"On schedules: {', '.join(s['name'] for s in user_schedules[user_id])}")
    if user_id in user_policies:
        print(f"In escalation policies: {', '.join(p['name'] for p in user_policies[user_id])}")
    if user_id not in user_schedules and user_id not in user_policies:
        print("Not on any schedules or in any escalation policies.")
        
    # Ask if user should be removed
    remove = input(f"Remove {user_summary} from team? (y/N): ").strip().lower()
    
    if remove == "y":
        # First handle schedules if needed
        if user_id in user_schedules:
            print(f"\nRemoving {user_summary} from schedules first:")
            for schedule in user_schedules[user_id]:
                confirm = input(f"Remove {user_summary} from schedule '{schedule['name']}'? (y/N): ").strip().lower()
                if confirm == "y":
                    remove_user_from_schedule(schedule["id"], user_id, user_summary)
                else:
                    print(f"Skipped removing from schedule '{schedule['name']}'")
        
        # Then handle escalation policies if needed
        if user_id in user_policies:
            print(f"\nRemoving {user_summary} from escalation policies:")
            for policy in user_policies[user_id]:
                confirm = input(f"Remove {user_summary} from escalation policy '{policy['name']}'? (y/N): ").strip().lower()
                if confirm == "y":
                    remove_user_from_escalation_policy(policy["id"], user_id, user_summary)
                else:
                    print(f"Skipped removing from escalation policy '{policy['name']}'")
        
        # Finally remove from team
        print(f"\nRemoving {user_summary} from team...")
        remove_url = f"https://api.pagerduty.com/teams/{TEAM_ID}/members/{user_id}"
        del_resp = requests.delete(remove_url, headers=headers, timeout=30)
        if del_resp.status_code == 204:
            print(f"Successfully removed {user_summary} from team.")
        else:
            print(f"Failed to remove {user_summary} from team: {del_resp.text}")
    else:
        print(f"Skipped {user_summary}.")

print("\nDone. All requested user removals have been processed.")