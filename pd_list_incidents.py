#!/usr/bin/env python3
"""List and export PagerDuty incidents (read-only) for pipelines and ticketing."""

import argparse
import csv
import json
import sys

from prettytable import PrettyTable

from pd_common import add_token_arguments, get_pd_api_token, paginate

VALID_STATUSES = frozenset({"triggered", "acknowledged", "resolved"})

FIELDNAMES = [
    "id",
    "incident_number",
    "title",
    "status",
    "urgency",
    "created_at",
    "html_url",
    "service_id",
    "service_summary",
    "assignees",
]


def parse_multi(values):
    """Flatten argparse append + comma-separated tokens into a unique ordered list."""
    out = []
    seen = set()
    for raw in values or []:
        for part in raw.split(","):
            s = part.strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
    return out


def normalize_statuses(status_args):
    out = []
    for s in parse_multi(status_args):
        low = s.lower()
        if low not in VALID_STATUSES:
            print(
                f"Error: invalid status {s!r}. Use one of: {', '.join(sorted(VALID_STATUSES))}.",
                file=sys.stderr,
            )
            sys.exit(2)
        out.append(low)
    return out


def build_query_params(since, until, statuses, service_ids, team_ids, user_ids):
    params = {}
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if statuses:
        params["statuses[]"] = statuses
    if service_ids:
        params["service_ids[]"] = service_ids
    if team_ids:
        params["team_ids[]"] = team_ids
    if user_ids:
        params["user_ids[]"] = user_ids
    return params


def fetch_incidents(token, params):
    print("Fetching incidents...", end="", flush=True, file=sys.stderr)
    incidents = list(paginate("incidents", token, params=params))
    print(f" Found {len(incidents)}.", file=sys.stderr)
    if not params.get("since") and not params.get("until"):
        print(
            "Note: no --since/--until filter; export may be large.",
            file=sys.stderr,
        )
    return incidents


def _incident_number(inc):
    n = inc.get("incident_number")
    if n is None:
        n = inc.get("number")
    return str(n) if n is not None else ""


def _assignees_str(inc):
    parts = []
    for a in inc.get("assignments") or []:
        asg = a.get("assignee") or {}
        summ = (asg.get("summary") or "").strip()
        iid = asg.get("id") or ""
        if summ or iid:
            parts.append(f"{summ} ({iid})".strip())
    return " | ".join(parts)


def incident_row(inc):
    svc = inc.get("service") or {}
    return {
        "id": inc.get("id") or "",
        "incident_number": _incident_number(inc),
        "title": inc.get("title") or "",
        "status": inc.get("status") or "",
        "urgency": inc.get("urgency") or "",
        "created_at": inc.get("created_at") or "",
        "html_url": inc.get("html_url") or "",
        "service_id": svc.get("id") or "",
        "service_summary": svc.get("summary") or "",
        "assignees": _assignees_str(inc),
    }


def output_table(rows, outfile):
    t = PrettyTable()
    t.field_names = FIELDNAMES
    t.max_width["title"] = 48
    t.max_width["assignees"] = 40
    for r in rows:
        t.add_row([r[k] for k in FIELDNAMES])
    s = t.get_string()
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(s + "\n")
    else:
        print(s)


def output_csv(rows, outfile):
    out = open(outfile, "w", encoding="utf-8", newline="") if outfile else sys.stdout
    try:
        w = csv.DictWriter(out, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    finally:
        if outfile:
            out.close()


def output_json(rows, outfile):
    payload = json.dumps(rows, indent=2)
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
    else:
        print(payload)


def parse_arguments():
    p = argparse.ArgumentParser(
        description=(
            "Export PagerDuty incidents to table, CSV, or JSON. "
            "Assignees use 'Summary (id)' joined by ' | '. "
            "Prefer --since/--until for bounded exports."
        )
    )
    add_token_arguments(p)
    p.add_argument(
        "-f",
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table)",
    )
    p.add_argument("-o", "--output", help="Write to this file instead of stdout")
    p.add_argument(
        "--since",
        metavar="ISO8601",
        help="Return incidents created or updated on or after this time (UTC, e.g. 2026-01-01T00:00:00Z)",
    )
    p.add_argument(
        "--until",
        metavar="ISO8601",
        help="Return incidents created or updated before this time (UTC)",
    )
    p.add_argument(
        "--status",
        dest="statuses",
        action="append",
        default=[],
        metavar="STATUS",
        help=(
            "Filter by status (repeat or comma-separate): triggered, acknowledged, resolved. "
            "Example: --status triggered,acknowledged"
        ),
    )
    p.add_argument(
        "--service-id",
        dest="service_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Filter by service ID (repeat for multiple). Comma-separated values allowed per flag.",
    )
    p.add_argument(
        "--team-id",
        dest="team_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Filter by team ID (repeat for multiple).",
    )
    p.add_argument(
        "--user-id",
        dest="user_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Incidents assigned to this user ID (repeat for multiple). Resolved incidents are omitted by the API.",
    )
    return p.parse_args()


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    statuses = normalize_statuses(args.statuses)
    service_ids = parse_multi(args.service_ids)
    team_ids = parse_multi(args.team_ids)
    user_ids = parse_multi(args.user_ids)
    params = build_query_params(
        args.since, args.until, statuses, service_ids, team_ids, user_ids
    )
    incidents = fetch_incidents(token, params)
    rows = [incident_row(i) for i in incidents]
    if args.format == "table":
        output_table(rows, args.output)
    elif args.format == "csv":
        output_csv(rows, args.output)
    else:
        output_json(rows, args.output)


if __name__ == "__main__":
    main()
