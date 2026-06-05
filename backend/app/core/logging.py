import logging
from typing import Any

import structlog

from app.core.config import settings

_CONFIGURED = False


def _resolve_level() -> int:
    """Map the configured ``LOG_LEVEL`` string to a stdlib level int.

    Falls back to ``INFO`` for unknown values so a typo never silences logging
    entirely. Tests set ``LOG_LEVEL=WARNING`` to keep request/task access logs
    out of the pytest output.
    """
    return getattr(logging, str(settings.log_level).upper(), logging.INFO)


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    level = _resolve_level()
    logging.basicConfig(
        format="%(message)s",
        level=level,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(component: str | None = None, **initial_values: Any) -> Any:
    """Return a structlog logger, optionally tagged with a ``component`` field.

    ``configure_logging`` is invoked lazily so loggers obtained from Celery
    workers or scripts (which do not go through :func:`app.main.create_app`)
    still emit JSON with merged context variables.
    """
    configure_logging()
    logger = structlog.get_logger()
    if component:
        initial_values = {"component": component, **initial_values}
    if initial_values:
        logger = logger.bind(**initial_values)
    return logger

