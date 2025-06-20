import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()
PD_API_TOKEN = os.getenv("PD_API_TOKEN")
PD_API_URL = "https://api.pagerduty.com/services"
HEADERS = {
    "Authorization": f"Token token={PD_API_TOKEN}",
    "Accept": "application/vnd.pagerduty+json;version=2",
    "Content-Type": "application/json"
}

def get_all_services():
    services = []
    url = PD_API_URL
    while url:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        services.extend(data.get("services", []))
        if data.get("more"):
            next_offset = data.get("offset", 0) + data.get("limit", 100)
            url = f"{PD_API_URL}?offset={next_offset}&limit=100"
        else:
            url = None
    return services

def update_service_urgency_rule(service):
    service_id = service["id"]
    # Set urgency to 'severity_based' for dynamic notifications based on alert severity
    incident_urgency_rule = service.get("incident_urgency_rule", {})
    if not incident_urgency_rule:
        incident_urgency_rule = {
            "type": "constant",
            "urgency": "severity_based"
        }
    else:
        incident_urgency_rule["urgency"] = "severity_based"

    payload = {
        "service": {
            "incident_urgency_rule": incident_urgency_rule
        }
    }
    resp = requests.put(f"{PD_API_URL}/{service_id}", headers=HEADERS, json=payload)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    if not PD_API_TOKEN:
        print("PagerDuty API token not found. Please set PD_API_TOKEN in your environment or .env file.")
        exit(1)

    print("Fetching all services...")
    services = get_all_services()
    print(f"Found {len(services)} services.")

    for service in services:
        service_id = service["id"]
        print(f"Updating incident_urgency_rule for service {service['name']} ({service_id})...")
        try:
            update_service_urgency_rule(service)
            print(f"Service {service['name']} updated.")
        except Exception as e:
            print(f"Failed to update service {service['name']} ({service_id}): {e}")

    print("All service incident_urgency_rule values updated to 'severity_based'.")