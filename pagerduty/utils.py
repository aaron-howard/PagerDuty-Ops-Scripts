"""
PagerDuty Utilities

Utility functions for PagerDuty operations.
"""

import json
import csv
import io
from typing import Dict, Any, List, Optional, Union
from prettytable import PrettyTable
import logging
from .errors import ValidationError

logger = logging.getLogger(__name__)

def validate_pagerduty_id(pd_id: str, id_type: str = "ID") -> bool:
    """
    Validate PagerDuty ID format.

    Args:
        pd_id: PagerDuty ID to validate
        id_type: Type of ID for error messages

    Returns:
        True if valid, False otherwise

    Raises:
        ValidationError: If ID is invalid
    """
    if not pd_id or not isinstance(pd_id, str):
        raise ValidationError(f"{id_type} must be a non-empty string", field=id_type)

    if len(pd_id) < 20 or len(pd_id) > 36:
        raise ValidationError(f"{id_type} must be between 20-36 characters", field=id_type)

    return True

def format_output(
    data: List[Dict],
    format_type: str = 'table',
    field_names: Optional[List[str]] = None
) -> Union[str, PrettyTable]:
    """
    Format data for output in various formats.

    Args:
        data: List of dictionaries containing data
        format_type: Output format ('table', 'csv', 'json')
        field_names: List of field names for headers

    Returns:
        Formatted output as string or PrettyTable

    Raises:
        ValueError: If format_type is invalid
    """
    if not data:
        return "No data to format"

    if not field_names:
        field_names = list(data[0].keys()) if data else []

    if format_type == 'table':
        table = PrettyTable()
        table.field_names = field_names

        for item in data:
            row = [item.get(field, "") for field in field_names]
            table.add_row(row)

        return table

    elif format_type == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=field_names)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    elif format_type == 'json':
        return json.dumps(data, indent=2, ensure_ascii=False)

    else:
        raise ValueError(f"Invalid format type: {format_type}")

def chunk_list(items: List[Any], chunk_size: int = 100) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def get_nested_value(data: Dict, key_path: str, default: Any = None) -> Any:
    """
    Get nested value from dictionary using dot notation.

    Args:
        data: Dictionary to search
        key_path: Dot-separated path to value
        default: Default value if key not found

    Returns:
        Value at specified path or default
    """
    keys = key_path.split('.')
    current = data

    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default

    return current if current is not None else default

def set_nested_value(data: Dict, key_path: str, value: Any) -> None:
    """
    Set nested value in dictionary using dot notation.

    Args:
        data: Dictionary to modify
        key_path: Dot-separated path to value
        value: Value to set
    """
    keys = key_path.split('.')
    current = data

    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]

    current[keys[-1]] = value

def mask_sensitive_data(data: Any, sensitive_keys: List[str] = None) -> Any:
    """
    Mask sensitive data in dictionaries or strings.

    Args:
        data: Data to process
        sensitive_keys: List of keys to mask

    Returns:
        Data with sensitive values masked
    """
    if sensitive_keys is None:
        sensitive_keys = ['token', 'api_key', 'password', 'secret', 'access_token']

    if isinstance(data, dict):
        return {k: mask_sensitive_data(v, sensitive_keys) if k.lower() not in sensitive_keys else "***MASKED***" for k, v in data.items()}
    elif isinstance(data, list):
        return [mask_sensitive_data(item, sensitive_keys) for item in data]
    elif isinstance(data, str):
        for key in sensitive_keys:
            if key in data.lower():
                return data.replace(key, f"{key}_MASKED")
        return data
    else:
        return data

def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid email format, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone: str) -> bool:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        True if valid phone format, False otherwise
    """
    import re
    # Basic international phone number validation
    pattern = r'^\+?[0-9\s\-\(\)]{10,}$'
    return bool(re.match(pattern, phone))