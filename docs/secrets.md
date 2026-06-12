# Secrets management

## The rules

1. **Never** put a token on the command line (`-t` is deprecated and warns), in git, in a Dockerfile, or in CI logs.
2. Inject `PD_API_TOKEN` as an environment variable from a secret store at runtime.
3. Use the **least-privileged token** that works (see scope table below).
4. Rotate on any suspicion of exposure and treat leakage as a credential incident.

## Token scopes by command

| Token capability needed | Commands |
|---|---|
| **Read-only** REST token | pd-list-* , pd-export-* , pd-audit-export, pd-standards-report, pd-team-members, pd-eo-export, pd-v3-schedules |
| **Full-access** REST token | pd-patch-role, pd-rename-resources, pd-update-team-roles, pd-remove-team-members, pd-service-urgency, pd-bulk-maintenance-window, pd-apply-tags, pd-bulk-extensions, pd-alert-grouping, pd-eo-apply |
| Full-access + **SCIM** enabled | pd-scim-user-audit |

Keep two tokens: a read-only one for scheduled exports, a full-access one used only for supervised bulk changes.

## Delivery patterns

**Local development** — `.env` file (git-ignored):
```
PD_API_TOKEN=u+xxxxxxxx
PD_TEAM_ID=PXXXXXX
```

**Windows Task Scheduler** — store with `cmdkey`/DPAPI or pull from your vault in the wrapper script; set the variable for the process, not machine-wide.

**Linux cron / systemd** — `EnvironmentFile=/etc/pagerduty-ops/env` readable only by the service user (`chmod 600`), or `systemd-creds`.

**GitHub Actions** — repository/organization **Secrets** (`secrets.PD_TEST_TOKEN` is already wired for integration tests). Never `echo` secrets; this repo's logging never prints tokens.

**Enterprise vaults** — Azure Key Vault / AWS SSM / CyberArk: fetch at job start, export into the process environment, never write to disk.

## What this codebase does to protect you

- Tokens are read from env/getpass only and never logged; HTTP error logging is redacted to PagerDuty's error envelope (status, code, message) — raw bodies that may contain user PII are discarded.
- `gitleaks` runs in CI on every push (full history) and locally via pre-commit.
- `.gitignore` covers `.env`; `.mcp.json` uses `${PD_API_TOKEN}` interpolation, not a literal.
