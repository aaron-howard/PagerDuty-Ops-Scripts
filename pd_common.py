"""DEPRECATED compatibility layer - use the pagerduty_ops package instead.

Preserves the historical pd_common API surface for any external callers:
- make_api_request returns None on failure (the package's request() raises
  PDApiError instead - prefer that for new code)
- paginate / paginate_cursor / fetch_all / expand_query_params re-exported
- get_pd_api_token / get_pd_team_id / build_headers / add_token_arguments kept

This module will be removed in a future major version.
"""

from __future__ import annotations

import warnings

from pagerduty_ops import api as _api
from pagerduty_ops.api import ACCEPT_HEADER as PD_API_HEADERS_ACCEPT
from pagerduty_ops.api import PD_API_BASE as PD_API_BASE
from pagerduty_ops.api import REQUEST_TIMEOUT as REQUEST_TIMEOUT
from pagerduty_ops.api import PDApiError as PDApiError
from pagerduty_ops.api import build_headers as build_headers
from pagerduty_ops.api import expand_query_params as expand_query_params
from pagerduty_ops.api import fetch_all as fetch_all
from pagerduty_ops.api import paginate as paginate
from pagerduty_ops.api import paginate_cursor as paginate_cursor
from pagerduty_ops.bulkops import apply_name_affix_update as apply_name_affix_update
from pagerduty_ops.bulkops import name_has_affix as _name_has_affix
from pagerduty_ops.cli import add_token_args as add_token_arguments
from pagerduty_ops.config import get_api_token as get_pd_api_token
from pagerduty_ops.config import get_team_id as get_pd_team_id
from pagerduty_ops.log import get_logger

__all__ = [
    "PD_API_BASE", "PD_API_HEADERS_ACCEPT", "REQUEST_TIMEOUT", "PDApiError",
    "build_headers", "expand_query_params", "fetch_all", "paginate",
    "paginate_cursor", "apply_name_affix_update", "_name_has_affix",
    "add_token_arguments", "get_pd_api_token", "get_pd_team_id",
    "make_api_request",
]

warnings.warn(
    "pd_common is deprecated; import from pagerduty_ops instead.",
    DeprecationWarning,
    stacklevel=2,
)

log = get_logger("pd_common")


def make_api_request(endpoint, token, method="GET", params=None, data=None, extra_headers=None):
    """Legacy contract: returns parsed JSON, or None on any failure (logged)."""
    try:
        return _api.request(endpoint, token, method=method, params=params, data=data,
                            extra_headers=extra_headers)
    except PDApiError as e:
        log.error("%s", e)
        return None
