"""Shared utility functions for logging, serialization, and BSON handling."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


class StructuredFormatter(logging.Formatter):
    """Log formatter that emits JSON for DEBUG/WARN/ERROR and plain text for INFO.

    INFO level produces a concise ``LEVEL:  message`` line with any extra
    keyword arguments appended as ``key=value`` pairs.  All other levels
    produce a full JSON object with timestamps, module info and optional
    exception tracebacks.
    """

    _EXCLUDE: frozenset[str] = frozenset((
        "msg", "args", "created", "exc_info", "exc_text", "exc_type",
        "filename", "funcName", "levelname", "levelno", "lineno",
        "message", "module", "msecs", "name", "pathname",
        "process", "processName", "relativeCreated", "stack_info",
        "thread", "threadName", "taskName", "extra",
    ))

    def format(self, record: logging.LogRecord) -> str:
        # INFO: plain text "LEVEL message" with extra kwargs as key=value
        if record.levelno == logging.INFO:
            parts = [f"{record.levelname}:\t  {record.getMessage()}"]
            for key, val in record.__dict__.items():
                if key not in self._EXCLUDE and not key.startswith("_"):
                    parts.append(f"{key}={val}")
            return " ".join(parts)

        # DEBUG / WARNING / ERROR: full JSON
        obj: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "lvl": record.levelname,
            "name": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info and record.exc_info[0] is not None:
            obj["err"] = self.formatException(record.exc_info)
        for key, val in record.__dict__.items():
            if key not in self._EXCLUDE and not key.startswith("_"):
                obj[key] = val
        return json.dumps(obj, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the shared ``pyapi`` logger with structured JSON output.

    Call once during application startup (e.g. inside the lifespan).
    """
    logger = logging.getLogger("pyapi")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)


def objectid_to_str(v: Any) -> Any:
    """Convert a MongoDB ``ObjectId`` to its string representation."""
    return str(v) if isinstance(v, ObjectId) else v


def make_serializable(obj: Any) -> Any:
    """Recursively convert LangChain objects to JSON-serializable types."""
    if hasattr(obj, "model_dump"):
        return make_serializable(obj.model_dump())
    if hasattr(obj, "dict"):
        return make_serializable(obj.dict())
    if isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    if hasattr(obj, "__str__"):
        return str(obj)
    return obj
