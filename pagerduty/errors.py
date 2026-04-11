"""
PagerDuty Error Classes

Custom exception classes for PagerDuty API interactions.
"""


class PagerDutyError(Exception):
    """Base class for all PagerDuty-related errors."""

    pass


class APIError(PagerDutyError):
    """Exception raised for PagerDuty API errors."""

    def __init__(self, message, status_code=None, response=None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(f"API Error {status_code}: {message}" if status_code else message)


class AuthError(PagerDutyError):
    """Exception raised for authentication failures."""

    def __init__(self, message):
        self.message = message
        super().__init__(f"Authentication Error: {message}")


class ConfigError(PagerDutyError):
    """Exception raised for configuration issues."""

    def __init__(self, message):
        self.message = message
        super().__init__(f"Configuration Error: {message}")


class RateLimitError(PagerDutyError):
    """Exception raised when rate limits are exceeded."""

    def __init__(self, message, retry_after=None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(
            f"Rate Limit Exceeded: {message}"
            + (f" Retry after {retry_after} seconds" if retry_after else "")
        )


class NotFoundError(PagerDutyError):
    """Exception raised when a resource is not found."""

    def __init__(self, resource_type, resource_id=None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(
            f"{resource_type} not found" + (f" (ID: {resource_id})" if resource_id else "")
        )


class ValidationError(PagerDutyError):
    """Exception raised for validation failures."""

    def __init__(self, message, field=None):
        self.message = message
        self.field = field
        super().__init__(f"Validation Error: {message}" + (f" (Field: {field})" if field else ""))
