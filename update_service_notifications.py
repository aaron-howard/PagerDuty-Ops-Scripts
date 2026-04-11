import argparse
from collections.abc import Sequence

from pagerduty import PagerDutyAPIClient
from pagerduty.cli_common import (
    add_deprecated_token_argument,
    add_no_progress_argument,
    add_standard_cli_options,
    apply_cli_config_path,
    apply_log_level_from_args,
    init_cli_env,
    parse_argv,
    progress_wait,
    resolve_api_token_or_exit,
    status_line,
)
from pagerduty.resources import ServicesResource


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Set incident_urgency_rule urgency to severity_based for all services."
    )
    add_standard_cli_options(parser)
    add_deprecated_token_argument(parser)
    add_no_progress_argument(parser)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many services would be updated without calling the API",
    )
    return parser.parse_args(parse_argv(argv))


def _service_needs_urgency_update(service: dict) -> bool:
    rule = service.get("incident_urgency_rule")
    if not rule:
        return True
    return rule.get("urgency") != "severity_based"


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


def main(argv: Sequence[str] | None = None) -> None:
    init_cli_env()
    args = parse_arguments(argv)
    apply_cli_config_path(args)
    apply_log_level_from_args(args)
    pd_api_token = resolve_api_token_or_exit(args.token, allow_prompt=False)

    client = PagerDutyAPIClient(api_token=pd_api_token)
    try:
        services_api = ServicesResource(client)
        with progress_wait(args, "Fetching all services..."):
            services = services_api.list()
        status_line(args, f"Found {len(services)} services.")

        pending = [s for s in services if _service_needs_urgency_update(s)]
        if args.dry_run:
            print(
                f"Dry run: {len(pending)} service(s) would have incident_urgency_rule "
                "set to urgency 'severity_based'."
            )
            for service in pending:
                sid = service["id"]
                print(f"  - {service['name']} ({sid})")
            return

        updated_any = False
        for service in services:
            service_id = service["id"]
            if not _service_needs_urgency_update(service):
                continue
            updated_any = True
            print(f"Updating incident_urgency_rule for service {service['name']} ({service_id})...")
            try:
                update_service_urgency_rule(services_api, service)
                print(f"Service {service['name']} updated.")
            except Exception as e:
                print(f"Failed to update service {service['name']} ({service_id}): {e}")

        if updated_any:
            print(
                "All applicable service incident_urgency_rule values updated to 'severity_based'."
            )
        else:
            print("No services required incident_urgency_rule changes.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
