#!/usr/bin/env python3
"""Set every PagerDuty service's incident_urgency_rule to 'severity_based'."""

import argparse

from pd_common import fetch_all, get_pd_api_token, make_api_request


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Set incident_urgency_rule.urgency to 'severity_based' on all services."
    )
    parser.add_argument("-t", "--token", help="PagerDuty API token")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which services would be updated without making changes.",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    return parser.parse_args()


def update_service_urgency_rule(token, service, dry_run=False):
    service_id = service["id"]
    rule = dict(service.get("incident_urgency_rule") or {"type": "constant"})
    rule["urgency"] = "severity_based"
    if dry_run:
        return True
    result = make_api_request(
        f"services/{service_id}",
        token,
        method="PUT",
        data={"service": {"incident_urgency_rule": rule}},
    )
    return result is not None


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token)

    services = fetch_all("services", token, label="services")
    pending = [s for s in services if (s.get("incident_urgency_rule") or {}).get("urgency") != "severity_based"]
    print(f"\n{len(pending)} services need urgency='severity_based'.")
    if not pending:
        return

    if not args.dry_run and not args.yes:
        answer = input(f"Update {len(pending)} services? (y/n): ").strip().lower()
        if answer != "y":
            print("Operation cancelled.")
            return

    updated = 0
    failed = 0
    for service in pending:
        name = service.get("name", service["id"])
        if args.dry_run:
            print(f"Would update {name} ({service['id']})")
            updated += 1
            continue
        try:
            if update_service_urgency_rule(token, service):
                print(f"Updated {name} ({service['id']})")
                updated += 1
            else:
                print(f"Failed to update {name} ({service['id']})")
                failed += 1
        except Exception as e:
            print(f"Failed to update {name} ({service['id']}): {e}")
            failed += 1

    verb = "Would update" if args.dry_run else "Updated"
    print(f"\nSummary: {verb} {updated} services, {failed} failed.")


if __name__ == "__main__":
    main()
