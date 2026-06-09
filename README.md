# PagerDuty-Ops-Scripts

Daily Operations Scripts for managing the PagerDuty application.

## Prerequisites

- Python 3.7+
- Install dependencies from `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```
- Optional development tools:
  ```bash
  pip install -r requirements-dev.txt
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

## Contributing (git workflow)

Use **one branch per feature** and merge each into **`main`** through its **own pull request**. Do not combine unrelated script or doc changes in a single branch/PR. Agents and contributors should follow the same rules; see [AGENTS.md](AGENTS.md) for the full Cursor Cloud notes including this workflow.

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
- `-t`, `--token`: PagerDuty API token. If omitted, uses the `PD_API_TOKEN` environment variable. Use `--prompt` for secure interactive entry when unset (local dev only).
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

### `pd_bulk_maintenance_window.py`

Bulk-creates maintenance windows from a CSV (`service_id, start_time, end_time, description`).
Times must be ISO 8601 with timezone. Requires a `--from-email` (a valid PagerDuty user email)
because the API needs a `From` header for window creation.

**Usage:**
```bash
python pd_bulk_maintenance_window.py windows.csv --from-email you@example.com [--dry-run] [--yes]
```

### `pd_apply_tags.py`

Bulk add/remove PagerDuty tags from a CSV (`entity_type, entity_id, tag_label, action`).
Supports `users`, `teams`, `services`, and `escalation_policies`. Creates new tags as needed.
Groups operations per entity and submits one atomic `change_tags` call per entity.

**Usage:**
```bash
python pd_apply_tags.py tags.csv [--dry-run] [--yes]
```

### `pd_audit_export.py`

Exports `/audit/records` to CSV or JSON with cursor pagination. Useful for compliance
reports and change-history audits. Supports filtering by date range, actor, action prefix,
and root resource type.

**Usage:**
```bash
python pd_audit_export.py --since 2026-04-01T00:00:00Z --until 2026-05-01T00:00:00Z \
    --action update --root-resource-type services -f csv -o audit.csv
```

### `pd_scim_user_audit.py`

Diffs PagerDuty SCIM users (`/scim/v2/Users`) against an expected-users CSV
(`email, displayName, active`) exported from your IdP. Reports orphans, missing users,
and field drift. Read-only; does not provision or deprovision.

**Usage:**
```bash
python pd_scim_user_audit.py expected_users.csv -o scim_audit.txt
```

### `pd_standards_report.py`

Exports per-resource adoption of PagerDuty Service Standards. Useful for compliance
dashboards. Use `--failing-only` to focus on services that aren't meeting standards.

**Usage:**
```bash
python pd_standards_report.py --resource-type technical_services --failing-only -f csv -o standards.csv
```

### `pd_event_orchestration_rules.py`

Exports each Event Orchestration's metadata, router config, and global catch-all rules
to one JSON file per orchestration in the output directory. Designed so the directory
can be committed to git and rule changes show up as reviewable diffs.

**Usage:**
```bash
python pd_event_orchestration_rules.py -o event_orchestrations/
```

### `pd_bulk_extensions.py`

Bulk-attaches an extension (Slack, Generic Webhook, etc) to many services. Targets are
chosen via `--service-filter` substring or `--services-csv`. The schema is resolved by
substring match against `/extension_schemas`.

**Usage:**
```bash
python pd_bulk_extensions.py \
    --schema "Generic Webhook" \
    --name "Datadog hook" \
    --endpoint-url https://example.com/hook \
    --service-filter prod [--dry-run] [--yes]
```

### `pd_v3_schedules_list.py`

Read-only inventory of PagerDuty Schedules v3 (Early Access). v3 is the
"flexible schedules" API (rotations + events + custom shifts + overrides as
separate sub-resources, instead of v2's embedded `schedule_layers`). v2 and v3
schedules coexist in the same account.

**PagerDuty marks v3 as Early Access** with the warning *"Do not use this
endpoint in production, as it may change"*. This script is intended for
inventory/visibility only. The existing v2 schedule scripts in this repo
remain the right tool for production schedule operations until v3 is GA.

The script automatically sends the required `X-EARLY-ACCESS:
flexible-schedules-early-access` header.

**Usage:**
```bash
python pd_v3_schedules_list.py [-f table|csv|json] [-o FILE]
python pd_v3_schedules_list.py --get PSCHEDID [--include-users]
```

### `pd_alert_grouping.py`

Manages PagerDuty Alert Grouping Settings. `--list` prints existing settings and the
services they cover; `--attach NAME --services-csv FILE` adds services to the named
setting (CSV column: `service_id`).

**Usage:**
```bash
python pd_alert_grouping.py --list
python pd_alert_grouping.py --attach "Intelligent grouping" --services-csv services.csv [--dry-run] [--yes]
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