"""List members of a PagerDuty team with their team roles (read-only).

Replaces the deprecated pd_get_teams_user_role.py. For ad-hoc reads from an
MCP-aware client, the PagerDuty MCP server's list_team_members tool is the
better choice; this command exists for CLI/CSV pipelines.
"""

from __future__ import annotations

from ..api import paginate
from ..cli import init, standard_parser
from ..config import get_team_id
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("team_members")

FIELDNAMES = ["user_id", "type", "name", "role"]


def build_parser():
    p = standard_parser(
        "List members of a PagerDuty team with roles.", formats=("table", "csv", "json")
    )
    p.add_argument("--team-id", help="PagerDuty team ID (or set PD_TEAM_ID).")
    return p


def member_row(member: dict) -> dict:
    user = member.get("user", {})
    return {
        "user_id": user.get("id", ""),
        "type": user.get("type", ""),
        "name": user.get("summary", ""),
        "role": member.get("role", ""),
    }


def fetch_members(token, team_id) -> list[dict]:
    """Paginated — teams with more than 25 members are fully listed."""
    return list(paginate(f"teams/{team_id}/members", token, items_key="members"))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    team_id = get_team_id(args.team_id)
    members = fetch_members(token, team_id)
    log.info("Found %d members on team %s.", len(members), team_id)
    rows = [member_row(m) for m in members]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=members), args.output)
    return 0
