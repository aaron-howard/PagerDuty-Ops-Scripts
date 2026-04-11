---
name: Bug report
about: Report unexpected behavior in the toolkit or CLIs
title: ''
labels: ''
assignees: ''

---

**Describe the bug**  
A clear description of what went wrong (including any traceback or API error text).

**How you ran it**  
- Command (for example `pd-export-ids --format table` or `pagerduty-ops export-ids …`)  
- Package install style: `pip install -e .` / `pip install -r requirements.txt` / other  

**Environment**  
- OS (e.g. Windows 11, Ubuntu 22.04)  
- Python version (`python --version`)  
- Package version if known (`python -c "import pagerduty; print(pagerduty.__version__)"`)  

**Configuration (no secrets)**  
- Token source: env `PD_API_TOKEN` / `--config` file / prompted (do **not** paste tokens)  
- Relevant flags: `--verbose`, `--dry-run`, `--no-progress`, etc.  

**Expected behavior**  
What you expected to happen.

**Actual behavior**  
What happened instead (logs, exit code, partial output—redact tokens and IDs if needed).

**Additional context**  
PagerDuty account/region notes, minimal repro, or links to relevant API docs.
