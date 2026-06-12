#!/usr/bin/env python3
"""Compatibility shim — logic moved to pagerduty_ops.commands.scim_user_audit.

Behavior is preserved, plus: retries with 429 backoff, structured stderr
logging, and non-zero exit codes on failure (see docs/usage.md).
"""

from pagerduty_ops.cli import run
from pagerduty_ops.commands.scim_user_audit import main

if __name__ == "__main__":
    run(main)
