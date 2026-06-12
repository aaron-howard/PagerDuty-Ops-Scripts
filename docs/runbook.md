# Operational runbook

## Running scheduled exports (cron / Task Scheduler / Actions)

Pattern for any scheduled job:

```bash
#!/usr/bin/env bash
set -euo pipefail
export PD_API_TOKEN="$(your-vault-fetch pagerduty/readonly-token)"
pd-list-incidents --since "$(date -u -d '1 day ago' +%FT%TZ)" \
    -f csv -o "/data/exports/incidents_$(date +%F).csv" --log-file /var/log/pd-ops.log
```

Rely on the exit-code contract: `0` ok, `1` partial failure, `2` config error, `3` auth error. Alert on any non-zero. With `--log-file`, logs are timestamped and greppable; stdout stays clean for data.

## Running bulk changes (human-supervised)

1. `--dry-run` and review every line.
2. Re-run with `-y` (non-interactive shells **require** `-y`; the command refuses otherwise).
3. Check the summary line and exit code; `1` means some items failed — the log names each one.
4. Re-running after a partial failure is safe: renames, maintenance windows, and extensions are idempotent; role changes are state-based.

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| exit 3 / "HTTP 401" | token invalid or rotated | fetch a fresh token; check the secret store |
| exit 3 / "HTTP 403" | token lacks scope (e.g. SCIM, write) | see docs/secrets.md scope table |
| exit 2 "CSV missing required columns" | wrong input file header | fix the header row; column names are case-sensitive |
| exit 2 "not valid ISO 8601" | timestamp without timezone | use `2026-05-01T02:00:00Z` style |
| "rate-limited (429); retrying" warnings | normal under bulk load | nothing — backoff is automatic; persistent 429 failures mean another integration is consuming the budget |
| "hit the 10,000-record classic pagination cap" | export window too wide | narrow `--since/--until` and export in batches |
| exit 1 with per-item failures | individual resources rejected (404 deleted, validation) | grep the log for `ERROR`, fix or drop those rows, re-run (idempotent) |
| command refuses to run: "needs a TTY" | interactive command in a pipeline | use the non-interactive form (`--set-role`, `-y`) or run from a terminal |

## Incident response: bad bulk change shipped

1. **Stop** any scheduled re-runs.
2. Reconstruct what changed: every write is logged at INFO with before/after context (`--log-file`), and `pd-audit-export --since ... --actor-id <token user>` gives the authoritative server-side record.
3. Reverse with the same tooling, e.g. wrong role: `pd-patch-role --from-role observer --to-role user --dry-run`; wrong rename: re-run `pd-rename-resources` with the inverse affix... after a `--list` review; EO changes: `git revert` the JSON and `pd-eo-apply --apply -y`.
4. If the token may have been exposed, rotate it immediately (credential incident per SECURITY.md).

## Maintenance

- Dependabot opens weekly dependency PRs; CI (lint + tests + pip-audit + gitleaks) gates them.
- Release: bump `version` in `pyproject.toml`, update `CHANGELOG.md`, `git tag vX.Y.Z && git push --tags` — `release.yml` verifies version/tag match, runs tests, and publishes artifacts.
- Adding a command: new module in `pagerduty_ops/commands/` (copy a similar one), entry in `pyproject.toml [project.scripts]`, tests in `tests/unit/`, row in README + docs/usage.md.
