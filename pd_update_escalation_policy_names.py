#!/usr/bin/env python3
"""Append 'EP' to PagerDuty escalation policy names that don't already have it."""

import argparse

from pd_common import append_suffix_update, get_pd_api_token


def parse_arguments():
    parser = argparse.ArgumentParser(description='Update PagerDuty escalation policy names by appending "EP".')
    parser.add_argument("-t", "--token", help="PagerDuty API token")
    parser.add_argument("-l", "--list", action="store_true", help="List escalation policies without making changes")
    parser.add_argument("-f", "--filter", help="Only process policies containing this text in their name")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    return parser.parse_args()


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token)
    append_suffix_update(
        token=token,
        resource="escalation_policies",
        item_kind="escalation_policy",
        suffix="EP",
        name_filter=args.filter,
        list_only=args.list,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
