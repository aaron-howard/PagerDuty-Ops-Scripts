"""
PagerDuty Python SDK

A comprehensive Python package for interacting with PagerDuty APIs.
"""

from .api_client import PagerDutyAPIClient
from .config import Config, load_config
from .errors import APIError, AuthError, ConfigError, PagerDutyError
from .logging import setup_logging

__version__ = "1.0.0"
__author__ = "PagerDuty Scripts Team"
__license__ = "MIT"
