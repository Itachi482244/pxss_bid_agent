"""Regression tests for the observability layer (request id + task context).

These assert the wiring contract rather than rendered log bytes: a per-request
correlation id is created/echoed, uncaught exceptions become a clean JSON 500
carrying that id, and :func:`observed_task` binds ``task_id``/``task_type`` for
the duration of a task and always resets them afterwards.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.contextvars import get_contextvars

from app.core.observability import REQUEST_ID_HEADER, observed_task, register_observability
from app.main import app


def test_request_id_present_on_response() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get(REQUEST_ID_HEADER)


def test_request_id_is_echoed_when_supplied() -> None:
    client = TestClient(app)
    response = client.get("/health", headers={REQUEST_ID_HEADER: "fixed-req-123"})
    assert response.headers.get(REQUEST_ID_HEADER) == "fixed-req-123"


def _exception_app() -> FastAPI:
    test_app = FastAPI()
    register_observability(test_app)

    @test_app.get("/boom")
    def boom() -> dict[str, str]:  # pragma: no cover - body raises
        raise RuntimeError("kaboom")

    return test_app


def test_unhandled_exception_returns_clean_json_500() -> None:
    client = TestClient(_exception_app(), raise_server_exceptions=False)
    response = client.get("/boom")
    assert response.status_code == 500
    body = response.json()
    assert body["detail"]
    assert body.get("request_id")
    # The same correlation id is on the header and in the body.
    assert response.headers.get(REQUEST_ID_HEADER) == body["request_id"]
    # The raw exception message must never leak in the user-facing detail field.
    assert "kaboom" not in body["detail"]


def test_observed_task_binds_and_resets_context() -> None:
    seen: dict[str, object] = {}

    @observed_task("unit_demo")
    def run(db: object, task_id: str) -> dict[str, str]:
        seen.update(get_contextvars())
        return {"status": "succeeded"}

    result = run(None, "task-xyz")

    assert result == {"status": "succeeded"}
    assert seen.get("task_id") == "task-xyz"
    assert seen.get("task_type") == "unit_demo"
    # Context must be cleared once the task returns so it cannot bleed into the
    # rest of an inline request.
    current = get_contextvars()
    assert "task_id" not in current
    assert "task_type" not in current


def test_observed_task_resets_context_on_exception() -> None:
    @observed_task("unit_demo")
    def run(db: object, task_id: str) -> dict[str, str]:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        run(None, "task-err")

    current = get_contextvars()
    assert "task_id" not in current
    assert "task_type" not in current
