# Contributing

Thank you for helping improve **PagerDuty-Ops-Scripts**. This document describes how we work together and what to expect when you contribute.

## Code of conduct

Everyone participating in issues, pull requests, and discussions is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- Skim the [README](README.md) for prerequisites (`Python 3.7+`, `requirements.txt`, `PD_API_TOKEN`, and related environment variables).
- Many scripts perform **bulk or write operations** against the PagerDuty API. When a script offers `--dry-run` (or similar), use it first against a non-production account or a safe scope.

## How to contribute

1. **Issues first (optional but helpful)**  
   For larger changes or new scripts, opening an issue lets maintainers align on scope and approach before you invest significant time.

2. **Fork and branch**  
   Create a focused branch from the default branch (for example, `fix/patch-role-docs` or `feat/export-filter`).

3. **Pull request**  
   Open a PR with a clear title and description. Use the [pull request template](.github/pull_request_template.md) as a checklist.

## Coding guidelines

- **Match existing style** in the file you edit: imports, naming, argparse patterns, and use of shared helpers in [`pd_common.py`](pd_common.py) where appropriate.
- **Do not commit secrets.** Never add API tokens, `.env` files with real credentials, or customer-specific identifiers that should stay private.
- **PagerDuty API usage:** Prefer existing helpers (`get_pd_api_token`, `make_api_request`, etc.) for consistency, timeouts, and headers.
- **Dependencies:** If you add a package, update [`requirements.txt`](requirements.txt) with a reasonable version constraint and note it in the PR.

## Testing and verification

This repository does not currently ship an automated test suite. Before opening a PR:

- Run the script with **read-only** or **dry-run** modes when available.
- Confirm behavior against a **test** PagerDuty account or minimal scope when writes are involved.
- Mention in the PR how you verified the change (commands run, sample output, or “docs-only”).

## Documentation

- Update the **README** if you add a new script, change CLI flags, or alter required environment variables.
- Keep usage examples copy-pasteable and accurate.

## Licensing

By contributing, you agree that your contributions will be licensed under the same terms as the project ([MIT License](LICENSE)).
