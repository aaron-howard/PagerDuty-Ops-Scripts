# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/) · Versioning: [SemVer](https://semver.org/).

## [1.0.0] - 2026-06-11

### Added
- `pagerduty_ops` package: shared HTTP client with automatic retries and 429
  `Retry-After` backoff, typed `PDApiError`, structured stderr logging
  (`-v/-q/--log-file`), table/csv/json renderers, and a documented exit-code
  contract (0 ok / 1 failures / 2 usage / 3 auth / 130 interrupt).
- Console commands for every script (`pd-list-users`, `pd-patch-role`, …) via
  `pip install -e .`.
- Idempotency: maintenance-window creation skips identical existing windows;
  extension attachment skips services already carrying the same extension.
- Input validation: ISO 8601 timestamps (timezone required), https-only
  endpoint URLs, role enums, CSV column checks — all before any write.
- Test suite: 60+ unit tests (mocked HTTP via `responses`) and opt-in
  read-only integration tests gated on `PD_TEST_TOKEN`.
- Real CI (`ci.yml`): ruff, pytest on 3.10/3.12 with coverage, pip-audit,
  gitleaks full-history scan. Tag-driven `release.yml`.
- Docs: architecture, per-command usage, secrets-management guide (including
  token-scope table), operational runbook.

### Changed
- All `pd_*.py` scripts are now thin shims over the package; arguments and
  behavior preserved.
- All diagnostics moved to stderr — piped CSV/JSON output can no longer be
  corrupted by progress or error text.
- Bulk commands now exit 1 on partial failure (previously always 0) and abort
  immediately on auth errors.
- Team member operations are fully paginated (previously silently truncated
  at the API default of 25 — `pd_remove_team_members` could remove a user
  from a team while leaving them on an unseen schedule).
- API error logging redacted to PagerDuty's error envelope (no response-body
  PII in logs).
- `-t/--token` deprecated (warns); use `PD_API_TOKEN`.

### Removed
- Duplicated API client in `pd_export_ids.py` (and its 4 unused imports).
- Demo CI workflow (replaced by real gates; stub retained as deprecated).
- `prettytable` dependency (standardized on `tabulate`).

### Deprecated
- `pd_common` module (re-exports preserved, removal no earlier than v2.0.0).
- `pd_get_teams_user_role.py` (use `pd-team-members` or the PagerDuty MCP
  server's `list_team_members`).
