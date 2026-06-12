"""Unit tests for pd_common (HTTP mocked with the `responses` library).

Run:  pip install pytest responses && pytest tests/ -v
Works against the current pd_common.py; tests marked `v2` target
audit/proposed/pd_common_improved.py behavior (retries, PDApiError).
"""

import pytest
import responses

import pd_common
from pd_common import (
    PD_API_BASE,
    _name_has_affix,
    expand_query_params,
    get_pd_api_token,
    paginate,
    paginate_cursor,
)


# ---------- token resolution ----------

def test_token_from_cli_arg_wins(monkeypatch):
    monkeypatch.setenv("PD_API_TOKEN", "env-token")
    assert get_pd_api_token("cli-token") == "cli-token"


def test_token_from_env(monkeypatch):
    monkeypatch.setenv("PD_API_TOKEN", "env-token")
    assert get_pd_api_token(None) == "env-token"


def test_missing_token_exits(monkeypatch, capsys):
    monkeypatch.delenv("PD_API_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        get_pd_api_token(None, allow_prompt=False)
    assert exc.value.code == 1
    assert "No API token" in capsys.readouterr().err


# ---------- expand_query_params ----------

def test_expand_query_params():
    pairs = expand_query_params(
        {"team_ids[]": ["T1", "T2"], "is_overview": True, "skip": None, "q": "x"}
    )
    assert ("team_ids[]", "T1") in pairs and ("team_ids[]", "T2") in pairs
    assert ("is_overview", "true") in pairs
    assert ("q", "x") in pairs
    assert all(k != "skip" for k, _ in pairs)


# ---------- offset pagination ----------

@responses.activate
def test_paginate_follows_more_flag():
    responses.get(
        f"{PD_API_BASE}/users",
        json={"users": [{"id": "U1"}], "more": True},
        match=[responses.matchers.query_param_matcher({"limit": "2", "offset": "0"})],
    )
    responses.get(
        f"{PD_API_BASE}/users",
        json={"users": [{"id": "U2"}], "more": False},
        match=[responses.matchers.query_param_matcher({"limit": "2", "offset": "2"})],
    )
    items = list(paginate("users", "tok", page_size=2))
    assert [i["id"] for i in items] == ["U1", "U2"]


@responses.activate
def test_paginate_items_key_override():
    responses.get(
        f"{PD_API_BASE}/teams/T1/members",
        json={"members": [{"role": "manager"}], "more": False},
    )
    items = list(paginate("teams/T1/members", "tok", items_key="members"))
    assert items == [{"role": "manager"}]


# ---------- cursor pagination ----------

@responses.activate
def test_paginate_cursor_follows_next_cursor():
    responses.get(
        f"{PD_API_BASE}/audit/records",
        json={"records": [{"id": "R1"}], "next_cursor": "abc"},
    )
    responses.get(
        f"{PD_API_BASE}/audit/records",
        json={"records": [{"id": "R2"}], "next_cursor": None},
    )
    items = list(paginate_cursor("audit/records", "tok", items_key="records"))
    assert [i["id"] for i in items] == ["R1", "R2"]


# ---------- rename idempotency ----------

@pytest.mark.parametrize(
    ("name", "affix", "position", "ignore_case", "expected"),
    [
        ("Payments SVC", " SVC", "suffix", False, True),
        ("Payments", " SVC", "suffix", False, False),
        ("payments svc", " SVC", "suffix", True, True),
        ("[SRE] DB", "[SRE] ", "prefix", False, True),
        ("DB", "[SRE] ", "prefix", False, False),
        (None, "X", "suffix", False, False),
        ("anything", "", "suffix", False, True),  # empty affix is always "present"
    ],
)
def test_name_has_affix(name, affix, position, ignore_case, expected):
    assert _name_has_affix(name, affix, position, ignore_case=ignore_case) is expected


# ---------- v2 behavior (pd_common_improved) ----------

@pytest.mark.skipif(
    not hasattr(pd_common, "PDApiError"), reason="requires pd_common_improved"
)
class TestV2:
    @responses.activate
    def test_retries_on_429_then_succeeds(self):
        responses.get(
            f"{PD_API_BASE}/users",
            status=429,
            headers={"Retry-After": "0"},
        )
        responses.get(f"{PD_API_BASE}/users", json={"users": [], "more": False})
        assert pd_common.make_api_request("users", "tok") == {"users": [], "more": False}

    @responses.activate
    def test_auth_error_raises_with_status(self):
        responses.get(
            f"{PD_API_BASE}/users",
            status=401,
            json={"error": {"code": 2001, "message": "Unauthorized"}},
        )
        with pytest.raises(pd_common.PDApiError) as exc:
            pd_common.make_api_request("users", "tok")
        assert exc.value.status_code == 401
        assert exc.value.is_auth_error

    @responses.activate
    def test_error_body_is_redacted(self, caplog):
        responses.get(
            f"{PD_API_BASE}/users",
            status=400,
            json={"error": {"message": "Bad"}, "secret_pii": "jane@example.com"},
        )
        with pytest.raises(pd_common.PDApiError):
            pd_common.make_api_request("users", "tok")
        assert "jane@example.com" not in caplog.text
