# Production-Readiness Audit — PagerDuty-Ops-Scripts

**Audited:** 2026-06-11, commit `cf8a640` (main)
**Auditor scope:** all 26 tracked Python files, CI config, docs, git history
**Note:** the repo is pure Python (not PowerShell). Flat layout: 24 CLI scripts + `pd_common.py` shared helpers + `demo_sample_output.py`. No `tests/` directory is tracked in git (local `tests/__pycache__` artifacts are stale leftovers from an untracked refactor).

---

## 1. Executive Summary

This is a well-documented, thoughtfully scoped collection of PagerDuty ops scripts with several production-grade habits already in place: a shared helper module, consistent `--dry-run` / `-y` guards on every mutating script, token resolution that prefers env vars, request timeouts everywhere, an excellent README, and clean git history (no leaked secrets found in code or history). For interactive, human-supervised use it is in decent shape.

It is **not yet safe for unattended production use** (cron, CI/CD, scheduled exports). The failure-handling layer is the core problem: errors are printed and swallowed, exit codes lie, there is no rate-limit/retry logic, three legacy scripts silently truncate at 25 team members, and there are zero automated tests.

### Top 5 issues blocking production readiness

1. **No retry / 429 rate-limit handling anywhere** (`pd_common.py:make_api_request`). PagerDuty actively rate-limits (HTTP 429 + `Retry-After`). Every bulk script (e.g. `pd_patch_role.py` over hundreds of users) will hit 429s mid-run; each is counted as a generic "failed" with no retry, leaving the account half-migrated. — **Critical**
2. **Exit codes lie; errors are swallowed.** `make_api_request` returns `None` on any error and bulk scripts print `Summary: ... N failed.` then **exit 0**. A scheduled job that failed 90% of its writes reports success to cron/CI/monitoring. — **Critical**
3. **Missing pagination on team-member reads** in `pd_get_teams_user_role.py`, `pd_update_team_roles.py`, and `pd_remove_team_members.py` (also schedules/EP lists in the latter). `GET /teams/{id}/members` defaults to 25 items. For a team with 30 members, `pd_remove_team_members.py` can remove a user from the team **while they remain on an unseen schedule/escalation policy** — the exact failure mode the script exists to prevent. — **Critical**
4. **Zero automated tests; CI is theater.** `.github/workflows/demo.yml` runs `py_compile` plus a wall of `echo` statements (which still advertise three scripts that were deleted). `requirements-dev.txt` lists `ruff` and `pre-commit` but no config for either is committed, and ruff currently reports 4 errors. — **High**
5. **Error output corrupts data output.** `pd_common.py:83–97` prints API errors to **stdout**, while export scripts write CSV/JSON to stdout by design. A transient mid-pagination error injects `Error: API request failed - ...` into the middle of a piped CSV, and on HTTP errors the **full response body** is echoed (potential PII in logs). — **High**

---

## 2. Production Readiness Score

| Category | Score | Rationale |
|---|---:|---|
| Architecture | 62/100 | Good shared module + consistent CLI conventions; but 3 legacy scripts bypass `pd_common`, `pd_export_ids.py` duplicates the entire API client, no package structure |
| Security | 58/100 | No leaked secrets, env-var-first auth, timeouts, good SECURITY.md; but `-t/--token` CLI arg leaks to shell history/process list, response bodies echoed on error, no secret scanning or dependency pinning |
| Reliability | 38/100 | Dry-run/confirm everywhere is great; but no retries, swallowed errors, misleading exit codes, truncated pagination in 3 scripts, no logging, non-idempotent maintenance-window creation |
| Testing | 5/100 | No tests at all; only `py_compile` in CI |
| Performance | 60/100 | Generator-based pagination is right; but full-collection fetches where filtered queries exist, serial writes, no offset-cap (10k) handling |
| DevOps / CI/CD | 35/100 | Dependabot configured (good); CI has no lint/test/scan gates, no versioning/releases, dev tools declared but unconfigured |
| Documentation | 80/100 | Outstanding README & AGENTS.md; gaps: no permission-scope-per-script table, stale DEMO/workflow references to deleted scripts, no CHANGELOG |
| **Overall** | **48/100** | Solid interactive tooling; not yet trustworthy unattended |

---

## 3. Detailed Findings

### A. Architecture & Code Quality

**A1. Three legacy scripts bypass `pd_common.py` entirely — Severity: High**
Files: `pd_get_teams_user_role.py`, `pd_update_team_roles.py`, `pd_remove_team_members.py`
They hand-roll headers, raw `requests` calls, and uncaught `raise_for_status()` (an API error gives the operator a raw traceback). They also run logic at module import time (the first two), making them untestable and un-importable.
Fix: route every call through `pd_common` helpers; wrap all logic in `main()`. A full rewrite of `pd_update_team_roles.py` is provided in `audit/proposed/pd_update_team_roles_v2.py`.

**A2. `pd_export_ids.py` duplicates the entire API client — Severity: Medium**
Files: `pd_export_ids.py:33–72` reimplements `make_api_request` and pagination already in `pd_common.py`; also 4 unused imports (`os`, `sys`, `prettytable`, `datetime` — ruff F401, lines 10/11/13/16) and a bare `except Exception` at line 237.
Fix: delete local copies, import from `pd_common`; run `ruff check --fix`.

**A3. Mixed stdout/stderr conventions — Severity: Medium**
Newer scripts correctly send progress to stderr (`pd_list_incidents.py:74`), older ones to stdout (`pd_list_users.py:15`, `pd_common.py:fetch_all:172`). Piping `pd_list_users.py -f csv` to a file captures `Fetching users... Found N.` inside the CSV.
Fix: all diagnostics → stderr, only data → stdout. One-line changes in `pd_common.fetch_all` and the older list scripts.

**A4. No package structure or `pyproject.toml` — Severity: Medium**
Flat root of 26 scripts; no entry points, no pinned tool config, scripts only run from the repo root (`from pd_common import ...`).
Recommended target structure (incremental, keep thin script shims for compatibility):

```
pagerduty_ops/
  __init__.py
  api.py          # client: session, retries, errors
  config.py       # token/env resolution
  pagination.py
  output.py       # table/csv/json renderers (currently triplicated in ~8 scripts)
  cli/            # one module per command
tests/
pyproject.toml    # [project.scripts] pd-list-users = ... etc.
```

**A5. Output rendering triplicated across ~8 scripts — Severity: Low**
`output_table/output_csv/output_json` are copy-pasted in `pd_list_users.py`, `pd_list_teams.py`, `pd_list_incidents.py`, and near-duplicated in the render functions of 5 more. Extract to `pd_common` (or `output.py` above).

**A6. Inconsistent table libraries — Severity: Low**
`prettytable` in some scripts, `tabulate` in others, both in `requirements.txt`. Pick one.

### B. Security

**B1. No leaked secrets — PASS.** Scanned working tree and full git history; nothing found. `.gitignore` covers `.env`; `.mcp.json` uses `${PD_API_TOKEN}` interpolation rather than a literal token. Good.

**B2. `-t/--token` CLI argument — Severity: High**
Files: `pd_common.py:17–28` (used by every script). A token passed via `-t` lands in shell history, `ps` output, and CI logs. The help text says "prefer PD_API_TOKEN" but the footgun remains.
Fix: deprecate `-t` (warn loudly when used), or accept only a file path / env var name. At minimum redact it from any echoed argv.

**B3. Full API response bodies echoed on error — Severity: Medium**
File: `pd_common.py:88–89` (`print(f"Response: {e.response.text}")`), similar in `pd_bulk_maintenance_window.py:79–80`, `pd_update_team_roles.py:59`, `pd_remove_team_members.py:245`. PagerDuty error bodies can include user emails/names; these end up in cron logs and CI output.
Fix: log only `status_code` + PagerDuty `error.code`/`error.message` fields; full body only at DEBUG level.

**B4. Unpinned dependencies, no lockfile, no audit — Severity: Medium**
Files: `requirements.txt` (all `>=`), CI installs latest at run time. Combined with Dependabot this is backwards: builds aren't reproducible, and there's no `pip-audit`/CodeQL gate.
Fix: pin with `pip-compile` (or pin `==` + let Dependabot bump), add `pip-audit` and secret-scanning (gitleaks) jobs to CI (provided in `audit/proposed/ci.yml`).

**B5. No input validation on URLs / role strings — Severity: Low**
`pd_bulk_extensions.py --endpoint-url` accepts any string (typo → webhook firing at the wrong host); `pd_update_team_roles.py:51` accepts any role text and PATCHes it; `pd_patch_role.py` at least warns. Validate `https://` URLs and role enums before writing.

**B6. SCIM/legacy scripts print tracebacks on auth failure — Severity: Low**
`pd_scim_user_audit.py:49`, `pd_get_teams_user_role.py:51` — uncaught `raise_for_status()`. Catch and exit 1 with a clean message.

### C. Operational Reliability

**C1. No retry / backoff / 429 handling — Severity: Critical**
File: `pd_common.py:65–98`, plus every raw-`requests` call site. See Top-5 #1. Fix provided: `audit/proposed/pd_common_improved.py` adds a `requests.Session` with `urllib3.Retry` honoring `Retry-After` on 429/5xx, idempotent-method-aware.

**C2. Swallowed errors + always-zero exit codes — Severity: Critical**
Files: `pd_common.py:make_api_request` (returns `None` for *every* failure class — 401, 403, 404, 429, network), `pd_patch_role.py:104–105`, `update_service_notifications.py:78–79`, `pd_apply_tags.py:162–163`, `pd_rename_resources.py` (via `apply_name_affix_update`), `pd_bulk_maintenance_window.py:113–114` — all print a failure summary and exit 0. Only `pd_apply_event_orchestration_rules.py:194–195` gets this right (`sys.exit(1)` on failures).
Fix: raise a typed `PDApiError` (or return a result object), and `sys.exit(1)` whenever `failed > 0`. A 401 should abort the whole run immediately, not "fail" N times in a loop.

**C3. Truncated pagination in team scripts — Severity: Critical**
Files: `pd_get_teams_user_role.py:50`, `pd_update_team_roles.py:29`, `pd_remove_team_members.py:138–150` (members, schedules, escalation policies — all single unpaginated GETs, API default limit 25). Worst case documented in Top-5 #3.
Fix: `members = list(paginate(f"teams/{team_id}/members", token, items_key="members"))` — the helper already exists.

**C4. No logging framework — Severity: High**
Everything is `print()`. No timestamps, no levels, no `--verbose`/`--quiet`, nothing greppable for monitoring. For scheduled jobs you cannot reconstruct what changed when.
Fix: `logging` with a stderr handler (+ optional `--log-file` / JSON format); audit-relevant writes (renames, role changes, removals) logged at INFO with before/after values.

**C5. Non-idempotent maintenance windows — Severity: Medium**
File: `pd_bulk_maintenance_window.py`. Re-running the same CSV (e.g. after a partial failure) creates duplicate windows. Fix: query existing windows per service/time range and skip exact matches, or support an idempotency tag in the description.

**C6. No monitoring hooks — Severity: Low**
For cron use, add an optional `--heartbeat-url` (healthchecks.io-style ping) or at minimum machine-readable summary output (`--summary-json`) so schedulers can alert on `failed > 0`.

### D. Testing

**D1. No tests exist — Severity: Critical** (acknowledged in `AGENTS.md`). The logic most worth testing is pure and easy to test: `expand_query_params`, `paginate` (offset & `more` handling), `paginate_cursor`, `_name_has_affix` idempotency, `pd_list_incidents.parse_multi`/`normalize_statuses`, `pd_scim_user_audit.diff`, CSV loaders' validation paths.
Provided: `audit/proposed/tests/test_pd_common.py` (unit, mocked HTTP via `responses`) and `audit/proposed/tests/test_cli_smoke.py` (every script's `--help` exits 0 — catches import-time breakage that `py_compile` misses, and will immediately flag the module-level-execution scripts A1).
Mocking strategy: `responses` (or `requests-mock`) at the HTTP layer for `pd_common` itself; `unittest.mock.patch("pd_common.make_api_request")` for script-level logic. Add one optional integration test gated on `PD_TEST_TOKEN` against read-only endpoints (`/users?limit=1`).

**D2. CI never imports the scripts — Severity: High**
`py_compile` passes even when a script executes API calls at import (A1). The `--help` smoke test fixes this cheaply.

### E. Performance

**E1. Full-collection fetch where the API filters server-side — Severity: Medium**
`pd_list_users.py:14–27` and `pd_list_teams.py` fetch *all* users/teams then filter client-side; `/users` supports `query=`. `pd_patch_role.py` fetches all users to find one role (acceptable — no role filter in API — but should stream rather than `list()` everything when only counting).
Fix: pass `params={"query": text_filter}` when the filter is a plain substring; keep client-side as fallback.

**E2. Classic-pagination 10k offset cap unhandled — Severity: Medium**
`pd_common.py:paginate` will silently stop (or 400) at offset 10,000. For `pd_export_log_entries.py`/`pd_list_incidents.py` on a busy account, a month of data can exceed this — the export is silently incomplete: dangerous for the stated compliance use.
Fix: detect `offset + limit > 10000` and either error loudly with guidance to narrow `--since/--until`, or auto-window the export by date.

**E3. Serial writes — Severity: Low**
Bulk updates are one-at-a-time. That's defensible under rate limits; with C1's retry layer in place, a small `ThreadPoolExecutor(max_workers=3–5)` is a safe speedup for large runs. Don't parallelize before retries exist.

**E4. `pd_remove_team_members.py` N+1 reads — Severity: Low**
One GET per schedule (line 158) and per escalation policy (line 169) just to build the overview. Fine for small teams; with C3's pagination fix, memoize policy details (it re-fetches each policy again at removal time).

### F. DevOps / CI/CD

**F1. Replace the demo workflow with a real CI gate — Severity: High**
`.github/workflows/demo.yml` is mostly `echo`, still references deleted scripts (`pd_update_service_names.py` etc.), and gates nothing. Provided `audit/proposed/ci.yml`: ruff → pytest → pip-audit → gitleaks, on push/PR.
**F2. Dev tooling declared but unconfigured — Severity: Medium** — `requirements-dev.txt` has `pre-commit`+`ruff` but no `.pre-commit-config.yaml` or `pyproject.toml` `[tool.ruff]`. Provided in `audit/proposed/`.
**F3. No versioning/releases — Severity: Low** — adopt tags + `CHANGELOG.md` (Keep-a-Changelog), since SECURITY.md already says "latest main is the supported line", releases give operators a stable pin target.
**F4. Branch protection — Severity: Low** — require the new CI checks on `main`; CODEOWNERS with yourself as owner of `pd_common.py`.

### G. Documentation

**G1. README is genuinely strong** (per-script usage, MCP-vs-script decision table, migration notes). Gaps:
- **Token scope table — Medium**: nothing says which scripts need a read-only vs full-access token, or that `pd_scim_user_audit.py` needs SCIM scope (only its epilog mentions it). One table prevents over-privileged tokens.
- **Stale references — Low**: `demo.yml` and `DEMO.md` advertise the three deleted rename scripts.
- **Exit-code & logging contract — Low**: once C2/C4 land, document them (operators script against this).
- **No CHANGELOG — Low.**

---

## 4. Prioritized 30-Day Roadmap

**Week 1 — Critical correctness (unblocks unattended use)**
1. Fix pagination in the three team scripts (C3) — ~1 hr, highest risk reduction per line.
2. Land `pd_common` v2: retries + 429 backoff, typed errors, stderr-only diagnostics, non-zero exit on failure (C1, C2, A3, B3). Base on `audit/proposed/pd_common_improved.py`.
3. Make every bulk script propagate `failed > 0` → `sys.exit(1)` (C2).
4. Add the `--help` smoke test + ruff to CI; fix the 4 F401s (D2, F1 partial).

**Week 2 — Architecture & reliability**
5. Rewrite the three legacy scripts onto `pd_common` with `main()` guards (A1).
6. Delete duplicated client in `pd_export_ids.py` (A2); extract shared output renderers (A5).
7. Introduce `logging` with `--verbose/--quiet` (C4).
8. Unit tests for `pd_common` + the pure functions (D1); target ~70% on `pd_common.py`.

**Week 3 — Security & performance**
9. Deprecate `-t/--token`; redact response bodies (B2, B3).
10. Pin dependencies; add `pip-audit` + gitleaks to CI (B4).
11. Handle the 10k offset cap; server-side `query=` filters (E1, E2).
12. Idempotency check in `pd_bulk_maintenance_window.py` (C5).

**Week 4 — CI/CD & docs**
13. Replace demo.yml with `ci.yml`; add `.pre-commit-config.yaml`, `pyproject.toml` (F1, F2).
14. Begin package refactor (A4) — `pagerduty_ops/` package with script shims.
15. README: token-scope table, exit-code contract; CHANGELOG + first tagged release (G1, F3).
16. Optional: `--summary-json` / heartbeat hooks for scheduled jobs (C6).

---

## 5. Auto-Generated Code Fixes

Provided under `audit/proposed/` (review, then move into place):

| File | Replaces / adds |
|---|---|
| `pd_common_improved.py` | Drop-in evolution of `pd_common.py`: Session + Retry w/ 429 `Retry-After`, `PDApiError`, stderr diagnostics, redacted error bodies, `run_exit_code()` helper |
| `pd_update_team_roles_v2.py` | Full rewrite of `pd_update_team_roles.py`: paginated members, role validation, `--dry-run`/`-y`, argparse, exit codes |
| `tests/test_pd_common.py` | Unit tests: token resolution, pagination (offset/cursor/`more`), retry-on-429, affix idempotency, `expand_query_params` |
| `tests/test_cli_smoke.py` | `--help` exits 0 for every script (catches import-time execution) |
| `ci.yml` | GitHub Actions: ruff + pytest + pip-audit + gitleaks (move to `.github/workflows/`) |
| `pyproject.toml` | ruff config, pytest config, project metadata |
| `.pre-commit-config.yaml` | ruff + ruff-format + gitleaks hooks |

Patch-level fixes called out inline above: C3 pagination one-liners, C2 `sys.exit(1)` summaries, A2 import cleanup.

---

## 6. Clarifying Questions

Answers would sharpen the next iteration:

1. **Runtime environment** — Where will these actually run unattended (Windows Task Scheduler at the City, Linux cron, GitHub Actions)? Affects logging format and secrets delivery.
2. **Secrets management** — Is there an approved store (Azure Key Vault, AWS SSM, CyberArk)? The `.env`/env-var pattern is fine for dev but the report assumes env injection by the scheduler for prod.
3. **Token scope** — Single full-access account token today, or per-purpose tokens? Drives how aggressive the B2 deprecation should be.
4. **Scale** — Rough counts of users/services/incidents-per-month in the target account? Determines whether E2 (10k offset cap) is theoretical or imminent.
5. **Packaging appetite** — Keep flat scripts (operators `git pull` and run) or move to an installable package with console entry points (A4)? Both are defensible; the roadmap assumes incremental packaging in week 4.
