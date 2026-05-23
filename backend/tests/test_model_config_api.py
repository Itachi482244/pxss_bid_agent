from __future__ import annotations

import base64
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import AIModelConfig, AuditLog, ModelInvocationLog
from app.services.llm_gateway import chat_completion
from app.services.model_config_crypto import decrypt_api_key, encrypt_api_key, mask_api_key
from scripts.seed_dev_data import seed


TEST_KEY = base64.b64encode(b"1" * 32).decode("ascii")


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


@pytest.fixture(autouse=True)
def isolate_model_configs() -> None:
    with SessionLocal() as db:
        db.execute(delete(AIModelConfig))
        db.commit()
    yield
    with SessionLocal() as db:
        db.execute(delete(AIModelConfig))
        db.commit()


def test_api_key_encryption_roundtrip_and_mask(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "model_config_encryption_key", TEST_KEY)
    encrypted, masked, version = encrypt_api_key("sk-test-abcdef")
    assert encrypted.startswith("aesgcm:")
    assert masked == "sk-t****cdef"
    assert version == settings.model_config_encryption_key_version
    assert decrypt_api_key(encrypted) == "sk-test-abcdef"
    assert mask_api_key("12345678") == "12****78"


def test_model_config_requires_encryption_key_for_new_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "model_config_encryption_key", "")
    client = TestClient(app)

    response = client.put(
        "/api/v1/system/model-configs/chat",
        json={
            "provider": "deepseek",
            "base_url": "https://example.test/v1",
            "simple_model": "deepseek-chat",
            "complex_model": "deepseek-reasoner",
            "timeout_seconds": 20,
            "enabled": True,
            "api_key": "sk-no-key",
        },
    )

    assert response.status_code == 409
    assert "加密密钥不可用" in response.json()["detail"]


def test_model_config_create_read_update_clear_and_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "model_config_encryption_key", TEST_KEY)
    client = TestClient(app)

    create_response = client.put(
        "/api/v1/system/model-configs/chat",
        json={
            "provider": "deepseek",
            "base_url": "https://example.test/v1",
            "simple_model": "deepseek-v4-flash",
            "complex_model": "deepseek-v4-pro",
            "timeout_seconds": 20,
            "enabled": True,
            "api_key": "sk-created-secret",
        },
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["source"] == "db"
    assert payload["api_key_masked"] == "sk-c****cret"
    assert payload["has_api_key"] is True
    assert "sk-created-secret" not in str(payload)

    with SessionLocal() as db:
        config = db.scalar(select(AIModelConfig).where(AIModelConfig.capability == "chat"))
        assert config is not None
        assert config.api_key_encrypted
        assert decrypt_api_key(config.api_key_encrypted) == "sk-created-secret"
        assert db.scalar(select(AuditLog).where(AuditLog.action == "model_config.updated")) is not None

    update_response = client.put(
        "/api/v1/system/model-configs/chat",
        json={
            "provider": "deepseek",
            "base_url": "https://example.test/v1",
            "simple_model": "deepseek-v4-flash",
            "complex_model": "deepseek-v4-pro",
            "timeout_seconds": 21,
            "enabled": True,
        },
    )
    assert update_response.status_code == 200
    with SessionLocal() as db:
        config = db.scalar(select(AIModelConfig).where(AIModelConfig.capability == "chat"))
        assert config is not None
        assert decrypt_api_key(config.api_key_encrypted or "") == "sk-created-secret"

    clear_response = client.put(
        "/api/v1/system/model-configs/chat",
        json={
            "provider": "deepseek",
            "base_url": "https://example.test/v1",
            "simple_model": "deepseek-v4-flash",
            "complex_model": "deepseek-v4-pro",
            "timeout_seconds": 21,
            "enabled": True,
            "clear_api_key": True,
        },
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["has_api_key"] is False


def test_model_config_test_endpoint_uses_decrypted_key_and_updates_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "model_config_encryption_key", TEST_KEY)
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            calls.append({"url": url, "headers": headers, "json": json, "timeout": self.timeout})
            return FakeResponse()

    monkeypatch.setattr("app.api.v1.routes.system.httpx.Client", FakeClient)
    client = TestClient(app)
    client.put(
        "/api/v1/system/model-configs/chat",
        json={
            "provider": "deepseek",
            "base_url": "https://example.test/v1",
            "simple_model": "deepseek-v4-flash",
            "complex_model": "deepseek-v4-pro",
            "timeout_seconds": 19,
            "enabled": True,
            "api_key": "sk-test-endpoint",
        },
    )

    response = client.post("/api/v1/system/model-configs/chat/test", json={})
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert calls[0]["headers"]["Authorization"] == "Bearer sk-test-endpoint"  # type: ignore[index]
    assert calls[0]["url"] == "https://example.test/v1/chat/completions"

    with SessionLocal() as db:
        config = db.scalar(select(AIModelConfig).where(AIModelConfig.capability == "chat"))
        assert config is not None
        assert config.last_test_status == "success"
        assert db.scalar(select(AuditLog).where(AuditLog.action == "model_config.tested")) is not None


def test_llm_gateway_prefers_db_config_and_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "model_config_encryption_key", TEST_KEY)
    monkeypatch.setattr(settings, "llm_provider", "deepseek")
    monkeypatch.setattr(settings, "llm_api_key", "env-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://env.example/v1")
    monkeypatch.setattr(settings, "llm_simple_model", "env-simple")
    monkeypatch.setattr(settings, "llm_complex_model", "env-complex")
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(self, url: str, *, headers: dict[str, str], json: dict[str, object]) -> FakeResponse:
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr("app.services.llm_gateway.httpx.Client", FakeClient)
    client = TestClient(app)
    client.put(
        "/api/v1/system/model-configs/chat",
        json={
            "provider": "openai_compatible",
            "base_url": "https://db.example/v1",
            "simple_model": "db-simple",
            "complex_model": "db-complex",
            "timeout_seconds": 18,
            "enabled": True,
            "api_key": "db-key",
        },
    )

    with SessionLocal() as db:
        config = db.scalar(select(AIModelConfig).where(AIModelConfig.capability == "chat"))
        assert config is not None
        result = chat_completion(
            db,
            tenant_id=config.tenant_id,
            task_type="unit",
            prompt_version="unit@1",
            messages=[{"role": "user", "content": "hi"}],
            complexity="simple",
        )
        db.commit()
        assert result.model_name == "db-simple"
        assert calls[-1]["url"] == "https://db.example/v1/chat/completions"
        assert calls[-1]["headers"]["Authorization"] == "Bearer db-key"  # type: ignore[index]
        log = db.get(ModelInvocationLog, result.log_id)
        assert log is not None
        assert log.request_json["model_config_source"] == "db"

        config.enabled = False
        db.commit()
        result = chat_completion(
            db,
            tenant_id=config.tenant_id,
            task_type="unit",
            prompt_version="unit@1",
            messages=[{"role": "user", "content": "hi"}],
            complexity="complex",
        )
        db.commit()
        assert result.model_name == "env-complex"
        assert calls[-1]["url"] == "https://env.example/v1/chat/completions"
        assert calls[-1]["headers"]["Authorization"] == "Bearer env-key"  # type: ignore[index]
