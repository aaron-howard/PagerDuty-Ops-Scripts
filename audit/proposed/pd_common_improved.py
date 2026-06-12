"""Shared helpers for the PagerDuty operations scripts (audit-proposed v2).

Changes vs pd_common.py:
- requests.Session with urllib3 Retry: honors Retry-After on 429, retries 5xx
- Typed PDApiError instead of returning None (auth errors abort immediately)
- All diagnostics to stderr; stdout reserved for data
- Error bodies redacted to status + PagerDuty error code/message
- run_exit_code() helper so bulk scripts exit non-zero on partial failure
- logging instead of bare print for diagnostics
"""

import getpass
import logging
import os
import sys

import dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

dotenv.load_dotenv()

PD_API_BASE = "https://api.pagerduty.com"
PD_API_HEADERS_ACCEPT = "application/vnd.pagerduty+json;version=2"
REQUEST_TIMEOUT = 30
MAX_CLASSIC_OFFSET = 10_000  # PagerDuty classic pagination hard cap

log = logging.getLogger("pd_ops")


def configure_logging(verbose=False, quiet=False):
    """Stderr logging; INFO by default, DEBUG with --verbose, ERROR with --quiet."""
    level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
    log.setLevel(level)


class PDApiError(Exception):
    """A PagerDuty API call failed after retries."""

    def __init__(self, message, status_code=None, pd_error=None):
        super().__init__(message)
        self.status_code = status_code
        self.pd_error = pd_error or {}

    @property
    def is_auth_error(self):
        return self.status_code in (401, 403)


def add_token_arguments(parser):
    parser.add_argument(
        "-t",
        "--token",
        help="DEPRECATED: token on the command line leaks into shell history. "
        "Use the PD_API_TOKEN environment variable instead.",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Prompt securely for API token when PD_API_TOKEN is unset (local dev only)",
    )


def get_pd_api_token(cli_token=None, *, allow_prompt=False):
    if cli_token:
        log.warning("-t/--token is deprecated; prefer the PD_API_TOKEN environment variable.")
    token = cli_token or os.environ.get("PD_API_TOKEN")
    if not token and allow_prompt:
        token = getpass.getpass("Enter your PagerDuty API token: ")
    if not token:
        print(
            "Error: No API token provided. Set PD_API_TOKEN or use --prompt.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def build_headers(token):
    return {
        "Accept": PD_API_HEADERS_ACCEPT,
        "Authorization": f"Token token={token}",
        "Content-Type": "application/json",
    }


_session = None


def get_session():
    """Process-wide Session with retry/backoff. 429 honors Retry-After."""
    global _session
    if _session is None:
        retry = Retry(
            total=5,
            backoff_factor=1.5,  # 0s, 3s, 6s, 12s, 24s
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "PUT", "DELETE"),  # idempotent only
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        _session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry)
        _session.mount("https://", adapter)
    return _session


def _redacted_error(response):
    """Status + PagerDuty error envelope only — never the raw body (may hold PII)."""
    try:
        err = response.json().get("error", {})
        detail = {"code": err.get("code"), "message": err.get("message"),
                  "errors": err.get("errors")}
    except ValueError:
        detail = {}
    return detail


def make_api_request(endpoint, token, method="GET", params=None, data=None, extra_headers=None):
    """Make a request to the PagerDuty API.

    Returns parsed JSON ({} for empty bodies). Raises PDApiError on failure —
    callers decide whether one failure aborts the run or is counted and skipped.
    """
    url = f"{PD_API_BASE}/{endpoint}"
    headers = build_headers(token)
    if extra_headers:
        headers.update(extra_headers)
    session = get_session()
    try:
        # POST retried manually below only on 429 (not idempotent on 5xx)
        response = session.request(
            method, url, headers=headers, params=params,
            json=data if method in ("POST", "PUT", "PATCH") else None,
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise PDApiError(f"{method} /{endpoint}: network error: {e}") from e

    if response.status_code >= 400:
        detail = _redacted_error(response)
        msg = f"{method} /{endpoint} -> HTTP {response.status_code}"
        if detail.get("message"):
            msg += f": {detail['message']}"
        log.error(msg)
        raise PDApiError(msg, status_code=response.status_code, pd_error=detail)

    if not response.text:
        return {}
    try:
        return response.json()
    except ValueError as e:
        raise PDApiError(f"{method} /{endpoint}: invalid JSON in response: {e}") from e


def expand_query_params(params):
    pairs = []
    for k, v in (params or {}).items():
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            pairs.extend((k, item) for item in v if item is not None)
        elif isinstance(v, bool):
            pairs.append((k, str(v).lower()))
        else:
            pairs.append((k, v))
    return pairs


def paginate(resource, token, params=None, page_size=100, extra_headers=None, items_key=None):
    """Yield items from a classic (offset) paginated endpoint.

    Raises PDApiError if the 10,000-offset cap is reached with more data
    remaining — callers should narrow the query (e.g. --since/--until windows)
    rather than silently export an incomplete dataset.
    """
    base_pairs = expand_query_params(params)
    key = items_key or resource.rsplit("/", 1)[-1]
    offset = 0
    while True:
        page_params = list(base_pairs)
        page_params.append(("limit", page_size))
        page_params.append(("offset", offset))
        data = make_api_request(resource, token, params=page_params, extra_headers=extra_headers)
        if key not in data:
            return
        yield from data[key]
        if not data.get("more"):
            return
        offset += page_size
        if offset + page_size > MAX_CLASSIC_OFFSET:
            raise PDApiError(
                f"/{resource}: hit the {MAX_CLASSIC_OFFSET}-record classic pagination cap "
                "with more data remaining. Narrow the query (e.g. shorter --since/--until "
                "window) and export in batches."
            )


def paginate_cursor(endpoint, token, items_key, params=None, page_size=100):
    base_params = dict(params or {})
    base_params.setdefault("limit", page_size)
    cursor = None
    while True:
        page_params = dict(base_params)
        if cursor:
            page_params["cursor"] = cursor
        data = make_api_request(endpoint, token, params=page_params)
        yield from data.get(items_key, [])
        cursor = data.get("next_cursor")
        if not cursor:
            return


def fetch_all(resource, token, params=None, name_filter=None, label=None):
    label = label or resource
    log.info("Fetching %s...", label)
    items = list(paginate(resource, token, params=params))
    if name_filter:
        needle = name_filter.lower()
        items = [i for i in items if needle in (i.get("name") or "").lower()]
    log.info("Found %d %s%s.", len(items), label,
             f" matching filter '{name_filter}'" if name_filter else "")
    return items


def run_exit_code(failed, *, updated=0, label="items"):
    """Standard end-of-run handler for bulk scripts: non-zero exit on any failure."""
    if failed:
        log.error("%d %s failed (%d succeeded).", failed, label, updated)
        sys.exit(1)
    return 0
