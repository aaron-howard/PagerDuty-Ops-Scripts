"""Package metadata helpers (avoid import cycles with ``api_client`` / ``__init__``)."""

from __future__ import annotations

import importlib.metadata

_DIST_NAME = "pagerduty-ops-scripts"


def distribution_version() -> str:
    """Installed distribution version, or a local-dev placeholder when not installed."""
    try:
        return importlib.metadata.version(_DIST_NAME)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0+unknown"
