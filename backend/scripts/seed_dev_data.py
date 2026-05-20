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
CLEANROOM_PROJECT_NAME = "洁净车间净化设备采购与安装项目"
CLEANROOM_SECTION_CODE = "cleanroom-001"


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
    verification_status: str = "confirmed",
    data_level: str = "internal",
    valid_until: date | None = None,
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
        data_level=data_level,
        verification_status=verification_status,
        valid_until=valid_until,
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
        write_audit_log(db, tenant, project, section, user, item)
        write_audit_log(db, tenant, project, section, user, technical_item)
        cleanroom_project = get_or_create_cleanroom_project(db, tenant, user)
        cleanroom_section = get_or_create_cleanroom_section(db, tenant, cleanroom_project, user)
        for cleanroom_item in cleanroom_items:
            write_audit_log(db, tenant, cleanroom_project, cleanroom_section, user, cleanroom_item)
        db.commit()
        print(
            "Seeded demo data: "
            f"tenant={tenant.code}, project={project.name}, cleanroom_project={cleanroom_project.name}"
        )


if __name__ == "__main__":
    seed()
