"""
PagerDuty API Client

Core API client for interacting with PagerDuty REST APIs.
"""

import json
import logging
import time
from typing import Any
from urllib.parse import urljoin

import requests

from ._meta import distribution_version
from .config import get_config
from .errors import APIError, AuthError, NotFoundError, PagerDutyError, RateLimitError
from .logging import log_api_request

# Set up logging
logger = logging.getLogger(__name__)


class PagerDutyAPIClient:
    """PagerDuty API Client."""

    DEFAULT_BASE_URL = "https://api.pagerduty.com"
    DEFAULT_API_VERSION = "v2"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RATE_LIMIT_RETRY_AFTER = 60  # seconds
    # Guard against buggy or non-v2 collection responses that never clear ``more``.
    MAX_PAGINATION_ITERATIONS = 10_000

    def __init__(
        self,
        api_token: str | None = None,
        base_url: str | None = None,
        api_version: str = DEFAULT_API_VERSION,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        user_agent: str | None = None,
    ):
        """
        Initialize PagerDuty API Client.

        Args:
            api_token: PagerDuty API token
            base_url: Base API URL
            api_version: API version
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            user_agent: Custom user agent string
        """
        cfg = get_config()
        self.api_token = api_token if api_token is not None else cfg.get("api_token")
        self.base_url = base_url or cfg.get("base_url", self.DEFAULT_BASE_URL)
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent or (f"pagerduty-ops-scripts/{distribution_version()}")

        if not isinstance(self.api_token, str) or not self.api_token.strip():
            raise AuthError("API token is required")

        # Set up session
        self.session = requests.Session()
        self.session.headers.update(self._get_default_headers())

        logger.info("PagerDuty API Client initialized")

    def _get_default_headers(self) -> dict[str, str]:
        """Get default headers for API requests."""
        return {
            "Authorization": f"Token token={self.api_token}",
            "Accept": f"application/vnd.pagerduty+json;version={self.api_version}",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }

    def _handle_response(self, response: requests.Response) -> Any:
        """Handle API response and raise appropriate exceptions."""
        try:
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", self.RATE_LIMIT_RETRY_AFTER))
                raise RateLimitError("API rate limit exceeded", retry_after=retry_after)

            # Check for authentication errors
            if response.status_code == 401:
                raise AuthError("Unauthorized - Invalid API token")

            # Check for not found errors
            if response.status_code == 404:
                raise NotFoundError("resource")

            # Check for other errors
            if response.status_code >= 400:
                error_data: Any = {}
                error_msg = response.text or ""
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except json.JSONDecodeError:
                        pass
                raise APIError(
                    error_msg,
                    status_code=response.status_code,
                    response=error_data if error_data else None,
                )

            # Return JSON response if available
            return response.json() if response.text else {}

        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {str(e)}")
            raise APIError("Invalid JSON response from API") from e

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
        json_data: dict | None = None,
        retry_count: int = 0,
    ) -> Any:
        """
        Make API request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Form data
            json_data: JSON data
            retry_count: Current retry count

        Returns:
            API response data

        Raises:
            APIError: For API-related errors
            RateLimitError: For rate limit exceeded errors
            AuthError: For authentication errors
        """
        url = urljoin(f"{self.base_url}/", endpoint)
        start_time = time.time()

        try:
            response = self.session.request(
                method, url, params=params, data=data, json=json_data, timeout=self.timeout
            )

            duration_ms = (time.time() - start_time) * 1000
            log_api_request(
                logger,
                method,
                endpoint,
                response.status_code,
                duration_ms,
                response.ok,
                request_id=getattr(response, "request_id", None),
            )

            return self._handle_response(response)

        except RateLimitError as e:
            if retry_count < self.max_retries:
                logger.warning(f"Rate limit exceeded. Retrying in {e.retry_after} seconds...")
                time.sleep(e.retry_after)
                return self._make_request(
                    method, endpoint, params, data, json_data, retry_count + 1
                )
            raise

        except PagerDutyError:
            raise

        except requests.RequestException as e:
            if retry_count < self.max_retries:
                logger.warning(
                    f"Request failed. Retrying ({retry_count + 1}/{self.max_retries})..."
                )
                time.sleep(2**retry_count)  # Exponential backoff
                return self._make_request(
                    method, endpoint, params, data, json_data, retry_count + 1
                )
            raise APIError(f"API request failed: {str(e)}") from e

    def get(self, endpoint: str, params: dict | None = None) -> Any:
        """Make GET request."""
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: dict | None = None, json_data: dict | None = None) -> Any:
        """Make POST request."""
        return self._make_request("POST", endpoint, data=data, json_data=json_data)

    def put(self, endpoint: str, data: dict | None = None, json_data: dict | None = None) -> Any:
        """Make PUT request."""
        return self._make_request("PUT", endpoint, data=data, json_data=json_data)

    def patch(self, endpoint: str, data: dict | None = None, json_data: dict | None = None) -> Any:
        """Make PATCH request."""
        return self._make_request("PATCH", endpoint, data=data, json_data=json_data)

    def delete(self, endpoint: str, params: dict | None = None) -> Any:
        """Make DELETE request."""
        return self._make_request("DELETE", endpoint, params=params)

    def get_paginated(
        self,
        endpoint: str,
        params: dict | None = None,
        *,
        items_key: str | None = None,
    ) -> list[dict]:
        """
        Walk a PagerDuty REST API v2 **collection** using ``limit`` / ``offset`` and the ``more`` flag.

        This matches the common index pattern for resources such as ``teams``, ``users``, and
        ``services`` (see PagerDuty REST API docs on pagination). Custom or nested paths may
        use a different JSON envelope; pass *items_key* to select the list field explicitly, or
        extend :meth:`_get_items_key` for new first-path segments.

        Args:
            endpoint: API endpoint path (for example ``"teams"``).
            params: Optional query parameters (``limit`` / ``offset`` default to 100 / 0).
            items_key: JSON key holding the page of objects (defaults to :meth:`_get_items_key`).

        Returns:
            Merged list of resource objects from every page.

        Raises:
            APIError: If pagination exceeds :attr:`MAX_PAGINATION_ITERATIONS` (stuck ``more`` loop).
        """
        all_items: list[dict] = []
        current_params = params.copy() if params else {}
        current_params.setdefault("limit", 100)
        current_params.setdefault("offset", 0)

        iterations = 0
        while True:
            iterations += 1
            if iterations > self.MAX_PAGINATION_ITERATIONS:
                raise APIError(
                    f"Pagination stopped after {self.MAX_PAGINATION_ITERATIONS} pages "
                    f"({endpoint!r}); check API response shape or ``more`` flag."
                )

            response = self.get(endpoint, params=current_params)
            if not response:
                break

            resolved_key = items_key if items_key is not None else self._get_items_key(endpoint)
            if not resolved_key:
                logger.warning(
                    "No list envelope key for endpoint %r; stopping after first page.",
                    endpoint,
                )
                break
            if resolved_key in response:
                page = response[resolved_key]
                if isinstance(page, list):
                    all_items.extend(page)
                else:
                    logger.warning(
                        "Expected list at key %r for %r, got %s; stopping pagination.",
                        resolved_key,
                        endpoint,
                        type(page).__name__,
                    )
                    break

            if not response.get("more", False):
                break

            current_params["offset"] += current_params["limit"]

        logger.info(f"Retrieved {len(all_items)} items from {endpoint}")
        return all_items

    def _get_items_key(self, endpoint: str) -> str | None:
        """Get the key for items in paginated responses based on endpoint."""
        endpoint_mapping = {
            "teams": "teams",
            "users": "users",
            "services": "services",
            "schedules": "schedules",
            "escalation_policies": "escalation_policies",
            "webhook_subscriptions": "webhook_subscriptions",
            "incidents": "incidents",
        }

        # Extract endpoint base (e.g., 'teams' from '/teams')
        endpoint_base = endpoint.strip("/").split("/")[0]
        return endpoint_mapping.get(endpoint_base)

    def close(self) -> None:
        """Close the API client session."""
        self.session.close()
        logger.info("PagerDuty API Client session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
