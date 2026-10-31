"""Structured logging configuration for the API process."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sys
import sysconfig
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any


def _load_stdlib_logging():
    stdlib_path = sysconfig.get_paths()["stdlib"]
    spec = importlib.machinery.PathFinder.find_spec("logging", [stdlib_path])
    if spec is None or spec.loader is None:
        raise ImportError("Unable to locate the Python standard logging module")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__" and __package__ in {None, ""}:
    logging_module = _load_stdlib_logging()
else:
    import logging as logging_module


if TYPE_CHECKING:
    from logging import Formatter as LoggingFormatter
    from logging import LogRecord as LoggingLogRecord
else:
    LoggingFormatter = logging_module.Formatter
    LoggingLogRecord = logging_module.LogRecord


_RESERVED_LOG_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}

_JSON_HANDLER_MARKER = "_civicos_json_handler"


class JsonFormatter(LoggingFormatter):
    """Render log records as compact JSON for machines and humans."""

    def format(self, record: LoggingLogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key not in _RESERVED_LOG_ATTRS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, separators=(",", ":"))


def _normalize_log_level(log_level: str | int) -> int:
    if isinstance(log_level, int):
        return log_level

    if isinstance(log_level, str):
        normalized = log_level.strip().upper()
        if normalized in logging_module._nameToLevel:
            return logging_module._nameToLevel[normalized]
        if normalized.isdigit():
            return int(normalized)

    return logging_module.INFO


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logging once for JSON stdout output."""

    root_logger = logging_module.getLogger()
    root_logger.setLevel(_normalize_log_level(log_level))

    root_logger.handlers = [
        handler
        for handler in root_logger.handlers
        if not getattr(handler, _JSON_HANDLER_MARKER, False)
    ]

    handler = logging_module.StreamHandler(sys.stdout)
    setattr(handler, _JSON_HANDLER_MARKER, True)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    logging_module.getLogger("uvicorn.access").setLevel(logging_module.WARNING)
