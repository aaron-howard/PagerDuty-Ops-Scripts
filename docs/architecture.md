# Architecture

## Design goals

1. **Safe unattended operation.** Every failure mode either retries, aborts loudly, or is counted and reflected in the exit code. Nothing is silently swallowed.
2. **stdout is data, stderr is diagnostics.** Exports can be piped (`pd-list-users -f csv > users.csv`) without log lines corrupting the output.
3. **One implementation of everything.** HTTP, pagination, rendering, confirmation guards, and CSV validation each exist exactly once, in `pagerduty_ops/`.
4. **Backward compatibility.** The flat `pd_*.py` scripts remain as shims; `pd_common.py` re-exports the old API surface (with its old return-None contract) for any external callers.

## Layering

```
pd_*.py shims ──▶ pagerduty_ops.cli.run(main) ──▶ pagerduty_ops.commands.* ──▶ cli / output / bulkops ──▶ api ──▶ PagerDuty
console_scripts ─┘                                    config / log ──────┘
```

Setuptools entry points are defined in `pagerduty_ops/console_scripts.py`; each invokes `run(main)` like the `pd_*.py` shims.

### `api.py` — HTTP client

- A single `requests.Session` with `urllib3.Retry`: 5 attempts, exponential backoff, `status_forcelist={429,500,502,503,504}`, `Retry-After` honored. Only idempotent methods (GET/HEAD/PUT/DELETE) are auto-retried.
- POST/PATCH are **not** idempotent, so they get a manual retry loop for **429 only** (a 500 on a POST could have committed — retrying could duplicate the write).
- All failures raise `PDApiError` carrying `status_code` and the redacted PagerDuty error envelope. `is_auth_error` lets bulk loops abort immediately on 401/403 instead of "failing" every remaining item.
- `paginate()` (offset) raises at PagerDuty's 10,000-record classic-pagination cap with data remaining, so compliance exports are never silently incomplete. `paginate_cursor()` covers /audit/records.

### `cli.py` — command plumbing and the exit-code contract

`standard_parser()` gives every command identical flags (`-t/--prompt`, `-v/-q/--log-file`, optional `-f/-o`, optional `--dry-run/-y`). `confirm()` is the single write guard: dry-run and `-y` pass through; a non-TTY stdin without `-y` raises **exit 2** (usage) so unattended jobs do not look successful. `finish_bulk()` converts (succeeded, failed) into exit code 0/1. `run()` wraps entry points and maps `PDApiError` → exit 1 (or 3 for auth) and Ctrl-C → 130.

### `bulkops.py` — bulk-operation building blocks

Idempotent affix renaming (skips names already carrying the affix), validated CSV loading (missing-column → exit 2, per-row `_line` for error messages), and strict ISO 8601 parsing (timezone required).

### Error-handling policy

| Failure | Behavior |
|---|---|
| 429 | retried with `Retry-After`/backoff, all methods |
| transient 5xx | retried for idempotent methods only |
| 401/403 | `PDApiError(is_auth_error)` — bulk loops re-raise immediately |
| other 4xx | counted as a failed item; loop continues; exit 1 at the end |
| network error | retried by the adapter (connect errors), then `PDApiError` |
| bad input (CSV/args) | exit 2 before any API write happens |

### Idempotency

- Renames: affix-presence check before writing.
- Maintenance windows: existing (service, start, end) windows are fetched first; duplicate rows are skipped, so re-running a CSV after a partial failure is safe.
- Extensions: services that already have an extension with the same name + endpoint URL are skipped.
- Service urgency / role changes: target selection is state-based ("everyone still in role X"), so re-runs converge naturally.

## Testing strategy

- **Unit (`tests/unit`)**: HTTP mocked with `responses` at the transport layer. Covers retry behavior (manual 429 path; adapter Retry asserted by configuration since `responses` bypasses urllib3), pagination (multi-page, items-key override, 10k cap), error redaction, exit codes (partial failure → 1, dry-run → 0 with zero writes), CSV/ISO validation, parser smoke for all 23 command parsers, and subprocess `--help` for all 24 legacy shims.
- **Integration (`tests/integration`)**: opt-in via `PD_TEST_TOKEN` (read-only sandbox token), read-only endpoints only.

## Versioning

Semantic versioning, tag-driven releases (`vX.Y.Z` must match `pyproject.toml`). The shim layer and `pd_common` compatibility surface will be removed no earlier than v2.0.0.
