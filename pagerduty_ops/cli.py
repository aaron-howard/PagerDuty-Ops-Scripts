"""Shared CLI plumbing: argument groups, confirmation guards, exit-code policy.

Exit codes (documented contract — schedulers and CI rely on these):
    0   success (including "nothing to do" and reviewed dry-runs)
    1   one or more operations failed (partial failure in bulk runs)
    2   usage / configuration error (bad arguments, missing token)
    3   authentication / authorization error (token rejected)
    130 interrupted (Ctrl-C)
"""

from __future__ import annotations

import argparse
import sys

from .api import PDApiError
from .config import get_api_token
from .log import configure_logging, get_logger

log = get_logger("cli")

EXIT_OK = 0
EXIT_FAILURES = 1
EXIT_USAGE = 2
EXIT_AUTH = 3


def add_token_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-t",
        "--token",
        help="DEPRECATED: prefer the PD_API_TOKEN environment variable "
        "(CLI tokens leak into shell history).",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Prompt securely for the API token when PD_API_TOKEN is unset (local dev only).",
    )


def add_logging_args(parser: argparse.ArgumentParser) -> None:
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-v", "--verbose", action="store_true", help="Debug logging to stderr.")
    g.add_argument("-q", "--quiet", action="store_true", help="Errors only.")
    parser.add_argument("--log-file", help="Also append logs to this file.")


def add_format_args(parser, formats=("table", "csv", "json"), default="table") -> None:
    parser.add_argument(
        "-f", "--format", choices=list(formats), default=default,
        help=f"Output format (default: {default}).",
    )
    parser.add_argument("-o", "--output", help="Write to this file instead of stdout.")


def add_write_guards(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview every change without writing."
    )
    parser.add_argument(
        "-y", "--yes", action="store_true", help="Skip the interactive confirmation prompt."
    )


def standard_parser(
    description: str, *, formats=None, write_guards=False
) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    add_token_args(p)
    add_logging_args(p)
    if formats:
        add_format_args(p, formats)
    if write_guards:
        add_write_guards(p)
    return p


def init(args) -> str:
    """Configure logging from parsed args and resolve the API token."""
    configure_logging(
        verbose=getattr(args, "verbose", False),
        quiet=getattr(args, "quiet", False),
        log_file=getattr(args, "log_file", None),
    )
    return get_api_token(args.token, allow_prompt=args.prompt)


def confirm(question: str, *, assume_yes: bool, dry_run: bool = False) -> bool:
    """Interactive write guard. Dry runs and -y/--yes proceed without asking."""
    if dry_run or assume_yes:
        return True
    if not sys.stdin.isatty():
        log.error("Refusing to write without confirmation on a non-interactive stdin. "
                  "Pass -y/--yes (after reviewing --dry-run output).")
        return False
    answer = input(f"{question} (y/n): ").strip().lower()
    if answer != "y":
        print("Operation cancelled.", file=sys.stderr)
        return False
    return True


def finish_bulk(succeeded: int, failed: int, *, dry_run: bool, label: str = "items") -> int:
    """Standard bulk-run epilogue: summary to stderr, non-zero exit on failures."""
    verb = "Would update" if dry_run else "Updated"
    log.info("Summary: %s %d %s, %d failed.", verb, succeeded, label, failed)
    return EXIT_FAILURES if failed else EXIT_OK


def run(main_fn, argv=None) -> None:
    """Entry-point wrapper for shims/console scripts: maps exceptions to exit codes."""
    try:
        sys.exit(main_fn(argv))
    except PDApiError as e:
        configure_logging()  # no-op if already configured
        log.error("%s", e)
        sys.exit(EXIT_AUTH if e.is_auth_error else EXIT_FAILURES)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        sys.exit(130)
