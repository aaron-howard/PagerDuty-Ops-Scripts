"""Unit tests for pagerduty_ops.api — HTTP mocked with `responses`."""

import pytest
import responses
from responses import matchers

from pagerduty_ops.api import (
    MAX_CLASSIC_OFFSET,
    PD_API_BASE,
    PDApiError,
    expand_query_params,
    get_session,
    paginate,
    paginate_cursor,
    request,
)

# ---------- request() ----------

@responses.activate
def test_request_success(token):
    responses.get(f"{PD_API_BASE}/users", json={"users": []})
    assert request("users", token) == {"users": []}
    assert responses.calls[0].request.headers["Authorization"] == f"Token token={token}"


@responses.activate
def test_request_empty_body_returns_empty_dict(token):
    responses.delete(f"{PD_API_BASE}/tags/T1", status=204, body="")
    assert request("tags/T1", token, method="DELETE") == {}


@responses.activate
def test_request_http_error_raises_typed_error(token):
    responses.get(
        f"{PD_API_BASE}/users",
        status=404,
        json={"error": {"code": 2100, "message": "Not Found"}},
    )
    with pytest.raises(PDApiError) as exc:
        request("users", token)
    assert exc.value.status_code == 404
    assert "Not Found" in str(exc.value)
    assert not exc.value.is_auth_error


@responses.activate
def test_request_auth_error_flag(token):
    responses.get(f"{PD_API_BASE}/users", status=401, json={"error": {"message": "Unauthorized"}})
    with pytest.raises(PDApiError) as exc:
        request("users", token)
    assert exc.value.is_auth_error


@responses.activate
def test_error_detail_is_redacted_envelope_only(token):
    """Raw bodies (which can contain PII) must not leak into the exception."""
    responses.get(
        f"{PD_API_BASE}/users",
        status=400,
        json={"error": {"message": "Bad"}, "users": [{"email": "jane.doe@example.com"}]},
    )
    with pytest.raises(PDApiError) as exc:
        request("users", token)
    assert "jane.doe@example.com" not in str(exc.value)
    assert "jane.doe@example.com" not in str(exc.value.pd_error)


@responses.activate
def test_post_retries_on_429_with_retry_after(token, monkeypatch):
    """POST is not retried by urllib3 (non-idempotent); our manual 429 loop handles it."""
    sleeps = []
    monkeypatch.setattr("pagerduty_ops.api.time.sleep", sleeps.append)
    responses.post(f"{PD_API_BASE}/tags", status=429, headers={"Retry-After": "7"})
    responses.post(f"{PD_API_BASE}/tags", json={"tag": {"id": "T1"}})
    result = request("tags", token, method="POST", data={"tag": {}})
    assert result == {"tag": {"id": "T1"}}
    assert sleeps == [7.0]


@responses.activate
def test_post_429_exhaustion_raises(token, monkeypatch):
    monkeypatch.setattr("pagerduty_ops.api.time.sleep", lambda _s: None)
    for _ in range(4):
        responses.post(f"{PD_API_BASE}/tags", status=429, headers={"Retry-After": "1"})
    with pytest.raises(PDApiError) as exc:
        request("tags", token, method="POST", data={})
    assert exc.value.status_code == 429


def test_get_session_retry_configuration():
    """GET/PUT/DELETE retries are delegated to urllib3 Retry on the adapter."""
    adapter = get_session().get_adapter("https://api.pagerduty.com")
    retry = adapter.max_retries
    assert retry.total == 5
    assert 429 in retry.status_forcelist and 503 in retry.status_forcelist
    assert "GET" in retry.allowed_methods and "PUT" in retry.allowed_methods
    assert "POST" not in retry.allowed_methods  # POST handled manually (429 only)
    assert retry.respect_retry_after_header


# ---------- expand_query_params ----------

def test_expand_query_params():
    pairs = expand_query_params(
        {"team_ids[]": ["T1", "T2"], "is_overview": True, "skip": None, "q": "x"}
    )
    assert ("team_ids[]", "T1") in pairs and ("team_ids[]", "T2") in pairs
    assert ("is_overview", "true") in pairs
    assert ("q", "x") in pairs
    assert all(k != "skip" for k, _ in pairs)


# ---------- pagination ----------

@responses.activate
def test_paginate_follows_more_flag(token):
    responses.get(
        f"{PD_API_BASE}/users",
        json={"users": [{"id": "U1"}], "more": True},
        match=[matchers.query_param_matcher({"limit": "2", "offset": "0"})],
    )
    responses.get(
        f"{PD_API_BASE}/users",
        json={"users": [{"id": "U2"}], "more": False},
        match=[matchers.query_param_matcher({"limit": "2", "offset": "2"})],
    )
    assert [u["id"] for u in paginate("users", token, page_size=2)] == ["U1", "U2"]


@responses.activate
def test_paginate_items_key_override(token):
    responses.get(
        f"{PD_API_BASE}/teams/T1/members",
        json={"members": [{"role": "manager"}], "more": False},
    )
    assert list(paginate("teams/T1/members", token, items_key="members")) == [
        {"role": "manager"}
    ]


@responses.activate
def test_paginate_raises_at_classic_offset_cap(token):
    """Compliance exports must never be silently incomplete."""
    page_size = 100
    pages = MAX_CLASSIC_OFFSET // page_size
    for _ in range(pages):
        responses.get(
            f"{PD_API_BASE}/log_entries",
            json={"log_entries": [{"id": "L"}] * page_size, "more": True},
        )
    gen = paginate("log_entries", token, page_size=page_size)
    with pytest.raises(PDApiError, match="pagination cap"):
        list(gen)


@responses.activate
def test_paginate_cursor_follows_next_cursor(token):
    responses.get(f"{PD_API_BASE}/audit/records",
                  json={"records": [{"id": "R1"}], "next_cursor": "abc"})
    responses.get(f"{PD_API_BASE}/audit/records",
                  json={"records": [{"id": "R2"}], "next_cursor": None})
    items = list(paginate_cursor("audit/records", token, items_key="records"))
    assert [i["id"] for i in items] == ["R1", "R2"]
