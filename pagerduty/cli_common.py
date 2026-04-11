"""Shared CLI helpers for operational scripts (env, config, token, logging)."""

from __future__ import annotations

import argparse
import contextlib
import getpass
import logging
import os
import sys
import threading
from collections.abc import Iterator, Sequence

import dotenv

from pagerduty.config import configure_default_config_file, get_config

# Exit codes for all CLIs (argparse uses 2 for parse errors by convention).
EXIT_SUCCESS = 0
EXIT_ERROR = 1  # operational failure: auth, API, I/O, unexpected errors
EXIT_USAGE = 2  # invalid invocation or argument values (after parse, or dispatcher)


def init_cli_env() -> None:
    """Load variables from a local ``.env`` file into the process environment."""
    dotenv.load_dotenv()


def add_standard_cli_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="PagerDuty config file (.yaml/.json). Overrides default search paths.",
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument("-v", "--verbose", action="store_true", help="More log output")
    g.add_argument("-q", "--quiet", action="store_true", help="Less log output")


def add_deprecated_token_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-t",
        "--token",
        help="API token (avoid: use PD_API_TOKEN or config file; may be stored in shell history)",
    )


def add_no_progress_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress fetch/status lines (errors and prompts still print)",
    )


def show_progress(args: argparse.Namespace | None) -> bool:
    """False when ``--no-progress`` was passed on *args*."""
    if args is None:
        return True
    return not getattr(args, "no_progress", False)


def status_line(
    args: argparse.Namespace | None,
    msg: str,
    *,
    end: str = "\n",
    flush: bool = False,
) -> None:
    """Print *msg* unless progress is disabled via ``--no-progress``."""
    if not show_progress(args):
        return
    print(msg, end=end, flush=flush)


_SPINNER_FRAMES = ("-", "\\", "|", "/")
_SPINNER_INTERVAL_SEC = 0.12


@contextlib.contextmanager
def progress_wait(args: argparse.Namespace | None, label: str) -> Iterator[None]:
    """
    Show activity while a slow operation runs.

    On an interactive TTY (``stdout``), prints a small ASCII spinner and *label* on one line.
    Otherwise prints *label* once. Disabled when ``--no-progress`` is set on *args*.
    The line is cleared after the block on a TTY so a following :func:`status_line` can print normally.
    """
    if not show_progress(args):
        yield
        return

    out = sys.stdout
    if not out.isatty():
        print(label, flush=True)
        yield
        return

    stop = threading.Event()

    def _spin() -> None:
        i = 0
        while not stop.wait(_SPINNER_INTERVAL_SEC):
            frame = _SPINNER_FRAMES[i % len(_SPINNER_FRAMES)]
            i += 1
            print(f"\r{frame} {label}", end="", flush=True, file=out)

    worker = threading.Thread(target=_spin, daemon=True)
    worker.start()
    try:
        yield
    finally:
        stop.set()
        worker.join(timeout=_SPINNER_INTERVAL_SEC * 4)
        clear_width = len(label) + 3
        print("\r" + " " * clear_width + "\r", end="", flush=True, file=out)


def parse_argv(argv: Sequence[str] | None) -> list[str] | None:
    """Normalize ``argv`` for :meth:`argparse.ArgumentParser.parse_args` (``None`` = sys.argv)."""
    if argv is None:
        return None
    return list(argv)


def apply_log_level_from_args(args: argparse.Namespace, *, default: int = logging.INFO) -> None:
    if getattr(args, "verbose", False):
        level = logging.DEBUG
    elif getattr(args, "quiet", False):
        level = logging.WARNING
    else:
        level = default
    logging.basicConfig(level=level, format="%(levelname)s %(name)s %(message)s")

    # Verbose scripts should not enable urllib3's DEBUG wire logs (headers/bodies).
    if (
        getattr(args, "verbose", False)
        and not os.environ.get("PAGERDUTY_ALLOW_HTTP_LIBRARY_DEBUG", "").strip()
    ):
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)


def apply_cli_config_path(args: argparse.Namespace) -> None:
    """If ``args.config`` is set, reset default config to load that file."""
    path = getattr(args, "config", None)
    if path:
        configure_default_config_file(path)


def resolve_api_token(
    cli_token: str | None,
    *,
    allow_prompt: bool = True,
    prompt: str = "PagerDuty API token: ",
) -> str | None:
    """
    Resolve token from CLI (deprecated), environment, config file, or prompt.

    Warns on stderr when ``cli_token`` is used.
    """
    if cli_token is not None and cli_token != "":
        print(
            "Warning: passing the API token via -t/--token can expose it in shell history; "
            "prefer PD_API_TOKEN or a config file.",
            file=sys.stderr,
        )
        return cli_token.strip()

    env_tok = os.environ.get("PD_API_TOKEN")
    if env_tok:
        return env_tok.strip()

    cfg_tok = get_config().get("api_token")
    if isinstance(cfg_tok, str) and cfg_tok.strip():
        return cfg_tok.strip()

    if allow_prompt:
        return getpass.getpass(prompt).strip() or None
    return None


def resolve_api_token_or_exit(
    cli_token: str | None,
    *,
    allow_prompt: bool = True,
    prompt: str = "PagerDuty API token: ",
) -> str:
    token = resolve_api_token(cli_token, allow_prompt=allow_prompt, prompt=prompt)
    if not token:
        print("Error: No API token (set PD_API_TOKEN, use a config file, or enter when prompted).")
        sys.exit(EXIT_ERROR)
    return token
