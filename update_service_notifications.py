import os
import sys

from dotenv import load_dotenv

from pagerduty import PagerDutyAPIClient
from pagerduty.resources import ServicesResource

load_dotenv()


def update_service_urgency_rule(services_api: ServicesResource, service: dict) -> dict:
    service_id = service["id"]
    incident_urgency_rule = service.get("incident_urgency_rule", {})
    if not incident_urgency_rule:
        incident_urgency_rule = {
            "type": "constant",
            "urgency": "severity_based",
        }
    else:
        incident_urgency_rule = dict(incident_urgency_rule)
        incident_urgency_rule["urgency"] = "severity_based"

    return services_api.update(service_id, {"incident_urgency_rule": incident_urgency_rule})


def main() -> None:
    pd_api_token = os.getenv("PD_API_TOKEN")
    if not pd_api_token:
        print("PagerDuty API token not found. Please set PD_API_TOKEN in your environment or .env file.")
        sys.exit(1)

    client = PagerDutyAPIClient(api_token=pd_api_token)
    try:
        services_api = ServicesResource(client)
        print("Fetching all services...")
        services = services_api.list()
        print(f"Found {len(services)} services.")

        for service in services:
            service_id = service["id"]
            print(f"Updating incident_urgency_rule for service {service['name']} ({service_id})...")
            try:
                update_service_urgency_rule(services_api, service)
                print(f"Service {service['name']} updated.")
            except Exception as e:
                print(f"Failed to update service {service['name']} ({service_id}): {e}")

        print("All service incident_urgency_rule values updated to 'severity_based'.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
