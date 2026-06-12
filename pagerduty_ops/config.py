"""Configuration and secret resolution.

Resolution order for the API token:
1. --token CLI argument (DEPRECATED — leaks into shell history / process list)
2. PD_API_TOKEN environment variable (recommended; inject from your secret store)
3. interactive getpass prompt, only when --prompt was passed (local dev)

No secret is ever written to disk or logged by this module.
"""

from __future__ import annotations

import getpass
import logging
import os
import sys

import dotenv

dotenv.load_dotenv()

log = logging.getLogger("pd_ops.config")


class ConfigError(SystemExit):
    """Missing/invalid configuration. Exits with code 2 (usage error)."""

    def __init__(self, message: str):
        print(f"Error: {message}", file=sys.stderr)
        super().__init__(2)


def get_api_token(cli_token: str | None = None, *, allow_prompt: bool = False) -> str:
    if cli_token:
        log.warning(
            "-t/--token on the command line is deprecated (visible in shell history and "
            "process lists). Prefer the PD_API_TOKEN environment variable."
        )
    token = cli_token or os.environ.get("PD_API_TOKEN")
    if not token and allow_prompt:
        token = getpass.getpass("Enter your PagerDuty API token: ")
    if not token:
        raise ConfigError(
            "No API token provided. Set PD_API_TOKEN, or use --prompt for interactive entry."
        )
    return token.strip()


def get_team_id(cli_team_id: str | None = None, *, allow_prompt: bool = True) -> str:
    team_id = cli_team_id or os.environ.get("PD_TEAM_ID")
    if not team_id and allow_prompt and sys.stdin.isatty():
        team_id = input("Enter your PagerDuty team ID: ")
    if not team_id or not team_id.strip():
        raise ConfigError("No team ID provided. Pass --team-id or set PD_TEAM_ID.")
    return team_id.strip()


def get_from_email(cli_value: str | None = None, *, required: bool = True) -> str | None:
    """PagerDuty 'From' header value required by some mutating endpoints."""
    value = cli_value or os.environ.get("PD_FROM_EMAIL")
    if not value and required:
        raise ConfigError(
            "A PagerDuty 'From' email is required. Pass --from-email or set PD_FROM_EMAIL."
        )
    if value and "@" not in value:
        raise ConfigError(f"--from-email {value!r} does not look like an email address.")
    return value
