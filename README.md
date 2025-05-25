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

## Contributing

1. Fork this repository
2. Create a feature branch
3. Submit a pull request

## License

See [LICENSE](LICENSE)