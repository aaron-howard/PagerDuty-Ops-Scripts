"""Unit tests for bulkops: rename idempotency, CSV loading, ISO validation."""

import pytest
import responses

from pagerduty_ops.api import PD_API_BASE
from pagerduty_ops.bulkops import (
    apply_name_affix_update,
    load_csv_rows,
    name_has_affix,
    parse_iso8601,
)

# ---------- idempotency check ----------

@pytest.mark.parametrize(
    ("name", "affix", "position", "ignore_case", "expected"),
    [
        ("Payments SVC", " SVC", "suffix", False, True),
        ("Payments", " SVC", "suffix", False, False),
        ("payments svc", " SVC", "suffix", True, True),
        ("payments svc", " SVC", "suffix", False, False),
        ("[SRE] DB", "[SRE] ", "prefix", False, True),
        ("DB", "[SRE] ", "prefix", False, False),
        (None, "X", "suffix", False, False),
        ("anything", "", "suffix", False, True),
    ],
)
def test_name_has_affix(name, affix, position, ignore_case, expected):
    assert name_has_affix(name, affix, position, ignore_case=ignore_case) is expected


@responses.activate
def test_rename_skips_already_affixed_and_exits_zero(token, capsys):
    responses.get(
        f"{PD_API_BASE}/services",
        json={"services": [
            {"id": "P1", "name": "Payments SVC"},
            {"id": "P2", "name": "Search"},
        ], "more": False},
    )
    responses.put(
        f"{PD_API_BASE}/services/P2",
        json={"service": {"id": "P2", "name": "Search SVC"}},
    )
    code = apply_name_affix_update(
        token=token, resource="services", item_kind="service",
        position="suffix", affix=" SVC", assume_yes=True,
    )
    assert code == 0
    # exactly one PUT, for the service lacking the suffix
    puts = [c for c in responses.calls if c.request.method == "PUT"]
    assert len(puts) == 1 and "/services/P2" in puts[0].request.url


@responses.activate
def test_rename_partial_failure_exits_one(token):
    responses.get(
        f"{PD_API_BASE}/services",
        json={"services": [{"id": "P2", "name": "Search"}], "more": False},
    )
    responses.put(f"{PD_API_BASE}/services/P2", status=400,
                  json={"error": {"message": "nope"}})
    code = apply_name_affix_update(
        token=token, resource="services", item_kind="service",
        position="suffix", affix=" SVC", assume_yes=True,
    )
    assert code == 1


@responses.activate
def test_rename_dry_run_makes_no_writes(token):
    responses.get(
        f"{PD_API_BASE}/services",
        json={"services": [{"id": "P2", "name": "Search"}], "more": False},
    )
    code = apply_name_affix_update(
        token=token, resource="services", item_kind="service",
        position="suffix", affix=" SVC", dry_run=True,
    )
    assert code == 0
    assert all(c.request.method == "GET" for c in responses.calls)


# ---------- CSV loading ----------

def _write_csv(tmp_path, text):
    p = tmp_path / "input.csv"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_load_csv_rows_happy_path(tmp_path):
    path = _write_csv(tmp_path, "service_id,start_time\nP1,2026-05-01T02:00:00Z\n,skipped\n")
    rows = load_csv_rows(path, {"service_id", "start_time"}, skip_if_missing=("service_id",))
    assert len(rows) == 1
    assert rows[0]["service_id"] == "P1"
    assert rows[0]["_line"] == 2


def test_load_csv_rows_missing_column_exits_2(tmp_path, capsys):
    path = _write_csv(tmp_path, "service_id\nP1\n")
    with pytest.raises(SystemExit) as exc:
        load_csv_rows(path, {"service_id", "start_time"})
    assert exc.value.code == 2
    assert "missing required columns" in capsys.readouterr().err


def test_load_csv_rows_unreadable_file_exits_2(tmp_path):
    with pytest.raises(SystemExit):
        load_csv_rows(str(tmp_path / "nope.csv"), {"x"})


# ---------- ISO 8601 validation ----------

def test_parse_iso8601_accepts_z_and_offset():
    assert parse_iso8601("2026-05-01T02:00:00Z", field="t", line=2)
    assert parse_iso8601("2026-05-01T02:00:00-04:00", field="t", line=2)


@pytest.mark.parametrize("bad", ["not-a-date", "2026-05-01T02:00:00", "2026-13-01T00:00:00Z"])
def test_parse_iso8601_rejects_invalid(bad):
    with pytest.raises(SystemExit):
        parse_iso8601(bad, field="t", line=3)
