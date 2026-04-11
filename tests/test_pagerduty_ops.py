"""Tests for the pagerduty-ops dispatcher."""

import pytest

import pagerduty_ops


def test_main_no_args_prints_usage_and_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        pagerduty_ops.main([])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "export-ids" in out
    assert "pagerduty-ops" in out


def test_main_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        pagerduty_ops.main(["--help"])
    assert exc.value.code == 0
    assert "Commands:" in capsys.readouterr().out


def test_main_unknown_command_exits_2(capsys):
    with pytest.raises(SystemExit) as exc:
        pagerduty_ops.main(["not-a-command"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "unknown command" in err


def test_main_delegates_export_ids_help(capsys):
    with pytest.raises(SystemExit) as exc:
        pagerduty_ops.main(["export-ids", "--help"])
    assert exc.value.code == 0
    assert "Export PagerDuty" in capsys.readouterr().out
