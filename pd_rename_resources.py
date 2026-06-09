#!/usr/bin/env python3
"""Bulk-rename PagerDuty services, schedules, or escalation policies with a configurable prefix or suffix."""

import argparse
import sys

from pd_common import add_token_arguments, apply_name_affix_update, get_pd_api_token

RESOURCE_KIND = {
    "services": "service",
    "schedules": "schedule",
    "escalation_policies": "escalation_policy",
}


def _affix_from_tty():
    if not sys.stdin.isatty():
        return None, None
    print("No --prefix/--suffix provided; interactive mode.", file=sys.stderr)
    choice = input("Add (p)refix or (s)uffix? ").strip().lower()
    if choice.startswith("p"):
        position = "prefix"
    elif choice.startswith("s"):
        position = "suffix"
    else:
        print("Error: enter 'p' for prefix or 's' for suffix.", file=sys.stderr)
        return None, None
    affix = input("Affix string (applied literally, e.g. ' SVC' or '-prod'): ")
    return position, affix


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=(
            "Bulk-add a literal prefix or suffix to PagerDuty resource names "
            "(services, schedules, or escalation policies). "
            "Skips items that already start or end with the affix (see --ignore-case)."
        )
    )
    add_token_arguments(parser)
    parser.add_argument(
        "--resource",
        required=True,
        choices=sorted(RESOURCE_KIND),
        help="Which resource type to rename",
    )
    g = parser.add_mutually_exclusive_group(required=False)
    g.add_argument(
        "--prefix",
        metavar="TEXT",
        help="Prefix to add to the start of each name (mutually exclusive with --suffix)",
    )
    g.add_argument(
        "--suffix",
        metavar="TEXT",
        help="Suffix to add to the end of each name (mutually exclusive with --prefix)",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List resources without making changes",
    )
    parser.add_argument(
        "-f",
        "--filter",
        dest="name_filter",
        help="Only process resources whose name contains this substring (case-insensitive)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt before writes",
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help="When checking if the affix is already present, compare case-insensitively",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    token = get_pd_api_token(args.token, allow_prompt=args.prompt)

    position = "suffix"
    affix = ""
    if args.list:
        pass  # affix not used when listing only
    elif args.prefix is not None:
        position = "prefix"
        affix = args.prefix
    elif args.suffix is not None:
        position = "suffix"
        affix = args.suffix
    else:
        position, affix = _affix_from_tty()
        if position is None:
            sys.exit(2)

    if not args.list and affix is None:
        print("Error: affix string is required.", file=sys.stderr)
        sys.exit(2)

    item_kind = RESOURCE_KIND[args.resource]
    apply_name_affix_update(
        token=token,
        resource=args.resource,
        item_kind=item_kind,
        position=position,
        affix=affix,
        name_filter=args.name_filter,
        list_only=args.list,
        dry_run=args.dry_run,
        confirm=not args.yes,
        ignore_case=args.ignore_case,
    )


if __name__ == "__main__":
    main()
