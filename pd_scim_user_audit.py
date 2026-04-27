#!/usr/bin/env python3
"""Diff PagerDuty SCIM users against an expected-users CSV.

Reads /scim/v2/Users (PagerDuty's SCIM endpoint) and compares it against a CSV
exported from your IdP (Okta, Entra, etc). Reports three buckets:

  - in PagerDuty but not in the expected list  (orphaned users)
  - in the expected list but not in PagerDuty  (missing users)
  - present in both but with field drift       (email/active/displayName)

CSV columns (header row required): email, displayName, active

This is read-only. It prints a report; it does not provision or deprovision.
"""

import argparse
import csv
import sys

import requests

from pd_common import REQUEST_TIMEOUT, get_pd_api_token

SCIM_BASE = "https://api.pagerduty.com/scim/v2"
SCIM_PAGE_SIZE = 100


def parse_arguments():
    parser = argparse.ArgumentParser(description="Diff PagerDuty SCIM users vs an expected-users CSV.")
    parser.add_argument("expected_csv", help="CSV with columns: email, displayName, active")
    parser.add_argument("-t", "--token", help="PagerDuty API token (must have SCIM scope)")
    parser.add_argument("-o", "--output", help="Write the report to this file (default stdout).")
    return parser.parse_args()


def fetch_scim_users(token):
    headers = {
        "Authorization": f"Token token={token}",
        "Accept": "application/scim+json",
    }
    users = []
    start_index = 1
    while True:
        params = {"startIndex": start_index, "count": SCIM_PAGE_SIZE}
        resp = requests.get(f"{SCIM_BASE}/Users", headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        resources = body.get("Resources", [])
        users.extend(resources)
        total = body.get("totalResults", 0)
        if start_index + len(resources) > total or not resources:
            break
        start_index += len(resources)
    return users


def primary_email(scim_user):
    for entry in scim_user.get("emails", []) or []:
        if entry.get("primary"):
            return (entry.get("value") or "").lower()
    if scim_user.get("emails"):
        return (scim_user["emails"][0].get("value") or "").lower()
    return ""


def normalize_pd_user(u):
    return {
        "id": u.get("id"),
        "email": primary_email(u),
        "displayName": u.get("displayName") or "",
        "active": bool(u.get("active", True)),
    }


def load_expected(path):
    required = {"email", "displayName", "active"}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"Error: CSV missing required columns: {sorted(missing)}", file=sys.stderr)
            sys.exit(2)
        out = {}
        for row in reader:
            email = (row.get("email") or "").strip().lower()
            if not email:
                continue
            out[email] = {
                "email": email,
                "displayName": (row.get("displayName") or "").strip(),
                "active": (row.get("active") or "").strip().lower() in {"true", "yes", "1", "active"},
            }
        return out


def diff(pd_users, expected):
    pd_by_email = {u["email"]: u for u in pd_users if u["email"]}
    pd_emails = set(pd_by_email)
    expected_emails = set(expected)

    orphans = sorted(pd_emails - expected_emails)
    missing = sorted(expected_emails - pd_emails)
    drifts = []
    for email in sorted(pd_emails & expected_emails):
        pd = pd_by_email[email]
        exp = expected[email]
        diffs = []
        if pd["displayName"] != exp["displayName"]:
            diffs.append(f"displayName: pd={pd['displayName']!r} expected={exp['displayName']!r}")
        if pd["active"] != exp["active"]:
            diffs.append(f"active: pd={pd['active']} expected={exp['active']}")
        if diffs:
            drifts.append((email, pd["id"], "; ".join(diffs)))
    return orphans, missing, drifts


def render(orphans, missing, drifts):
    lines = []
    lines.append(f"=== Orphaned in PagerDuty ({len(orphans)}) ===")
    lines.extend(f"  {e}" for e in orphans)
    lines.append("")
    lines.append(f"=== Missing from PagerDuty ({len(missing)}) ===")
    lines.extend(f"  {e}" for e in missing)
    lines.append("")
    lines.append(f"=== Field drift ({len(drifts)}) ===")
    for email, pd_id, detail in drifts:
        lines.append(f"  {email} ({pd_id}): {detail}")
    return "\n".join(lines) + "\n"


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token)
    expected = load_expected(args.expected_csv)
    print(f"Loaded {len(expected)} expected users from {args.expected_csv}", file=sys.stderr)

    print("Fetching PagerDuty SCIM users...", end="", flush=True, file=sys.stderr)
    pd_users_raw = fetch_scim_users(token)
    pd_users = [normalize_pd_user(u) for u in pd_users_raw]
    print(f" got {len(pd_users)}.", file=sys.stderr)

    orphans, missing, drifts = diff(pd_users, expected)
    report = render(orphans, missing, drifts)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(report)


if __name__ == "__main__":
    main()
