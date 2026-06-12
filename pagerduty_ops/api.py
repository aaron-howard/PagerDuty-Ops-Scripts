"""HTTP layer for the PagerDuty REST API.

Provides:
- a process-wide requests.Session with automatic retries (429 honors
  Retry-After; transient 5xx retried for idempotent methods)
- manual 429 retry loop for non-idempotent methods (POST/PATCH)
- PDApiError: a typed exception instead of silent None returns
- offset (`paginate`) and cursor (`paginate_cursor`) pagination with an
  explicit error at PagerDuty's 10,000-record classic pagination cap
- response-body redaction: only the PagerDuty error envelope is logged,
  never the raw body (which can contain user PII)
"""

from __future__ import annotations

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PD_API_BASE = "https://api.pagerduty.com"
ACCEPT_HEADER = "application/vnd.pagerduty+json;version=2"
REQUEST_TIMEOUT = 30
MAX_CLASSIC_OFFSET = 10_000  # PagerDuty classic pagination hard cap
MUTATING_429_ATTEMPTS = 4  # manual retry budget for POST/PATCH on 429
MAX_RETRY_AFTER_SECONDS = 120

log = logging.getLogger("pd_ops.api")


class PDApiError(Exception):
    """A PagerDuty API call failed (after retries, where applicable)."""

    def __init__(self, message: str, status_code: int | None = None, pd_error: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.pd_error = pd_error or {}

    @property
    def is_auth_error(self) -> bool:
        return self.status_code in (401, 403)


_session: requests.Session | None = None


def get_session() -> requests.Session:
    """Process-wide Session. GET/PUT/DELETE retried by urllib3 (429 + 5xx,
    honoring Retry-After). POST/PATCH handled manually in request()."""
    global _session
    if _session is None:
        retry = Retry(
            total=5,
            connect=3,
            backoff_factor=1.5,  # 0s, 3s, 6s, 12s, 24s
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD", "PUT", "DELETE"),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        s = requests.Session()
        s.mount("https://", HTTPAdapter(max_retries=retry))
        _session = s
    return _session


def reset_session() -> None:
    """Testing hook."""
    global _session
    _session = None


def build_headers(token: str, extra: dict | None = None) -> dict:
    headers = {
        "Accept": ACCEPT_HEADER,
        "Authorization": f"Token token={token}",
        "Content-Type": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _redacted_error(response: requests.Response) -> dict:
    """Extract only PagerDuty's error envelope — never log the raw body."""
    try:
        err = response.json().get("error", {})
        if isinstance(err, dict):
            return {
                "code": err.get("code"),
                "message": err.get("message"),
                "errors": err.get("errors"),
            }
    except ValueError:
        pass
    return {}


def _retry_after_seconds(response: requests.Response, attempt: int) -> float:
    raw = response.headers.get("Retry-After", "")
    try:
        delay = float(raw)
    except (TypeError, ValueError):
        delay = float(2**attempt)
    return min(max(delay, 0.0), MAX_RETRY_AFTER_SECONDS)


def request(
    endpoint: str,
    token: str,
    method: str = "GET",
    params=None,
    data=None,
    extra_headers: dict | None = None,
) -> dict:
    """Make one logical API call. Returns parsed JSON ({} for empty bodies).

    Raises PDApiError on any failure. Callers decide whether a failure aborts
    the run (auth errors should) or is counted and skipped (bulk loops).
    """
    url = f"{PD_API_BASE}/{endpoint.lstrip('/')}"
    headers = build_headers(token, extra_headers)
    session = get_session()
    json_body = data if method in ("POST", "PUT", "PATCH") else None
    attempts = MUTATING_429_ATTEMPTS if method in ("POST", "PATCH") else 1

    response = None
    for attempt in range(attempts):
        try:
            response = session.request(
                method, url, headers=headers, params=params, json=json_body, timeout=REQUEST_TIMEOUT
            )
        except requests.RequestException as e:
            raise PDApiError(f"{method} /{endpoint}: network error: {e}") from e
        if response.status_code == 429 and attempt < attempts - 1:
            delay = _retry_after_seconds(response, attempt)
            log.warning(
                "%s /%s rate-limited (429); retrying in %.1fs (attempt %d/%d)",
                method, endpoint, delay, attempt + 1, attempts,
            )
            time.sleep(delay)
            continue
        break

    if response.status_code >= 400:
        detail = _redacted_error(response)
        msg = f"{method} /{endpoint} -> HTTP {response.status_code}"
        if detail.get("message"):
            msg += f": {detail['message']}"
        if detail.get("errors"):
            msg += f" ({'; '.join(str(x) for x in detail['errors'])})"
        raise PDApiError(msg, status_code=response.status_code, pd_error=detail)

    if not response.text:
        return {}
    try:
        return response.json()
    except ValueError as e:
        raise PDApiError(f"{method} /{endpoint}: invalid JSON in response: {e}") from e


def expand_query_params(params) -> list[tuple]:
    """Dict -> (key, value) pairs; lists become repeated keys, bools lowercase."""
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


def paginate(
    resource: str,
    token: str,
    params=None,
    page_size: int = 100,
    extra_headers: dict | None = None,
    items_key: str | None = None,
):
    """Yield items from a classic (offset) paginated list endpoint.

    Raises PDApiError if the 10,000-record cap is reached with data remaining,
    so compliance exports are never silently incomplete — narrow the query
    (e.g. shorter --since/--until window) instead.
    """
    base_pairs = expand_query_params(params)
    key = items_key or resource.rsplit("/", 1)[-1]
    offset = 0
    while True:
        page_params = [*base_pairs, ("limit", page_size), ("offset", offset)]
        data = request(resource, token, params=page_params, extra_headers=extra_headers)
        if key not in data:
            return
        yield from data[key]
        if not data.get("more"):
            return
        offset += page_size
        if offset + page_size > MAX_CLASSIC_OFFSET:
            raise PDApiError(
                f"/{resource}: hit the {MAX_CLASSIC_OFFSET}-record classic pagination cap with "
                "more data remaining. Narrow the query and export in batches."
            )


def paginate_cursor(endpoint: str, token: str, items_key: str, params=None, page_size: int = 100):
    """Yield items from a cursor-paginated endpoint (e.g. /audit/records)."""
    base_params = dict(params or {})
    base_params.setdefault("limit", page_size)
    cursor = None
    while True:
        page_params = dict(base_params)
        if cursor:
            page_params["cursor"] = cursor
        data = request(endpoint, token, params=page_params)
        yield from data.get(items_key, [])
        cursor = data.get("next_cursor")
        if not cursor:
            return


def fetch_all(resource, token, params=None, name_filter=None, label=None, **kwargs) -> list:
    """Fetch a whole collection, with optional client-side substring name filter."""
    label = label or resource
    log.info("Fetching %s...", label)
    items = list(paginate(resource, token, params=params, **kwargs))
    if name_filter:
        needle = name_filter.lower()
        items = [i for i in items if needle in (i.get("name") or "").lower()]
    log.info(
        "Found %d %s%s.", len(items), label, f" matching '{name_filter}'" if name_filter else ""
    )
    return items
