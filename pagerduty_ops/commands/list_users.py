"""List all PagerDuty users (flat directory export for pipelines and audits)."""

from __future__ import annotations

from ..api import fetch_all
from ..cli import init, standard_parser
from ..output import render_rows, write_payload

FIELDNAMES = ["id", "name", "email", "role", "job_title"]


def build_parser():
    p = standard_parser(
        "List PagerDuty users (id, name, email, role, job title).",
        formats=("table", "csv", "json"),
    )
    p.add_argument(
        "--filter",
        dest="text_filter",
        metavar="TEXT",
        help="Substring match on name or email (server-side query, case-insensitive).",
    )
    return p


def user_row(u: dict) -> dict:
    return {f: (u.get(f) or "") for f in FIELDNAMES}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    # /users supports server-side `query` on name and email; keep a client-side
    # pass as well so behavior matches the documented substring contract.
    params = {"query": args.text_filter} if args.text_filter else None
    users = fetch_all("users", token, params=params, label="users")
    if args.text_filter:
        needle = args.text_filter.lower()
        users = [
            u for u in users
            if needle in (u.get("name") or "").lower() or needle in (u.get("email") or "").lower()
        ]
    rows = [user_row(u) for u in users]
    write_payload(render_rows(rows, FIELDNAMES, args.format), args.output)
    return 0
