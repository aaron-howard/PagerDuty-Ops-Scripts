"""Tests for pagerduty.api_client.PagerDutyAPIClient."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from pagerduty.api_client import PagerDutyAPIClient
from pagerduty.errors import APIError, AuthError, NotFoundError, RateLimitError

# Non-empty token; avoids PD_API_TOKEN env. Validity is enforced by the API, not length.
VALID_TEST_TOKEN = "pd-test-token-opaque"


def _response(
    status_code: int,
    *,
    text: str = "",
    json_data=None,
    json_side_effect=None,
    headers=None,
):
    """Build a MagicMock shaped like requests.Response for _handle_response tests."""
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.text = text
    resp.headers = headers or {}
    if json_side_effect is not None:
        resp.json.side_effect = json_side_effect
    else:
        if json_data is not None:
            resp.json.return_value = json_data
        elif text:
            # Default: parse text as JSON when json() is called
            def _json():
                return json.loads(text)

            resp.json.side_effect = _json
    return resp


@pytest.fixture
def client():
    return PagerDutyAPIClient(api_token=VALID_TEST_TOKEN)


class TestHandleResponse:
    def test_200_json_body(self, client):
        body = {"teams": [{"id": "T1"}]}
        resp = _response(200, text=json.dumps(body), json_data=body)
        assert client._handle_response(resp) == body

    def test_200_empty_body(self, client):
        resp = _response(200, text="")
        resp.json.return_value = None  # should not be called when text is empty
        assert client._handle_response(resp) == {}

    def test_401_raises_auth_error(self, client):
        resp = _response(401, text="Unauthorized")
        with pytest.raises(AuthError, match="Unauthorized"):
            client._handle_response(resp)

    def test_404_raises_not_found_error(self, client):
        resp = _response(404, text="Not Found")
        with pytest.raises(NotFoundError):
            client._handle_response(resp)

    def test_429_raises_rate_limit_error_with_retry_after_header(self, client):
        resp = _response(
            429,
            text="Too Many Requests",
            headers={"Retry-After": "42"},
        )
        with pytest.raises(RateLimitError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.retry_after == 42

    def test_400_raises_api_error_with_pd_shaped_message(self, client):
        payload = {"error": {"message": "bad request detail"}}
        resp = _response(400, text=json.dumps(payload), json_data=payload)
        with pytest.raises(APIError) as exc_info:
            client._handle_response(resp)
        assert exc_info.value.message == "bad request detail"
        assert exc_info.value.status_code == 400
        assert exc_info.value.response == payload

    def test_400_non_json_body_uses_raw_text(self, client):
        resp = _response(
            400, text="plain error", json_side_effect=json.JSONDecodeError("e", "doc", 0)
        )
        with pytest.raises(APIError) as exc_info:
            client._handle_response(resp)
        assert "plain error" in exc_info.value.message or exc_info.value.message == "plain error"
        assert exc_info.value.status_code == 400

    def test_200_invalid_json_raises_api_error(self, client):
        resp = _response(200, text="not-json{")
        resp.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        with pytest.raises(APIError, match="Invalid JSON response from API"):
            client._handle_response(resp)


class TestGetPaginated:
    def test_two_pages_merged_and_offset_progression(self, client):
        page1 = {
            "teams": [{"id": "a"}, {"id": "b"}],
            "more": True,
        }
        page2 = {
            "teams": [{"id": "c"}],
            "more": False,
        }
        captured_params = []

        def fake_get(endpoint, params=None):
            # Copy now: unittest.mock keeps references; get_paginated mutates offset in place.
            captured_params.append(dict(params or {}))
            if len(captured_params) == 1:
                return page1
            return page2

        with patch.object(client, "get", side_effect=fake_get):
            result = client.get_paginated("teams")

        assert len(result) == 3
        assert [item["id"] for item in result] == ["a", "b", "c"]

        assert len(captured_params) == 2
        assert captured_params[0]["offset"] == 0
        assert captured_params[0]["limit"] == 100
        assert captured_params[1]["offset"] == 100
        assert captured_params[1]["limit"] == 100

    def test_explicit_items_key_used(self, client):
        page1 = {"widgets": [{"id": "1"}], "more": True}
        page2 = {"widgets": [{"id": "2"}], "more": False}
        calls: list[dict] = []

        def fake_get(endpoint, params=None):
            calls.append(dict(params or {}))
            return page1 if len(calls) == 1 else page2

        with patch.object(client, "get", side_effect=fake_get):
            result = client.get_paginated("custom/things", items_key="widgets")

        assert [item["id"] for item in result] == ["1", "2"]
        assert len(calls) == 2

    def test_non_list_envelope_stops_pagination(self, client):
        def fake_get(endpoint, params=None):
            return {"teams": {"not": "a list"}, "more": False}

        with patch.object(client, "get", side_effect=fake_get):
            assert client.get_paginated("teams") == []

    def test_unmapped_endpoint_returns_empty_without_crash(self, client):
        def fake_get(endpoint, params=None):
            return {"records": [{"id": "z"}], "more": False}

        with patch.object(client, "get", side_effect=fake_get):
            assert client.get_paginated("unknown_collection") == []

    def test_stuck_more_raises_after_max_iterations(self, client):
        def fake_get(endpoint, params=None):
            return {"teams": [{"id": "same"}], "more": True}

        with (
            patch.object(PagerDutyAPIClient, "MAX_PAGINATION_ITERATIONS", 3),
            patch.object(client, "get", side_effect=fake_get),
        ):
            with pytest.raises(APIError, match="Pagination stopped"):
                client.get_paginated("teams")


class TestValidateToken:
    def test_empty_token_raises(self):
        with pytest.raises(AuthError, match="API token is required"):
            PagerDutyAPIClient(api_token="")

    def test_whitespace_only_token_raises(self):
        with pytest.raises(AuthError, match="API token is required"):
            PagerDutyAPIClient(api_token="   \t")


class TestMakeRequestPropagatesPagerDutyErrors:
    def test_get_does_not_wrap_api_error(self, client):
        payload = {"error": {"message": "nope"}}
        mock_resp = _response(400, text=json.dumps(payload), json_data=payload)
        client.session.request = MagicMock(return_value=mock_resp)

        with pytest.raises(APIError) as exc_info:
            client.get("teams")
        assert exc_info.value.message == "nope"
        assert exc_info.value.status_code == 400

    def test_get_does_not_wrap_auth_error(self, client):
        mock_resp = _response(401, text="go away")
        client.session.request = MagicMock(return_value=mock_resp)

        with pytest.raises(AuthError):
            client.get("teams")

    def test_get_does_not_wrap_not_found(self, client):
        mock_resp = _response(404, text="missing")
        client.session.request = MagicMock(return_value=mock_resp)

        with pytest.raises(NotFoundError):
            client.get("teams/T1")
