from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    AuditLog,
    BidSection,
    ComplianceItem,
    Document,
    DocumentChunk,
    DocumentVersion,
    EnterpriseMaterial,
    Project,
    ProjectMember,
    Tenant,
    User,
)
from app.services.material_retrieval import rebuild_material_chunks


DEMO_TENANT_CODE = "demo"
DEMO_USER_EXTERNAL_ID = "demo-admin"
DEMO_PROJECT_NAME = "智慧园区弱电工程投标"
DEMO_SECTION_CODE = "section-001"


def get_or_create_tenant(db: Session) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.code == DEMO_TENANT_CODE))
    if tenant is not None:
        return tenant

    tenant = Tenant(code=DEMO_TENANT_CODE, name="演示租户", status="active")
    db.add(tenant)
    db.flush()
    return tenant


def get_or_create_user(db: Session, tenant: Tenant) -> User:
    user = db.scalar(
        select(User).where(
            User.tenant_id == tenant.id,
            User.external_id == DEMO_USER_EXTERNAL_ID,
        )
    )
    if user is not None:
        return user

    user = User(
        tenant_id=tenant.id,
        external_id=DEMO_USER_EXTERNAL_ID,
        name="演示管理员",
        email="demo@example.com",
        mobile="13800000000",
        status="active",
    )
    db.add(user)
    db.flush()
    return user


def get_or_create_project(db: Session, tenant: Tenant, user: User) -> Project:
    project = db.scalar(
        select(Project).where(Project.tenant_id == tenant.id, Project.name == DEMO_PROJECT_NAME)
    )
    if project is not None:
        if project.status == "archived" or project.archived_at is not None:
            project.status = "pending_confirm"
            project.archived_at = None
            db.flush()
        return project

    project = Project(
        tenant_id=tenant.id,
        name=DEMO_PROJECT_NAME,
        purchaser="智慧园区建设单位",
        agency="示例招标代理公司",
        budget_amount=Decimal("1280000.00"),
        region_code="CN-3301",
        industry_code="weak-current",
        notice_url="https://example.com/tender/demo",
        status="pending_confirm",
        bid_deadline_at=datetime.now(UTC) + timedelta(days=14),
        created_by=user.id,
    )
    db.add(project)
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
    return project


def get_or_create_section(
    db: Session,
    tenant: Tenant,
    project: Project,
    user: User,
) -> BidSection:
    section = db.scalar(
        select(BidSection).where(
            BidSection.tenant_id == tenant.id,
            BidSection.project_id == project.id,
            BidSection.code == DEMO_SECTION_CODE,
        )
    )
    if section is not None:
        if section.status == "archived":
            section.status = "pending_confirm"
            db.flush()
        return section

    section = BidSection(
        tenant_id=tenant.id,
        project_id=project.id,
        code=DEMO_SECTION_CODE,
        name="一标段：综合布线与安防",
        budget_amount=Decimal("680000.00"),
        status="pending_confirm",
        bid_deadline_at=project.bid_deadline_at,
        created_by=user.id,
    )
    db.add(section)
    db.flush()
    return section


def get_or_create_document(
    db: Session,
    tenant: Tenant,
    project: Project,
    section: BidSection,
    user: User,
) -> tuple[Document, DocumentVersion, DocumentChunk, DocumentChunk]:
    document = db.scalar(
        select(Document).where(
            Document.tenant_id == tenant.id,
            Document.project_id == project.id,
            Document.section_id == section.id,
            Document.original_filename == "招标文件.pdf",
        )
    )
    if document is not None and document.current_version_id is not None:
        version = db.get(DocumentVersion, document.current_version_id)
        chunk = db.scalar(
            select(DocumentChunk).where(
                DocumentChunk.tenant_id == tenant.id,
                DocumentChunk.document_version_id == document.current_version_id,
                DocumentChunk.chunk_index == 1,
            )
        )
        if version is not None and chunk is not None:
            technical_chunk = db.scalar(
                select(DocumentChunk).where(
                    DocumentChunk.tenant_id == tenant.id,
                    DocumentChunk.document_version_id == document.current_version_id,
                    DocumentChunk.chunk_index == 2,
                )
            )
            if technical_chunk is None:
                technical_chunk = DocumentChunk(
                    tenant_id=tenant.id,
                    document_id=document.id,
                    document_version_id=version.id,
                    section_id=section.id,
                    chunk_index=2,
                    page_no=18,
                    heading_path="第五章/技术要求",
                    content_text="技术响应要求：洁净设备应提供产品样本、检测报告和安装调试验收方案，关键设备参数需满足招标文件要求。",
                    content_hash="3" * 64,
                    bbox_json={"page": 18, "x": 80, "y": 220, "w": 440, "h": 64},
                    table_json=None,
                )
                db.add(technical_chunk)
                db.flush()
            return document, version, chunk, technical_chunk

    now = datetime.now(UTC)
    document = Document(
        tenant_id=tenant.id,
        project_id=project.id,
        section_id=section.id,
        doc_type="tender",
        title="招标文件",
        source_type="public_url",
        source_site="示例公共资源交易平台",
        source_url="https://example.com/tender/demo/files/tender.pdf",
        original_filename="招标文件.pdf",
        content_type="application/pdf",
        file_ext="pdf",
        file_size=2048,
        sha256="0" * 64,
        bucket=settings.minio_bucket,
        object_key=f"tenant/{tenant.id}/project/{project.id}/documents/demo/tender.pdf",
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
        sha256="1" * 64,
        parse_status="frozen",
        parser_name="seed-parser",
        parser_version="0.1.0",
        frozen_at=now,
        created_by=user.id,
        change_reason="开发环境初始化样例",
    )
    db.add(version)
    db.flush()

    document.current_version_id = version.id

    chunk = DocumentChunk(
        tenant_id=tenant.id,
        document_id=document.id,
        document_version_id=version.id,
        section_id=section.id,
        chunk_index=1,
        page_no=12,
        heading_path="第三章/资格要求",
        content_text="投标人须提供有效营业执照，并加盖公章。",
        content_hash="2" * 64,
        bbox_json={"page": 12, "x": 80, "y": 120, "w": 420, "h": 48},
        table_json=None,
    )
    db.add(chunk)
    db.flush()

    technical_chunk = DocumentChunk(
        tenant_id=tenant.id,
        document_id=document.id,
        document_version_id=version.id,
        section_id=section.id,
        chunk_index=2,
        page_no=18,
        heading_path="第五章/技术要求",
        content_text="技术响应要求：洁净设备应提供产品样本、检测报告和安装调试验收方案，关键设备参数需满足招标文件要求。",
        content_hash="3" * 64,
        bbox_json={"page": 18, "x": 80, "y": 220, "w": 440, "h": 64},
        table_json=None,
    )
    db.add(technical_chunk)
    db.flush()
    return document, version, chunk, technical_chunk


def get_or_create_compliance_item(
    db: Session,
    tenant: Tenant,
    project: Project,
    section: BidSection,
    user: User,
    document: Document,
    version: DocumentVersion,
    chunk: DocumentChunk,
) -> ComplianceItem:
    item = db.scalar(
        select(ComplianceItem).where(
            ComplianceItem.tenant_id == tenant.id,
            ComplianceItem.project_id == project.id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.normalized_requirement == "provide_valid_business_license",
        )
    )
    if item is not None:
        return item

    item = ComplianceItem(
        tenant_id=tenant.id,
        project_id=project.id,
        section_id=section.id,
        source_document_id=document.id,
        source_version_id=version.id,
        source_chunk_id=chunk.id,
        source_page_no=chunk.page_no,
        item_type="qualification",
        requirement_text="投标人须提供有效营业执照，并加盖公章。",
        normalized_requirement="provide_valid_business_license",
        response_suggestion="从企业资质库补充营业执照扫描件，并确认有效期。",
        evidence_text=chunk.content_text,
        status="pending_confirm",
        risk_level="medium",
        is_mandatory=True,
        is_batch_confirm_allowed=False,
        owner_user_id=user.id,
        confidence_score=Decimal("0.9500"),
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    return item


def get_or_create_technical_response_item(
    db: Session,
    tenant: Tenant,
    project: Project,
    section: BidSection,
    user: User,
    document: Document,
    version: DocumentVersion,
    chunk: DocumentChunk,
) -> ComplianceItem:
    item = db.scalar(
        select(ComplianceItem).where(
            ComplianceItem.tenant_id == tenant.id,
            ComplianceItem.project_id == project.id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.normalized_requirement == "technical_clean_equipment_materials",
        )
    )
    if item is not None:
        return item

    item = ComplianceItem(
        tenant_id=tenant.id,
        project_id=project.id,
        section_id=section.id,
        source_document_id=document.id,
        source_version_id=version.id,
        source_chunk_id=chunk.id,
        source_page_no=chunk.page_no,
        item_type="technical_response",
        requirement_text=chunk.content_text,
        normalized_requirement="technical_clean_equipment_materials",
        response_suggestion="作为技术响应待确认项处理，核对产品样本、检测报告和安装调试验收方案是否齐备。",
        evidence_text=chunk.content_text,
        explanation_json={
            "rule_code": "RULE-TECHNICAL-RESPONSE",
            "rule_name": "技术响应要求识别",
            "rule_reason": "命中关键词：技术响应、洁净设备、检测报告、安装调试、验收，因此识别为技术响应。",
            "risk_reason": "该条款涉及技术参数、设备配置、安装调试或验收响应，v1.0 只形成待确认技术响应项，不自动生成技术标承诺。",
            "batch_confirm_reason": "高风险项不允许批量确认，必须逐条核验来源和响应证据。",
            "matched_keywords": ["技术响应", "洁净设备", "检测报告", "安装调试", "验收"],
            "extraction_provider": "seed",
        },
        status="pending_confirm",
        risk_level="high",
        is_mandatory=True,
        is_batch_confirm_allowed=False,
        owner_user_id=user.id,
        confidence_score=Decimal("0.8500"),
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    return item


def get_or_create_demo_material(
    db: Session,
    tenant: Tenant,
    user: User,
    *,
    material_type: str,
    name: str,
    evidence_text: str,
    structured_fields: dict[str, object],
) -> EnterpriseMaterial:
    material = db.scalar(
        select(EnterpriseMaterial).where(
            EnterpriseMaterial.tenant_id == tenant.id,
            EnterpriseMaterial.material_type == material_type,
            EnterpriseMaterial.name == name,
        )
    )
    if material is not None:
        return material

    material = EnterpriseMaterial(
        tenant_id=tenant.id,
        material_type=material_type,
        name=name,
        data_level="internal",
        verification_status="confirmed",
        structured_fields=structured_fields,
        evidence_text=evidence_text,
        created_by=user.id,
        updated_by=user.id,
    )
    db.add(material)
    db.flush()
    rebuild_material_chunks(db, material)
    return material


def seed_cleanroom_materials(db: Session, tenant: Tenant, user: User) -> None:
    get_or_create_demo_material(
        db,
        tenant,
        user,
        material_type="product_catalog",
        name="洁净设备产品目录示例",
        evidence_text="包含风淋室、传递窗、高效过滤器等洁净设备型号、技术参数和适用场景。",
        structured_fields={
            "industry": "cleanroom",
            "product_types": ["风淋室", "传递窗", "高效过滤器"],
            "mvp_stage": "v1.0_presale",
        },
    )
    get_or_create_demo_material(
        db,
        tenant,
        user,
        material_type="test_report",
        name="高效过滤器检测报告示例",
        evidence_text="检测报告载明过滤效率、阻力、检漏结果和适用洁净等级，可作为技术响应证据。",
        structured_fields={"report_type": "filter_test", "industry": "cleanroom"},
    )
    get_or_create_demo_material(
        db,
        tenant,
        user,
        material_type="technical_proposal",
        name="洁净工程安装调试验收方案示例",
        evidence_text="方案包含设备安装、单机调试、系统联调、洁净度检测和验收配合流程。",
        structured_fields={"proposal_type": "installation_commissioning_acceptance", "industry": "cleanroom"},
    )


def write_audit_log(
    db: Session,
    tenant: Tenant,
    project: Project,
    section: BidSection,
    user: User,
    item: ComplianceItem,
) -> None:
    existing = db.scalar(
        select(AuditLog).where(
            AuditLog.tenant_id == tenant.id,
            AuditLog.action == "seed.dev_data_created",
            AuditLog.object_id == item.id,
        )
    )
    if existing is not None:
        return

    db.add(
        AuditLog(
            tenant_id=tenant.id,
            project_id=project.id,
            section_id=section.id,
            actor_user_id=user.id,
            actor_type="system",
            action="seed.dev_data_created",
            object_type="compliance_item",
            object_id=item.id,
            after_json={
                "project": project.name,
                "section": section.name,
                "requirement": item.requirement_text,
            },
            reason="开发环境初始化样例数据",
            severity="info",
        )
    )


def seed() -> None:
    with SessionLocal() as db:
        tenant = get_or_create_tenant(db)
        user = get_or_create_user(db, tenant)
        project = get_or_create_project(db, tenant, user)
        section = get_or_create_section(db, tenant, project, user)
        document, version, chunk, technical_chunk = get_or_create_document(db, tenant, project, section, user)
        item = get_or_create_compliance_item(
            db,
            tenant,
            project,
            section,
            user,
            document,
            version,
            chunk,
        )
        technical_item = get_or_create_technical_response_item(
            db,
            tenant,
            project,
            section,
            user,
            document,
            version,
            technical_chunk,
        )
        seed_cleanroom_materials(db, tenant, user)
        write_audit_log(db, tenant, project, section, user, item)
        write_audit_log(db, tenant, project, section, user, technical_item)
        db.commit()
        print(
            "Seeded demo data: "
            f"tenant={tenant.code}, project={project.name}, section={section.name}"
        )


if __name__ == "__main__":
    seed()
