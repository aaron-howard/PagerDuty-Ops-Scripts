"""
PagerDuty Logging Module

Centralized logging configuration and utilities.
"""

import json
import logging
import logging.handlers
import os
from datetime import datetime, timezone
from typing import Any, Optional


class PagerDutyFormatter(logging.Formatter):
    """Custom formatter for PagerDuty logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with additional context."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        return json.dumps(log_data)


class MaskingFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""

    SENSITIVE_KEYS = ["token", "api_key", "password", "secret", "access_token"]

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive information in log messages."""
        original_msg = record.msg
        if isinstance(original_msg, str):
            for key in self.SENSITIVE_KEYS:
                if key in original_msg.lower():
                    record.msg = original_msg.replace(key, f"{key}_MASKED")
        return True


def setup_logging(
    name: str = "pagerduty",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    console_log: bool = True,
) -> logging.Logger:
    """
    Set up logging configuration.

    Args:
        name: Logger name
        level: Logging level
        log_file: Path to log file (optional)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
        console_log: Whether to log to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers to avoid duplicate logs
    logger.handlers.clear()

    # Create formatter
    formatter = PagerDutyFormatter()

    # Add masking filter
    masking_filter = MaskingFilter()

    # Console handler
    if console_log:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(masking_filter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(masking_filter)
        logger.addHandler(file_handler)

    return logger


def log_api_request(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    success: bool = True,
    **kwargs: Any,
) -> None:
    """
    Log API request details.

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: API endpoint
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        success: Whether the request was successful
        **kwargs: Additional context to log
    """
    extra = {
        "request_id": kwargs.get("request_id"),
        "method": method,
        "endpoint": endpoint,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "success": success,
    }

    if success:
        logger.info(f"API {method} {endpoint} - {status_code} ({duration_ms:.2f}ms)", extra=extra)
    else:
        logger.error(
            f"API {method} {endpoint} failed - {status_code} ({duration_ms:.2f}ms)", extra=extra
        )


# Global logger instance
logger = setup_logging()
