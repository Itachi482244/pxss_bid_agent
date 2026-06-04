from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    BidSection,
    ComplianceEvidenceBinding,
    ComplianceItem,
    Document,
    DocumentChunk,
    DocumentVersion,
    EnterpriseMaterial,
    EnterpriseProfile,
    Project,
    ProjectMember,
    Tenant,
    User,
)
from scripts.seed_dev_data import (
    DEMO_TENANT_CODE,
    DEMO_USER_EXTERNAL_ID,
    MINGZHU_COMPANY_NAME,
    seed,
    seed_mingzhu_mock_enterprise_data,
)
from app.services.business_draft import BusinessDraftError
from app.services.context_pack import build_context_pack_preview, create_context_pack


def setup_module() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def _add_mingzhu_project_with_items() -> tuple[str, str]:
    now = datetime.now(UTC)
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.code == DEMO_TENANT_CODE))
        user = db.scalar(select(User).where(User.external_id == DEMO_USER_EXTERNAL_ID))
        assert tenant is not None
        assert user is not None

        suffix = uuid4().hex[:8]
        project = Project(
            tenant_id=tenant.id,
            name=f"明珠公寓老旧小区综合改造提升项目-资料包测试-{suffix}",
            purchaser="杭州市上城区九堡街道明珠公寓业委会（模拟）",
            agency="杭州城市更新咨询有限公司（模拟）",
            budget_amount=Decimal("3887963.00"),
            region_code="CN-330102",
            industry_code="building-renovation",
            status="pending_confirm",
            bid_deadline_at=datetime(2024, 12, 30, 6, 0, tzinfo=UTC),
            created_by=user.id,
        )
        db.add(project)
        db.flush()
        section = BidSection(
            tenant_id=tenant.id,
            project_id=project.id,
            code=f"mingzhu-test-{suffix}",
            name="一标段：明珠公寓老旧小区综合改造提升项目",
            budget_amount=Decimal("3887963.00"),
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
            title="明珠公寓测试交易文件",
            source_type="upload",
            original_filename="明珠公寓测试交易文件.pdf",
            content_type="application/pdf",
            file_ext="pdf",
            file_size=4096,
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
            change_reason="测试明珠公寓模拟资料绑定",
        )
        db.add(version)
        db.flush()
        document.current_version_id = version.id

        requirements = [
            (
                "qualification",
                "资质要求：(1)具备 施工总承包 建筑工程施工总承包 三级 资质；",
                "high",
                True,
            ),
            (
                "qualification",
                "资质要求：拟派项目负责人具有注册在潜在承包人单位的 建筑工程二级及以上 资格。",
                "high",
                True,
            ),
            (
                "scoring",
                "企业业绩：2019年1月1日以来承接过金额250万元及以上类似改造施工业绩。",
                "medium",
                False,
            ),
            (
                "mandatory_response",
                "履约担保：履约担保的金额为合同总价的2%。",
                "high",
                True,
            ),
            (
                "format",
                "响应文件的组成：法定代表人身份证明、授权委托书、诚信承诺书。",
                "medium",
                False,
            ),
            (
                "technical_response",
                "质量要求：符合现行国家有关工程施工验收规范和标准的合格要求。",
                "high",
                True,
            ),
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
                bbox_json=None,
                table_json=None,
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
                    normalized_requirement=f"mingzhu_mock_{index}",
                    response_suggestion="测试模拟资料自动绑定",
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
        db.commit()
        return str(project.id), str(section.id)


def test_seed_mingzhu_mock_enterprise_data_creates_materials_and_binds_items() -> None:
    project_id, section_id = _add_mingzhu_project_with_items()
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.code == DEMO_TENANT_CODE))
        user = db.scalar(select(User).where(User.external_id == DEMO_USER_EXTERNAL_ID))
        assert tenant is not None
        assert user is not None
        tenant_id = tenant.id

        summary = seed_mingzhu_mock_enterprise_data(db, tenant, user)
        preview = build_context_pack_preview(
            db,
            tenant_id=tenant.id,
            project_id=UUID(project_id),
            section_id=UUID(section_id),
            section_types=["bid_letter", "bid_commitment", "qualification_performance_summary"],
        )
        db.commit()
        assert summary["materials"] >= 10
        assert summary["bindings_created"] >= 6
        readiness_codes = {check["code"] for check in preview["readiness_json"]["checks"]}
        assert "qualification.decision_missing" in readiness_codes
        try:
            create_context_pack(
                db,
                tenant_id=tenant.id,
                project_id=UUID(project_id),
                section_id=UUID(section_id),
                actor_user_id=user.id,
                section_types=["bid_letter", "bid_commitment"],
            )
        except BusinessDraftError as exc:
            assert "资格预评估" in str(exc)
        else:
            raise AssertionError("ContextPack confirmation should require qualification decision")
        project_facts = preview["context_json"]["project_facts"]
        assert project_facts["project_manager_name"] == "王建安"
        assert project_facts["project_manager_id_no"] == "330102198806168888"
        assert project_facts["construction_period_days"] == 180
        assert project_facts["quality_standard"] == "合格"
        missing_fields = {
            item["field"]
            for item in preview["context_json"]["missing_facts"]
        }
        assert not {
            "project_manager_name",
            "project_manager_id_no",
            "construction_period_days",
            "quality_standard",
        } & missing_fields

    with SessionLocal() as db:
        profile = db.scalar(select(EnterpriseProfile).where(EnterpriseProfile.tenant_id == tenant_id))
        assert profile is not None
        assert profile.company_name == MINGZHU_COMPANY_NAME

        materials = db.scalars(
            select(EnterpriseMaterial).where(
                EnterpriseMaterial.tenant_id == tenant_id,
                EnterpriseMaterial.name.like("明珠公寓模拟-%"),
            )
        ).all()
        assert {material.material_type for material in materials} >= {
            "license",
            "qualification",
            "personnel",
            "performance",
            "commitment",
        }

        bindings = db.scalars(
            select(ComplianceEvidenceBinding).where(
                ComplianceEvidenceBinding.project_id == UUID(project_id),
                ComplianceEvidenceBinding.section_id == UUID(section_id),
                ComplianceEvidenceBinding.status == "active",
            )
        ).all()
        assert len(bindings) == 6
        bound_names = {binding.material_snapshot["name"] for binding in bindings}
        assert "明珠公寓模拟-建筑工程施工总承包二级资质" in bound_names
        assert "明珠公寓模拟-项目经理王建安注册建造师及安全B证" in bound_names
        assert "明珠公寓模拟-近三年老旧小区综合改造业绩" in bound_names
        assert "明珠公寓模拟-履约担保及低价风险差额担保承诺" in bound_names
        assert "明珠公寓模拟-施工组织及质量安全文明施工方案" in bound_names

        project = db.get(Project, UUID(project_id))
        section = db.get(BidSection, UUID(section_id))
        assert project is not None
        assert section is not None
        project.status = "archived"
        project.archived_at = datetime.now(UTC)
        section.status = "archived"
        db.commit()
