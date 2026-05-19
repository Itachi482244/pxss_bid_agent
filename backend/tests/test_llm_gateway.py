from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import AuditLog, BidSection, ModelInvocationLog, Project, Tenant, User
from app.services.llm_gateway import LLMGatewayError, chat_completion
from scripts.seed_dev_data import DEMO_PROJECT_NAME, DEMO_TENANT_CODE, DEMO_USER_EXTERNAL_ID, seed


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def _seed_context():
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.code == DEMO_TENANT_CODE))
        user = db.scalar(select(User).where(User.external_id == DEMO_USER_EXTERNAL_ID))
        project = db.scalar(select(Project).where(Project.name == DEMO_PROJECT_NAME))
        assert tenant is not None
        assert user is not None
        assert project is not None
        section = db.scalar(
            select(BidSection).where(
                BidSection.tenant_id == tenant.id,
                BidSection.project_id == project.id,
            )
        )
        assert section is not None
        return tenant.id, user.id, project.id, section.id


def test_llm_gateway_selects_complex_model_and_logs_success(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id, user_id, project_id, section_id = _seed_context()
    calls: list[dict[str, object]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {"content": '{"content_text":"已基于证据生成章节。"}'},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18},
            }

    class FakeClient:
        def __init__(self, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def post(
            self,
            url: str,
            *,
            headers: dict[str, str],
            json: dict[str, object],
        ) -> FakeResponse:
            calls.append({"url": url, "headers": headers, "json": json})
            return FakeResponse()

    monkeypatch.setattr(settings, "llm_provider", "deepseek")
    monkeypatch.setattr(settings, "llm_api_key", "test-api-key")
    monkeypatch.setattr(settings, "llm_base_url", "https://example.test/v1")
    monkeypatch.setattr(settings, "llm_simple_model", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "llm_complex_model", "deepseek-v4-pro")
    monkeypatch.setattr("app.services.llm_gateway.httpx.Client", FakeClient)

    with SessionLocal() as db:
        result = chat_completion(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            actor_user_id=user_id,
            actor_type="user",
            task_type="business_draft_generation",
            prompt_version="unit-test@2026-05-17",
            messages=[{"role": "user", "content": "请生成商务标章节"}],
            complexity="complex",
            response_format={"type": "json_object"},
        )
        db.commit()

        assert result.model_name == "deepseek-v4-pro"
        assert result.complexity == "complex"
        assert result.usage["total_tokens"] == 18
        assert calls[0]["json"]["model"] == "deepseek-v4-pro"  # type: ignore[index]

        log = db.get(ModelInvocationLog, result.log_id)
        assert log is not None
        assert log.status == "succeeded"
        assert log.model_name == "deepseek-v4-pro"
        assert log.total_tokens == 18
        assert "test-api-key" not in str(log.request_json)

        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.object_id == result.log_id,
                AuditLog.action == "model.invocation_succeeded",
            )
        )
        assert audit is not None
        assert audit.after_json is not None
        assert audit.after_json["model_name"] == "deepseek-v4-pro"


def test_llm_gateway_selects_simple_model_and_logs_skip(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id, user_id, project_id, section_id = _seed_context()

    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_simple_model", "deepseek-v4-flash")
    monkeypatch.setattr(settings, "llm_complex_model", "deepseek-v4-pro")

    with SessionLocal() as db:
        with pytest.raises(LLMGatewayError) as exc_info:
            chat_completion(
                db,
                tenant_id=tenant_id,
                project_id=project_id,
                section_id=section_id,
                actor_user_id=user_id,
                actor_type="user",
                task_type="compliance_matrix_generation",
                prompt_version="unit-test@2026-05-17",
                messages=[{"role": "user", "content": "抽取一个简单条款"}],
                complexity="simple",
                response_format={"type": "json_object"},
            )
        db.commit()

        assert exc_info.value.code == "LLM_NOT_CONFIGURED"
        log = db.get(ModelInvocationLog, exc_info.value.log_id)
        assert log is not None
        assert log.status == "skipped"
        assert log.model_name == "deepseek-v4-flash"
        assert log.complexity == "simple"

        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.object_id == log.id,
                AuditLog.action == "model.invocation_skipped",
            )
        )
        assert audit is not None
        assert audit.severity == "warning"
