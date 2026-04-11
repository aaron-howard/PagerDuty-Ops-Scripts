"""
PagerDuty Escalation Policies Resource

Escalation policies-specific operations and functionality.
"""

import logging

from ..errors import PagerDutyError
from .base import BaseResource

logger = logging.getLogger(__name__)


class EscalationPoliciesResource(BaseResource):
    """Escalation policies resource class."""

    def __init__(self, api_client=None):
        super().__init__(api_client)
        self.resource_name = "escalation_policy"
        self.endpoint = "escalation_policies"

    def get_services(self, policy_id: str) -> list[dict]:
        """
        Get services using this escalation policy.

        Args:
            policy_id: Escalation policy ID

        Returns:
            List of services
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{policy_id}/services")
        except Exception as e:
            logger.error(f"Failed to get services for escalation policy {policy_id}: {str(e)}")
            raise PagerDutyError(f"Failed to get escalation policy services: {str(e)}") from e

    def update_rule(self, policy_id: str, rule_id: str, rule_data: dict) -> dict:
        """
        Update escalation policy rule.

        Args:
            policy_id: Escalation policy ID
            rule_id: Rule ID
            rule_data: Rule data

        Returns:
            Updated escalation policy data
        """
        try:
            # Get current policy
            policy = self.get(policy_id)

            # Update the specific rule
            rules = policy.get("escalation_rules", [])
            for i, rule in enumerate(rules):
                if str(rule.get("id")) == str(rule_id):
                    rules[i] = rule_data
                    break

            # Update the policy
            update_data = {"escalation_policy": {"escalation_rules": rules}}
            return self.api_client.put(f"{self.endpoint}/{policy_id}", json_data=update_data)
        except Exception as e:
            logger.error(f"Failed to update rule for escalation policy {policy_id}: {str(e)}")
            raise PagerDutyError(f"Failed to update escalation policy rule: {str(e)}") from e
