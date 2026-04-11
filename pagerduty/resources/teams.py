"""
PagerDuty Teams Resource

Teams-specific operations and functionality.
"""

from typing import Dict, List
from .base import BaseResource
from ..errors import PagerDutyError
import logging

logger = logging.getLogger(__name__)

class TeamsResource(BaseResource):
    """Teams resource class."""

    def __init__(self, api_client=None):
        super().__init__(api_client)
        self.resource_name = "team"
        self.endpoint = "teams"

    def get_members(self, team_id: str) -> List[Dict]:
        """
        Get team members.

        Args:
            team_id: Team ID

        Returns:
            List of team members
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{team_id}/members")
        except Exception as e:
            logger.error(f"Failed to get team members for {team_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get team members: {str(e)}") from e

    def add_member(self, team_id: str, user_id: str, role: str = "member") -> Dict:
        """
        Add member to team.

        Args:
            team_id: Team ID
            user_id: User ID
            role: Member role (manager, responder, observer)

        Returns:
            Updated team membership data
        """
        try:
            data = {
                "member": {
                    "user_id": user_id,
                    "role": role
                }
            }
            return self.api_client.post(f"{self.endpoint}/{team_id}/members", json_data=data)
        except Exception as e:
            logger.error(f"Failed to add member to team {team_id}: {str(e)}")
            raise PagerDutyError(f"Failed to add team member: {str(e)}") from e

    def remove_member(self, team_id: str, user_id: str) -> bool:
        """
        Remove member from team.

        Args:
            team_id: Team ID
            user_id: User ID

        Returns:
            True if removal was successful
        """
        try:
            self.api_client.delete(f"{self.endpoint}/{team_id}/members/{user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove member from team {team_id}: {str(e)}")
            raise PagerDutyError(f"Failed to remove team member: {str(e)}") from e

    def update_member_role(self, team_id: str, user_id: str, role: str) -> Dict:
        """
        Update member role in team.

        Args:
            team_id: Team ID
            user_id: User ID
            role: New role (manager, responder, observer)

        Returns:
            Updated team membership data
        """
        try:
            data = {"role": role}
            return self.api_client.put(f"{self.endpoint}/{team_id}/members/{user_id}", json_data=data)
        except Exception as e:
            logger.error(f"Failed to update member role in team {team_id}: {str(e)}")
            raise PagerDutyError(f"Failed to update team member role: {str(e)}") from e

    def get_schedules(self, team_id: str) -> List[Dict]:
        """
        Get team schedules.

        Args:
            team_id: Team ID

        Returns:
            List of team schedules
        """
        try:
            return self.api_client.get("schedules", params={"team_ids[]": team_id})
        except Exception as e:
            logger.error(f"Failed to get schedules for team {team_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get team schedules: {str(e)}") from e

    def get_escalation_policies(self, team_id: str) -> List[Dict]:
        """
        Get team escalation policies.

        Args:
            team_id: Team ID

        Returns:
            List of team escalation policies
        """
        try:
            return self.api_client.get("escalation_policies", params={"team_ids[]": team_id})
        except Exception as e:
            logger.error(f"Failed to get escalation policies for team {team_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get team escalation policies: {str(e)}") from e