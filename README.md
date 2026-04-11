# PagerDuty Python SDK

A comprehensive Python package for interacting with PagerDuty APIs, designed to improve security, error handling, logging, and code organization across all PagerDuty operations scripts.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Basic Usage](#basic-usage)
  - [API Client](#api-client)
  - [Resources](#resources)
  - [Logging](#logging)
  - [Error Handling](#error-handling)
- [Examples](#examples)
- [Migration Guide](#migration-guide)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

✅ **Comprehensive API Coverage** - Full support for PagerDuty REST API
✅ **Secure Token Handling** - Safe API token management and validation
✅ **Robust Error Handling** - Custom exceptions and retry logic
✅ **Structured Logging** - JSON logging with sensitive data masking
✅ **Flexible Configuration** - YAML/JSON files and environment variables
✅ **Modular Architecture** - Clean separation of concerns
✅ **Pagination Support** - Automatic handling of paginated responses
✅ **Type Hints** - Full type annotation support
✅ **Resource-Oriented** - Intuitive resource-based interface

## Installation

### Prerequisites

- Python 3.9+
- Dependencies are declared in `pyproject.toml` / `requirements.txt` (`requests`, `python-dotenv`, `PyYAML`, `prettytable`, `tabulate`)

### Install from source

```bash
git clone <your-fork-or-clone-url>
cd PagerDuty-Ops-Scripts

# Editable install (includes the pagerduty package and CLI entry points)
pip install -e .
```

After installation, CLI commands such as `pd-export-ids` and `pd-update-service-names` are available on your PATH.

### Install dependencies only (no package install)

```bash
pip install -r requirements.txt
```

## Configuration

The SDK supports multiple configuration methods:

### 1. Environment Variables

```bash
export PD_API_TOKEN="your_api_token_here"
export PD_BASE_URL="https://api.pagerduty.com"
export PD_API_VERSION="v2"
```

### 2. Configuration File

Create a `.pagerduty.yaml` file:

```yaml
api_token: "your_api_token_here"
base_url: "https://api.pagerduty.com"
api_version: "v2"
timeout: 30
max_retries: 3
log_level: "INFO"
log_file: "pagerduty.log"
```

### 3. Programmatic Configuration

```python
from pagerduty.config import Config

config = Config()
config.set("api_token", "your_api_token")
config.set("log_level", "DEBUG")
```

## Usage

### Basic Usage

```python
from pagerduty import PagerDutyAPIClient
from pagerduty.resources import TeamsResource

# Initialize API client (reads PD_API_TOKEN from the environment or config files)
client = PagerDutyAPIClient()

# Get all teams
teams = TeamsResource(client).list()
print(f"Found {len(teams)} teams")

# Get a specific team (API returns an envelope)
team_body = TeamsResource(client).get("TEAM_ID")
team = team_body.get("team", team_body)
print(f"Team: {team['name']}")
```

### API Client

```python
from pagerduty import PagerDutyAPIClient

# Initialize client
client = PagerDutyAPIClient()

# Make API requests
try:
    # GET request
    teams = client.get("teams")

    # POST request
    new_team = client.post("teams", json_data={
        "team": {
            "name": "My Team",
            "description": "Team description"
        }
    })

    # PUT request
    updated_team = client.put(f"teams/{team_id}", json_data={
        "team": {
            "name": "Updated Team Name"
        }
    })

    # DELETE request
    client.delete(f"teams/{team_id}")

except Exception as e:
    print(f"API Error: {str(e)}")
```

### Resources

The SDK provides resource-specific classes for common PagerDuty entities:

```python
from pagerduty.resources import (
    TeamsResource, UsersResource, ServicesResource,
    SchedulesResource, EscalationPoliciesResource, WebhooksResource
)

# Initialize resources
teams = TeamsResource()
users = UsersResource()
services = ServicesResource()

# Teams operations
all_teams = teams.list()
team_members = teams.get_members("TEAM_ID")
teams.add_member("TEAM_ID", "USER_ID", "manager")

# Users operations
all_users = users.list()
user_contact_methods = users.get_contact_methods("USER_ID")

# Services operations
all_services = services.list()
service_integrations = services.get_integrations("SERVICE_ID")
```

### Logging

The SDK includes comprehensive logging:

```python
from pagerduty.logging import setup_logging

# Basic logging setup
logger = setup_logging(
    name="my_app",
    level="INFO",
    log_file="my_app.log"
)

# Log messages
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")

# API request logging is automatic
```

### Error Handling

The SDK provides custom exceptions:

```python
from pagerduty import PagerDutyAPIClient
from pagerduty.errors import APIError, AuthError, RateLimitError, NotFoundError

client = PagerDutyAPIClient()

try:
    # This will raise an exception if token is invalid
    teams = client.get("teams")

except AuthError as e:
    print(f"Authentication failed: {str(e)}")
    # Handle authentication error

except RateLimitError as e:
    print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
    # Implement retry logic

except NotFoundError as e:
    print(f"Resource not found: {str(e)}")
    # Handle missing resource

except APIError as e:
    print(f"API Error {e.status_code}: {str(e)}")
    # Handle general API errors

except Exception as e:
    print(f"Unexpected error: {str(e)}")
    # Handle other exceptions
```

## Examples

### Export PagerDuty IDs (Improved Version)

```python
from pagerduty import PagerDutyAPIClient
from pagerduty.resources import (
    TeamsResource, SchedulesResource,
    EscalationPoliciesResource, ServicesResource, WebhooksResource
)
from pagerduty.utils import format_output
import argparse

def main():
    parser = argparse.ArgumentParser(description='Export PagerDuty IDs and names')
    parser.add_argument('-f', '--format', choices=['table', 'csv', 'json'], default='table')
    args = parser.parse_args()

    # Initialize resources
    client = PagerDutyAPIClient()
    teams = TeamsResource(client)
    schedules = SchedulesResource(client)
    policies = EscalationPoliciesResource(client)
    services = ServicesResource(client)
    webhooks = WebhooksResource(client)

    # Get all data
    all_teams = teams.list()
    all_schedules = schedules.list()
    all_policies = policies.list()
    all_services = services.list()
    all_webhooks = webhooks.list()

    # Process and format data
    result = []
    for team in all_teams:
        team_data = {
            "team_id": team["id"],
            "team_name": team["name"],
            "schedule_id": "",
            "schedule_name": "",
            "policy_id": "",
            "policy_name": "",
            "service_id": "",
            "service_name": "",
            "webhook_id": "",
            "webhook_name": ""
        }
        result.append(team_data)

    # Format output
    output = format_output(result, format_type=args.format)
    print(output)

if __name__ == "__main__":
    main()
```

### Update Service Names

```python
from pagerduty import PagerDutyAPIClient
from pagerduty.resources import ServicesResource
import argparse

def main():
    parser = argparse.ArgumentParser(description='Update service names')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()

    client = PagerDutyAPIClient()
    services = ServicesResource(client)

    # Get all services
    all_services = services.list()

    for service in all_services:
        current_name = service['name']
        if not current_name.endswith(' SVC'):
            new_name = f"{current_name} SVC"

            if args.dry_run:
                print(f"Would rename '{current_name}' to '{new_name}'")
            else:
                try:
                    updated = services.update(service['id'], {"name": new_name})
                    print(f"Updated '{current_name}' to '{new_name}'")
                except Exception as e:
                    print(f"Failed to update {current_name}: {str(e)}")

if __name__ == "__main__":
    main()
```

## Migration Guide

### From Original Scripts to SDK

**Before (Original Script):**
```python
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.environ.get('PD_API_TOKEN')

headers = {
    "Authorization": f"Token token={API_TOKEN}",
    "Accept": "application/vnd.pagerduty+json;version=2"
}

response = requests.get("https://api.pagerduty.com/teams", headers=headers)
teams = response.json().get("teams", [])
```

**After (Using SDK):**
```python
from pagerduty import PagerDutyAPIClient
from pagerduty.resources import TeamsResource

# Initialize client (automatically loads from environment)
client = PagerDutyAPIClient()

# Get teams using resource
teams = TeamsResource(client).list()

# Or use client directly
teams = client.get("teams")
```

### Key Improvements

1. **Security**: Automatic token validation and secure handling
2. **Error Handling**: Built-in retry logic and custom exceptions
3. **Logging**: Automatic API request logging
4. **Configuration**: Flexible configuration management
5. **Code Organization**: Modular, resource-oriented architecture

## Development

Install dev dependencies (pytest, ruff):

```bash
pip install -e ".[dev]"
```

Run checks locally:

```bash
ruff check pagerduty tests
pytest
```

CI runs the same `ruff` and `pytest` steps on pushes and pull requests to `main` / `master` (see `.github/workflows/ci.yml`).

To generate API documentation locally, use a tool such as `pdoc` against the `pagerduty` package.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Add or update tests when you introduce test coverage
4. Submit a pull request

### Code Standards

- Follow PEP 8 style guide
- Use type hints
- Write comprehensive docstrings
- Include unit tests
- Maintain backward compatibility

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

© 2023 PagerDuty Scripts Team