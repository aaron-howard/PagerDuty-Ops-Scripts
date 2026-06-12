"""List PagerDuty status pages, or posts for one status page. Read-only."""

from __future__ import annotations

from ..api import paginate, request
from ..cli import init, standard_parser
from ..log import get_logger
from ..output import render_rows, write_payload

log = get_logger("list_status_pages")

PAGE_FIELDS = ["id", "name", "html_url"]
POST_FIELDS = ["id", "title", "post_type", "starts_at", "ends_at", "status"]


def build_parser():
    p = standard_parser(
        "List PagerDuty status pages or posts on one page.", formats=("table", "csv", "json")
    )
    p.add_argument("--name-filter", help="Substring match on page name (pages mode only).")
    p.add_argument("--posts", metavar="STATUS_PAGE_ID",
                   help="List posts for this status page instead of listing pages.")
    return p


def page_row(p: dict) -> dict:
    return {
        "id": p.get("id", ""),
        "name": p.get("name") or p.get("summary", ""),
        "html_url": p.get("html_url", ""),
    }


def post_row(p: dict) -> dict:
    status_obj = p.get("status") or {}
    return {
        "id": p.get("id", ""),
        "title": p.get("title", ""),
        "post_type": p.get("post_type") or "",
        "starts_at": p.get("starts_at", ""),
        "ends_at": p.get("ends_at", ""),
        "status": status_obj.get("id", "") if isinstance(status_obj, dict) else "",
    }


def fetch_posts(token, page_id) -> list:
    # Probe once: the items key has shipped as both 'posts' and 'status_page_posts'.
    probe = request(f"status_pages/{page_id}/posts", token, params={"limit": 1})
    items_key = "posts" if "posts" in probe else "status_page_posts"
    return list(paginate(f"status_pages/{page_id}/posts", token, items_key=items_key))


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    if args.posts:
        log.info("Fetching posts for status page %s...", args.posts)
        posts = fetch_posts(token, args.posts)
        log.info("Found %d posts.", len(posts))
        payload = render_rows([post_row(p) for p in posts], POST_FIELDS, args.format, raw=posts)
    else:
        log.info("Fetching status pages...")
        pages = list(paginate("status_pages", token))
        if args.name_filter:
            needle = args.name_filter.lower()
            pages = [p for p in pages if needle in (p.get("name") or "").lower()]
        log.info("Found %d status pages.", len(pages))
        payload = render_rows([page_row(p) for p in pages], PAGE_FIELDS, args.format, raw=pages)
    write_payload(payload, args.output)
    return 0
