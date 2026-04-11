"""
PagerDuty Users Resource

Users-specific operations and functionality.
"""

import logging

from ..errors import PagerDutyError
from .base import BaseResource

logger = logging.getLogger(__name__)


class UsersResource(BaseResource):
    """Users resource class."""

    def __init__(self, api_client=None):
        super().__init__(api_client)
        self.resource_name = "user"
        self.endpoint = "users"

    def get_contact_methods(self, user_id: str) -> list[dict]:
        """
        Get user contact methods.

        Args:
            user_id: User ID

        Returns:
            List of contact methods
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{user_id}/contact_methods")
        except Exception as e:
            logger.error(f"Failed to get contact methods for user {user_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get user contact methods: {str(e)}") from e

    def get_notification_rules(self, user_id: str) -> list[dict]:
        """
        Get user notification rules.

        Args:
            user_id: User ID

        Returns:
            List of notification rules
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{user_id}/notification_rules")
        except Exception as e:
            logger.error(f"Failed to get notification rules for user {user_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get user notification rules: {str(e)}") from e

    def get_oncall_schedules(self, user_id: str) -> list[dict]:
        """
        Get schedules where user is on call.

        Args:
            user_id: User ID

        Returns:
            List of on-call schedules
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{user_id}/on_call_schedules")
        except Exception as e:
            logger.error(f"Failed to get on-call schedules for user {user_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get user on-call schedules: {str(e)}") from e

    def update_contact_method(self, user_id: str, contact_method_id: str, data: dict) -> dict:
        """
        Update user contact method.

        Args:
            user_id: User ID
            contact_method_id: Contact method ID
            data: Contact method data

        Returns:
            Updated contact method data
        """
        try:
            return self.api_client.put(
                f"{self.endpoint}/{user_id}/contact_methods/{contact_method_id}",
                json_data={"contact_method": data},
            )
        except Exception as e:
            logger.error(f"Failed to update contact method for user {user_id}: {str(e)}")
            raise PagerDutyError(f"Failed to update user contact method: {str(e)}") from e
