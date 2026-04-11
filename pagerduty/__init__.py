"""
PagerDuty operations toolkit — HTTP client, config, and resource helpers for admin scripts.
"""

from ._meta import distribution_version
from .api_client import PagerDutyAPIClient
from .config import Config, configure_default_config_file, get_config, load_config
from .errors import APIError, AuthError, ConfigError, PagerDutyError
from .logging import setup_logging

__all__ = [
    "APIError",
    "AuthError",
    "Config",
    "ConfigError",
    "PagerDutyAPIClient",
    "PagerDutyError",
    "__version__",
    "configure_default_config_file",
    "get_config",
    "load_config",
    "setup_logging",
]

__version__ = distribution_version()
__author__ = "PagerDuty Scripts Team"
__license__ = "MIT"
