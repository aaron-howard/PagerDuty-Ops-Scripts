#!/usr/bin/env python3
"""Export PagerDuty service-standards adoption to CSV or table.

Pulls /standards/scores/{resource_type} and reports per-resource pass/fail
counts plus the per-standard breakdown. Read-only; intended for compliance
dashboards and adoption tracking.
"""

import argparse
import csv
import io
import sys

from pd_common import add_token_arguments, get_pd_api_token, make_api_request


def parse_arguments():
    parser = argparse.ArgumentParser(description="Export PagerDuty standards adoption.")
    add_token_arguments(parser)
    parser.add_argument(
        "--resource-type",
        default="technical_services",
        choices=["technical_services", "teams"],
        help="Resource type to score (default: technical_services).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "csv"],
        default="table",
        help="Output format (default: table).",
    )
    parser.add_argument("-o", "--output", help="Output file (default stdout).")
    parser.add_argument(
        "--failing-only",
        action="store_true",
        help="Include only resources with at least one failing standard.",
    )
    return parser.parse_args()


def fetch_scores(token, resource_type):
    data = make_api_request(f"standards/scores/{resource_type}", token)
    if not data:
        return []
    return data.get("resources") or data.get("scores") or []


def render_csv(rows):
    buf = io.StringIO()
    fields = ["resource_id", "resource_name", "passing", "total", "failing_standards"]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def render_table(rows):
    try:
        from tabulate import tabulate
    except ImportError:
        return render_csv(rows)
    return tabulate(
        [[r["resource_id"], r["resource_name"], r["passing"], r["total"], r["failing_standards"]] for r in rows],
        headers=["ID", "Name", "Pass", "Total", "Failing"],
        tablefmt="github",
    ) + "\n"


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    print(f"Fetching standards scores for {args.resource_type}...", end="", flush=True, file=sys.stderr)
    raw = fetch_scores(token, args.resource_type)
    print(f" got {len(raw)} resources.", file=sys.stderr)

    rows = []
    for entry in raw:
        resource = entry.get("resource") or entry
        score = entry.get("score") or entry
        passing = score.get("passing") if isinstance(score, dict) else None
        total = score.get("total") if isinstance(score, dict) else None
        standards = entry.get("standards") or []
        failing_labels = [s.get("name", "") for s in standards if not s.get("pass", True)]
        if args.failing_only and not failing_labels:
            continue
        rows.append({
            "resource_id": resource.get("id", ""),
            "resource_name": resource.get("name", "") or resource.get("summary", ""),
            "passing": passing if passing is not None else (len(standards) - len(failing_labels)),
            "total": total if total is not None else len(standards),
            "failing_standards": "; ".join(failing_labels),
        })

    rows.sort(key=lambda r: (r["total"] - r["passing"] if isinstance(r["passing"], int) and isinstance(r["total"], int) else 0), reverse=True)

    payload = render_csv(rows) if args.format == "csv" else render_table(rows)
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        print(f"Wrote {len(rows)} rows to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
