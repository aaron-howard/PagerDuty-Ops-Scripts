# PagerDuty Ops Scripts

Python **operations toolkit** for PagerDuty: a small `pagerduty` client library, focused resource helpers, and CLI scripts for bulk/admin tasks. It is **not** a full coverage SDK for every PagerDuty REST endpoint—extend the client and `resources` package when you need more surface area.

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
- [Changelog](CHANGELOG.md)
- [License](#license)

## Features

✅ **Targeted API helpers** - REST client plus resource modules for teams, users, services, schedules, escalation policies, and webhooks used by this repo’s scripts  
✅ **Secure token handling** - Prefer env/config; optional CLI token with warnings  
✅ **Error handling & retries** - Custom exceptions, rate-limit and transport retries  
✅ **Structured logging** - JSON logs with credential redaction patterns  
✅ **Configuration** - YAML/JSON files and `PD_*` environment variables  
✅ **CLI ergonomics** - `pagerduty-ops` umbrella command and `pd-*` entry points  
✅ **Pagination** - `limit` / `offset` + `more` for standard v2 collection envelopes (extend mappings as needed)  
✅ **Type hints** - Typed for static checking (Python 3.10+)

## Installation

### Prerequisites

- Python **3.10+** (required for modern typing syntax used in this codebase)
- Dependencies are declared in `pyproject.toml` / `requirements.txt` (`requests`, `urllib3`, `python-dotenv`, `PyYAML`, `prettytable`, `tabulate`)

### Install from source

```bash
git clone <your-fork-or-clone-url>
cd PagerDuty-Ops-Scripts

# Editable install (includes the pagerduty package and CLI entry points)
pip install -e .
```

After installation, use **`pagerduty-ops`** for a single entry point with subcommands (for example `pagerduty-ops export-ids --help`), or call the dedicated scripts directly (`pd-export-ids`, `pd-update-service-names`, and others on your PATH).

### Install dependencies only (no package install)

Runtime dependencies are listed in `pyproject.toml` under `[project.dependencies]`. `requirements.txt` mirrors them for convenience:

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

### 4. Command-line scripts

Installed entry points (`pd-export-ids`, `pd-update-service-names`, etc.) share a common pattern:

- **`--config PATH`** — load settings from that YAML/JSON file (overrides the default filename search).
- **`-v` / `--verbose`** and **`-q` / `--quiet`** — adjust log verbosity.
- **`-t` / `--token`** — optional API token. Prefer **`PD_API_TOKEN`** or an **`api_token`** entry in a config file; tokens passed on the command line can appear in shell history.

Resolution order for the token: `-t` (emits a stderr warning), then `PD_API_TOKEN`, then `api_token` from the merged config, then a secure prompt where the script allows it.

With **`-v` / `--verbose`**, the `urllib3` and **`requests`** loggers stay at **WARNING** so low-level HTTP debug output (which can include headers) is not enabled. To allow full library debugging, set environment variable **`PAGERDUTY_ALLOW_HTTP_LIBRARY_DEBUG=1`**.

The `PagerDutyAPIClient` records **method, endpoint path, status, and timing** via `log_api_request`—not request or response bodies.

JSON log lines from `pagerduty.logging` apply **redaction** for common credential patterns (for example `Token token=…`, `Bearer …`, and `api_token=…`).

Importing the `pagerduty` package does **not** read config files from disk until something needs them (for example creating `PagerDutyAPIClient()` without an explicit token, or calling `get_config()` / `config.get()`).

**`pd-export-ids`** accepts **`--without RESOURCE [RESOURCE …]`** to skip fetching schedules, escalation policies, services, or webhooks when you only need part of the export (fewer API calls). Skipping **services** limits webhook-to-team association in the output. Use **`--concurrency N`** (with `N>1`) to fetch multiple resource lists in parallel (each worker uses its own HTTP session). **`--no-progress`** hides fetch status lines and the interactive spinner.

**`update-service-notifications`** supports **`--dry-run`** (list services that would change) and **`--no-progress`**. **`pd-patch-role`** supports **`--dry-run`** to list observers that would be promoted, and **`--no-progress`** to hide the user-list spinner.

**`pd-update-team-roles`** and **`pd-remove-team-members`** support **`--dry-run`** to fetch and display membership/assignment data without interactive prompts or mutating calls. Those two, **`pd-get-teams-user-role`**, and **`pd-patch-role`** accept **`--no-progress`** to hide fetch/spinner output during list loads.

Bulk renames (`pd-update-*-names`) accept **`--no-progress`** to suppress fetch status lines and the spinner.

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

Install dev dependencies (pytest, ruff, mypy, pre-commit, tomli for tests, typing stubs):

```bash
pip install -e ".[dev]"
```

Run checks locally:

```bash
ruff check .
ruff format --check .
mypy
pytest
```

Optional **live API** regression checks (not run in CI): set **`PAGERDUTY_INTEGRATION_TESTS=1`** and **`PD_API_TOKEN`**, then run **`pytest -m integration`**. Default **`pytest`** skips them.

```bash
python -m pip install pip-audit
pip-audit -r requirements.txt
```

Optional: install Git hooks so Ruff and mypy run on every commit:

```bash
pre-commit install
pre-commit run --all-files   # once, to warm caches
```

CI runs **Gitleaks** (secret scan), **pip-audit** on `requirements.txt`, **Ruff** (`check` + `format --check`), **mypy**, and **pytest** on Python **3.10, 3.11, and 3.12** for pushes and pull requests to `main` / `master` (see `.github/workflows/ci.yml` and `.github/workflows/gitleaks.yml`).

Release-facing changes are summarized in [CHANGELOG.md](CHANGELOG.md). The package version in `pyproject.toml` is the source of truth; `pagerduty.__version__` and the HTTP `User-Agent` read it via `importlib.metadata` when the distribution is installed.

### CLI exit codes

Scripts and `pagerduty-ops` follow a common convention (and `argparse` still exits **2** on parse errors):

| Code | Meaning |
|------|--------|
| **0** | Success |
| **1** | Operational error (for example missing API token, API failure, I/O error) |
| **2** | Usage / invalid arguments (for example unknown `pagerduty-ops` subcommand, invalid flag values after parse) |

Constants: `pagerduty.cli_common.EXIT_SUCCESS`, `EXIT_ERROR`, `EXIT_USAGE`.

### requirements.txt

Runtime dependency names and constraints are defined in **`pyproject.toml`** (`[project.dependencies]`). `requirements.txt` is kept in sync for `pip install -r` workflows; CI runs a test that fails if the two lists diverge.

**Dependabot** opens weekly PRs for pip and monthly PRs for GitHub Actions, with **grouped updates** (fewer PRs per ecosystem; see `.github/dependabot.yml`).

To generate API documentation locally, use a tool such as `pdoc` against the `pagerduty` package.

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Add or update tests when you introduce test coverage
4. Submit a pull request

### Code Standards

- Follow PEP 8 style guide
- Use type hints (`mypy` must pass)
- Write comprehensive docstrings
- Include unit tests
- Maintain backward compatibility
- Prefer `pre-commit install` so hooks match CI

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

© 2023 PagerDuty Scripts Team