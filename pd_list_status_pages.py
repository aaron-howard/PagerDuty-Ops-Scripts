#!/usr/bin/env python3
"""List PagerDuty status pages, or list posts for one status page.

Uses GET /status_pages and GET /status_pages/{id}/posts. Read-only.
"""

import argparse
import csv
import io
import json
import sys

from pd_common import add_token_arguments, get_pd_api_token, make_api_request, paginate


def parse_arguments():
    parser = argparse.ArgumentParser(description="List PagerDuty status pages or posts on a page.")
    add_token_arguments(parser)
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "csv", "json"],
        default="table",
        help="Output format (default: table).",
    )
    parser.add_argument("-o", "--output", help="Output file (default stdout).")
    parser.add_argument(
        "--name-filter",
        help="Substring match (case-insensitive) against status page name (pages mode only).",
    )
    parser.add_argument(
        "--posts",
        metavar="STATUS_PAGE_ID",
        help="List posts for this status page instead of listing pages.",
    )
    return parser.parse_args()


def fetch_pages(token, name_filter):
    print("Fetching status pages...", end="", flush=True, file=sys.stderr)
    pages = list(paginate("status_pages", token))
    if name_filter:
        needle = name_filter.lower()
        pages = [p for p in pages if needle in (p.get("name") or "").lower()]
    print(f" {len(pages)} found.", file=sys.stderr)
    return pages


def fetch_posts(token, page_id):
    print(f"Fetching posts for status page {page_id}...", end="", flush=True, file=sys.stderr)
    probe = make_api_request(f"status_pages/{page_id}/posts", token, params={"limit": 1})
    if not probe:
        return []
    items_key = "posts"
    if items_key not in probe and "status_page_posts" in probe:
        items_key = "status_page_posts"
    posts = list(
        paginate(f"status_pages/{page_id}/posts", token, items_key=items_key)
    )
    print(f" {len(posts)} found.", file=sys.stderr)
    return posts


def render_pages(pages, fmt):
    if fmt == "json":
        return json.dumps(pages, indent=2)
    rows = []
    for p in pages:
        rows.append(
            {
                "id": p.get("id", ""),
                "name": p.get("name") or p.get("summary", ""),
                "html_url": p.get("html_url", ""),
            }
        )
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["id", "name", "html_url"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()
    try:
        from tabulate import tabulate
    except ImportError:
        return "\n".join(f"{r['id']}\t{r['name']}" for r in rows) + "\n"
    return (
        tabulate(
            [[r["id"], r["name"], r["html_url"]] for r in rows],
            headers=["ID", "Name", "URL"],
            tablefmt="github",
        )
        + f"\n\nTotal: {len(rows)} status pages\n"
    )


def render_posts(posts, fmt):
    if fmt == "json":
        return json.dumps(posts, indent=2)
    rows = []
    for p in posts:
        post_type = p.get("post_type") or ""
        status_obj = p.get("status") or {}
        status_id = status_obj.get("id") if isinstance(status_obj, dict) else ""
        rows.append(
            {
                "id": p.get("id", ""),
                "title": p.get("title", ""),
                "post_type": post_type,
                "starts_at": p.get("starts_at", ""),
                "ends_at": p.get("ends_at", ""),
                "status": status_id,
            }
        )
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["id", "title", "post_type", "starts_at", "ends_at", "status"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return buf.getvalue()
    try:
        from tabulate import tabulate
    except ImportError:
        return "\n".join(f"{r['id']}\t{r['title']}\t{r['post_type']}" for r in rows) + "\n"
    return (
        tabulate(
            [
                [r["id"], r["title"], r["post_type"], r["starts_at"], r["ends_at"], r["status"]]
                for r in rows
            ],
            headers=["ID", "Title", "Type", "Starts", "Ends", "Status"],
            tablefmt="github",
        )
        + f"\n\nTotal: {len(posts)} posts\n"
    )


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)

    if args.posts:
        posts = fetch_posts(token, args.posts)
        payload = render_posts(posts, args.format)
    else:
        pages = fetch_pages(token, args.name_filter)
        payload = render_pages(pages, args.format)

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(payload)
        print(f"Wrote output to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(payload)


if __name__ == "__main__":
    main()
