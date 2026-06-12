"""pagerduty_ops — production-hardened PagerDuty operations toolkit.

Public surface:
    pagerduty_ops.api      HTTP client (retries, rate limiting, typed errors, pagination)
    pagerduty_ops.config   token / team-id / From-email resolution
    pagerduty_ops.log      structured logging setup
    pagerduty_ops.output   table / csv / json rendering and file output
    pagerduty_ops.commands one module per CLI command
"""

__version__ = "1.0.0"
