"""
PagerDuty API Client

Core API client for interacting with PagerDuty REST APIs.
"""

import json
import logging
import time
from typing import Any, Optional
from urllib.parse import urljoin

import requests

from .config import config
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

    def __init__(
        self,
        api_token: Optional[str] = None,
        base_url: Optional[str] = None,
        api_version: str = DEFAULT_API_VERSION,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = MAX_RETRIES,
        user_agent: Optional[str] = None,
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
        self.api_token = api_token if api_token is not None else config.get("api_token")
        self.base_url = base_url or config.get("base_url", self.DEFAULT_BASE_URL)
        self.api_version = api_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent or f"pagerduty-python-sdk/{config.get('version', '1.0.0')}"

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
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        json_data: Optional[dict] = None,
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

    def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Make GET request."""
        return self._make_request("GET", endpoint, params=params)

    def post(
        self, endpoint: str, data: Optional[dict] = None, json_data: Optional[dict] = None
    ) -> Any:
        """Make POST request."""
        return self._make_request("POST", endpoint, data=data, json_data=json_data)

    def put(
        self, endpoint: str, data: Optional[dict] = None, json_data: Optional[dict] = None
    ) -> Any:
        """Make PUT request."""
        return self._make_request("PUT", endpoint, data=data, json_data=json_data)

    def patch(
        self, endpoint: str, data: Optional[dict] = None, json_data: Optional[dict] = None
    ) -> Any:
        """Make PATCH request."""
        return self._make_request("PATCH", endpoint, data=data, json_data=json_data)

    def delete(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Make DELETE request."""
        return self._make_request("DELETE", endpoint, params=params)

    def get_paginated(self, endpoint: str, params: Optional[dict] = None) -> list[dict]:
        """
        Get all items from a paginated endpoint.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            List of all items from all pages
        """
        all_items = []
        current_params = params.copy() if params else {}
        current_params.setdefault("limit", 100)
        current_params.setdefault("offset", 0)

        while True:
            response = self.get(endpoint, params=current_params)
            if not response:
                break

            items_key = self._get_items_key(endpoint)
            if items_key and items_key in response:
                all_items.extend(response[items_key])

            if not response.get("more", False):
                break

            current_params["offset"] += current_params["limit"]

        logger.info(f"Retrieved {len(all_items)} items from {endpoint}")
        return all_items

    def _get_items_key(self, endpoint: str) -> Optional[str]:
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
