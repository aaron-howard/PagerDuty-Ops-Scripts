"""
PagerDuty Resource Base Class

Base class for all PagerDuty resource classes.
"""

from typing import Dict, Any, List, Optional, Union
from ..api_client import PagerDutyAPIClient
from ..errors import PagerDutyError, NotFoundError
import logging

logger = logging.getLogger(__name__)

class BaseResource:
    """Base class for PagerDuty resources."""

    def __init__(self, api_client: Optional[PagerDutyAPIClient] = None):
        """
        Initialize resource.

        Args:
            api_client: PagerDuty API client instance
        """
        self.api_client = api_client or PagerDutyAPIClient()
        self.resource_name = self.__class__.__name__.replace('Resource', '').lower()
        self.endpoint = f"{self.resource_name}s"

    def get(self, resource_id: str, params: Optional[Dict] = None) -> Dict:
        """
        Get a single resource by ID.

        Args:
            resource_id: Resource ID
            params: Additional query parameters

        Returns:
            Resource data

        Raises:
            NotFoundError: If resource is not found
            PagerDutyError: For other API errors
        """
        try:
            return self.api_client.get(f"{self.endpoint}/{resource_id}", params=params)
        except NotFoundError:
            logger.warning(f"{self.resource_name.capitalize()} not found: {resource_id}")
            raise
        except Exception as e:
            logger.error(f"Failed to get {self.resource_name}: {str(e)}")
            raise PagerDutyError(f"Failed to get {self.resource_name}: {str(e)}") from e

    def list(self, params: Optional[Dict] = None) -> List[Dict]:
        """
        List all resources.

        Args:
            params: Query parameters

        Returns:
            List of resources
        """
        try:
            return self.api_client.get_paginated(self.endpoint, params=params)
        except Exception as e:
            logger.error(f"Failed to list {self.resource_name}s: {str(e)}")
            raise PagerDutyError(f"Failed to list {self.resource_name}s: {str(e)}") from e

    def create(self, data: Dict) -> Dict:
        """
        Create a new resource.

        Args:
            data: Resource data

        Returns:
            Created resource data
        """
        try:
            return self.api_client.post(self.endpoint, json_data={self.resource_name: data})
        except Exception as e:
            logger.error(f"Failed to create {self.resource_name}: {str(e)}")
            raise PagerDutyError(f"Failed to create {self.resource_name}: {str(e)}") from e

    def update(self, resource_id: str, data: Dict) -> Dict:
        """
        Update a resource.

        Args:
            resource_id: Resource ID
            data: Resource data to update

        Returns:
            Updated resource data
        """
        try:
            return self.api_client.put(f"{self.endpoint}/{resource_id}", json_data={self.resource_name: data})
        except Exception as e:
            logger.error(f"Failed to update {self.resource_name} {resource_id}: {str(e)}")
            raise PagerDutyError(f"Failed to update {self.resource_name}: {str(e)}") from e

    def delete(self, resource_id: str) -> bool:
        """
        Delete a resource.

        Args:
            resource_id: Resource ID

        Returns:
            True if deletion was successful
        """
        try:
            self.api_client.delete(f"{self.endpoint}/{resource_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {self.resource_name} {resource_id}: {str(e)}")
            raise PagerDutyError(f"Failed to delete {self.resource_name}: {str(e)}") from e

    def get_by_name(self, name: str) -> Optional[Dict]:
        """
        Get resource by name.

        Args:
            name: Resource name

        Returns:
            Resource data if found, None otherwise
        """
        try:
            resources = self.list(params={'query': name})
            for resource in resources:
                if resource.get('name') == name:
                    return resource
            return None
        except Exception as e:
            logger.error(f"Failed to get {self.resource_name} by name: {str(e)}")
            return None

    def search(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Search resources by query.

        Args:
            query: Search query
            params: Additional parameters

        Returns:
            List of matching resources
        """
        search_params = params.copy() if params else {}
        search_params['query'] = query
        return self.list(params=search_params)