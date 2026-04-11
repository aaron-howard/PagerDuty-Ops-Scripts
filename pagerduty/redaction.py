"""Redact secrets and credentials from strings before logging."""

from __future__ import annotations

import re

# PagerDuty REST: Authorization: Token token=<secret>
_TOKEN_HEADER = re.compile(
    r"(?i)(Token\s+token=)([A-Za-z0-9_+\-=]{16,})",
)
_BEARER = re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9_\-\.=~+/]{20,})")
# assignment-style secrets in debug prints (key=value / key: value)
_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:api[_-]?token|api[_-]?key|password|secret|access_token)\s*[:=]\s*)(\S{12,})"
)


def redact_log_text(text: str) -> str:
    """Return *text* with likely credentials replaced by placeholders."""
    if not text or not isinstance(text, str):
        return text
    redacted = _TOKEN_HEADER.sub(r"\1***REDACTED***", text)
    redacted = _BEARER.sub(r"\1***REDACTED***", redacted)
    redacted = _ASSIGNMENT.sub(r"\1***REDACTED***", redacted)
    return redacted
