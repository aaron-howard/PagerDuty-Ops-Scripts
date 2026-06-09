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
| Member-level reads for a known team (`list_team_members`, roles on that team) | **MCP server** (or team-specific scripts below) |
| Flat export of **all users** or **all teams** (CSV/JSON for pipelines, audits, spreadsheets) | **Scripts**: [pd_list_users.py](pd_list_users.py), [pd_list_teams.py](pd_list_teams.py) |
| **Incident** exports on a schedule, wide filters, or files for ticketing / SIEM (not ad-hoc triage in the IDE) | **Script**: [pd_list_incidents.py](pd_list_incidents.py) |
| **Event Orchestration** router/global **apply from git-exported JSON** (diff-first, then `--apply`) | **Script**: [pd_apply_event_orchestration_rules.py](pd_apply_event_orchestration_rules.py) |
| **Alert grouping** create/update/delete from JSON, or bulk attach from CSV | **Script**: [pd_alert_grouping.py](pd_alert_grouping.py) |
| Bulk writes that need a CSV input, `--dry-run`, or interactive confirmation | **Scripts in this repo** |
| Operations the MCP server **cannot** perform (see below) | **Scripts in this repo** |

The PagerDuty MCP server intentionally does not expose write access to several
high-impact areas. The scripts here cover the gaps:

- **User role updates** — MCP exposes no user write tools.
  Use [pd_patch_role.py](pd_patch_role.py).
- **Escalation policy writes** — MCP escalation policy writes are disabled.
  Use [pd_rename_resources.py](pd_rename_resources.py) with `--resource escalation_policies`.
- **Maintenance windows, tags, audit export, SCIM, standards, licenses,
  webhooks, extensions, analytics** — none are in the MCP server today.

When adding new functionality, prefer the MCP server for read-only / ad-hoc use
cases. Reach for a script when you need bulk writes, dry-run rehearsal, CSV
input, scheduled exports (including incidents), or coverage of one of the gap areas above.

## Scripts

### Migration: bulk rename scripts

The former Dallas-specific scripts `pd_update_service_names.py`, `pd_update_schedule_names.py`,
and `pd_update_escalation_policy_names.py` were **removed** in favor of a single generic tool.

Use [pd_rename_resources.py](pd_rename_resources.py) with a **literal** `--prefix` or `--suffix`
(no automatic spacing). Examples matching the old behavior (note the leading space in the suffix):

```bash
python pd_rename_resources.py --resource services --suffix " SVC" --dry-run
python pd_rename_resources.py --resource schedules --suffix " SCH" --dry-run
python pd_rename_resources.py --resource escalation_policies --suffix " EP" --dry-run
```

Add `-y`/`--yes` for non-interactive runs after you have reviewed `--dry-run` output.

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

### `pd_rename_resources.py`

Bulk-add a configurable **prefix** or **suffix** to names of `services`, `schedules`, or
`escalation_policies`. Skips resources that already start or end with the given affix string
(case-sensitive by default; use `--ignore-case` for a case-insensitive check only).

**Usage:**
```bash
export PD_API_TOKEN=your_token_here
python pd_rename_resources.py --resource services --suffix "-prod" [--list] [-f FILTER] [--dry-run] [-y]
python pd_rename_resources.py --resource schedules --prefix "[SRE] " --dry-run
```

If you run from a TTY and omit `--prefix` / `--suffix`, the script prompts for prefix vs suffix
and the affix string. `--list` does not require an affix. Standard token flags: `-t`, `--prompt`.

### `pd_list_users.py`

Read-only flat list of all users (`id`, `name`, `email`, `role`, `job_title`) with optional
substring filter on name or email. Outputs `table`, `csv`, or `json`.

**Usage:**
```bash
python pd_list_users.py [-f table|csv|json] [-o FILE] [--filter TEXT]
```

### `pd_list_teams.py`

Read-only flat list of all teams (`id`, `name`, `description`) with optional substring filter
on name or description.

**Usage:**
```bash
python pd_list_teams.py [-f table|csv|json] [-o FILE] [--filter TEXT]
```

### `pd_list_incidents.py`

Read-only export of incidents with filters for time range (`--since` / `--until`), `status`
(`triggered`, `acknowledged`, `resolved`), `service-id`, `team-id`, and assignee `user-id`.
Outputs `table`, `csv`, or `json`. Assignee column format: `Summary (id)` entries joined by ` | `.

**Usage:**
```bash
python pd_list_incidents.py --since 2026-01-01T00:00:00Z --status triggered --status acknowledged -f csv -o incidents.csv
python pd_list_incidents.py --team-id PXXXXXX -f json -o team_incidents.json
```

Without `--since`/`--until`, the API returns a potentially large set; the script prints a reminder on stderr.

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

Pair with [pd_apply_event_orchestration_rules.py](pd_apply_event_orchestration_rules.py) to
push reviewed JSON back to the API: **diff-only first**, then **`--apply -y`** (apply always requires `-y`).

**Usage:**
```bash
python pd_event_orchestration_rules.py -o event_orchestrations/
```

### `pd_apply_event_orchestration_rules.py`

Applies router and `global` **orchestration_path** objects from a directory of JSON files
in the same format as [pd_event_orchestration_rules.py](pd_event_orchestration_rules.py).

**Step 1 — diff only (default, or pass `--dry-run` explicitly):** fetches live state, prints
unified diffs on stderr, **no writes**. Review this output (or capture it in CI on every PR).

**Step 2 — apply:** `--apply` **must** be used with **`-y`/`--yes`** after review. PUTs only
paths that differ. `--apply` cannot be combined with `--dry-run`. There is no interactive
apply path.

**Usage:**
```bash
python pd_apply_event_orchestration_rules.py -d event_orchestrations/
python pd_apply_event_orchestration_rules.py -d event_orchestrations/ --dry-run
python pd_apply_event_orchestration_rules.py -d event_orchestrations/ --apply -y
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
inventory/visibility only. For production v2 schedule **renames**, use
[pd_rename_resources.py](pd_rename_resources.py) with `--resource schedules` until v3 is GA.

The script automatically sends the required `X-EARLY-ACCESS:
flexible-schedules-early-access` header.

**Usage:**
```bash
python pd_v3_schedules_list.py [-f table|csv|json] [-o FILE]
python pd_v3_schedules_list.py --get PSCHEDID [--include-users]
```

### `pd_alert_grouping.py`

Manages PagerDuty Alert Grouping Settings (same REST resources the MCP can create/update/delete
interactively; this script is for **JSON files**, **CSV bulk attach**, and **CI**):

- **`--list`**: print all settings and the services each covers.
- **`--attach NAME --services-csv FILE`**: add `service_id` rows to the uniquely matched setting.
- **`--get-json ID`**: dump one setting as JSON (`-o FILE` optional).
- **`--create-json FILE`**: POST a new setting; JSON must include `name`, `type`, `config`, and `services`
  (service ids as strings or objects). Wrap in `{"alert_grouping_setting": {...}}` or pass the inner object only.
- **`--update-json FILE`**: PUT an existing setting; JSON must include `id`.
- **`--delete ID`**: DELETE a setting.

Use **`--dry-run`** to preview creates/updates/deletes; **`-y`/`--yes`** skips confirmation prompts for writes.

**Usage:**
```bash
python pd_alert_grouping.py --list
python pd_alert_grouping.py --attach "Intelligent grouping" --services-csv services.csv [--dry-run] [--yes]
python pd_alert_grouping.py --get-json PZC4OM1 -o setting.json
python pd_alert_grouping.py --create-json new_setting.json --dry-run
python pd_alert_grouping.py --update-json setting.json -y
python pd_alert_grouping.py --delete PZC4OM1 --dry-run
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

#### Bulk resource rename (preview)
```bash
python pd_rename_resources.py --resource services --suffix " SVC" --dry-run
```
Shows planned renames without writing. Use `--list` alone to print current names without an affix.

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