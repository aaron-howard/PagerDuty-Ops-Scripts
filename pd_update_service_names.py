#!/usr/bin/env python3
"""Append 'SVC' to PagerDuty service names that don't already have it."""

import argparse

from pd_common import append_suffix_update, add_token_arguments, get_pd_api_token


def parse_arguments():
    parser = argparse.ArgumentParser(description='Update PagerDuty service names by appending "SVC".')
    add_token_arguments(parser)
    parser.add_argument("-l", "--list", action="store_true", help="List services without making changes")
    parser.add_argument("-f", "--filter", help="Only process services containing this text in their name")
    parser.add_argument("-d", "--dry-run", action="store_true", help="Show what would be done without making changes")
    return parser.parse_args()


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)
    append_suffix_update(
        token=token,
        resource="services",
        item_kind="service",
        suffix="SVC",
        name_filter=args.filter,
        list_only=args.list,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
