"""MVP1.2 ContextPack exception-path regression tests.

Covers the convergence rules from the MVP1.2 plan section 8 that the happy-path
``test_mvp12_context_pack_api`` does not exercise:

- 缺证据 / 强制项未确认 -> readiness block.
- 限额设计等承诺性条款不误判为企业资料缺证据。
"""

from __future__ import annotations

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
    BidSection,
    ComplianceItem,
    Document,
    DocumentChunk,
    DocumentVersion,
    Project,
    ProjectMember,
    QualificationDecision,
    Tenant,
    User,
)
from app.services.context_pack import build_context_pack_preview
from app.services.business_draft import BusinessDraftError
from app.services.context_pack import _assert_context_pack_can_be_confirmed
from app.services.evidence_policy import (
    enterprise_evidence_not_required,
    requires_enterprise_evidence,
)
from scripts.seed_dev_data import DEMO_TENANT_CODE, DEMO_USER_EXTERNAL_ID, seed


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def _seed_blocking_project(recommendation: str = "go") -> tuple[str, str]:
    """Create a DEMO-tenant project whose ContextPack readiness is ``block``.

    Items are ``qualification``/high and left ``pending_confirm`` with no
    evidence binding, which deterministically triggers both
    ``evidence.missing_required`` and ``matrix.guard_items_unconfirmed``. A
    confirmed qualification decision is attached so the test proves that
    non-qualification readiness blockers still prevent confirmation.
    """
    now = datetime.now(UTC)
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.code == DEMO_TENANT_CODE))
        user = db.scalar(select(User).where(User.external_id == DEMO_USER_EXTERNAL_ID))
        assert tenant is not None and user is not None

        project = Project(
            tenant_id=tenant.id,
            name=f"MVP1.2异常路径测试项目-{suffix}",
            purchaser="模拟招标人",
            agency="模拟代理机构",
            budget_amount=Decimal("1000000.00"),
            region_code="CN-330102",
            industry_code="building-renovation",
            status="pending_confirm",
            bid_deadline_at=datetime(2026, 12, 30, 6, 0, tzinfo=UTC),
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        section = BidSection(
            tenant_id=tenant.id,
            project_id=project.id,
            code=f"mvp12-exc-{suffix}",
            name="一标段：MVP1.2 异常路径测试",
            budget_amount=Decimal("1000000.00"),
            status="pending_confirm",
            bid_deadline_at=project.bid_deadline_at,
            created_by=user.id,
        )
        db.add(section)
        db.flush()
        db.add(
            ProjectMember(
                tenant_id=tenant.id,
                project_id=project.id,
                user_id=user.id,
                role_code="owner",
                status="active",
                created_by=user.id,
            )
        )
        document = Document(
            tenant_id=tenant.id,
            project_id=project.id,
            section_id=section.id,
            doc_type="tender",
            title="异常路径测试交易文件",
            source_type="upload",
            original_filename="exc.pdf",
            content_type="application/pdf",
            file_ext="pdf",
            file_size=2048,
            sha256=f"{suffix:0<64}"[:64],
            bucket=settings.minio_bucket,
            object_key=f"tenant/{tenant.id}/project/{project.id}/documents/{suffix}/tender.pdf",
            status="available",
            created_by=user.id,
            acquired_at=now,
        )
        db.add(document)
        db.flush()
        version = DocumentVersion(
            tenant_id=tenant.id,
            document_id=document.id,
            version_no=1,
            version_label="v0.1",
            object_key=f"tenant/{tenant.id}/project/{project.id}/documents/{document.id}/v1/parsed.json",
            sha256=f"{suffix:1<64}"[:64],
            parse_status="frozen",
            parser_name="seed-test",
            parser_version="0.1.0",
            frozen_at=now,
            created_by=user.id,
            change_reason="异常路径测试",
        )
        db.add(version)
        db.flush()
        document.current_version_id = version.id

        requirements = [
            ("qualification", "资质要求：具备建筑工程施工总承包三级及以上资质。", "high", True),
            ("mandatory_response", "履约担保：履约担保金额为合同总价的2%。", "high", True),
        ]
        for index, (item_type, text, risk_level, is_mandatory) in enumerate(requirements, start=1):
            chunk = DocumentChunk(
                tenant_id=tenant.id,
                document_id=document.id,
                document_version_id=version.id,
                section_id=section.id,
                chunk_index=index,
                page_no=index,
                heading_path=f"测试条款/{index}",
                content_text=text,
                content_hash=f"{index:064x}"[-64:],
            )
            db.add(chunk)
            db.flush()
            db.add(
                ComplianceItem(
                    tenant_id=tenant.id,
                    project_id=project.id,
                    section_id=section.id,
                    source_document_id=document.id,
                    source_version_id=version.id,
                    source_chunk_id=chunk.id,
                    source_page_no=index,
                    item_type=item_type,
                    requirement_text=text,
                    normalized_requirement=f"mvp12_exc_{suffix}_{index}",
                    response_suggestion="测试响应建议",
                    evidence_text=text,
                    status="pending_confirm",
                    risk_level=risk_level,
                    is_mandatory=is_mandatory,
                    is_batch_confirm_allowed=False,
                    owner_user_id=user.id,
                    confidence_score=Decimal("0.9000"),
                    created_by=user.id,
                )
            )
        db.add(
            QualificationDecision(
                tenant_id=tenant.id,
                project_id=project.id,
                section_id=section.id,
                recommendation=recommendation,
                status="confirmed",
                summary="测试：人工确认参标建议",
                satisfied_count=1,
                blocking_count=0,
                missing_count=0,
                pending_count=0,
                created_by=user.id,
                confirmed_by=user.id,
                confirmed_at=now,
                confirm_reason="测试确认",
            )
        )
        db.commit()
        return str(project.id), str(section.id)


def test_readiness_flags_missing_evidence_and_unconfirmed_guard_items() -> None:
    project_id, section_id = _seed_blocking_project(recommendation="go")
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.code == DEMO_TENANT_CODE))
        assert tenant is not None
        preview = build_context_pack_preview(
            db,
            tenant_id=tenant.id,
            project_id=UUID(project_id),
            section_id=UUID(section_id),
            section_types=["bid_letter", "qualification_performance_summary"],
        )
        db.commit()

    codes = {check["code"] for check in preview["readiness_json"]["checks"]}
    assert "evidence.missing_required" in codes
    assert "matrix.guard_items_unconfirmed" in codes
    assert preview["readiness_status"] == "block"
    with pytest.raises(BusinessDraftError, match="仍存在阻断项"):
        _assert_context_pack_can_be_confirmed(preview)


def test_confirmed_no_go_is_allowed_as_context_pack_risk_snapshot() -> None:
    preview = {
        "readiness_json": {
            "status": "block",
            "checks": [
                {
                    "code": "qualification.no_go_confirmed",
                    "status": "block",
                    "summary": "已确认的参标建议为 No-Go。",
                    "action": "仅允许保存风险快照。",
                }
            ],
        }
    }

    _assert_context_pack_can_be_confirmed(preview)


def test_commitment_only_limit_design_does_not_require_enterprise_evidence() -> None:
    limit_design = SimpleNamespace(
        item_type="mandatory_response",
        requirement_text="并进行限额设计，确保施工图预算不超中标合同上限价",
        response_suggestion=None,
        status="confirmed",
        risk_level="high",
        is_mandatory=True,
        explanation_json={},
    )
    qualification = SimpleNamespace(
        item_type="qualification",
        requirement_text="施工单位须具备市政公用工程施工总承包二级及以上资质。",
        response_suggestion=None,
        status="confirmed",
        risk_level="high",
        is_mandatory=True,
        explanation_json={},
    )
    performance_bond = SimpleNamespace(
        item_type="mandatory_response",
        requirement_text="履约担保：履约担保金额为合同总价的2%。",
        response_suggestion=None,
        status="needs_material",
        risk_level="high",
        is_mandatory=True,
        explanation_json={},
    )

    assert enterprise_evidence_not_required(limit_design) is True
    assert requires_enterprise_evidence(limit_design) is False
    assert requires_enterprise_evidence(qualification) is True
    assert requires_enterprise_evidence(performance_bond) is True
