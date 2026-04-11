#!/usr/bin/env python3
"""
Unified entry point for PagerDuty ops CLIs (``pagerduty-ops <command> [args...]``).
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Sequence

from pagerduty.cli_common import EXIT_SUCCESS, EXIT_USAGE

# command name -> module name (must expose ``main(argv=None)``)
_COMMANDS: dict[str, str] = {
    "export-ids": "pd_export_ids",
    "update-service-names": "pd_update_service_names",
    "update-schedule-names": "pd_update_schedule_names",
    "update-escalation-policy-names": "pd_update_escalation_policy_names",
    "patch-role": "pd_patch_role",
    "update-team-roles": "pd_update_team_roles",
    "get-teams-user-role": "pd_get_teams_user_role",
    "remove-team-members": "pd_remove_team_members",
    "update-service-notifications": "update_service_notifications",
}


def _usage() -> str:
    lines = [
        "usage: pagerduty-ops <command> [options]",
        "",
        "Commands:",
    ]
    w = max(len(k) for k in _COMMANDS)
    for name in sorted(_COMMANDS):
        lines.append(f"  {name.ljust(w)}  ({_COMMANDS[name]})")
    lines.extend(
        [
            "",
            "Run a command's help with: pagerduty-ops <command> --help",
            "Individual tools remain available (e.g. pd-export-ids).",
        ]
    )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help", "help"):
        print(_usage())
        sys.exit(EXIT_SUCCESS)

    cmd = args[0]
    rest = args[1:]
    mod_name = _COMMANDS.get(cmd)
    if mod_name is None:
        print(f"pagerduty-ops: unknown command {cmd!r}", file=sys.stderr)
        print(_usage(), file=sys.stderr)
        sys.exit(EXIT_USAGE)

    mod = importlib.import_module(mod_name)
    main_fn = getattr(mod, "main")
    main_fn(rest)


if __name__ == "__main__":
    main()
