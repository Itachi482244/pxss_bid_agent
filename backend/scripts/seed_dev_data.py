from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    AuditLog,
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
from app.services.material_retrieval import rebuild_material_chunks


DEMO_TENANT_CODE = "demo"
DEMO_USER_EXTERNAL_ID = "demo-admin"
DEMO_PROJECT_NAME = "智慧园区弱电工程投标"
DEMO_SECTION_CODE = "section-001"
CLEANROOM_PROJECT_NAME = "洁净车间净化设备采购与安装项目"
CLEANROOM_SECTION_CODE = "cleanroom-001"
MINGZHU_PROJECT_KEYWORD = "明珠公寓"
MINGZHU_COMPANY_NAME = "杭州明筑更新工程有限公司"


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
        project.updated_at = datetime.now(UTC)
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
        section.updated_at = datetime.now(UTC)
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
            Document.source_url == "https://example.com/tender/demo/files/tender.pdf",
        )
    )
    if document is not None and document.current_version_id is not None:
        document.status = "available"
        document.doc_type = "tender"
        document.source_type = "public_url"
        document.source_site = "示例公共资源交易平台"
        document.source_url = "https://example.com/tender/demo/files/tender.pdf"
        document.file_ext = "pdf"
        document.bucket = settings.minio_bucket
        version = db.scalar(
            select(DocumentVersion).where(
                DocumentVersion.tenant_id == tenant.id,
                DocumentVersion.document_id == document.id,
                DocumentVersion.version_label == "v0.1",
            )
        ) or db.get(DocumentVersion, document.current_version_id)
        if version is not None and document.current_version_id != version.id:
            document.current_version_id = version.id
        target_version_id = version.id if version is not None else document.current_version_id
        chunk = db.scalar(
            select(DocumentChunk).where(
                DocumentChunk.tenant_id == tenant.id,
                DocumentChunk.document_version_id == target_version_id,
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
        item.source_document_id = document.id
        item.source_version_id = version.id
        item.source_chunk_id = chunk.id
        item.source_page_no = chunk.page_no
        item.item_type = "qualification"
        item.requirement_text = "投标人须提供有效营业执照，并加盖公章。"
        item.response_suggestion = "从企业资质库补充营业执照扫描件，并确认有效期。"
        item.evidence_text = chunk.content_text
        item.status = "pending_confirm"
        item.risk_level = "medium"
        item.is_mandatory = True
        item.is_batch_confirm_allowed = False
        item.owner_user_id = user.id
        item.deleted_at = None
        db.flush()
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
        item.source_document_id = document.id
        item.source_version_id = version.id
        item.source_chunk_id = chunk.id
        item.source_page_no = chunk.page_no
        item.item_type = "technical_response"
        item.requirement_text = chunk.content_text
        item.response_suggestion = "作为技术响应待确认项处理，核对产品样本、检测报告和安装调试验收方案是否齐备。"
        item.evidence_text = chunk.content_text
        item.status = "pending_confirm"
        item.risk_level = "high"
        item.is_mandatory = True
        item.is_batch_confirm_allowed = False
        item.owner_user_id = user.id
        item.deleted_at = None
        db.flush()
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


def get_or_create_cleanroom_project(db: Session, tenant: Tenant, user: User) -> Project:
    project = db.scalar(
        select(Project).where(Project.tenant_id == tenant.id, Project.name == CLEANROOM_PROJECT_NAME)
    )
    if project is not None:
        if project.status == "archived" or project.archived_at is not None:
            project.status = "pending_confirm"
            project.archived_at = None
        project.updated_at = datetime.now(UTC)
        db.flush()
        return project

    project = Project(
        tenant_id=tenant.id,
        name=CLEANROOM_PROJECT_NAME,
        purchaser="某生物医药企业（脱敏）",
        agency="某工程咨询有限公司（脱敏）",
        budget_amount=Decimal("2360000.00"),
        region_code="CN-3205",
        industry_code="cleanroom-equipment",
        notice_url="https://example.com/tender/cleanroom-demo",
        status="pending_confirm",
        bid_deadline_at=datetime.now(UTC) + timedelta(days=21),
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


def get_or_create_cleanroom_section(
    db: Session,
    tenant: Tenant,
    project: Project,
    user: User,
) -> BidSection:
    section = db.scalar(
        select(BidSection).where(
            BidSection.tenant_id == tenant.id,
            BidSection.project_id == project.id,
            BidSection.code == CLEANROOM_SECTION_CODE,
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
        code=CLEANROOM_SECTION_CODE,
        name="一标段：洁净设备采购、安装调试及验收",
        budget_amount=Decimal("2360000.00"),
        status="pending_confirm",
        bid_deadline_at=project.bid_deadline_at,
        created_by=user.id,
    )
    db.add(section)
    db.flush()
    return section


def get_or_create_cleanroom_document(
    db: Session,
    tenant: Tenant,
    project: Project,
    section: BidSection,
    user: User,
) -> tuple[Document, DocumentVersion, dict[str, DocumentChunk]]:
    document = db.scalar(
        select(Document).where(
            Document.tenant_id == tenant.id,
            Document.project_id == project.id,
            Document.section_id == section.id,
            Document.original_filename == "洁净车间净化设备采购与安装招标文件.pdf",
        )
    )
    if document is not None and document.current_version_id is not None:
        document.status = "available"
        document.doc_type = "tender"
        document.source_type = "public_url"
        document.source_site = "脱敏公共资源交易平台"
        document.source_url = "https://example.com/tender/cleanroom-demo/files/tender.pdf"
        document.file_ext = "pdf"
        document.bucket = settings.minio_bucket
        version = db.get(DocumentVersion, document.current_version_id)
        chunks = db.scalars(
            select(DocumentChunk)
            .where(DocumentChunk.document_version_id == document.current_version_id)
            .order_by(DocumentChunk.chunk_index.asc())
        ).all()
        if version is not None and chunks:
            return document, version, {chunk.heading_path or str(chunk.chunk_index): chunk for chunk in chunks}

    now = datetime.now(UTC)
    document = Document(
        tenant_id=tenant.id,
        project_id=project.id,
        section_id=section.id,
        doc_type="tender",
        title="洁净车间净化设备采购与安装招标文件",
        source_type="public_url",
        source_site="脱敏公共资源交易平台",
        source_url="https://example.com/tender/cleanroom-demo/files/tender.pdf",
        original_filename="洁净车间净化设备采购与安装招标文件.pdf",
        content_type="application/pdf",
        file_ext="pdf",
        file_size=4096,
        sha256="4" * 64,
        bucket=settings.minio_bucket,
        object_key=f"tenant/{tenant.id}/project/{project.id}/documents/cleanroom/tender.pdf",
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
        sha256="5" * 64,
        parse_status="frozen",
        parser_name="seed-parser",
        parser_version="0.1.0",
        frozen_at=now,
        created_by=user.id,
        change_reason="净化设备脱敏演示样本初始化",
    )
    db.add(version)
    db.flush()
    document.current_version_id = version.id

    chunk_specs = [
        (
            1,
            8,
            "第三章/资格要求",
            "投标人须提供有效营业执照、机电工程相关资质证明和近三年洁净工程或净化设备供货安装业绩。",
        ),
        (
            2,
            14,
            "第三章/实质性响应",
            "投标文件须提供净化设备产品目录、检测报告和安装调试验收方案；缺少任一项将按实质性不响应处理。",
        ),
        (
            3,
            20,
            "第五章/技术要求",
            "技术响应要求：洁净设备应满足洁净等级 ISO 7，送风量、过滤效率、压差控制和噪声指标须逐项响应。",
        ),
        (
            4,
            26,
            "第六章/评分办法",
            "评分办法：同类洁净工程业绩、检测报告完整性、安装调试验收方案和售后响应承诺为技术评分重点。",
        ),
        (
            5,
            3,
            "第一章/投标截止时间",
            "投标截止时间：以交易平台最终通知为准，逾期上传或未按格式加密的投标文件将被拒收。",
        ),
    ]
    chunks: dict[str, DocumentChunk] = {}
    for chunk_index, page_no, heading_path, content_text in chunk_specs:
        chunk = DocumentChunk(
            tenant_id=tenant.id,
            document_id=document.id,
            document_version_id=version.id,
            section_id=section.id,
            chunk_index=chunk_index,
            page_no=page_no,
            heading_path=heading_path,
            content_text=content_text,
            content_hash=f"{chunk_index + 5:x}" * 64,
            bbox_json={"page": page_no, "x": 80, "y": 100 + chunk_index * 30, "w": 460, "h": 58},
            table_json=None,
        )
        db.add(chunk)
        db.flush()
        chunks[heading_path] = chunk
    return document, version, chunks


def get_or_create_cleanroom_compliance_item(
    db: Session,
    tenant: Tenant,
    project: Project,
    section: BidSection,
    user: User,
    document: Document,
    version: DocumentVersion,
    chunk: DocumentChunk,
    *,
    normalized_requirement: str,
    item_type: str,
    requirement_text: str,
    response_suggestion: str,
    status: str,
    risk_level: str,
    is_mandatory: bool,
    rule_name: str,
) -> ComplianceItem:
    item = db.scalar(
        select(ComplianceItem).where(
            ComplianceItem.tenant_id == tenant.id,
            ComplianceItem.project_id == project.id,
            ComplianceItem.section_id == section.id,
            ComplianceItem.normalized_requirement == normalized_requirement,
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
        item_type=item_type,
        requirement_text=requirement_text,
        normalized_requirement=normalized_requirement,
        response_suggestion=response_suggestion,
        evidence_text=chunk.content_text,
        explanation_json={
            "rule_code": f"RULE-CLEANROOM-{item_type.upper()}",
            "rule_name": rule_name,
            "rule_reason": "净化设备脱敏演示样本初始化识别。",
            "risk_reason": response_suggestion,
            "matched_keywords": ["净化", "洁净", "检测报告", "安装调试", "验收"],
            "extraction_provider": "seed",
        },
        status=status,
        risk_level=risk_level,
        is_mandatory=is_mandatory,
        is_batch_confirm_allowed=False if risk_level == "high" or is_mandatory else True,
        owner_user_id=user.id,
        confidence_score=Decimal("0.8800"),
        created_by=user.id,
    )
    db.add(item)
    db.flush()
    return item


def seed_cleanroom_demo_project(db: Session, tenant: Tenant, user: User) -> list[ComplianceItem]:
    project = get_or_create_cleanroom_project(db, tenant, user)
    section = get_or_create_cleanroom_section(db, tenant, project, user)
    document, version, chunks = get_or_create_cleanroom_document(db, tenant, project, section, user)
    return [
        get_or_create_cleanroom_compliance_item(
            db,
            tenant,
            project,
            section,
            user,
            document,
            version,
            chunks["第三章/资格要求"],
            normalized_requirement="cleanroom_license_qualification_performance",
            item_type="qualification",
            requirement_text="投标人须提供有效营业执照、机电工程相关资质证明和近三年洁净工程或净化设备供货安装业绩。",
            response_suggestion="补充营业执照、机电工程资质和洁净工程业绩证明。",
            status="pending_confirm",
            risk_level="high",
            is_mandatory=True,
            rule_name="净化项目资格要求",
        ),
        get_or_create_cleanroom_compliance_item(
            db,
            tenant,
            project,
            section,
            user,
            document,
            version,
            chunks["第三章/实质性响应"],
            normalized_requirement="cleanroom_mandatory_product_report_proposal",
            item_type="mandatory_response",
            requirement_text="投标文件须提供净化设备产品目录、检测报告和安装调试验收方案；缺少任一项将按实质性不响应处理。",
            response_suggestion="该项故意保留缺证据风险，用于演示提交前核验阻塞。",
            status="needs_material",
            risk_level="high",
            is_mandatory=True,
            rule_name="净化项目强制证据要求",
        ),
        get_or_create_cleanroom_compliance_item(
            db,
            tenant,
            project,
            section,
            user,
            document,
            version,
            chunks["第五章/技术要求"],
            normalized_requirement="cleanroom_technical_iso7_airflow_pressure_noise",
            item_type="technical_response",
            requirement_text="技术响应要求：洁净设备应满足洁净等级 ISO 7，送风量、过滤效率、压差控制和噪声指标须逐项响应。",
            response_suggestion="v1.0 只形成技术响应待确认项，不生成技术标章节。",
            status="pending_confirm",
            risk_level="medium",
            is_mandatory=True,
            rule_name="净化技术响应要求",
        ),
        get_or_create_cleanroom_compliance_item(
            db,
            tenant,
            project,
            section,
            user,
            document,
            version,
            chunks["第六章/评分办法"],
            normalized_requirement="cleanroom_scoring_performance_report_acceptance_service",
            item_type="scoring",
            requirement_text="评分办法：同类洁净工程业绩、检测报告完整性、安装调试验收方案和售后响应承诺为技术评分重点。",
            response_suggestion="作为评分项处理，优先绑定业绩、检测报告和技术方案证据。",
            status="pending_confirm",
            risk_level="medium",
            is_mandatory=False,
            rule_name="净化技术评分项",
        ),
        get_or_create_cleanroom_compliance_item(
            db,
            tenant,
            project,
            section,
            user,
            document,
            version,
            chunks["第一章/投标截止时间"],
            normalized_requirement="cleanroom_deadline_platform_final_notice",
            item_type="deadline",
            requirement_text="投标截止时间以交易平台最终通知为准，逾期上传或未按格式加密的投标文件将被拒收。",
            response_suggestion="关键日期需人工确认，后续如导入补遗需重新检查矩阵版本。",
            status="pending_confirm",
            risk_level="high",
            is_mandatory=True,
            rule_name="投标截止时间风险",
        ),
    ]


def get_or_create_demo_material(
    db: Session,
    tenant: Tenant,
    user: User,
    *,
    material_type: str,
    name: str,
    evidence_text: str,
    structured_fields: dict[str, object],
    issuing_authority: str | None = None,
    certificate_no: str | None = None,
    holder_name: str | None = None,
    project_name: str | None = None,
    amount: str | None = None,
    valid_from: date | None = None,
    verification_status: str = "confirmed",
    data_level: str = "internal",
    valid_until: date | None = None,
    file_name: str | None = None,
) -> EnterpriseMaterial:
    material = db.scalar(
        select(EnterpriseMaterial).where(
            EnterpriseMaterial.tenant_id == tenant.id,
            EnterpriseMaterial.material_type == material_type,
            EnterpriseMaterial.name == name,
        )
    )
    if material is not None:
        material.issuing_authority = issuing_authority
        material.certificate_no = certificate_no
        material.holder_name = holder_name
        material.project_name = project_name
        material.amount = amount
        material.valid_from = valid_from
        material.data_level = data_level
        material.verification_status = verification_status
        material.valid_until = valid_until
        material.structured_fields = structured_fields
        material.evidence_text = evidence_text
        material.file_name = file_name
        material.updated_by = user.id
        material.updated_at = datetime.now(UTC)
        db.flush()
        rebuild_material_chunks(db, material)
        return material

    material = EnterpriseMaterial(
        tenant_id=tenant.id,
        material_type=material_type,
        name=name,
        issuing_authority=issuing_authority,
        certificate_no=certificate_no,
        holder_name=holder_name,
        project_name=project_name,
        amount=amount,
        valid_from=valid_from,
        data_level=data_level,
        verification_status=verification_status,
        valid_until=valid_until,
        structured_fields=structured_fields,
        evidence_text=evidence_text,
        file_name=file_name,
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
    get_or_create_demo_material(
        db,
        tenant,
        user,
        material_type="qualification",
        name="过期机电工程资质证书示例",
        evidence_text="该资质证书已过有效期，仅用于演示资料状态风险，不应直接作为正式投标主证据。",
        structured_fields={"industry": "cleanroom", "risk_demo": "expired_material"},
        verification_status="expired",
        valid_until=date(2024, 12, 31),
    )
    get_or_create_demo_material(
        db,
        tenant,
        user,
        material_type="technical_proposal",
        name="待确认洁净设备售后服务承诺示例",
        evidence_text="售后服务承诺仍处于草稿状态，需业务负责人确认后才能作为正式响应证据。",
        structured_fields={"industry": "cleanroom", "risk_demo": "draft_material"},
        verification_status="draft",
    )


def upsert_mingzhu_enterprise_profile(db: Session, tenant: Tenant, user: User) -> EnterpriseProfile:
    profile = db.scalar(select(EnterpriseProfile).where(EnterpriseProfile.tenant_id == tenant.id))
    if profile is None:
        profile = EnterpriseProfile(
            tenant_id=tenant.id,
            company_name=MINGZHU_COMPANY_NAME,
            unified_social_credit_code="91330110MA2MZJG001",
            legal_representative="陈明",
            registered_address="浙江省杭州市上城区九堡街道九沙大道88号1幢801室",
            business_scope=(
                "房屋建筑工程、市政公用工程、建筑装修装饰工程、老旧小区综合改造工程施工；"
                "建筑立面及屋面整治、室外附属工程、弱电及消防配套工程施工；工程项目管理。"
            ),
            region_preferences=["浙江省", "杭州市", "上城区"],
            industry_preferences=["建筑工程", "老旧小区改造", "城市更新"],
            forbidden_rules=[],
            created_by=user.id,
            updated_by=user.id,
        )
        db.add(profile)
        db.flush()
        return profile

    profile.company_name = MINGZHU_COMPANY_NAME
    profile.unified_social_credit_code = "91330110MA2MZJG001"
    profile.legal_representative = "陈明"
    profile.registered_address = "浙江省杭州市上城区九堡街道九沙大道88号1幢801室"
    profile.business_scope = (
        "房屋建筑工程、市政公用工程、建筑装修装饰工程、老旧小区综合改造工程施工；"
        "建筑立面及屋面整治、室外附属工程、弱电及消防配套工程施工；工程项目管理。"
    )
    profile.region_preferences = ["浙江省", "杭州市", "上城区"]
    profile.industry_preferences = ["建筑工程", "老旧小区改造", "城市更新"]
    profile.forbidden_rules = []
    profile.updated_by = user.id
    profile.updated_at = datetime.now(UTC)
    db.flush()
    return profile


def seed_mingzhu_enterprise_materials(
    db: Session,
    tenant: Tenant,
    user: User,
) -> dict[str, EnterpriseMaterial]:
    common_fields = {
        "company_name": MINGZHU_COMPANY_NAME,
        "project_fit": "明珠公寓老旧小区综合改造提升项目",
        "data_source": "seed_dev_data.mock",
        "is_mock": True,
    }
    return {
        "license": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="license",
            name="明珠公寓模拟-营业执照",
            issuing_authority="杭州市市场监督管理局",
            certificate_no="91330110MA2MZJG001",
            holder_name=MINGZHU_COMPANY_NAME,
            valid_from=date(2021, 5, 18),
            valid_until=date(2036, 5, 17),
            evidence_text=(
                "营业执照载明企业主体为杭州明筑更新工程有限公司，统一社会信用代码"
                "91330110MA2MZJG001，经营范围包含房屋建筑工程、建筑装修装饰工程、"
                "老旧小区综合改造工程施工，可覆盖明珠公寓项目主体资格、注册资金和营业范围响应。"
            ),
            structured_fields=common_fields
            | {
                "registered_capital": "6000万元人民币",
                "business_scope_keywords": ["建筑工程", "老旧小区改造", "建筑装修装饰", "城市更新"],
            },
            file_name="mock_mingzhu_business_license.pdf",
        ),
        "construction_qualification": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="qualification",
            name="明珠公寓模拟-建筑工程施工总承包二级资质",
            issuing_authority="浙江省住房和城乡建设厅",
            certificate_no="D233MZ2026001",
            holder_name=MINGZHU_COMPANY_NAME,
            valid_from=date(2024, 1, 1),
            valid_until=date(2029, 12, 31),
            evidence_text=(
                "建筑业企业资质证书载明资质类别为建筑工程施工总承包二级，有效期至2029-12-31，"
                "等级高于明珠公寓项目要求的建筑工程施工总承包三级资质。"
            ),
            structured_fields=common_fields
            | {
                "qualification_category": "建筑工程施工总承包",
                "grade": "二级",
                "meets_min_grade": "三级",
            },
            file_name="mock_mingzhu_construction_qualification.pdf",
        ),
        "safety_license": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="qualification",
            name="明珠公寓模拟-安全生产许可证",
            issuing_authority="浙江省住房和城乡建设厅",
            certificate_no="(浙)JZ安许证字[2026]019876",
            holder_name=MINGZHU_COMPANY_NAME,
            valid_from=date(2026, 1, 1),
            valid_until=date(2029, 12, 31),
            evidence_text=(
                "安全生产许可证处于有效期，许可范围覆盖建筑施工，可作为施工安全资格响应材料。"
            ),
            structured_fields=common_fields | {"certificate_type": "安全生产许可证"},
            file_name="mock_mingzhu_safety_license.pdf",
        ),
        "project_manager": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="personnel",
            name="明珠公寓模拟-项目经理王建安注册建造师及安全B证",
            issuing_authority="浙江省住房和城乡建设厅",
            certificate_no="浙2332021202308888 / 浙建安B(2023)3108888",
            holder_name="王建安",
            valid_from=date(2023, 4, 12),
            valid_until=date(2028, 12, 31),
            evidence_text=(
                "王建安为本单位在册人员，具备建筑工程专业二级注册建造师资格、安全生产考核合格B证，"
                "注册单位为杭州明筑更新工程有限公司；当前无在建项目锁定记录。"
            ),
            structured_fields=common_fields
            | {
                "person_name": "王建安",
                "role": "拟派项目负责人",
                "registered_major": "建筑工程",
                "constructor_grade": "二级",
                "safety_b_certificate": "浙建安B(2023)3108888",
                "no_active_project_commitment": True,
                "id_no": "330102198806168888",
            },
            file_name="mock_mingzhu_project_manager_certificates.pdf",
        ),
        "senior_title": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="personnel",
            name="明珠公寓模拟-项目经理高级工程师职称证书",
            issuing_authority="浙江省人力资源和社会保障厅",
            certificate_no="G3301MZ20220088",
            holder_name="王建安",
            valid_from=date(2022, 9, 20),
            evidence_text="王建安具备建筑工程管理高级工程师职称，可覆盖评分办法中的项目经理高级职称加分项。",
            structured_fields=common_fields
            | {"person_name": "王建安", "title": "高级工程师", "major": "建筑工程管理"},
            file_name="mock_mingzhu_project_manager_senior_title.pdf",
        ),
        "performance": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="performance",
            name="明珠公寓模拟-近三年老旧小区综合改造业绩",
            issuing_authority="杭州市城市更新建设单位（模拟）",
            certificate_no="HT-MZ-JG-2024-011",
            holder_name=MINGZHU_COMPANY_NAME,
            project_name="杭州市翠苑三区老旧小区综合改造提升工程",
            amount="868.42万元",
            valid_from=date(2024, 3, 15),
            evidence_text=(
                "合同签订时间为2024-03-15，合同金额868.42万元，工程内容包含建筑立面整治、"
                "屋面防水修缮、楼道公共部位修缮和室外附属改造；竣工验收结论为合格，"
                "满足2019年1月1日以来金额250万元及以上类似改造施工业绩评分要求。"
            ),
            structured_fields=common_fields
            | {
                "performance_type": "老旧小区综合改造",
                "contract_signed_at": "2024-03-15",
                "acceptance_status": "合格",
                "amount_cny": 8684200,
            },
            file_name="mock_mingzhu_similar_performance.pdf",
        ),
        "iso_system": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="qualification",
            name="明珠公寓模拟-质量环境职业健康安全三体系认证",
            issuing_authority="中建认证中心（模拟）",
            certificate_no="QEO-MZ-2026-001",
            holder_name=MINGZHU_COMPANY_NAME,
            valid_from=date(2026, 1, 10),
            valid_until=date(2029, 1, 9),
            evidence_text=(
                "企业通过ISO 9001质量管理体系、ISO 14001环境管理体系、ISO 45001职业健康安全管理体系认证，"
                "三项证书均处于有效期。"
            ),
            structured_fields=common_fields
            | {"certifications": ["ISO 9001", "ISO 14001", "ISO 45001"]},
            file_name="mock_mingzhu_iso_certificates.pdf",
        ),
        "credit_commitment": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="commitment",
            name="明珠公寓模拟-信用与无重大违法记录承诺",
            evidence_text=(
                "企业承诺不存在被依法暂停或取消投标资格、被限制参与上城区限额以下公共资源交易活动、"
                "失信被执行、重大违法、重大质量安全事故或其他禁止参标情形。"
            ),
            structured_fields=common_fields
            | {"commitment_scope": ["信用", "失信", "黑名单", "处罚", "重大违法", "禁止参标"]},
            file_name="mock_mingzhu_credit_commitment.pdf",
        ),
        "financial_tax_social_security": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="other",
            name="明珠公寓模拟-财务纳税及社保证明",
            issuing_authority="主管税务机关及社保经办机构（模拟）",
            holder_name=MINGZHU_COMPANY_NAME,
            valid_from=date(2026, 5, 1),
            evidence_text=(
                "企业2025年度财务状况正常，依法纳税；拟派项目负责人王建安及授权代理人李文的社保"
                "由杭州明筑更新工程有限公司连续缴纳，覆盖投标文件编制期。"
            ),
            structured_fields=common_fields
            | {
                "tax_status": "正常",
                "social_security_staff": ["王建安", "李文"],
                "financial_report_years": ["2023", "2024", "2025"],
            },
            file_name="mock_mingzhu_tax_social_security.pdf",
        ),
        "authorization": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="commitment",
            name="明珠公寓模拟-法定代表人身份证明及授权委托书",
            holder_name="陈明 / 李文",
            evidence_text=(
                "法定代表人为陈明；授权代理人为李文，授权范围包含明珠公寓老旧小区综合改造提升项目"
                "响应文件签署、递交、澄清、合同签订等事项，并附身份证明材料。"
            ),
            structured_fields=common_fields
            | {
                "legal_representative": "陈明",
                "legal_representative_title": "执行董事兼总经理",
                "authorized_agent": "李文",
                "authorized_agent_name": "李文",
                "authorization_project": "明珠公寓",
            },
            file_name="mock_mingzhu_authorization_letter.pdf",
        ),
        "bid_security": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="commitment",
            name="明珠公寓模拟-履约担保及低价风险差额担保承诺",
            evidence_text=(
                "企业承诺成交后按交易文件要求提交合同总价2%的履约担保；如成交价低于风险控制价，"
                "将按要求提交成交价与风险控制价差额担保，担保形式接受银行保函、保证保险、担保公司担保或基本账户转账。"
            ),
            structured_fields=common_fields
            | {
                "performance_bond": "合同总价的2%",
                "performance_bond_ratio": "2%",
                "low_price_difference_bond": True,
                "bid_security_amount": "交易保证金：无",
                "bid_security_form": "无",
            },
            file_name="mock_mingzhu_performance_bond_commitment.pdf",
        ),
        "response_commitment": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="commitment",
            name="明珠公寓模拟-商务响应及工期质量承诺",
            evidence_text=(
                "企业承诺响应明珠公寓项目全部商务实质性条款：计划工期180日历天，质量标准为符合现行国家"
                "有关工程施工验收规范和标准的合格要求，承包方式为包工、包料、包工期、包质量、包安全、包文明施工。"
            ),
            structured_fields=common_fields
            | {
                "construction_period_days": 180,
                "quality_standard": "合格",
                "project_scope": "明珠公寓建筑立面、屋面、楼道公共部位及室外附属综合改造提升",
                "warranty_period": "按交易文件及工程质量保修书执行，缺陷责任期不低于24个月",
                "response_scope": "商务实质性响应",
            },
            file_name="mock_mingzhu_business_response_commitment.pdf",
        ),
        "paper_file_commitment": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="commitment",
            name="明珠公寓模拟-电子及纸质响应文件一致性承诺",
            evidence_text=(
                "企业承诺按交易文件要求使用投标工具制作并递交电子响应文件；成交后7个工作日内补交与电子"
                "响应文件一致的纸质正本1份、副本3份及电子光盘，并包含施工组织设计文件。"
            ),
            structured_fields=common_fields
            | {"paper_original_count": 1, "paper_copy_count": 3, "electronic_file_consistency": True},
            file_name="mock_mingzhu_file_consistency_commitment.pdf",
        ),
        "construction_quality_plan": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="technical_proposal",
            name="明珠公寓模拟-施工组织及质量安全文明施工方案",
            evidence_text=(
                "方案覆盖老旧小区改造施工组织、居民出行协调、建筑立面及屋面整治、成品保护、质量验收、"
                "安全文明施工和应急响应措施，可支撑质量、安全、文明施工及施工组织设计相关响应。"
            ),
            structured_fields=common_fields
            | {"proposal_scope": ["施工组织设计", "质量验收", "安全文明施工", "居民协调"]},
            file_name="mock_mingzhu_construction_quality_plan.pdf",
        ),
        "non_consortium": get_or_create_demo_material(
            db,
            tenant,
            user,
            material_type="commitment",
            name="明珠公寓模拟-非联合体及不分包承诺",
            evidence_text=(
                "企业承诺本项目以独立投标人身份参与，不组成联合体；成交后不违法分包、转包，并按合同约定"
                "组织自有项目管理团队履约。"
            ),
            structured_fields=common_fields
            | {"consortium": False, "is_consortium": False, "illegal_subcontracting": False},
            file_name="mock_mingzhu_non_consortium_commitment.pdf",
        ),
    }


def _mingzhu_material_snapshot(material: EnterpriseMaterial) -> dict[str, object]:
    return {
        "id": str(material.id),
        "material_type": material.material_type,
        "name": material.name,
        "issuing_authority": material.issuing_authority,
        "certificate_no": material.certificate_no,
        "holder_name": material.holder_name,
        "project_name": material.project_name,
        "amount": material.amount,
        "valid_from": material.valid_from.isoformat() if material.valid_from else None,
        "valid_until": material.valid_until.isoformat() if material.valid_until else None,
        "data_level": material.data_level,
        "verification_status": material.verification_status,
        "structured_fields": material.structured_fields,
        "evidence_text": material.evidence_text,
        "file_name": material.file_name,
        "sha256": material.sha256,
    }


def _mingzhu_material_key_for_item(item: ComplianceItem) -> str:
    text = f"{item.requirement_text}\n{item.normalized_requirement or ''}\n{item.response_suggestion or ''}"
    if "联合体" in text or "分包" in text:
        return "non_consortium"
    if "安全生产许可证" in text:
        return "safety_license"
    if "营业执照" in text:
        return "license"
    if "注册资金" in text or "注册资本" in text:
        return "license"
    if "三体系" in text or "管理体系认证" in text or "ISO" in text:
        return "iso_system"
    if "职称" in text:
        return "senior_title"
    if any(signal in text for signal in ("项目负责人", "项目经理", "建造师", "安全B证", "B证", "在建")):
        return "project_manager"
    if "业绩" in text or "类似工程" in text or "类似改造" in text:
        return "performance"
    if "资质" in text or "施工总承包" in text:
        return "construction_qualification"
    if any(signal in text for signal in ("信用", "失信", "黑名单", "处罚", "重大违法", "限制参与", "禁止参标")):
        return "credit_commitment"
    if any(signal in text for signal in ("社保", "纳税", "财务")):
        return "financial_tax_social_security"
    if any(signal in text for signal in ("法定代表人", "授权委托", "代理人", "身份证明")):
        return "authorization"
    if any(signal in text for signal in ("履约担保", "保证金", "保函", "保证保险", "风险控制价", "差额担保")):
        return "bid_security"
    if any(signal in text for signal in ("电子响应文件", "纸质响应文件", "响应文件的组成", "光盘", "投标工具")):
        return "paper_file_commitment"
    if item.item_type == "technical_response" or any(
        signal in text for signal in ("施工组织", "质量", "验收", "安全", "文明施工", "成品保护")
    ):
        return "construction_quality_plan"
    if any(signal in text for signal in ("工期", "期限", "承包方式", "响应函", "报价", "合同总价")):
        return "response_commitment"
    if item.item_type == "format":
        return "paper_file_commitment"
    if item.item_type == "scoring":
        return "performance"
    if item.item_type == "qualification":
        return "construction_qualification"
    return "response_commitment"


def _bind_mingzhu_evidence(
    db: Session,
    tenant: Tenant,
    user: User,
    project: Project,
    section: BidSection,
    item: ComplianceItem,
    material: EnterpriseMaterial,
) -> str:
    existing = db.scalar(
        select(ComplianceEvidenceBinding).where(
            ComplianceEvidenceBinding.tenant_id == tenant.id,
            ComplianceEvidenceBinding.compliance_item_id == item.id,
            ComplianceEvidenceBinding.enterprise_material_id == material.id,
            ComplianceEvidenceBinding.status == "active",
        )
    )
    evidence_text = (
        f"{material.evidence_text or material.name}\n"
        f"适配条款：{item.requirement_text[:360]}"
    )
    bind_reason = "明珠公寓演示数据：按条款关键词自动匹配模拟企业资料"
    if existing is not None:
        existing.project_id = project.id
        existing.section_id = section.id
        existing.evidence_text = evidence_text
        existing.material_snapshot = _mingzhu_material_snapshot(material)
        existing.confidence_score = Decimal("0.9300")
        existing.bind_reason = bind_reason
        return "updated"

    active_binding = db.scalar(
        select(ComplianceEvidenceBinding).where(
            ComplianceEvidenceBinding.tenant_id == tenant.id,
            ComplianceEvidenceBinding.compliance_item_id == item.id,
            ComplianceEvidenceBinding.status == "active",
        )
    )
    if active_binding is not None:
        return "skipped"

    db.add(
        ComplianceEvidenceBinding(
            tenant_id=tenant.id,
            project_id=project.id,
            section_id=section.id,
            compliance_item_id=item.id,
            enterprise_material_id=material.id,
            evidence_text=evidence_text,
            material_snapshot=_mingzhu_material_snapshot(material),
            confidence_score=Decimal("0.9300"),
            bind_reason=bind_reason,
            status="active",
            created_by=user.id,
        )
    )
    return "created"


def seed_mingzhu_mock_enterprise_data(db: Session, tenant: Tenant, user: User) -> dict[str, int]:
    upsert_mingzhu_enterprise_profile(db, tenant, user)
    materials = seed_mingzhu_enterprise_materials(db, tenant, user)
    summary = {
        "projects": 0,
        "sections": 0,
        "materials": len(materials),
        "bindings_created": 0,
        "bindings_updated": 0,
        "bindings_skipped": 0,
    }
    projects = db.scalars(
        select(Project).where(
            Project.tenant_id == tenant.id,
            Project.name.contains(MINGZHU_PROJECT_KEYWORD),
            Project.archived_at.is_(None),
        )
    ).all()
    for project in projects:
        summary["projects"] += 1
        sections = db.scalars(
            select(BidSection).where(
                BidSection.tenant_id == tenant.id,
                BidSection.project_id == project.id,
                BidSection.status != "archived",
            )
        ).all()
        for section in sections:
            summary["sections"] += 1
            items = db.scalars(
                select(ComplianceItem).where(
                    ComplianceItem.tenant_id == tenant.id,
                    ComplianceItem.project_id == project.id,
                    ComplianceItem.section_id == section.id,
                    ComplianceItem.deleted_at.is_(None),
                )
            ).all()
            for item in items:
                material = materials[_mingzhu_material_key_for_item(item)]
                result = _bind_mingzhu_evidence(db, tenant, user, project, section, item, material)
                if result == "created":
                    summary["bindings_created"] += 1
                elif result == "updated":
                    summary["bindings_updated"] += 1
                else:
                    summary["bindings_skipped"] += 1
    return summary


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
        cleanroom_items = seed_cleanroom_demo_project(db, tenant, user)
        seed_cleanroom_materials(db, tenant, user)
        mingzhu_summary = seed_mingzhu_mock_enterprise_data(db, tenant, user)
        write_audit_log(db, tenant, project, section, user, item)
        write_audit_log(db, tenant, project, section, user, technical_item)
        cleanroom_project = get_or_create_cleanroom_project(db, tenant, user)
        cleanroom_section = get_or_create_cleanroom_section(db, tenant, cleanroom_project, user)
        for cleanroom_item in cleanroom_items:
            write_audit_log(db, tenant, cleanroom_project, cleanroom_section, user, cleanroom_item)
        db.commit()
        print(
            "Seeded demo data: "
            f"tenant={tenant.code}, project={project.name}, cleanroom_project={cleanroom_project.name}, "
            f"mingzhu_projects={mingzhu_summary['projects']}, "
            f"mingzhu_bindings_created={mingzhu_summary['bindings_created']}, "
            f"mingzhu_bindings_updated={mingzhu_summary['bindings_updated']}"
        )


if __name__ == "__main__":
    seed()
