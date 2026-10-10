"""Body-free structured logging with a final credential redaction layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json
import logging
import re
import copy


_PRIVATE_KEYS = re.compile(r"password|secret|token|cookie|authorization|api.?key|email|prompt|question|chat|body", re.I)
_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)((?:password|passwd|token|api_key|secret)\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(://[^\s:/]+:)[^\s@]+(@)"),
)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: "[REDACTED]" if _PRIVATE_KEYS.search(str(key)) else redact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if not isinstance(value, str):
        return value
    result = value
    result = _PATTERNS[0].sub("[REDACTED]", result)
    result = _PATTERNS[1].sub(r"\1[REDACTED]", result)
    result = _PATTERNS[2].sub(r"\1[REDACTED]", result)
    return _PATTERNS[3].sub(r"\1[REDACTED]\2", result)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        safe_record = copy.copy(record)
        safe_record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            safe_record.args = tuple(redact(item) for item in record.args)
        elif isinstance(record.args, dict):
            safe_record.args = redact(record.args)
        fields: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": redact(safe_record.getMessage()),
        }
        if record.exc_info and record.exc_info[0]:
            fields["error_class"] = record.exc_info[0].__name__
        if hasattr(record, "error_class"):
            fields["error_class"] = str(record.error_class)
        return json.dumps(fields, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
