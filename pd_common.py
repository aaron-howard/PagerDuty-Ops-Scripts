"""Shared helpers for the PagerDuty operations scripts."""

import getpass
import os
import sys

import dotenv
import requests

dotenv.load_dotenv()

PD_API_BASE = "https://api.pagerduty.com"
PD_API_HEADERS_ACCEPT = "application/vnd.pagerduty+json;version=2"
REQUEST_TIMEOUT = 30


def add_token_arguments(parser):
    """Register standard -t/--token and --prompt flags on an argparse parser."""
    parser.add_argument(
        "-t",
        "--token",
        help="PagerDuty API token (prefer PD_API_TOKEN environment variable)",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Prompt securely for API token when PD_API_TOKEN is unset (local dev only)",
    )


def get_pd_api_token(cli_token=None, *, allow_prompt=False):
    """Resolve the PagerDuty API token from CLI arg, PD_API_TOKEN, or optional prompt."""
    token = cli_token or os.environ.get("PD_API_TOKEN")
    if not token and allow_prompt:
        token = getpass.getpass("Enter your PagerDuty API token: ")
    if not token:
        print(
            "Error: No API token provided. Set PD_API_TOKEN, pass -t/--token, "
            "or use --prompt for interactive entry.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def get_pd_team_id(cli_team_id=None):
    """Resolve the PagerDuty team ID from CLI arg, env, or interactive prompt."""
    team_id = cli_team_id or os.environ.get("PD_TEAM_ID")
    if not team_id:
        team_id = input("Enter your PagerDuty team ID: ")
    if not team_id:
        print("Error: No team ID provided.")
        sys.exit(1)
    return team_id.strip()


def build_headers(token):
    return {
        "Accept": PD_API_HEADERS_ACCEPT,
        "Authorization": f"Token token={token}",
        "Content-Type": "application/json",
    }


def make_api_request(endpoint, token, method="GET", params=None, data=None, extra_headers=None):
    """Make a request to the PagerDuty API. Returns parsed JSON or None on error."""
    url = f"{PD_API_BASE}/{endpoint}"
    headers = build_headers(token)
    if extra_headers:
        headers.update(extra_headers)
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, params=params, timeout=REQUEST_TIMEOUT)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
        else:
            print(f"Error: Unsupported method {method}")
            return None
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error: API request failed - {e}")
        if getattr(e, "response", None) is not None and e.response.text:
            print(f"Response: {e.response.text}")
        return None

    if not response.text:
        return {}
    try:
        return response.json()
    except ValueError as e:
        print(f"Error decoding JSON: {e}")
        return None


def paginate(resource, token, params=None, page_size=100, extra_headers=None, items_key=None):
    """Yield items from a paginated PagerDuty list endpoint.

    `items_key` defaults to the last path segment of `resource` (so "schedules"
    for resource="v3/schedules"). Set explicitly when the response key differs
    from the URL path.
    """
    base_params = dict(params or {})
    key = items_key or resource.rsplit("/", 1)[-1]
    offset = 0
    while True:
        page_params = {**base_params, "limit": page_size, "offset": offset}
        data = make_api_request(resource, token, params=page_params, extra_headers=extra_headers)
        if not data or key not in data:
            break
        for item in data[key]:
            yield item
        if not data.get("more"):
            break
        offset += page_size


def paginate_cursor(endpoint, token, items_key, params=None, page_size=100):
    """Yield items from a cursor-paginated PagerDuty endpoint (e.g. /audit/records)."""
    base_params = dict(params or {})
    base_params.setdefault("limit", page_size)
    cursor = None
    while True:
        page_params = dict(base_params)
        if cursor:
            page_params["cursor"] = cursor
        data = make_api_request(endpoint, token, params=page_params)
        if not data:
            break
        for item in data.get(items_key, []):
            yield item
        cursor = data.get("next_cursor")
        if not cursor:
            break


def fetch_all(resource, token, params=None, name_filter=None, label=None):
    """Fetch all items from a paginated resource, with optional substring name filter."""
    label = label or resource
    print(f"Fetching {label}...", end="", flush=True)
    items = list(paginate(resource, token, params=params))
    if name_filter:
        needle = name_filter.lower()
        items = [i for i in items if needle in (i.get("name") or "").lower()]
    suffix = f" matching filter '{name_filter}'" if name_filter else ""
    print(f" Found {len(items)} {label}{suffix}.")
    return items


def append_suffix_update(
    *,
    token,
    resource,
    item_kind,
    suffix,
    name_filter=None,
    list_only=False,
    dry_run=False,
    confirm=True,
):
    """Generic flow: fetch a resource collection, append `suffix` to names that lack it.

    `resource` is the PagerDuty plural endpoint (e.g. "services").
    `item_kind` is the singular wrapper key in PUT bodies (e.g. "service").
    """
    items = fetch_all(resource, token, name_filter=name_filter, label=resource)

    if list_only:
        print(f"\nCurrent {resource}:")
        print("-" * 80)
        for item in items:
            print(f"ID: {item.get('id')}, Name: '{item.get('name')}'")
        print("-" * 80)
        print(f"Total: {len(items)} {resource}")
        return

    suffix_token = f" {suffix}"
    needs_update = [i for i in items if not (i.get("name") or "").strip().endswith(suffix_token)]
    print(f"\nFound {len(needs_update)} {resource} that need '{suffix}' appended.")
    if not needs_update:
        return

    if confirm and not dry_run:
        answer = input(f"Update {len(needs_update)} {resource}? (y/n): ").strip().lower()
        if answer != "y":
            print("Operation cancelled.")
            return

    updated = 0
    failed = 0
    for item in needs_update:
        item_id = item.get("id")
        current = (item.get("name") or "").strip()
        new_name = f"{current}{suffix_token}"
        if dry_run:
            print(f"Would rename {item_kind} '{current}' to '{new_name}' (ID: {item_id})")
            updated += 1
            continue
        result = make_api_request(
            f"{resource}/{item_id}",
            token,
            method="PUT",
            data={item_kind: {"name": new_name}},
        )
        if result and item_kind in result:
            print(f"Renamed {item_kind} '{current}' -> '{new_name}'")
            updated += 1
        else:
            print(f"Failed to rename {item_kind} '{current}' (ID: {item_id})")
            failed += 1

    verb = "Would update" if dry_run else "Updated"
    print(f"\nSummary: {verb} {updated} {resource}, {failed} failed.")
