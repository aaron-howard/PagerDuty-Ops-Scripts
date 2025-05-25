# PagerDuty-Ops-Scripts

Daily Operations Scripts for managing the PagerDuty application.

## Prerequisites

- Python 3.7+
- Install dependencies from `requirements.txt`:
  ```bash
  pip install -r requirements.txt
  ```
- A PagerDuty API token

## Setup

1. Clone the repository.
2. Set your PagerDuty API token as an environment variable:
   ```bash
   export PD_API_TOKEN=your_token_here
   ```

## Scripts

### `pd_export_ids.py`

Exports PagerDuty teams, schedules, escalation policies, services, and webhook subscriptions.

**Usage:**
```bash
python pd_export_ids.py [-t API_TOKEN] [-o OUTPUT_FILE] [-f FORMAT]
```
- `-t`, `--token`: PagerDuty API token. If omitted, uses the `PD_API_TOKEN` environment variable or prompts for input.
- `-o`, `--output`: Output file (default: print to console).
- `-f`, `--format`: Output format: `table`, `csv`, or `json` (default: `table`).

### `pd_patch_role.py`

Finds all PagerDuty users and updates their role as needed.

**Usage:**
```bash
export PD_API_TOKEN=your_token_here
python pd_patch_role.py
```

### `pd_update_service_names.py`

Updates PagerDuty service names by appending "SVC" to the end of each service name if it doesn't already have it.

**Usage:**
```powershell
$env:PD_API_TOKEN="your_token_here"
python pd_update_service_names.py [--list] [--filter TEXT] [--dry-run]
```

### `pd_update_schedule_names.py`

Updates PagerDuty schedule names by appending "SCH" to the end of each schedule name if it doesn't already have it.

**Usage:**
```powershell
$env:PD_API_TOKEN="your_token_here"
python pd_update_schedule_names.py [--list] [--filter TEXT] [--dry-run]
```
- `-t`, `--token`: PagerDuty API token. If omitted, uses the `PD_API_TOKEN` environment variable.
- `-l`, `--list`: List schedules without making changes.
- `-f`, `--filter`: Only process schedules containing this text in their name.
- `--dry-run`: Show what would be done without making changes to the schedules.
$env:PD_API_TOKEN="your_token_here"
python pd_update_service_names.py [-t API_TOKEN] [-d] [-l] [-f FILTER]
```
- `-t`, `--token`: PagerDuty API token. If omitted, uses the `PD_API_TOKEN` environment variable or prompts for input.
- `-d`, `--dry-run`: Perform a dry run (show what would change without making changes).
- `-l`, `--list`: List services without making changes.
- `-f`, `--filter`: Filter services by name (only update services containing this string).

## Contributing

1. Fork this repository
2. Create a feature branch
3. Submit a pull request

## License

See [LICENSE](LICENSE)