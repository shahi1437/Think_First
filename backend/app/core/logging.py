import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

_REDACTED_KEYS = frozenset(
    {
        "authorization",
        "password",
        "token",
        "api_key",
        "secret",
        "service_role_key",
        "database_url",
    }
)


def _redact_sensitive_fields(
    _logger: Any, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event_dict.keys()):
        lowered = key.lower()
        if any(sensitive in lowered for sensitive in _REDACTED_KEYS):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured JSON logging with request_id contextvar support."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact_sensitive_fields,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
