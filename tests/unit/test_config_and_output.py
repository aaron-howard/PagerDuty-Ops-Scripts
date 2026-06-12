"""Unit tests for config (token/team resolution) and output rendering."""

import json

import pytest

from pagerduty_ops.config import get_api_token, get_from_email, get_team_id
from pagerduty_ops.output import render_rows

# ---------- config ----------

def test_token_cli_arg_wins(monkeypatch):
    monkeypatch.setenv("PD_API_TOKEN", "env-token")
    assert get_api_token("cli-token") == "cli-token"


def test_token_from_env(monkeypatch):
    monkeypatch.setenv("PD_API_TOKEN", "env-token")
    assert get_api_token(None) == "env-token"


def test_missing_token_exits_2(monkeypatch, capsys):
    monkeypatch.delenv("PD_API_TOKEN", raising=False)
    with pytest.raises(SystemExit) as exc:
        get_api_token(None, allow_prompt=False)
    assert exc.value.code == 2
    assert "No API token" in capsys.readouterr().err


def test_team_id_from_env(monkeypatch):
    monkeypatch.setenv("PD_TEAM_ID", "  PTEAM1 ")
    assert get_team_id(None, allow_prompt=False) == "PTEAM1"


def test_missing_team_id_exits_2(monkeypatch):
    monkeypatch.delenv("PD_TEAM_ID", raising=False)
    with pytest.raises(SystemExit):
        get_team_id(None, allow_prompt=False)


def test_from_email_validation(monkeypatch):
    monkeypatch.delenv("PD_FROM_EMAIL", raising=False)
    assert get_from_email("ops@example.com") == "ops@example.com"
    with pytest.raises(SystemExit):
        get_from_email("not-an-email")
    with pytest.raises(SystemExit):
        get_from_email(None, required=True)
    assert get_from_email(None, required=False) is None


# ---------- output ----------

ROWS = [
    {"id": "P1", "name": "Alpha"},
    {"id": "P2", "name": "Beta, with comma"},
]
FIELDS = ["id", "name"]


def test_render_csv_quotes_correctly():
    out = render_rows(ROWS, FIELDS, "csv")
    lines = out.strip().splitlines()
    assert lines[0] == "id,name"
    assert lines[2] == 'P2,"Beta, with comma"'


def test_render_json_rows():
    assert json.loads(render_rows(ROWS, FIELDS, "json")) == ROWS


def test_render_json_raw_fidelity():
    raw = [{"id": "P1", "name": "Alpha", "extra": {"nested": True}}]
    assert json.loads(render_rows(ROWS, FIELDS, "json", raw=raw)) == raw


def test_render_table_contains_all_values():
    out = render_rows(ROWS, FIELDS, "table")
    for value in ("P1", "Alpha", "P2"):
        assert value in out
    assert "Total: 2" in out


def test_render_csv_ignores_extra_keys():
    rows = [{"id": "P1", "name": "A", "unexpected": "x"}]
    out = render_rows(rows, FIELDS, "csv")
    assert "unexpected" not in out
