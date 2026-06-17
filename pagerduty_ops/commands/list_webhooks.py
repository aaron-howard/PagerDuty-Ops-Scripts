"""List PagerDuty webhook subscriptions (V3 webhook_subscriptions API)."""

from __future__ import annotations

from ..api import fetch_all
from ..cli import init, standard_parser
from ..output import render_rows, write_payload
from .list_incidents import parse_multi

FIELDNAMES = [
    "id",
    "description",
    "scope_type",
    "scope_id",
    "endpoint_url",
    "events",
    "html_url",
]


def build_parser():
    p = standard_parser(
        "List PagerDuty webhook subscriptions (scope, endpoint, events).",
        formats=("table", "csv", "json"),
    )
    p.add_argument(
        "--filter",
        dest="text_filter",
        metavar="TEXT",
        help="Substring match on webhook description (case-insensitive).",
    )
    p.add_argument(
        "--service-id",
        dest="service_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Only webhooks scoped to this service; repeat or comma-separate.",
    )
    p.add_argument(
        "--team-id",
        dest="team_ids",
        action="append",
        default=[],
        metavar="ID",
        help="Only webhooks scoped to this team; repeat or comma-separate.",
    )
    return p


def webhook_scope(webhook: dict) -> tuple[str, str]:
    """Return (scope_type, scope_id) across known webhook payload shapes."""
    flt = webhook.get("filter") or {}
    if flt.get("type") and flt.get("id"):
        return flt["type"], flt["id"]
    svc = webhook.get("service")
    if svc and svc.get("id"):
        return "service_reference", svc["id"]
    conn = (webhook.get("delivery_method") or {}).get("connection") or {}
    svc = conn.get("service") or {}
    if svc.get("id"):
        return "service_reference", svc["id"]
    return "", ""


def webhook_endpoint(webhook: dict) -> str:
    delivery = webhook.get("delivery_method") or {}
    return delivery.get("url") or ""


def webhook_row(webhook: dict) -> dict:
    scope_type, scope_id = webhook_scope(webhook)
    events = webhook.get("events") or []
    return {
        "id": webhook.get("id") or "",
        "description": webhook.get("description") or "",
        "scope_type": scope_type,
        "scope_id": scope_id,
        "endpoint_url": webhook_endpoint(webhook),
        "events": ", ".join(events),
        "html_url": webhook.get("html_url") or "",
    }


def _matches_scope_filters(webhook: dict, service_ids: set[str], team_ids: set[str]) -> bool:
    scope_type, scope_id = webhook_scope(webhook)
    if service_ids and not (scope_type == "service_reference" and scope_id in service_ids):
        return False
    if team_ids and not (scope_type == "team_reference" and scope_id in team_ids):
        return False
    return True


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    webhooks = fetch_all("webhook_subscriptions", token, label="webhook subscriptions")
    service_ids = set(parse_multi(args.service_ids))
    team_ids = set(parse_multi(args.team_ids))
    if service_ids or team_ids:
        webhooks = [
            w for w in webhooks
            if _matches_scope_filters(w, service_ids, team_ids)
        ]
    if args.text_filter:
        needle = args.text_filter.lower()
        webhooks = [
            w for w in webhooks
            if needle in (w.get("description") or "").lower()
        ]
    rows = [webhook_row(w) for w in webhooks]
    write_payload(render_rows(rows, FIELDNAMES, args.format, raw=webhooks), args.output)
    return 0
