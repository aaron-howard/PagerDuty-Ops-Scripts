# PagerDuty Operations Scripts - Demo Guide

## Overview

This repository contains administrative scripts for PagerDuty management. While these scripts cannot run a traditional "live demo" due to security and API access requirements, we've created several ways to showcase their functionality.

## Demo Options

### 1. GitHub Actions Demo (Recommended)

**Location**: `.github/workflows/demo.yml`

**What it does**:
- Validates all script syntax
- Shows available functionality
- Demonstrates usage examples
- Runs sample data demonstrations

**How to trigger**:
- Automatically runs on pushes to main branch
- Can be manually triggered from GitHub Actions tab
- View results in the Actions section of your repository

### 2. Sample Data Demo Script

**Location**: `demo_sample_output.py`

**What it shows**:
- Example output from `pd_export_ids.py`
- Team member listings
- Service name update previews
- Schedule name update previews
- JSON export format examples
- Sample **v2 schedules** and **status pages** listings (same shapes as `pd_list_schedules.py` / `pd_list_status_pages.py`)

**How to run**:
```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows PowerShell
source venv/bin/activate     # Linux/Mac

# Run demo
python demo_sample_output.py
```

### 3. Enhanced Documentation

**Location**: `README.md`

**Features**:
- Comprehensive usage examples
- Security best practices
- Command-line options
- Environment variable setup

## Why No Live Demo?

### Security Concerns
- Scripts require real PagerDuty API tokens
- Exposing tokens in public demos would be a security risk
- API calls affect real PagerDuty instances

### Technical Limitations
- Scripts are command-line tools, not web applications
- Require actual PagerDuty account access
- Make live API calls that modify production data

## Demo Alternatives

### For Presentations
1. **Use the sample data demo script** - Shows realistic output
2. **Show GitHub Actions results** - Demonstrates automated validation
3. **Walk through README examples** - Explains functionality clearly

### For Testing
1. **Use `--dry-run` flags** - Safe testing without changes
2. **Set up test PagerDuty account** - Isolated environment
3. **Use staging environment** - Non-production testing

## Getting Started

1. **Clone the repository**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Set up environment variables**:
   ```bash
   export PD_API_TOKEN=your_token_here
   export PD_TEAM_ID=your_team_id_here
   ```
4. **Run sample demo**: `python demo_sample_output.py`
5. **Test with dry-run**: `python pd_update_service_names.py --dry-run`

## Security Best Practices

- ✅ Never commit API tokens to version control
- ✅ Use environment variables for sensitive data
- ✅ Always test with `--dry-run` first
- ✅ Review changes in staging before production
- ✅ Use secure token input methods

## Support

For questions or issues:
1. Check the README.md for detailed documentation
2. Review the GitHub Actions demo results
3. Run the sample demo script to see expected outputs
4. Open an issue for specific problems

---

*This demo setup provides a safe way to showcase PagerDuty operations scripts without compromising security or requiring live API access.*
