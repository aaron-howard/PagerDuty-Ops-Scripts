"""Tests for pagerduty.redaction.redact_log_text."""

import pytest

from pagerduty.redaction import redact_log_text


@pytest.mark.parametrize(
    ("raw", "must_not_contain"),
    [
        ("Authorization: Token token=u+abcdefghijklmnop", "u+abcdefghijklmnop"),
        ("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0", "eyJ"),
        ("api_token=supersecretvaluehere123", "supersecretvaluehere123"),
        ("API_KEY: anotherlongsecretvalue", "anotherlongsecretvalue"),
    ],
)
def test_redact_removes_secrets(raw: str, must_not_contain: str) -> None:
    out = redact_log_text(raw)
    assert must_not_contain not in out
    assert "***REDACTED***" in out


def test_redact_benign_text_unchanged() -> None:
    s = "Fetched 3 teams from schedules endpoint"
    assert redact_log_text(s) == s
