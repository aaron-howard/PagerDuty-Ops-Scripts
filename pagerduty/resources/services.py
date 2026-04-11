"""
PagerDuty Services Resource

Services-specific operations and functionality.
"""

import logging
from typing import Optional

from ..errors import PagerDutyError
from .base import BaseResource

logger = logging.getLogger(__name__)


class ServicesResource(BaseResource):
    """Services resource class."""

    def __init__(self, api_client=None):
        super().__init__(api_client)
        self.resource_name = "service"
        self.endpoint = "services"

    def get_integrations(self, service_id: str) -> list[dict]:
        """
        Get service integrations.

        Args:
            service_id: Service ID

        Returns:
            List of integrations
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{service_id}/integrations")
        except Exception as e:
            logger.error(f"Failed to get integrations for service {service_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get service integrations: {str(e)}") from e

    def create_integration(self, service_id: str, integration_data: dict) -> dict:
        """
        Create service integration.

        Args:
            service_id: Service ID
            integration_data: Integration data

        Returns:
            Created integration data
        """
        try:
            return self.api_client.post(
                f"{self.endpoint}/{service_id}/integrations",
                json_data={"integration": integration_data},
            )
        except Exception as e:
            logger.error(f"Failed to create integration for service {service_id}: {str(e)}")
            raise PagerDutyError(f"Failed to create service integration: {str(e)}") from e

    def get_incidents(self, service_id: str, params: Optional[dict] = None) -> list[dict]:
        """
        Get service incidents.

        Args:
            service_id: Service ID
            params: Query parameters

        Returns:
            List of incidents
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{service_id}/incidents", params=params)
        except Exception as e:
            logger.error(f"Failed to get incidents for service {service_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get service incidents: {str(e)}") from e

    def update_incident_urgency_rule(self, service_id: str, rule_data: dict) -> dict:
        """
        Update service incident urgency rule.

        Args:
            service_id: Service ID
            rule_data: Urgency rule data

        Returns:
            Updated service data
        """
        try:
            data = {"service": {"incident_urgency_rule": rule_data}}
            return self.api_client.put(f"{self.endpoint}/{service_id}", json_data=data)
        except Exception as e:
            logger.error(f"Failed to update urgency rule for service {service_id}: {str(e)}")
            raise PagerDutyError(f"Failed to update service urgency rule: {str(e)}") from e
