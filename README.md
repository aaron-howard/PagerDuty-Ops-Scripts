# PagerDuty-Ops-Scripts

Production-hardened operational automation for PagerDuty: bulk operations, compliance exports, and configuration management, built on a shared Python package (`pagerduty_ops`) with retries, rate-limit handling, structured logging, real exit codes, and a test suite.

## Quick start

```bash
git clone https://github.com/aaron-howard/PagerDuty-Ops-Scripts
cd PagerDuty-Ops-Scripts
pip install -e .            # or: pip install -e ".[dev]" for development

export PD_API_TOKEN=your_token_here   # never commit this; see docs/secrets.md

pd-list-users -f csv -o users.csv     # console command (installed)
python pd_list_users.py -f csv        # legacy script name — still works
```

Every command supports `--help`, `-f table|csv|json`, `-o FILE`, `-v/--verbose`, `-q/--quiet`, and `--log-file FILE`. Every **mutating** command supports `--dry-run` (preview) and `-y/--yes` (non-interactive), and refuses to write on a non-interactive stdin without `-y`.

## Architecture

All logic lives in the `pagerduty_ops` package; the flat `pd_*.py` files are thin compatibility shims so existing invocations and cron jobs keep working.

```
pagerduty_ops/
  api.py        HTTP client: retries + 429 backoff, typed PDApiError,
                offset/cursor pagination with 10k-cap protection
  config.py     token / team-id / From-email resolution (env-first)
  log.py        structured logging (stderr only — stdout is data-only)
  output.py     table/csv/json rendering
  cli.py        shared argparse plumbing, confirmation guards, exit codes
  bulkops.py    idempotent rename, CSV loading/validation
  commands/     one module per command
tests/
  unit/         pytest + responses (mocked HTTP) — run in CI
  integration/  opt-in, read-only, gated on PD_TEST_TOKEN
docs/           architecture, usage, secrets management, runbook
```

See [docs/architecture.md](docs/architecture.md) for details.

## Commands

| Command | Legacy script | Writes? | Purpose |
|---|---|---|---|
| `pd-list-users` | pd_list_users.py | no | All users → table/CSV/JSON |
| `pd-list-teams` | pd_list_teams.py | no | All teams |
| `pd-list-schedules` | pd_list_schedules.py | no | v2 schedules inventory |
| `pd-list-incidents` | pd_list_incidents.py | no | Incident export with filters |
| `pd-list-status-pages` | pd_list_status_pages.py | no | Status pages / posts |
| `pd-v3-schedules` | pd_v3_schedules_list.py | no | v3 schedules (Early Access) |
| `pd-export-ids` | pd_export_ids.py | no | Teams + schedules/EPs/services/webhooks |
| `pd-audit-export` | pd_audit_export.py | no | /audit/records compliance export |
| `pd-export-log-entries` | pd_export_log_entries.py | no | Log entries export |
| `pd-export-change-events` | pd_export_change_events.py | no | Change events export |
| `pd-scim-user-audit` | pd_scim_user_audit.py | no | SCIM vs IdP CSV diff |
| `pd-standards-report` | pd_standards_report.py | no | Service standards adoption |
| `pd-team-members` | pd_get_teams_user_role.py (deprecated) | no | Team members + roles |
| `pd-eo-export` | pd_event_orchestration_rules.py | no | Event Orchestration → JSON files |
| `pd-eo-apply` | pd_apply_event_orchestration_rules.py | **yes** | Diff/apply EO JSON (diff-first) |
| `pd-patch-role` | pd_patch_role.py | **yes** | Bulk user role changes |
| `pd-rename-resources` | pd_rename_resources.py | **yes** | Idempotent prefix/suffix renames |
| `pd-update-team-roles` | pd_update_team_roles.py | **yes** | Team role updates (interactive or `--set-role`) |
| `pd-remove-team-members` | pd_remove_team_members.py | **yes** | Guided offboarding from schedules/EPs/team |
| `pd-service-urgency` | update_service_notifications.py | **yes** | Set severity-based urgency on all services |
| `pd-bulk-maintenance-window` | pd_bulk_maintenance_window.py | **yes** | Windows from CSV (idempotent) |
| `pd-apply-tags` | pd_apply_tags.py | **yes** | Tag add/remove from CSV |
| `pd-bulk-extensions` | pd_bulk_extensions.py | **yes** | Attach extensions to services (idempotent) |
| `pd-alert-grouping` | pd_alert_grouping.py | **yes** | Alert grouping settings (list/attach/CRUD) |

Per-command usage and examples: [docs/usage.md](docs/usage.md).

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| `PD_API_TOKEN` | all commands | PagerDuty REST API token. See [docs/secrets.md](docs/secrets.md) for scope guidance — read-only commands work with a read-only token. |
| `PD_TEAM_ID` | team commands | Default team ID (`--team-id` overrides). |
| `PD_FROM_EMAIL` | some writes | PagerDuty `From` header (maintenance windows, EO apply). |

A `.env` file in the working directory is honored for local development (and git-ignored). `-t/--token` on the command line is **deprecated** — it leaks into shell history.

## Exit codes (contract for cron/CI)

| Code | Meaning |
|---|---|
| 0 | success (including clean dry-runs and "nothing to do") |
| 1 | one or more operations failed — check logs |
| 2 | usage/config error (bad args, missing token/CSV columns) |
| 3 | authentication/authorization error (token rejected) |
| 130 | interrupted |

Bulk commands abort immediately on auth errors instead of failing every item.

## Scripts vs the PagerDuty MCP server

PagerDuty's hosted MCP server (`.mcp.json` wires it up using `PD_API_TOKEN`) is the right tool for ad-hoc reads from MCP-aware clients ("who's on call?", "open incidents on X"). These commands are the right tool for bulk writes, CSV-driven changes, dry-run rehearsal, scheduled exports, and areas the MCP server doesn't expose (user role writes, maintenance windows, tags, audit/SCIM/standards exports, webhooks, extensions, EO apply-from-git).

## Development

```bash
pip install -e ".[dev]"
pre-commit install                      # ruff + gitleaks on every commit
python -m pytest tests/unit -v          # unit tests (mocked HTTP, no token needed)
ruff check .                            # lint
PD_TEST_TOKEN=... python -m pytest tests/integration -v   # opt-in, read-only
```

CI (`.github/workflows/ci.yml`) runs lint, the unit suite on Python 3.10/3.12, `pip-audit`, and a gitleaks history scan on every push/PR. Releases are tag-driven (`v*.*.*` → `release.yml` builds and publishes artifacts).

One branch per feature; one PR per branch into `main` (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## Security

- Tokens come from the environment or a secret store — never hardcoded, never logged. API error bodies are redacted to PagerDuty's error envelope (no PII in logs).
- All requests have timeouts, retries with backoff, and 429 `Retry-After` handling.
- Mutating commands are guarded: `--dry-run`, interactive confirmation, `-y` required when non-interactive.
- Report vulnerabilities per [SECURITY.md](SECURITY.md).

## Operations

Runbook for scheduled jobs, troubleshooting, and incident response: [docs/runbook.md](docs/runbook.md).

## License

See [LICENSE](LICENSE).
