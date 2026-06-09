# AGENTS.md

## Cursor Cloud specific instructions

This is a **Python CLI scripts** repo (no web server, no database, no Docker).
All scripts talk to the PagerDuty REST API and require a valid `PD_API_TOKEN`
environment variable. Some team-specific scripts also need `PD_TEAM_ID`.

### Quick reference

| Task | Command |
|---|---|
| Install deps | `pip install -r requirements.txt` |
| Syntax-check all scripts | `python -m py_compile *.py` (CI compiles every `*.py` in the repo root) |
| Run demo (no API token needed) | `python demo_sample_output.py` |
| Run any real script | `export PD_API_TOKEN=<token>` then `python <script>.py [--help]` |
| Dry-run a write script | Add `--dry-run` flag (most write scripts support it) |

### Branching & pull requests

- **One branch per feature** — implement each change set on its own branch (for example `cursor/<topic>` or `feature/<topic>`), not mixed with unrelated edits.
- **Merge through `main` via PR** — open one pull request per branch into `main` so review, CI, and rollback stay scoped to that feature.
- **Start from current `main`** — for a new feature, branch off up-to-date `main` (or rebase after earlier PRs land) instead of stacking unrelated work on an open feature branch.

### Gotchas

- **No automated test suite exists.** The CI workflow (`.github/workflows/demo.yml`) only runs `py_compile` on each script plus `demo_sample_output.py`. There are no pytest/unittest tests to run.
- **All real scripts require network access** to `api.pagerduty.com`. Without `PD_API_TOKEN` set, scripts will either exit with an error or prompt interactively for a token (via `getpass`).
- **Interactive prompts**: Several scripts (`pd_update_team_roles.py`, `pd_remove_team_members.py`, and the suffix-renaming scripts without `--yes`) prompt for confirmation on stdin. Use `--yes` or `--dry-run` flags when running non-interactively.
- **Shared helpers** live in `pd_common.py` — use `get_pd_api_token`, `make_api_request`, `paginate`, etc. for consistency.
- **Platform / config scripts**: `pd_event_orchestration_rules.py` + `pd_apply_event_orchestration_rules.py` (export/apply EO router+global), `pd_list_schedules.py` (v2 schedules), `pd_list_status_pages.py` (status pages and posts), and `pd_v3_schedules_list.py` (v3 Early Access schedules).
- **Dependencies install to user site-packages** (`~/.local/lib/...`) by default on Cloud VMs. This works fine; no virtualenv is needed.
