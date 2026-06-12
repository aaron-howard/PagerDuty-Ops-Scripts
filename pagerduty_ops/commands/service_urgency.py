"""Set every PagerDuty service's incident_urgency_rule to 'severity_based'.

Idempotent: services already at severity_based are skipped.
"""

from __future__ import annotations

import sys

from ..api import PDApiError, fetch_all, request
from ..cli import confirm, finish_bulk, init, standard_parser
from ..log import get_logger

log = get_logger("service_urgency")


def build_parser():
    return standard_parser(
        "Set incident_urgency_rule.urgency to 'severity_based' on all services.",
        write_guards=True,
    )


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)

    services = fetch_all("services", token, label="services")
    pending = [
        s for s in services
        if (s.get("incident_urgency_rule") or {}).get("urgency") != "severity_based"
    ]
    log.info("%d services need urgency='severity_based'.", len(pending))
    if not pending:
        return 0

    if not confirm(f"Update {len(pending)} services?", assume_yes=args.yes,
                   dry_run=args.dry_run):
        return 0

    updated = failed = 0
    for service in pending:
        name = service.get("name", service["id"])
        if args.dry_run:
            print(f"[dry-run] would update {name} ({service['id']})", file=sys.stderr)
            updated += 1
            continue
        rule = dict(service.get("incident_urgency_rule") or {"type": "constant"})
        rule["urgency"] = "severity_based"
        try:
            request(f"services/{service['id']}", token, method="PUT",
                    data={"service": {"incident_urgency_rule": rule}})
            log.info("Updated %s (%s)", name, service["id"])
            updated += 1
        except PDApiError as e:
            if e.is_auth_error:
                raise
            log.error("Failed to update %s (%s): %s", name, service["id"], e)
            failed += 1

    return finish_bulk(updated, failed, dry_run=args.dry_run, label="services")
