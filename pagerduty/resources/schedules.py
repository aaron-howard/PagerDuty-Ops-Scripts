"""
PagerDuty Schedules Resource

Schedules-specific operations and functionality.
"""

from typing import Dict, List, Optional
from .base import BaseResource
from ..errors import PagerDutyError
import logging

logger = logging.getLogger(__name__)

class SchedulesResource(BaseResource):
    """Schedules resource class."""

    def __init__(self, api_client=None):
        super().__init__(api_client)
        self.resource_name = "schedule"
        self.endpoint = "schedules"

    def get_users(self, schedule_id: str) -> List[Dict]:
        """
        Get schedule users.

        Args:
            schedule_id: Schedule ID

        Returns:
            List of users on schedule
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{schedule_id}/users")
        except Exception as e:
            logger.error(f"Failed to get users for schedule {schedule_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get schedule users: {str(e)}") from e

    def get_oncalls(self, schedule_id: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Get schedule on-calls.

        Args:
            schedule_id: Schedule ID
            params: Query parameters

        Returns:
            List of on-call entries
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{schedule_id}/oncalls", params=params)
        except Exception as e:
            logger.error(f"Failed to get on-calls for schedule {schedule_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get schedule on-calls: {str(e)}") from e

    def update_layer(self, schedule_id: str, layer_id: str, layer_data: Dict) -> Dict:
        """
        Update schedule layer.

        Args:
            schedule_id: Schedule ID
            layer_id: Layer ID
            layer_data: Layer data

        Returns:
            Updated schedule data
        """
        try:
            # Get current schedule
            schedule = self.get(schedule_id)

            # Update the specific layer
            layers = schedule.get('schedule_layers', [])
            for i, layer in enumerate(layers):
                if str(layer.get('id')) == str(layer_id):
                    layers[i] = layer_data
                    break

            # Update the schedule
            update_data = {"schedule": {"schedule_layers": layers}}
            return self.api_client.put(f"{self.endpoint}/{schedule_id}", json_data=update_data)
        except Exception as e:
            logger.error(f"Failed to update layer for schedule {schedule_id}: {str(e)}")
            raise PagerDutyError(f"Failed to update schedule layer: {str(e)}") from e