"""Bulk-rename PagerDuty services, schedules, or escalation policies by adding
a literal prefix or suffix. Idempotent: skips names that already carry it."""

from __future__ import annotations

import sys

from ..bulkops import apply_name_affix_update
from ..cli import init, standard_parser

RESOURCE_KIND = {
    "services": "service",
    "schedules": "schedule",
    "escalation_policies": "escalation_policy",
}


def build_parser():
    p = standard_parser(
        "Bulk-add a literal prefix or suffix to PagerDuty resource names. "
        "Skips items that already start/end with the affix.",
        write_guards=True,
    )
    p.add_argument("--resource", required=True, choices=sorted(RESOURCE_KIND))
    g = p.add_mutually_exclusive_group()
    g.add_argument("--prefix", metavar="TEXT", help="Literal prefix to add.")
    g.add_argument("--suffix", metavar="TEXT", help="Literal suffix to add.")
    p.add_argument("-l", "--list", action="store_true", help="List resources; no changes.")
    p.add_argument("--filter", dest="name_filter",
                   help="Only resources whose name contains this substring.")
    p.add_argument("--ignore-case", action="store_true",
                   help="Case-insensitive check for whether the affix is already present.")
    return p


def resolve_affix(args):
    if args.list:
        return "suffix", ""
    if args.prefix is not None:
        return "prefix", args.prefix
    if args.suffix is not None:
        return "suffix", args.suffix
    if sys.stdin.isatty():
        choice = input("Add (p)refix or (s)uffix? ").strip().lower()
        if choice.startswith("p"):
            position = "prefix"
        elif choice.startswith("s"):
            position = "suffix"
        else:
            print("Error: enter 'p' or 's'.", file=sys.stderr)
            raise SystemExit(2)
        return position, input("Affix string (applied literally, e.g. ' SVC'): ")
    print("Error: --prefix or --suffix is required when not running interactively.",
          file=sys.stderr)
    raise SystemExit(2)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    token = init(args)
    position, affix = resolve_affix(args)
    return apply_name_affix_update(
        token=token,
        resource=args.resource,
        item_kind=RESOURCE_KIND[args.resource],
        position=position,
        affix=affix,
        name_filter=args.name_filter,
        list_only=args.list,
        dry_run=args.dry_run,
        assume_yes=args.yes,
        ignore_case=args.ignore_case,
    )
