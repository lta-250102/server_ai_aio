import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any
from bson import ObjectId


class StructuredFormatter(logging.Formatter):
    """Output format depends on log level.

    INFO:      plain text "LEVEL message" — clean for normal flow
    DEBUG/WARN/ERROR: full JSON with extra fields, timestamps, stack traces
    """

    _EXCLUDE = frozenset((
        "msg", "args", "created", "exc_info", "exc_text", "exc_type",
        "filename", "funcName", "levelname", "levelno", "lineno",
        "message", "module", "msecs", "name", "pathname",
        "process", "processName", "relativeCreated", "stack_info",
        "thread", "threadName", "taskName", "extra",
    ))

    def format(self, record) -> str:
        # INFO: plain text "LEVEL message"
        if record.levelno == logging.INFO:
            return f"{record.levelname}:\t  {record.getMessage()}"

        # DEBUG / WARNING / ERROR: full JSON
        obj = {
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
        # Include extra kwargs (logger.info/warn/error("msg", extra={"k": "v"}))
        for key, val in record.__dict__.items():
            if key not in self._EXCLUDE and not key.startswith("_"):
                obj[key] = val
        return json.dumps(obj, ensure_ascii=False, default=str)


# Global flag: set after setup_logging() so helpers can check
_pyapi_logger = None


def get_logger() -> logging.Logger:
    """Return the shared pyapi logger (None if setup_logging hasn't run yet)."""
    global _pyapi_logger
    return _pyapi_logger

def setup_logging(level: str = "INFO"):
    """Configure the shared pyapi logger with structured JSON output.

    Pure built-in, no extra deps.  Call once during app startup (e.g. in lifespan).
    """
    global _pyapi_logger
    logger = logging.getLogger("pyapi")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    _pyapi_logger = logger

def objectid_to_str(v):
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
