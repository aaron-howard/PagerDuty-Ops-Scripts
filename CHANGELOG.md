# Changelog

Notable changes to this project are recorded here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-04-11

### Changed

- **Dependabot:** pip and GitHub Actions updates use **groups** so related bumps land in fewer pull requests.
- **Logging:** With `-v`, `requests` loggers are capped at WARNING alongside `urllib3` unless `PAGERDUTY_ALLOW_HTTP_LIBRARY_DEBUG` is set; module docs clarify that API logs omit HTTP bodies.
- **CLI exit codes:** `EXIT_SUCCESS` / `EXIT_ERROR` / `EXIT_USAGE` in `pagerduty.cli_common`; `pagerduty-ops` and token/export validation use them (`1` = operational, `2` = bad invocation / invalid args where applicable).
- **Python:** Supported versions are **3.10+** (aligned with PEP 604 typing used in the repo). CI runs Ruff, mypy, and pytest on **3.10, 3.11, and 3.12**.
- **Version metadata:** `pagerduty.__version__` and the API client `User-Agent` use `importlib.metadata` via `pagerduty._meta.distribution_version()` (falls back to `0.0.0+unknown` when not installed as a distribution).
- **Documentation:** README positions the repo as an ops toolkit (not full REST coverage). `PagerDutyAPIClient.get_paginated` documents the v2 collection pattern (`limit` / `offset`, `more` flag, envelope key via `_get_items_key`).

### Added

- **CLI progress:** `pagerduty.cli_common.progress_wait` shows an ASCII spinner on a TTY during long fetches (`--no-progress` disables it; non-TTY prints a one-line label). Used by **`pd-export-ids`**, bulk rename scripts, **`update-service-notifications`**, **`pd-patch-role`**, **`pd-get-teams-user-role`**, **`pd-update-team-roles`**, and **`pd-remove-team-members`** (including the team removal script’s schedule/policy scan).
- **Pagination:** `PagerDutyAPIClient.get_paginated` accepts optional `items_key`, validates list-shaped pages, stops when no envelope key is mapped, and raises if `more` never clears (safety cap `PagerDutyAPIClient.MAX_PAGINATION_ITERATIONS`).
- **Optional live tests:** `tests/test_integration_api.py` runs when `PAGERDUTY_INTEGRATION_TESTS=1` and `PD_API_TOKEN` are set (skipped in default CI).
- **`--dry-run`** on **`pd-update-team-roles`** and **`pd-remove-team-members`** (read-only preview, no prompts or writes).
- **`--no-progress`** on **`pd-patch-role`**, **`pd-get-teams-user-role`**, **`pd-update-team-roles`**, and **`pd-remove-team-members`** (aligned with other operational CLIs).
- Test that **`requirements.txt`** and **`pyproject.toml`** runtime dependency sets stay aligned; dev dependency **`tomli`** for parsing in tests.
- [CHANGELOG.md](CHANGELOG.md) (this file).
- **CI:** `.github/workflows/gitleaks.yml` and root `.gitleaks.toml` (allowlist for `tests/` and `README.md` where sample strings appear).
- **CI:** `pip-audit` runs in a dedicated job (Python 3.12) so the main matrix is not repeated for audit.

## [1.0.0] - 2026-04-11

Baseline release for changelog tracking (toolkit, CLIs, shared client, prior CI checks).

[Unreleased]: https://github.com/aaron-howard/PagerDuty-Ops-Scripts/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/aaron-howard/PagerDuty-Ops-Scripts/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/aaron-howard/PagerDuty-Ops-Scripts/releases/tag/v1.0.0
