# Security policy

## Supported versions

Security fixes are applied to the **default branch** of this repository as issues are confirmed and resolved. This project does not publish numbered releases on a fixed schedule; treat the latest commit on the default branch as the current supported line.

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, use one of the following:

1. **GitHub private security advisory** (preferred if enabled for this repository): use **Security → Report a vulnerability** on the GitHub repository page.
2. **Direct contact:** message the repository maintainers through GitHub using a **private** channel (for example, the email shown on the maintainer’s public GitHub profile, if available).

Include as much of the following as you can:

- Description of the issue and its impact
- Steps to reproduce, or proof-of-concept, if safe to share
- Affected components (specific script(s), dependency, or integration point)
- Any suggested mitigation you have in mind

We aim to acknowledge reports within a few business days. Timelines for fixes depend on severity and complexity; we will keep you informed when we can.

## Scope and expectations

These scripts interact with the **PagerDuty REST API** using credentials from the environment or CLI. General guidance:

- **Protect `PD_API_TOKEN` and other secrets** at all times; treat leakage as a credential incident in your organization’s process.
- This repository is **operational tooling**, not a hosted service. Vulnerabilities we care most about include unsafe handling of credentials, injection or deserialization issues, unexpected destructive API calls, and dependency flaws with practical exploit paths in normal use.

## Disclosure

We ask that you give maintainers a reasonable window to address confirmed issues before public disclosure. If you plan coordinated disclosure with a CVE or blog post, please mention that in your initial report so we can align on timing.
