# AGENTS.md

## Cursor Cloud specific instructions

This is a **Python CLI scripts** repo (no web server, no database, no Docker).
All scripts talk to the PagerDuty REST API and require a valid `PD_API_TOKEN`
environment variable. Some team-specific scripts also need `PD_TEAM_ID`.

### Quick reference

| Task | Command |
|---|---|
| Install deps | `pip install -r requirements.txt` |
| Syntax-check all scripts | `python -m py_compile <script>.py` (CI does this for every `.py` file) |
| Run demo (no API token needed) | `python demo_sample_output.py` |
| Run any real script | `export PD_API_TOKEN=<token>` then `python <script>.py [--help]` |
| Dry-run a write script | Add `--dry-run` flag (most write scripts support it) |

### Gotchas

- **No automated test suite exists.** The CI workflow (`.github/workflows/demo.yml`) only runs `py_compile` on each script plus `demo_sample_output.py`. There are no pytest/unittest tests to run.
- **All real scripts require network access** to `api.pagerduty.com`. Without `PD_API_TOKEN` set, scripts will either exit with an error or prompt interactively for a token (via `getpass`).
- **Interactive prompts**: Several scripts (`pd_update_team_roles.py`, `pd_remove_team_members.py`, and [pd_rename_resources.py](pd_rename_resources.py) without `--yes`) prompt for confirmation on stdin. Use `--yes` or `--dry-run` flags when running non-interactively.
- **Event Orchestration apply**: [pd_apply_event_orchestration_rules.py](pd_apply_event_orchestration_rules.py) only writes with **`--apply -y`** after you have reviewed a diff-only run; there is no interactive apply.
- **Shared helpers** live in `pd_common.py` — use `get_pd_api_token`, `make_api_request`, `paginate`, etc. for consistency.
- **Dependencies install to user site-packages** (`~/.local/lib/...`) by default on Cloud VMs. This works fine; no virtualenv is needed.
