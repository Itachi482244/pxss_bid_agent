"""Application-wide observability wiring.

Provides three correlated layers of structured logging on top of structlog's
context variables (see :func:`app.core.logging.configure_logging`):

* :class:`RequestLoggingMiddleware` binds a ``request_id`` (plus method/path and
  best-effort tenant/user identity) for the lifetime of an HTTP request and
  emits an access log line on completion. The id is echoed back in the
  ``X-Request-Id`` response header so a client/operator can grep one request
  end to end.
* :func:`unhandled_exception_handler` turns any uncaught exception into a clean
  JSON 500 (no stack leak unless ``APP_DEBUG``) carrying the same request id.
* :func:`observed_task` decorates async task entry points so every log emitted
  while a task runs — including LLM gateway logs — is tagged with ``task_id`` and
  ``task_type``. When a task runs inline inside a request, both ``request_id``
  and ``task_id`` appear on the same lines.
"""

from __future__ import annotations

import time
import uuid
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars, reset_contextvars

from app.core.config import settings
from app.core.logging import get_logger

REQUEST_ID_HEADER = "X-Request-Id"
_SILENT_PATHS = {"/health", "/favicon.ico"}

F = TypeVar("F", bound=Callable[..., Any])


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Bind a per-request correlation id and emit an access log line."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        clear_contextvars()
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id

        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        tenant_code = request.headers.get("X-Tenant-Code")
        if tenant_code:
            bind_contextvars(tenant_code=tenant_code)
        user_external_id = request.headers.get("X-User-External-Id")
        if user_external_id:
            bind_contextvars(user_external_id=user_external_id)

        log = get_logger("request")
        silent = request.url.path in _SILENT_PATHS
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            # Log the full stack here while context vars are still bound; the
            # exception handler only renders the client-facing response.
            log.exception("request.failed", duration_ms=duration_ms)
            clear_contextvars()
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers[REQUEST_ID_HEADER] = request_id
        if not silent:
            log.info(
                "request.completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
        clear_contextvars()
        return response


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a clean JSON 500 with the request id for any uncaught exception."""
    request_id = getattr(request.state, "request_id", None)
    content: dict[str, Any] = {"detail": "服务器内部错误，请稍后重试或联系管理员。"}
    if request_id:
        content["request_id"] = request_id
    if settings.app_debug:
        content["error"] = f"{exc.__class__.__name__}: {exc}"
    response = JSONResponse(status_code=500, content=content)
    if request_id:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


def register_observability(app: FastAPI) -> None:
    app.add_middleware(RequestLoggingMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)


def observed_task(task_type: str) -> Callable[[F], F]:
    """Tag every log emitted during an async task with ``task_id``/``task_type``.

    Works for both the inline execution path (inside a request) and the Celery
    worker path. Expects the wrapped function's signature to start with
    ``(db, task_id, ...)``; the task id is read positionally or from kwargs.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            task_id = kwargs.get("task_id")
            if task_id is None and len(args) >= 2:
                task_id = args[1]
            tokens = bind_contextvars(task_type=task_type, task_id=str(task_id))
            log = get_logger("task")
            started = time.perf_counter()
            log.info("task.started")
            try:
                result = func(*args, **kwargs)
            except Exception:
                duration_ms = int((time.perf_counter() - started) * 1000)
                log.exception("task.crashed", duration_ms=duration_ms)
                raise
            else:
                duration_ms = int((time.perf_counter() - started) * 1000)
                status_value = result.get("status") if isinstance(result, dict) else None
                log.info(
                    "task.finished",
                    duration_ms=duration_ms,
                    result_status=status_value,
                )
                return result
            finally:
                reset_contextvars(**tokens)

        return cast(F, wrapper)

    return decorator


__all__ = [
    "REQUEST_ID_HEADER",
    "RequestLoggingMiddleware",
    "observed_task",
    "register_observability",
    "unhandled_exception_handler",
]
