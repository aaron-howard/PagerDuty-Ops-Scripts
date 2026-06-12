# PagerDuty Ops Scripts — repository guidance

## Purpose

Python CLI utilities only (no web server, database, or Docker). Scripts call the PagerDuty REST API and expect `PD_API_TOKEN` in the environment unless documented otherwise. Never commit tokens, `.env` files with real secrets, or customer data.

## Layout

- Shared CLI and exit-code policy: `pagerduty_ops/cli.py` (`standard_parser`, `init`, `confirm`, `run`, `finish_bulk`).
- Command implementations: `pagerduty_ops/commands/*.py`.
- Legacy root shims `pd_*.py` delegate to `pagerduty_ops.cli.run(main)` so behavior matches installed console scripts when those use the same wrapper.
- HTTP and errors: `pagerduty_ops/api.py` (`PDApiError`, retries, pagination).

## Exit codes (contract)

Documented in `pagerduty_ops/cli.py` and `docs/architecture.md`:

- `0` — success (including dry-runs and nothing-to-do).
- `1` — operational failures (e.g. partial bulk failures, non-auth API errors surfaced via `run()`).
- `2` — usage / configuration (bad args, missing token, invalid CSV, **non-interactive stdin refusing a write without `-y`/`--dry-run`**).
- `3` — authentication / authorization (token rejected or insufficient scope).
- `130` — interrupted (Ctrl+C).

Schedulers and CI should alert on any non-zero exit.

## Reviews and changes

- Prefer minimal, focused diffs; match naming and patterns in surrounding code.
- When user-visible behavior changes, update `docs/architecture.md` and/or `docs/usage.md` and add or adjust unit tests under `tests/unit` (use `responses` for HTTP; avoid live API calls in default tests).
