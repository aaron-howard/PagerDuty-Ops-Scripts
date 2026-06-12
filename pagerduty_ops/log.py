"""Structured logging for all commands.

All diagnostics go to stderr — stdout is reserved exclusively for data
(CSV/JSON/table output), so exports can be piped safely.
"""

from __future__ import annotations

import logging
import sys

ROOT_LOGGER = "pd_ops"
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def configure_logging(verbose: bool = False, quiet: bool = False, log_file: str | None = None):
    """Idempotent setup. INFO default, DEBUG with --verbose, ERROR with --quiet."""
    logger = logging.getLogger(ROOT_LOGGER)
    if logger.handlers:  # already configured (e.g. tests, repeated calls)
        return logger
    level = logging.DEBUG if verbose else logging.ERROR if quiet else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)
    if log_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(fh)
    logger.setLevel(level)
    return logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{ROOT_LOGGER}.{name}")
