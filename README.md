# PagerDuty-Ops-Scripts

Daily Operations Scripts for managing the PagerDuty application.

## Prerequisites

- Python 3.7+
- Install dependencies from `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```
- A PagerDuty API token

## Setup

1. Clone the repository.
2. Set your PagerDuty API token as an environment variable:
   ```bash
   export PD_API_TOKEN=your_token_here
   ```
3. For team-specific scripts, set your team ID:
   ```bash
   export PD_TEAM_ID=your_team_id_here
   ```

## Environment Variables

- `PD_API_TOKEN`: Your PagerDuty API token (required for all scripts)
- `PD_TEAM_ID`: Your PagerDuty team ID (required for team-specific scripts)

## When to use scripts vs the PagerDuty MCP server

PagerDuty publishes a hosted Model Context Protocol server at
`https://mcp.pagerduty.com/mcp` ([source](https://github.com/PagerDuty/pagerduty-mcp-server)).
This repo includes an [.mcp.json](.mcp.json) that wires it into MCP-aware clients
(Claude Code, VS Code, etc.) using your existing `PD_API_TOKEN`.

The MCP server and these scripts have different jobs:

| Use case | Use this |
|---|---|
| Ad-hoc questions ("who's on call for team X right now?", "show open incidents on service Y") | **MCP server** |
| One-off reads of teams, services, schedules, oncalls, incidents | **MCP server** |
| Bulk writes that need a CSV input, `--dry-run`, or interactive confirmation | **Scripts in this repo** |
| Operations the MCP server **cannot** perform (see below) | **Scripts in this repo** |

The PagerDuty MCP server intentionally does not expose write access to several
high-impact areas. The scripts here cover the gaps:

- **User role updates** — MCP exposes no user write tools.
  Use [pd_patch_role.py](pd_patch_role.py).
- **Escalation policy writes** — MCP escalation policy writes are disabled.
  Use [pd_update_escalation_policy_names.py](pd_update_escalation_policy_names.py).
- **Maintenance windows, tags, audit export, SCIM, standards, licenses,
  webhooks, extensions, analytics** — none are in the MCP server today.

When adding new functionality, prefer the MCP server for read-only / ad-hoc use
cases. Reach for a script when you need bulk writes, dry-run rehearsal, CSV
input, or coverage of one of the gap areas above.

## Scripts

### `pd_export_ids.py`

Exports PagerDuty teams, schedules, escalation policies, services, and webhook subscriptions.

**Usage:**
```bash
python pd_export_ids.py [-t API_TOKEN] [-o OUTPUT_FILE] [-f FORMAT]
```
- `-t`, `--token`: PagerDuty API token. If omitted, uses the `PD_API_TOKEN` environment variable or prompts for secure input.
- `-o`, `--output`: Output file (default: print to console).
- `-f`, `--format`: Output format: `table`, `csv`, or `json` (default: `table`).

### `pd_patch_role.py`

Bulk-update PagerDuty user roles. Selects every user currently in `--from-role` and patches them to `--to-role`.

**Usage:**
```bash
export PD_API_TOKEN=your_token_here
python pd_patch_role.py --from-role user --to-role observer [--dry-run] [--yes]
```

### `pd_update_service_names.py`

Updates PagerDuty service names by appending "SVC" to the end of each service name if it doesn't already have it.

**Usage:**
```powershell
$env:PD_API_TOKEN="your_token_here"
python pd_update_service_names.py [--list] [--filter TEXT] [--dry-run]
```

### `pd_update_schedule_names.py`

Updates PagerDuty schedule names by appending "SCH" to the end of each schedule name if it doesn't already have it.

**Usage:**
```powershell
$env:PD_API_TOKEN="your_token_here"
python pd_update_schedule_names.py [--list] [--filter TEXT] [--dry-run]
```
- `-t`, `--token`: PagerDuty API token. If omitted, uses the `PD_API_TOKEN` environment variable.
- `-l`, `--list`: List schedules without making changes.
- `-f`, `--filter`: Only process schedules containing this text in their name.
- `--dry-run`: Show what would be done without making changes to the schedules.

### `pd_update_escalation_policy_names.py`

Updates PagerDuty escalation policy names by appending "EP" to the end of each policy name if it doesn't already have it.

**Usage:**
```powershell
$env:PD_API_TOKEN="your_token_here"
python pd_update_escalation_policy_names.py [--list] [--filter TEXT] [--dry-run]
```

### `pd_update_team_roles.py`

Lists team members and allows interactive role updates.

**Usage:**
```bash
export PD_API_TOKEN=your_token_here
export PD_TEAM_ID=your_team_id_here
python pd_update_team_roles.py
```

### `pd_get_teams_user_role.py` _(deprecated)_

Lists team members and their roles in a table format.

**Deprecated**: prefer the PagerDuty MCP server's `list_team_members` tool. The
script remains for CLI/CSV use cases and prints a deprecation notice on stderr.

**Usage:**
```bash
export PD_API_TOKEN=your_token_here
export PD_TEAM_ID=your_team_id_here
python pd_get_teams_user_role.py
```

### `pd_remove_team_members.py`

Interactive script to remove team members from schedules, escalation policies, and the team.

**Usage:**
```bash
export PD_API_TOKEN=your_token_here
export PD_TEAM_ID=your_team_id_here
python pd_remove_team_members.py [--dry-run]
```

### `update_service_notifications.py`

Updates all services to use severity-based incident urgency rules.

**Usage:**
```bash
export PD_API_TOKEN=your_token_here
python update_service_notifications.py [--dry-run] [--yes]
```

## Security Features

- **Secure Token Input**: API tokens are requested using `getpass.getpass()` to prevent them from appearing in terminal history
- **Environment Variables**: Sensitive data like API tokens and team IDs are stored in environment variables
- **Request Timeouts**: All HTTP requests include 30-second timeouts to prevent hanging
- **Input Validation**: Scripts validate required inputs before proceeding

## Demo & Examples

### Live Demo
This repository includes a GitHub Actions workflow that demonstrates the scripts' capabilities. You can trigger it manually or view the latest run to see:
- Script syntax validation
- Available functionality overview
- Usage examples and best practices

### Example Outputs

#### Export IDs Script
```bash
python pd_export_ids.py --format table
```
Outputs a comprehensive table showing teams and their associated schedules, escalation policies, services, and webhooks.

#### Service Name Updates
```bash
python pd_update_service_names.py --dry-run --list
```
Shows what services would be updated without making changes.

#### Team Member Management
```bash
python pd_get_teams_user_role.py
```
Displays team members in a formatted table with their roles.

### Security Best Practices
- Never commit API tokens to version control
- Use environment variables for sensitive data
- Always test with `--dry-run` before making changes
- Review changes in a staging environment first

## Contributing

1. Fork this repository
2. Create a feature branch
3. Submit a pull request

## License

See [LICENSE](LICENSE)