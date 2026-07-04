import logging
import json
import os
import re
import sys
from datetime import datetime, timezone


_REDACTION_PATTERNS = (
    (
        re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9._~+/=-]+"),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        "[REDACTED_JWT]",
    ),
    (
        re.compile(r"\bsb_(?:secret|publishable)_[A-Za-z0-9_-]+\b"),
        "[REDACTED_SUPABASE_KEY]",
    ),
    (
        re.compile(r"(?i)(token|password|secret|apikey|api_key)=([^&\s]+)"),
        r"\1=[REDACTED]",
    ),
    (
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    (
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}/"
            r"[0-9a-f-]{36}/S-[1-4][A-F]/[^\s]+",
            re.IGNORECASE,
        ),
        "[REDACTED_OBJECT_PATH]",
    ),
)


def redact(value: object) -> str:
    text = str(value)
    for pattern, replacement in _REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact(record.getMessage()),
            "module": record.module,
            "lineno": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(log_data, ensure_ascii=False)

def setup_logger(name: str = "emathtoco") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, level_name, logging.INFO))
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger

logger = setup_logger()
