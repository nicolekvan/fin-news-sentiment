"""Logging that never leaks credentials."""

from __future__ import annotations

import logging
import re

# Generic key-looking patterns, applied in addition to the exact configured secret values.
_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|apikey|authorization)\s*[=:]\s*)([^\s&\"']+)"),
]
REDACTED = "[REDACTED]"


def redact(text: str, secrets: list[str] | None = None) -> str:
    for secret in secrets or []:
        text = text.replace(secret, REDACTED)
    text = _PATTERNS[0].sub(REDACTED, text)
    return _PATTERNS[1].sub(lambda m: m.group(1) + REDACTED, text)


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: list[str] | None = None):
        super().__init__()
        self.secrets = secrets or []

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage(), self.secrets)
        record.args = None
        return True


def configure_logging(level: int = logging.INFO) -> None:
    from marketlens.config import get_settings

    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter(get_settings().secret_values()))
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)
