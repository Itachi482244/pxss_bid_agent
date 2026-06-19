from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    AgentReviewItem,
    AsyncTask,
    BidSection,
    ComplianceItem,
    Document,
    DocumentChunk,
    DocumentVersion,
    DraftBlock,
    EnterpriseMaterial,
    Project,
    ProjectMember,
    QualificationEvaluation,
    User,
)
from app.services import agent_assist as agent_assist_service
from app.services.agent.policy import DEFAULT_ACTION_POLICY
from app.services.agent.progress import budget_display_payload
from scripts.seed_dev_data import seed


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def _create_agent_golden_workspace() -> SimpleNamespace:
    token = uuid4().hex[:8]
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.status == "active"))
        assert user is not None
        project = Project(
            tenant_id=user.tenant_id,
            name=f"Agent Assist Golden {token}",
            purchaser="测试采购人",
            agency="测试代理",
            region_code="CN-HN",
            industry_code="cleanroom",
            status="pending_confirm",
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        db.add(
            ProjectMember(
                tenant_id=project.tenant_id,
                project_id=project.id,
                user_id=user.id,
                role_code="owner",
                status="active",
                created_by=user.id,
            )
        )
        section = BidSection(
            tenant_id=project.tenant_id,
            project_id=project.id,
            code=f"golden-{token}",
            name="Agent Assist Golden 标段",
            status="pending_confirm",
            created_by=user.id,
        )
        db.add(section)
        db.flush()

        document = Document(
            tenant_id=project.tenant_id,
            project_id=project.id,
            section_id=section.id,
            doc_type="tender",
            title=f"Agent Golden 招标文件 {token}",
            source_type="upload",
            original_filename=f"agent-golden-{token}.pdf",
            content_type="application/pdf",
            file_ext="pdf",
            file_size=128,
            sha256=hashlib.sha256(token.encode("utf-8")).hexdigest(),
            bucket=settings.minio_bucket,
            object_key=f"tests/agent-golden-{token}.pdf",
            status="available",
            created_by=user.id,
            acquired_at=datetime.now(UTC),
        )
        db.add(document)
        db.flush()
        version = DocumentVersion(
            tenant_id=project.tenant_id,
            document_id=document.id,
            version_no=1,
            version_label="v0.agent-golden",
            object_key=document.object_key,
            sha256=document.sha256,
            parse_status="succeeded",
            parser_name="agent-golden-test",
            parser_version="1.0",
            created_by=user.id,
        )
        db.add(version)
        db.flush()
        document.current_version_id = version.id
        chunk = DocumentChunk(
            tenant_id=project.tenant_id,
            document_id=document.id,
            document_version_id=version.id,
            section_id=section.id,
            chunk_index=1,
            page_no=3,
            heading_path="测试条款",
            content_text=f"Agent golden source {token}",
            content_hash=hashlib.sha256(f"chunk-{token}".encode("utf-8")).hexdigest(),
        )
        db.add(chunk)
        db.flush()

        material = EnterpriseMaterial(
            tenant_id=project.tenant_id,
            material_type="license",
            name=f"Agent Golden 可绑定证据 {token}",
            data_level="internal",
            verification_status="confirmed",
            evidence_text=f"Agent Golden 可绑定证据 {token}，用于资格证明。",
            file_name=f"agent-golden-material-{token}.pdf",
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(material)
        db.flush()

        def add_item(
            *,
            item_type: str,
            requirement_text: str,
            normalized_requirement: str,
            status: str,
            risk_level: str,
            is_mandatory: bool,
            confidence_score: Decimal,
        ) -> ComplianceItem:
            item = ComplianceItem(
                tenant_id=project.tenant_id,
                project_id=project.id,
                section_id=section.id,
                source_document_id=document.id,
                source_version_id=version.id,
                source_chunk_id=chunk.id,
                source_page_no=chunk.page_no,
                item_type=item_type,
                requirement_text=requirement_text,
                normalized_requirement=f"{normalized_requirement}_{token}",
                response_suggestion=f"Agent golden 响应建议 {token}",
                evidence_text=chunk.content_text,
                explanation_json={"source_quote": requirement_text[:40]},
                status=status,
                risk_level=risk_level,
                is_mandatory=is_mandatory,
                is_batch_confirm_allowed=risk_level != "high" and not is_mandatory,
                owner_user_id=user.id,
                confidence_score=confidence_score,
                created_by=user.id,
            )
            db.add(item)
            db.flush()
            return item

        low_item = add_item(
            item_type="reference_info",
            requirement_text=f"Agent golden 低风险参考信息 {token}",
            normalized_requirement="agent_golden_low",
            status="pending_confirm",
            risk_level="low",
            is_mandatory=False,
            confidence_score=Decimal("0.9500"),
        )
        missing_item = add_item(
            item_type="mandatory_response",
            requirement_text=f"Agent golden 缺少证据营业执照 {token}",
            normalized_requirement="agent_golden_missing",
            status="needs_material",
            risk_level="high",
            is_mandatory=True,
            confidence_score=Decimal("0.7400"),
        )
        qualification_item = add_item(
            item_type="qualification",
            requirement_text=f"Agent golden 可绑定证据资格证 {token}",
            normalized_requirement="agent_golden_qualification",
            status="needs_material",
            risk_level="medium",
            is_mandatory=True,
            confidence_score=Decimal("0.8200"),
        )
        technical_item = add_item(
            item_type="technical_response",
            requirement_text=f"Agent golden 技术参数响应 {token}",
            normalized_requirement="agent_golden_technical",
            status="pending_confirm",
            risk_level="medium",
            is_mandatory=False,
            confidence_score=Decimal("0.7800"),
        )
        draft_block = DraftBlock(
            tenant_id=project.tenant_id,
            project_id=project.id,
            section_id=section.id,
            block_type="paragraph",
            content_text=f"Agent golden 草稿 block {token}",
            sort_order=1,
            links_json={"compliance_item_id": str(technical_item.id)},
            risk_flags_json=[{"code": "needs_fact"}],
            review_status="needs_fact",
        )
        db.add(draft_block)
        db.commit()
        return SimpleNamespace(
            token=token,
            tenant_id=user.tenant_id,
            user_id=user.id,
            project_id=project.id,
            section_id=section.id,
            material_id=material.id,
            low_item_id=low_item.id,
            missing_item_id=missing_item.id,
            qualification_item_id=qualification_item.id,
            technical_item_id=technical_item.id,
            draft_block_id=draft_block.id,
        )


def _create_task(workspace: SimpleNamespace, *, steps: list[str] | None = None) -> UUID:
    run_key = f"agent-golden:{workspace.token}:{uuid4().hex[:8]}"
    with SessionLocal() as db:
        task = AsyncTask(
            tenant_id=workspace.tenant_id,
            project_id=workspace.project_id,
            section_id=workspace.section_id,
            task_type=agent_assist_service.AGENT_ASSIST_TASK_TYPE,
            status="pending",
            idempotency_key=f"agent-golden:{uuid4().hex}",
            progress=0,
            input_json={
                "run_key": run_key,
                "force": True,
                "scope": "section",
                "steps": steps
                or ["matrix_review", "evidence_binding", "qualification_technical"],
            },
            retry_count=0,
            max_retries=0,
            created_by=workspace.user_id,
        )
        db.add(task)
        db.commit()
        return task.id


def _patch_deterministic_agent_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    workspace: SimpleNamespace,
) -> None:
    def fake_search_material_hits(db, *, query: str, **_kwargs: object) -> list[SimpleNamespace]:
        if "可绑定证据" not in query:
            return []
        material = db.get(EnterpriseMaterial, workspace.material_id)
        assert material is not None
        return [
            SimpleNamespace(
                material=material,
                chunk=None,
                snippet=f"Agent golden 可绑定证据 {workspace.token}",
                confidence_score=Decimal("0.8700"),
                base_score=Decimal("0.8100"),
                rerank_score=None,
                recommend_reason="golden 语义命中",
            )
        ]

    def fake_run_qualification_evaluation(
        db,
        *,
        tenant_id,
        project_id,
        section_id,
        actor_user_id,
    ) -> list[QualificationEvaluation]:
        existing = db.scalar(
            select(QualificationEvaluation).where(
                QualificationEvaluation.tenant_id == tenant_id,
                QualificationEvaluation.compliance_item_id == workspace.qualification_item_id,
            )
        )
        if existing is not None:
            return [existing]
        item = db.get(ComplianceItem, workspace.qualification_item_id)
        assert item is not None
        evaluation = QualificationEvaluation(
            tenant_id=tenant_id,
            project_id=project_id,
            section_id=section_id,
            compliance_item_id=item.id,
            requirement_text=item.requirement_text,
            requirement_type="license",
            extracted_requirement={"token": workspace.token},
            evaluation_status="not_satisfied",
            risk_level="high",
            is_blocking=True,
            matched_rule_code="agent-golden",
            rule_version="1.0",
            reason="golden 阻断性资格风险",
            evidence_text=None,
            missing_materials=["资格证"],
            created_by=actor_user_id,
            updated_by=actor_user_id,
        )
        db.add(evaluation)
        db.flush()
        return [evaluation]

    monkeypatch.setattr(agent_assist_service, "search_material_hits", fake_search_material_hits)
    monkeypatch.setattr(
        agent_assist_service,
        "run_qualification_evaluation",
        fake_run_qualification_evaluation,
    )


def test_agent_assist_golden_semantic_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _create_agent_golden_workspace()
    _patch_deterministic_agent_dependencies(monkeypatch, workspace)
    task_id = _create_task(workspace)

    with SessionLocal() as db:
        summary = agent_assist_service.execute_agent_assist_task(db, task_id)

    assert summary["open_count"] >= 1
    assert summary["progress"]["percent"] == 100
    assert summary["progress"]["step"] == "finished"

    with SessionLocal() as db:
        task = db.get(AsyncTask, task_id)
        assert task is not None
        assert task.status == "succeeded"
        assert task.output_json is not None
        assert task.output_json["progress"]["percent"] == 100
        items = list(
            db.scalars(
                select(AgentReviewItem).where(
                    AgentReviewItem.async_task_id == task_id,
                    AgentReviewItem.run_key == summary["run_key"],
                )
            ).all()
        )

    semantic = {
        (
            item.step,
            item.action,
            item.status,
            item.severity,
            item.requires_human,
            item.object_type,
        )
        for item in items
    }
    assert (
        "matrix_review",
        "agent_matrix_low_risk_pass",
        "auto_passed",
        "low",
        False,
        "compliance_item",
    ) in semantic
    assert any(
        entry[:3] == ("matrix_review", "confirm_matrix_item", "open")
        and entry[3] == "critical"
        and entry[4] is True
        for entry in semantic
    )
    assert any(entry[:3] == ("evidence_binding", "missing_evidence", "open") for entry in semantic)
    assert any(
        entry[:3] == ("evidence_binding", "accept_evidence_binding", "open")
        for entry in semantic
    )
    assert (
        "qualification_technical",
        "review_qualification_evaluation",
        "open",
        "critical",
        True,
        "qualification_evaluation",
    ) in semantic
    assert any(
        entry[:3] == ("qualification_technical", "confirm_qualification_decision", "open")
        and entry[3] == "critical"
        for entry in semantic
    )
    assert any(
        entry[:3] == ("qualification_technical", "review_technical_response", "open")
        for entry in semantic
    )
    assert any(entry[:3] == ("qualification_technical", "review_draft_block", "open") for entry in semantic)


def test_agent_assist_plan_can_run_matrix_step_only() -> None:
    workspace = _create_agent_golden_workspace()
    task_id = _create_task(workspace, steps=["matrix_review"])

    with SessionLocal() as db:
        summary = agent_assist_service.execute_agent_assist_task(db, task_id)

    assert summary["matrix_review_count"] >= 1
    assert summary["evidence_binding_count"] == 0
    assert summary["qualification_technical_count"] == 0
    with SessionLocal() as db:
        steps = set(
            db.scalars(
                select(AgentReviewItem.step).where(AgentReviewItem.async_task_id == task_id)
            ).all()
        )
    assert steps == {"matrix_review"}


def test_agent_assist_partial_step_run_only_supersedes_enabled_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _create_agent_golden_workspace()
    _patch_deterministic_agent_dependencies(monkeypatch, workspace)
    first_task_id = _create_task(workspace)

    with SessionLocal() as db:
        first_summary = agent_assist_service.execute_agent_assist_task(db, first_task_id)
        assert first_summary["evidence_binding_count"] >= 1
        assert first_summary["qualification_technical_count"] >= 1

    matrix_only_task_id = _create_task(workspace, steps=["matrix_review"])

    with SessionLocal() as db:
        matrix_summary = agent_assist_service.execute_agent_assist_task(db, matrix_only_task_id)
        assert matrix_summary["matrix_review_count"] >= 1
        assert matrix_summary["evidence_binding_count"] == 0
        assert matrix_summary["qualification_technical_count"] == 0

        previous_items = list(
            db.scalars(
                select(AgentReviewItem).where(AgentReviewItem.async_task_id == first_task_id)
            ).all()
        )

    previous_status_by_step = {(item.step, item.status) for item in previous_items}
    assert ("matrix_review", "superseded") in previous_status_by_step
    assert any(
        item.step == "evidence_binding" and item.status == "open"
        for item in previous_items
    )
    assert any(
        item.step == "qualification_technical" and item.status == "open"
        for item in previous_items
    )


def test_action_policy_is_context_aware_for_source_verification() -> None:
    high_mandatory = SimpleNamespace(risk_level="high", is_mandatory=True, item_type="mandatory_response")
    low_reference = SimpleNamespace(risk_level="low", is_mandatory=False, item_type="reference_info")
    satisfied_evaluation = SimpleNamespace(
        evaluation_status="satisfied",
        is_blocking=False,
        risk_level="low",
    )
    blocking_evaluation = SimpleNamespace(
        evaluation_status="not_satisfied",
        is_blocking=True,
        risk_level="high",
    )

    assert DEFAULT_ACTION_POLICY.requires_source_verified("confirm_matrix_item", high_mandatory)
    assert not DEFAULT_ACTION_POLICY.requires_source_verified("confirm_matrix_item", low_reference)
    assert not DEFAULT_ACTION_POLICY.requires_source_verified(
        "confirm_qualification_decision",
        blocking_evaluation,
    )
    assert DEFAULT_ACTION_POLICY.automation_for("review_qualification_evaluation", satisfied_evaluation) == "auto"
    assert DEFAULT_ACTION_POLICY.automation_for("review_qualification_evaluation", blocking_evaluation) == "human"


def test_display_budget_preserves_authoritative_fields() -> None:
    payload = {
        "display_note": "x" * 40,
        "evidence_text": "y" * 40,
        "source_ref_json": {"source_chunk_id": str(uuid4()), "source_quote": "z" * 40},
        "items": [{"title": f"item-{index}"} for index in range(5)],
    }

    budgeted = budget_display_payload(payload, max_string_chars=12, max_list_items=2)

    assert budgeted["display_note"].startswith("x" * 12)
    assert "已截断" in budgeted["display_note"]
    assert budgeted["evidence_text"] == "y" * 40
    assert budgeted["source_ref_json"]["source_quote"] == "z" * 40
    assert budgeted["items"][-1] == {"_truncated": True, "omitted_count": 3}
