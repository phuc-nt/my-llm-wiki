# Shared secret/PII regex patterns used by note-writer and capture-filters.
# Conservative bias: false-positives over leaks.
from __future__ import annotations

import re

# Each entry: (pattern, short label).
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Private key blocks (PEM)
    (re.compile(r"-----BEGIN\s+(?:RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"), "PEM private key"),
    # AWS access key ID
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    # AWS secret access key (40 base64 chars after "aws_secret" or similar)
    (re.compile(r"(?i)aws[_\-]?secret[_\-]?access[_\-]?key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}"), "AWS secret"),
    # Generic API key / token assignments with long opaque values
    (re.compile(r"(?i)(?:api[_\-]?key|secret|token|password|passwd|bearer)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}"), "API key/token assignment"),
    # OpenAI-style key
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "OpenAI-style key"),
    # GitHub personal access token
    (re.compile(r"\bghp_[A-Za-z0-9]{36,}\b"), "GitHub token"),
    # GitHub fine-grained PAT
    (re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b"), "GitHub fine-grained PAT"),
    # Slack bot/user token
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}"), "Slack token"),
    # Google API key
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), "Google API key"),
    # JWT (three base64 segments)
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b"), "JWT token"),
]


def scan_for_secrets(text: str) -> str | None:
    """Return label of first matched pattern, or None when text is clean."""
    for pattern, label in _PATTERNS:
        if pattern.search(text):
            return label
    return None


def has_secret(text: str) -> bool:
    """Boolean form for filter pipelines that don't need the label."""
    return scan_for_secrets(text) is not None
