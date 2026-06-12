# Usage — command catalog

Conventions shared by every command: `--help`; `-v/--verbose`, `-q/--quiet`, `--log-file FILE`; token from `PD_API_TOKEN` (or `--prompt` locally). Read commands: `-f table|csv|json`, `-o FILE`. Write commands: `--dry-run` and `-y/--yes` — **always review a `--dry-run` first**, then re-run with `-y`. Legacy `python pd_*.py` names accept identical arguments.

## Read / export commands

### pd-list-users
```bash
pd-list-users -f csv -o users.csv
pd-list-users --filter "smith" -f json
```

### pd-list-teams
```bash
pd-list-teams --filter platform
```

### pd-list-schedules (v2)
```bash
pd-list-schedules --name-filter "SRE" -f csv -o schedules.csv
```

### pd-list-incidents
```bash
pd-list-incidents --since 2026-05-01T00:00:00Z --until 2026-06-01T00:00:00Z \
    --status triggered,acknowledged --team-id PXXXXXX -f csv -o incidents.csv
```
Unbounded exports warn and are capped at 10,000 records by the API — use `--since/--until` windows.

### pd-list-status-pages
```bash
pd-list-status-pages
pd-list-status-pages --posts PSTATUSPAGEID -f json
```

### pd-v3-schedules (Early Access — inventory only)
```bash
pd-v3-schedules
pd-v3-schedules --get PSCHEDID --include-users
```

### pd-export-ids
```bash
pd-export-ids -f csv -o inventory.csv
```

### pd-audit-export
```bash
pd-audit-export --since 2026-04-01T00:00:00Z --until 2026-05-01T00:00:00Z \
    --action update --root-resource-type services -f csv -o audit.csv
```

### pd-export-log-entries
```bash
pd-export-log-entries --since 2026-05-01T00:00:00Z --until 2026-06-01T00:00:00Z -f csv -o logs.csv
pd-export-log-entries --incident-id PT4KHLK -f json
```

### pd-export-change-events
```bash
pd-export-change-events --since 2026-05-01T00:00:00Z -f csv -o changes.csv
pd-export-change-events --service-id PIJ90N7 --since 2026-05-01T00:00:00Z
pd-export-change-events --incident-id PT4KHLK -f json
```

### pd-scim-user-audit (token needs SCIM scope)
```bash
pd-scim-user-audit expected_users.csv -o scim_report.txt
```
CSV columns: `email, displayName, active`.

### pd-standards-report
```bash
pd-standards-report --resource-type technical_services --failing-only -f csv -o standards.csv
```

### pd-team-members
```bash
pd-team-members --team-id PXXXXXX -f csv      # or PD_TEAM_ID
```

### pd-eo-export
```bash
pd-eo-export -o event_orchestrations/         # commit the directory to git
```

## Write commands

### pd-eo-apply (diff-first)
```bash
pd-eo-apply -i event_orchestrations/                                   # diff only
pd-eo-apply -i event_orchestrations/ --apply -y --from-email you@org.com
```

### pd-patch-role
```bash
pd-patch-role --from-role user --to-role observer --dry-run
pd-patch-role --from-role user --to-role observer -y
```

### pd-rename-resources (idempotent)
```bash
pd-rename-resources --resource services --suffix " SVC" --dry-run
pd-rename-resources --resource schedules --prefix "[SRE] " --filter prod -y
pd-rename-resources --resource escalation_policies --list
```

### pd-update-team-roles
```bash
pd-update-team-roles --team-id PXXXXXX                       # interactive
pd-update-team-roles --set-role responder --dry-run          # bulk preview
pd-update-team-roles --set-role responder -y                 # bulk apply
```

### pd-remove-team-members (interactive offboarding)
```bash
pd-remove-team-members --team-id PXXXXXX --dry-run
pd-remove-team-members --team-id PXXXXXX
```
Walks each member through removal from schedule layers and escalation-policy targets **before** team removal. Fully paginated (no 25-member truncation).

### pd-service-urgency
```bash
pd-service-urgency --dry-run && pd-service-urgency -y
```

### pd-bulk-maintenance-window (idempotent)
```bash
pd-bulk-maintenance-window windows.csv --from-email you@org.com --dry-run
pd-bulk-maintenance-window windows.csv --from-email you@org.com -y
```
CSV: `service_id, start_time, end_time, description` (ISO 8601 **with timezone**; validated before any write). Rows whose identical window already exists are skipped, so re-runs are safe.

### pd-apply-tags
```bash
pd-apply-tags tags.csv --dry-run
pd-apply-tags tags.csv -y
```
CSV: `entity_type (users|teams|services|escalation_policies), entity_id, tag_label, action (add|remove)`. Grouped into one atomic `change_tags` call per entity.

### pd-bulk-extensions (idempotent)
```bash
pd-bulk-extensions --schema "Generic Webhook" --name "Datadog hook" \
    --endpoint-url https://example.com/hook --service-filter prod --dry-run
```
`--endpoint-url` must be `https://`. Services already carrying an identical extension are skipped.

### pd-alert-grouping
```bash
pd-alert-grouping --list
pd-alert-grouping --attach "Intelligent grouping" --services-csv services.csv --dry-run
pd-alert-grouping --get-json PZC4OM1 -o setting.json
pd-alert-grouping --create-json new_setting.json --dry-run
pd-alert-grouping --update-json setting.json -y
pd-alert-grouping --delete PZC4OM1 --dry-run
```
