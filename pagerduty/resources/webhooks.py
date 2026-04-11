"""
PagerDuty Webhooks Resource

Webhooks-specific operations and functionality.
"""

from typing import Dict, List
from .base import BaseResource
from ..errors import PagerDutyError
import logging

logger = logging.getLogger(__name__)

class WebhooksResource(BaseResource):
    """Webhooks resource class."""

    def __init__(self, api_client=None):
        super().__init__(api_client)
        self.resource_name = "webhook_subscription"
        self.endpoint = "webhook_subscriptions"

    def get_by_service(self, service_id: str) -> List[Dict]:
        """
        Get webhooks for a specific service.

        Args:
            service_id: Service ID

        Returns:
            List of webhook subscriptions
        """
        try:
            all_webhooks = self.list()
            return [wh for wh in all_webhooks if self._is_for_service(wh, service_id)]
        except Exception as e:
            logger.error(f"Failed to get webhooks for service {service_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get service webhooks: {str(e)}") from e

    def _is_for_service(self, webhook: Dict, service_id: str) -> bool:
        """
        Check if webhook is for a specific service.

        Args:
            webhook: Webhook data
            service_id: Service ID

        Returns:
            True if webhook is for the service
        """
        # Check filter with service_reference type
        if webhook.get("filter", {}).get("type") == "service_reference":
            return webhook.get("filter", {}).get("id") == service_id

        # Check direct service reference
        if webhook.get("service", {}).get("id") == service_id:
            return True

        # Check legacy structure
        delivery_method = webhook.get("delivery_method", {})
        if "connection" in delivery_method and "service" in delivery_method["connection"]:
            return delivery_method["connection"]["service"]["id"] == service_id

        return False

    def create_for_service(self, service_id: str, webhook_data: Dict) -> Dict:
        """
        Create webhook for a specific service.

        Args:
            service_id: Service ID
            webhook_data: Webhook data

        Returns:
            Created webhook data
        """
        try:
            # Ensure the webhook is configured for the service
            if "filter" not in webhook_data:
                webhook_data["filter"] = {
                    "type": "service_reference",
                    "id": service_id
                }

            return self.create(webhook_data)
        except Exception as e:
            logger.error(f"Failed to create webhook for service {service_id}: {str(e)}")
            raise PagerDutyError(f"Failed to create service webhook: {str(e)}") from e