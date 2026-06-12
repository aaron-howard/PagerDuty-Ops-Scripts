#!/usr/bin/env python3
"""DEPRECATED compatibility shim.

Prefer the PagerDuty MCP server's list_team_members tool for ad-hoc reads,
or the team_members command (pagerduty_ops.commands.team_members) for
CLI/CSV pipelines. This shim now delegates to team_members (paginated —
the old script truncated at 25 members).
"""

import sys

from pagerduty_ops.cli import run
from pagerduty_ops.commands.team_members import main

if __name__ == "__main__":
    print(
        "[deprecated] pd_get_teams_user_role.py: prefer the PagerDuty MCP server's "
        "list_team_members tool, or `pd-team-members`. See README.md.",
        file=sys.stderr,
    )
    run(main)
