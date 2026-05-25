from __future__ import annotations

import hashlib
from io import BytesIO
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from docx import Document as DocxDocument
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import AuditLog, ComplianceItem, Document, DocumentChunk, DocumentVersion, Project, User
from app.services.file_acquisition import DownloadedFile
from scripts.seed_dev_data import seed


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def get_seed_project_and_section(client: TestClient) -> tuple[str, str]:
    projects = client.get("/api/v1/projects", params={"limit": 200}).json()
    project = next(item for item in projects if item["name"] == "智慧园区弱电工程投标")
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    return project["id"], sections[0]["id"]


def test_project_read_api_returns_seeded_workspace() -> None:
    client = TestClient(app)

    projects_response = client.get("/api/v1/projects", params={"limit": 200})
    assert projects_response.status_code == 200
    projects = projects_response.json()
    assert len(projects) >= 1
    project = next(item for item in projects if item["name"] == "智慧园区弱电工程投标")
    assert project["section_count"] == 1
    assert project["compliance_item_count"] >= 1
    assert project["pending_confirm_count"] >= 1

    project_id = project["id"]
    detail_response = client.get(f"/api/v1/projects/{project_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["notice_url"] == "https://example.com/tender/demo"

    sections_response = client.get(f"/api/v1/projects/{project_id}/sections")
    assert sections_response.status_code == 200
    sections = sections_response.json()
    assert len(sections) == 1
    section = sections[0]
    assert section["name"] == "一标段：综合布线与安防"
    assert section["document_count"] >= 1

    items_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section['id']}/compliance-items",
        params={"status": "pending_confirm", "risk_level": "medium"},
    )
    assert items_response.status_code == 200
    items = items_response.json()
    seed_item = next(item for item in items if item["source_page_no"] == 12)
    assert seed_item["source_version_label"] == "v0.1"
    assert seed_item["owner_name"] == "演示管理员"
    assert seed_item["priority_rank"] in {0, 1, 2, 3}
    assert seed_item["priority_label"].startswith("P")

    audit_response = client.get(
        f"/api/v1/projects/{project_id}/audit-logs",
        params={"action": "seed.dev_data_created"},
    )
    assert audit_response.status_code == 200
    audit_logs = audit_response.json()
    assert len(audit_logs) >= 1
    assert any(item["action"] == "seed.dev_data_created" for item in audit_logs)


def test_cleanroom_demo_sample_is_seeded_for_mvp1_hardening() -> None:
    client = TestClient(app)

    projects_response = client.get("/api/v1/projects", params={"limit": 200})
    assert projects_response.status_code == 200
    project = next(
        item for item in projects_response.json() if item["name"] == "洁净车间净化设备采购与安装项目"
    )
    sections_response = client.get(f"/api/v1/projects/{project['id']}/sections")
    assert sections_response.status_code == 200
    section = sections_response.json()[0]

    items_response = client.get(f"/api/v1/projects/{project['id']}/sections/{section['id']}/compliance-items")
    assert items_response.status_code == 200
    item_types = {item["item_type"] for item in items_response.json()}
    assert {"qualification", "mandatory_response", "technical_response", "scoring", "deadline"}.issubset(item_types)

    preflight_response = client.get(f"/api/v1/projects/{project['id']}/sections/{section['id']}/preflight-check")
    assert preflight_response.status_code == 200
    preflight = preflight_response.json()
    assert preflight["status"] == "block"
    assert preflight["mandatory_missing_evidence_count"] >= 1
    assert preflight["technical_pending_count"] >= 1

    search_response = client.get(
        "/api/v1/enterprise/materials/search",
        params={"query": "高效过滤器 检测报告 过滤效率 洁净等级", "limit": 50},
    )
    assert search_response.status_code == 200
    results = search_response.json()
    assert any(item["material_type"] == "test_report" and item["recommend_reason"] for item in results)


def test_preflight_check_detects_outdated_matrix_version() -> None:
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)

    initial_response = client.get(f"/api/v1/projects/{project_id}/sections/{section_id}/preflight-check")
    assert initial_response.status_code == 200

    with SessionLocal() as db:
        seed_matrix_item = db.scalar(
            select(ComplianceItem).where(
                ComplianceItem.project_id == UUID(project_id),
                ComplianceItem.section_id == UUID(section_id),
                ComplianceItem.normalized_requirement == "provide_valid_business_license",
                ComplianceItem.deleted_at.is_(None),
            )
        )
        assert seed_matrix_item is not None
        document = db.get(Document, seed_matrix_item.source_document_id)
        assert document is not None
        assert document.current_version_id is not None
        current = db.get(DocumentVersion, document.current_version_id)
        assert current is not None
        source_version = db.scalar(
            select(DocumentVersion)
            .join(DocumentChunk, DocumentChunk.document_version_id == DocumentVersion.id)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_no.asc())
        )
        assert source_version is not None
        max_version_no = db.scalar(
            select(func.max(DocumentVersion.version_no)).where(DocumentVersion.document_id == document.id)
        ) or current.version_no
        new_version = DocumentVersion(
            tenant_id=document.tenant_id,
            document_id=document.id,
            version_no=max_version_no + 1,
            version_label=f"v0.outdated-test-{max_version_no + 1}",
            object_key=current.object_key,
            sha256=current.sha256,
            parse_status="succeeded",
            parser_name="manual-editor",
            parser_version="1.0",
            created_by=document.created_by,
            change_reason="测试矩阵过期提醒",
        )
        db.add(new_version)
        db.flush()
        chunks = db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_version_id == source_version.id)
        ).all()
        for chunk in chunks:
            db.add(
                DocumentChunk(
                    tenant_id=chunk.tenant_id,
                    document_id=chunk.document_id,
                    document_version_id=new_version.id,
                    section_id=chunk.section_id,
                    chunk_index=chunk.chunk_index,
                    page_no=chunk.page_no,
                    heading_path=chunk.heading_path,
                    content_text=chunk.content_text,
                    content_hash=chunk.content_hash,
                    bbox_json=chunk.bbox_json,
                    table_json=chunk.table_json,
                )
            )
        document.current_version_id = new_version.id
        db.commit()

    response = client.get(f"/api/v1/projects/{project_id}/sections/{section_id}/preflight-check")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "block"
    assert payload["matrix_outdated"] is True
    assert payload["outdated_item_count"] >= 1
    assert any(item["code"] == "matrix_version" and item["status"] == "block" for item in payload["checks"])


def test_project_read_api_enforces_tenant_context() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/projects", headers={"X-Tenant-Code": "missing"})

    assert response.status_code == 404


def test_create_project_and_section_api() -> None:
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": f"API 新建项目 {uuid4().hex}",
            "purchaser": "测试采购人",
            "agency": "测试代理机构",
            "budget_amount": "1000000.00",
            "region_code": "CN-4306",
            "industry_code": "municipal",
            "notice_url": "https://example.com/notice",
            "section_name": "一标段：测试标段",
        },
    )
    assert create_response.status_code == 201
    project = create_response.json()
    assert project["section_count"] == 1
    assert project["status"] == "pending_files"

    section_response = client.post(
        f"/api/v1/projects/{project['id']}/sections",
        json={"code": "section-002", "name": "二标段：补充测试"},
    )
    assert section_response.status_code == 201
    section = section_response.json()
    assert section["name"] == "二标段：补充测试"

    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    assert len(sections) == 2


def test_update_project_and_section_key_fields_writes_audit_log() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": f"关键字段更新项目 {uuid4().hex}",
            "section_name": "一标段：待更新",
        },
    )
    assert create_response.status_code == 201
    created_project = create_response.json()
    project_id = created_project["id"]
    sections = client.get(f"/api/v1/projects/{project_id}/sections").json()
    section_id = sections[0]["id"]

    project_response = client.patch(
        f"/api/v1/projects/{project_id}",
        json={
            "purchaser": "更新后的采购人",
            "budget_amount": "1880000.00",
            "bid_deadline_at": "2026-01-08T09:30:00+08:00",
            "reason": "测试更新项目关键信息",
        },
    )
    assert project_response.status_code == 200
    project = project_response.json()
    assert project["purchaser"] == "更新后的采购人"
    assert project["budget_amount"] == "1880000.00"

    section_response = client.patch(
        f"/api/v1/projects/{project_id}/sections/{section_id}",
        json={
            "code": "cleanroom-001",
            "name": "更新后的标段",
            "budget_amount": "988000.00",
            "reason": "测试更新标段关键信息",
        },
    )
    assert section_response.status_code == 200
    section = section_response.json()
    assert section["code"] == "cleanroom-001"
    assert section["name"] == "更新后的标段"

    audit_response = client.get(f"/api/v1/projects/{project_id}/audit-logs")
    assert audit_response.status_code == 200
    actions = [item["action"] for item in audit_response.json()]
    assert "project.updated" in actions
    assert "section.updated" in actions


def test_delete_project_archives_and_hides_from_default_list() -> None:
    client = TestClient(app)
    project_name = f"待删除项目 {uuid4().hex}"

    create_response = client.post(
        "/api/v1/projects",
        json={"name": project_name, "section_name": "一标段：删除测试"},
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/projects/{project_id}")
    assert delete_response.status_code == 204

    projects = client.get("/api/v1/projects").json()
    assert all(item["id"] != project_id for item in projects)

    archived_projects = client.get("/api/v1/projects", params={"status": "archived"}).json()
    archived = next(item for item in archived_projects if item["id"] == project_id)
    assert archived["status"] == "archived"

    with SessionLocal() as db:
        project = db.get(Project, UUID(project_id))
        assert project is not None
        assert project.archived_at is not None
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.project_id == UUID(project_id),
                AuditLog.action == "project.archived",
            )
        )
        assert audit is not None


def build_import_docx_bytes(project_name: str) -> bytes:
    doc = DocxDocument()
    doc.add_heading(f"{project_name}招标公告", level=1)
    doc.add_paragraph(f"项目名称：{project_name}")
    doc.add_paragraph("招标人：岳阳市君山区城市管理局")
    doc.add_paragraph("招标代理机构：中技建设咨询有限公司")
    doc.add_paragraph("最高投标限价：1349.09万元")
    doc.add_paragraph("投标截止时间：2025年12月11日09时30分")
    doc.add_paragraph("本项目分为一个标段")
    doc.add_paragraph("投标人须提供有效营业执照，并加盖公章。")
    doc.add_paragraph("保修要求：按国务院2000年279号令相关规定及合同约定进行施工质量保修。")
    output = BytesIO()
    doc.save(output)
    return output.getvalue()


def test_project_import_from_uploaded_document_creates_project_document_and_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_api_key", "")
    settings.run_tasks_inline = True
    client = TestClient(app)
    project_name = f"导入文件项目 {uuid4().hex}"

    draft_response = client.post(
        "/api/v1/projects/import-drafts/upload",
        files={
            "file": (
                f"{project_name}.docx",
                build_import_docx_bytes(project_name),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["source"]["source_type"] == "manual_import"
    assert draft["project"]["name"] == project_name
    assert draft["project"]["purchaser"] == "岳阳市君山区城市管理局"
    assert draft["project"]["budget_amount"] == "13490900.00"
    assert draft["sections"][0]["name"].startswith("一标段")

    confirm_response = client.post("/api/v1/projects/import-drafts/confirm", json=draft)
    assert confirm_response.status_code == 201
    result = confirm_response.json()
    assert result["project"]["name"] == project_name
    assert result["document_id"]
    assert result["parse_task_id"]
    assert result["matrix_task_id"]

    documents_response = client.get(
        f"/api/v1/projects/{result['project']['id']}/sections/{result['section_id']}/documents"
    )
    assert documents_response.status_code == 200
    documents = documents_response.json()
    assert len(documents) == 1
    assert documents[0]["source_type"] == "manual_import"
    assert documents[0]["current_version"]["parse_status"] == "succeeded"

    items_response = client.get(
        f"/api/v1/projects/{result['project']['id']}/sections/{result['section_id']}/compliance-items"
    )
    assert items_response.status_code == 200
    items = items_response.json()
    assert any("营业执照" in item["requirement_text"] for item in items)


def test_project_import_confirm_accepts_async_processing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_api_key", "")
    settings.run_tasks_inline = True
    client = TestClient(app)
    project_name = f"异步导入文件项目 {uuid4().hex}"

    draft_response = client.post(
        "/api/v1/projects/import-drafts/upload",
        files={
            "file": (
                f"{project_name}.docx",
                build_import_docx_bytes(project_name),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    draft["async_processing"] = True

    confirm_response = client.post("/api/v1/projects/import-drafts/confirm", json=draft)
    assert confirm_response.status_code == 201
    result = confirm_response.json()
    assert result["project"]["name"] == project_name
    assert result["parse_task_id"]
    assert result["matrix_task_id"]


def test_project_import_from_public_url_html_creates_parsed_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_api_key", "")
    settings.run_tasks_inline = True
    client = TestClient(app)
    project_name = f"网页导入项目 {uuid4().hex}"
    html = f"""
    <html><body>
    <h1>{project_name}招标公告</h1>
    <p>项目名称：{project_name}</p>
    <p>招标人：岳阳市君山区城市管理局</p>
    <p>招标代理机构：中技建设咨询有限公司</p>
    <p>最高投标限价：1349.09万元</p>
    <p>开标时间：2025年12月11日09时30分</p>
    <p>投标人须提供有效营业执照，并加盖公章。</p>
    </body></html>
    """.encode()

    def fake_fetch_public_file(url: str) -> DownloadedFile:
        return DownloadedFile(
            final_url=url,
            filename="notice.html",
            content_type="text/html; charset=utf-8",
            content_length=len(html),
            http_status=200,
            redirect_chain=[],
            data=html,
        )

    monkeypatch.setattr("app.services.project_import.fetch_public_file", fake_fetch_public_file)

    draft_response = client.post(
        "/api/v1/projects/import-drafts/public-url",
        json={
            "source_url": "https://example.com/tender/notice.html",
            "source_site": "示例公共资源交易中心",
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["source"]["source_type"] == "public_url"
    assert draft["project"]["name"] == project_name

    confirm_response = client.post("/api/v1/projects/import-drafts/confirm", json=draft)
    assert confirm_response.status_code == 201
    result = confirm_response.json()
    assert result["project"]["notice_url"] == "https://example.com/tender/notice.html"
    assert result["parse_task_id"] is None
    assert result["matrix_task_id"]

    with SessionLocal() as db:
        document = db.get(Document, UUID(result["document_id"]))
        assert document is not None
        assert document.file_ext == "html"
        assert document.current_version_id is not None
        version = db.get(DocumentVersion, document.current_version_id)
        assert version is not None
        assert version.parse_status == "succeeded"
        chunk_ids = db.scalars(
            select(DocumentChunk.id).where(DocumentChunk.document_version_id == version.id)
        ).all()
        assert chunk_ids


def create_api_test_compliance_item(
    project_id: str,
    section_id: str,
    *,
    risk_level: str = "low",
    is_mandatory: bool = False,
    owner_user_id: UUID | None = None,
) -> str:
    with SessionLocal() as db:
        document = db.scalar(
            select(Document).where(
                Document.project_id == UUID(project_id),
                Document.section_id == UUID(section_id),
                Document.original_filename == "招标文件.pdf",
            )
        )
        assert document is not None
        chunk = db.scalar(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.created_at.asc())
        )
        assert chunk is not None
        version = db.get(DocumentVersion, chunk.document_version_id)
        assert version is not None
        user = db.scalar(select(User).where(User.external_id == "demo-admin"))
        assert user is not None
        item = ComplianceItem(
            tenant_id=document.tenant_id,
            project_id=document.project_id,
            section_id=UUID(section_id),
            source_document_id=document.id,
            source_version_id=version.id,
            source_chunk_id=chunk.id,
            source_page_no=chunk.page_no,
            item_type="mandatory_response",
            requirement_text=f"API 测试响应项 {uuid4().hex}",
            normalized_requirement=f"api_test:{uuid4().hex}",
            response_suggestion="请人工确认响应内容。",
            evidence_text=chunk.content_text,
            status="pending_confirm",
            risk_level=risk_level,
            is_mandatory=is_mandatory,
            is_batch_confirm_allowed=risk_level != "high" and not is_mandatory,
            owner_user_id=owner_user_id,
            confidence_score=Decimal("0.8000"),
            created_by=user.id,
        )
        db.add(item)
        db.commit()
        return str(item.id)


def create_review_test_chunks(
    project_id: str,
    section_id: str,
    contents: list[str],
) -> list[dict[str, object]]:
    with SessionLocal() as db:
        document = db.scalar(
            select(Document).where(
                Document.project_id == UUID(project_id),
                Document.section_id == UUID(section_id),
                Document.original_filename == "招标文件.pdf",
            )
        )
        assert document is not None
        assert document.current_version_id is not None
        max_index = db.scalar(
            select(func.max(DocumentChunk.chunk_index)).where(
                DocumentChunk.document_version_id == document.current_version_id
            )
        ) or 0
        chunks: list[DocumentChunk] = []
        for index, content in enumerate(contents, start=1):
            chunk = DocumentChunk(
                tenant_id=document.tenant_id,
                document_id=document.id,
                document_version_id=document.current_version_id,
                section_id=UUID(section_id),
                chunk_index=max_index + index,
                page_no=900 + index,
                heading_path=f"MVP1.1 P1 回归/第 {index} 处",
                content_text=content,
                content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                bbox_json=None,
                table_json=None,
            )
            db.add(chunk)
            chunks.append(chunk)
        db.commit()
        return [
            {
                "id": str(chunk.id),
                "chunk_index": chunk.chunk_index,
                "page_no": chunk.page_no,
                "content_text": chunk.content_text,
            }
            for chunk in chunks
        ]


def create_review_test_item(
    project_id: str,
    section_id: str,
    chunk_id: str,
    *,
    requirement_text: str,
    dedup_key: str,
    risk_level: str = "low",
    is_mandatory: bool = False,
) -> str:
    with SessionLocal() as db:
        chunk = db.get(DocumentChunk, UUID(chunk_id))
        assert chunk is not None
        document = db.get(Document, chunk.document_id)
        assert document is not None
        user = db.scalar(select(User).where(User.external_id == "demo-admin"))
        assert user is not None
        item = ComplianceItem(
            tenant_id=document.tenant_id,
            project_id=UUID(project_id),
            section_id=UUID(section_id),
            source_document_id=document.id,
            source_version_id=chunk.document_version_id,
            source_chunk_id=chunk.id,
            source_page_no=chunk.page_no,
            item_type="mandatory_response",
            requirement_text=requirement_text,
            normalized_requirement=f"p1_test:{dedup_key}:{uuid4().hex}",
            dedup_key=dedup_key,
            response_suggestion="P1 回归测试项，请人工确认。",
            evidence_text=chunk.content_text,
            explanation_json={
                "rule_code": "TEST-MVP11-P1",
                "rule_reason": "MVP1.1 P1 关联组回归测试注入项。",
            },
            status="pending_confirm",
            risk_level=risk_level,
            is_mandatory=is_mandatory,
            is_batch_confirm_allowed=risk_level != "high" and not is_mandatory,
            owner_user_id=user.id,
            confidence_score=Decimal("0.9000"),
            created_by=user.id,
        )
        db.add(item)
        db.commit()
        return str(item.id)


def test_compliance_item_update_confirm_assign_and_audit() -> None:
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    item_id = create_api_test_compliance_item(project_id, section_id)

    missing_reason_response = client.patch(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/{item_id}",
        json={"risk_level": "medium"},
    )
    assert missing_reason_response.status_code == 422

    update_response = client.patch(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/{item_id}",
        json={
            "risk_level": "medium",
            "is_mandatory": True,
            "status": "needs_material",
            "response_suggestion": "需补充承诺函并复核。",
            "reason": "测试人工修改矩阵项",
        },
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["risk_level"] == "medium"
    assert updated["is_mandatory"] is True
    assert updated["status"] == "needs_material"
    assert updated["is_batch_confirm_allowed"] is False
    assert updated["modify_reason"] == "测试人工修改矩阵项"

    assign_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/{item_id}/assign",
        json={"reason": "测试指派给当前用户"},
    )
    assert assign_response.status_code == 200
    assigned = assign_response.json()
    assert assigned["owner_name"] == "演示管理员"

    blocked_confirm_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/{item_id}/confirm",
        json={"reason": "测试单条确认"},
    )
    assert blocked_confirm_response.status_code == 409
    assert "source verification" in blocked_confirm_response.json()["detail"]

    confirm_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/{item_id}/confirm",
        json={"reason": "测试单条确认", "source_verified": True},
    )
    assert confirm_response.status_code == 200
    confirmed = confirm_response.json()
    assert confirmed["status"] == "confirmed"
    assert confirmed["confirmed_by"] is not None

    audit_response = client.get(
        f"/api/v1/projects/{project_id}/audit-logs",
        params={"object_type": "compliance_item", "limit": 50},
    )
    assert audit_response.status_code == 200
    actions = {
        item["action"]
        for item in audit_response.json()
        if item["object_id"] == item_id
    }
    assert {"matrix.item_updated", "matrix.item_assigned", "matrix.item_confirmed"} <= actions


def test_matrix_review_p1_manual_source_similar_candidates_and_apply() -> None:
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    unique = uuid4().hex[:8]
    selected_text = f"投标人须提供洁净设备安装调试方案 {unique}。"
    fuzzy_text = f"投标人须提供洁净设备调试安装方案 {unique}。"
    chunks = create_review_test_chunks(
        project_id,
        section_id,
        [
            f"补充条款：{selected_text} 本条用于人工补漏回归。",
            f"重复条款：{selected_text} 请在响应文件中承诺。",
            f"近似条款：{fuzzy_text}",
            f"采购人：测试单位 联系电话：13800000000 {selected_text}",
        ],
    )
    base_chunk = chunks[0]

    review_before_response = client.get(f"/api/v1/projects/{project_id}/sections/{section_id}/matrix-review")
    assert review_before_response.status_code == 200
    review_before = review_before_response.json()
    assert any(item["chunk"]["id"] == base_chunk["id"] for item in review_before["uncovered_chunks"])

    start = str(base_chunk["content_text"]).index(selected_text)
    create_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/from-source",
        json={
            "source_chunk_id": base_chunk["id"],
            "selected_text": selected_text,
            "selection_start_offset": start,
            "selection_end_offset": start + len(selected_text),
            "item_type": "mandatory_response",
            "risk_level": "medium",
            "is_mandatory": True,
            "response_suggestion": "请提供安装调试方案并在响应文件中承诺。",
            "reason": "P1 回归：人工从原文补漏新增",
        },
    )
    assert create_response.status_code == 201
    created_result = create_response.json()
    created_item = created_result["item"]
    assert created_item["source_create_method"] == "manual_selection"
    assert created_item["selected_text"] == selected_text
    assert created_item["selection_start_offset"] == start
    assert created_item["selection_end_offset"] == start + len(selected_text)
    assert created_item["dedup_key"]

    candidates = created_result["similar_candidates"]
    candidate_chunk_ids = {candidate["source_chunk_id"] for candidate in candidates}
    assert chunks[1]["id"] in candidate_chunk_ids
    assert chunks[2]["id"] in candidate_chunk_ids
    assert chunks[3]["id"] not in candidate_chunk_ids
    fuzzy_candidate = next(candidate for candidate in candidates if candidate["source_chunk_id"] == chunks[2]["id"])
    assert fuzzy_candidate["match_type"] == "fuzzy"
    assert any(segment["operation"] in {"insert", "replace"} for segment in fuzzy_candidate["diff_segments"])

    exact_candidate = next(candidate for candidate in candidates if candidate["source_chunk_id"] == chunks[1]["id"])
    apply_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/"
            f"{created_item['id']}/similar-candidates/apply"
        ),
        json={
            "reason": "P1 回归：逐个确认相似补票",
            "candidates": [
                {
                    "candidate_key": exact_candidate["candidate_key"],
                    "source_chunk_id": exact_candidate["source_chunk_id"],
                    "selected_text": exact_candidate["selected_text"],
                    "selection_start_offset": exact_candidate["selection_start_offset"],
                    "selection_end_offset": exact_candidate["selection_end_offset"],
                    "action": "join_group",
                },
                {
                    "candidate_key": fuzzy_candidate["candidate_key"],
                    "source_chunk_id": fuzzy_candidate["source_chunk_id"],
                    "selected_text": fuzzy_candidate["selected_text"],
                    "selection_start_offset": fuzzy_candidate["selection_start_offset"],
                    "selection_end_offset": fuzzy_candidate["selection_end_offset"],
                    "action": "create_independent",
                },
            ],
        },
    )
    assert apply_response.status_code == 200
    apply_result = apply_response.json()
    assert apply_result["affected_item_count"] == 3
    joined_items = [
        item for item in apply_result["items"]
        if item["source_chunk_id"] in {created_item["source_chunk_id"], chunks[1]["id"]}
    ]
    independent_items = [item for item in apply_result["items"] if item["source_chunk_id"] == chunks[2]["id"]]
    assert len(joined_items) == 2
    assert {item["duplicate_group_id"] for item in joined_items} == {apply_result["duplicate_group_id"]}
    assert independent_items[0]["duplicate_group_id"] is None

    audit_response = client.get(
        f"/api/v1/projects/{project_id}/audit-logs",
        params={"limit": 100},
    )
    assert audit_response.status_code == 200
    actions = {item["action"] for item in audit_response.json()}
    assert {"matrix.item_created_from_source", "matrix.similar_candidate_applied"} <= actions


def test_matrix_review_p1_duplicate_group_unlink_split_and_cascade_confirmation() -> None:
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    unique = uuid4().hex[:8]
    requirement = f"投标人须提供项目经理驻场服务承诺 {unique}。"
    dedup_key = f"p1_duplicate_{unique}"
    chunks = create_review_test_chunks(
        project_id,
        section_id,
        [
            f"第一处：{requirement}",
            f"第二处：{requirement}",
            f"第三处：{requirement}",
        ],
    )
    item_ids = [
        create_review_test_item(
            project_id,
            section_id,
            str(chunk["id"]),
            requirement_text=requirement,
            dedup_key=dedup_key,
        )
        for chunk in chunks
    ]

    review_candidate_response = client.get(f"/api/v1/projects/{project_id}/sections/{section_id}/matrix-review")
    assert review_candidate_response.status_code == 200
    candidate_groups = [
        group for group in review_candidate_response.json()["duplicate_groups"]
        if group["group_key"] == dedup_key and group["group_type"] == "candidate"
    ]
    assert candidate_groups and candidate_groups[0]["item_count"] == 3

    confirm_group_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/"
            f"{item_ids[0]}/duplicate-group/confirm"
        ),
        json={"reason": "P1 回归：人工确认重复关联组"},
    )
    assert confirm_group_response.status_code == 200
    group_result = confirm_group_response.json()
    assert group_result["affected_item_count"] == 3
    assert group_result["duplicate_group_id"]
    assert {item["duplicate_group_status"] for item in group_result["items"]} == {"confirmed"}

    unlink_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/"
            f"{item_ids[2]}/duplicate-group/unlink"
        ),
        json={"reason": "P1 回归：第三处存在语义差异，解除联动"},
    )
    assert unlink_response.status_code == 200
    unlinked_item = unlink_response.json()["items"][0]
    assert unlinked_item["duplicate_group_id"] is None
    assert unlinked_item["duplicate_group_status"] == "unlinked"

    confirm_item_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/{item_ids[0]}/confirm",
        json={"reason": "P1 回归：确认同组条目并验证级联", "cascade": True},
    )
    assert confirm_item_response.status_code == 200
    confirmed_item = confirm_item_response.json()
    assert confirmed_item["status"] == "confirmed"
    assert confirmed_item["cascade_affected_count"] == 1
    assert confirmed_item["cascade_affected_items"][0]["id"] == item_ids[1]

    with SessionLocal() as db:
        first = db.get(ComplianceItem, UUID(item_ids[0]))
        second = db.get(ComplianceItem, UUID(item_ids[1]))
        third = db.get(ComplianceItem, UUID(item_ids[2]))
        assert first is not None and second is not None and third is not None
        assert first.status == "confirmed"
        assert second.status == "confirmed"
        assert third.status == "pending_confirm"
        assert third.duplicate_group_status == "unlinked"

    split_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/"
            f"{item_ids[2]}/duplicate-group/split"
        ),
        json={"reason": "P1 回归：拆分为独立关联组"},
    )
    assert split_response.status_code == 200
    split_item = split_response.json()["items"][0]
    assert split_item["duplicate_group_id"]
    assert split_item["duplicate_group_id"] != group_result["duplicate_group_id"]
    assert split_item["duplicate_group_status"] == "confirmed"

    audit_response = client.get(
        f"/api/v1/projects/{project_id}/audit-logs",
        params={"limit": 120},
    )
    assert audit_response.status_code == 200
    actions = {item["action"] for item in audit_response.json()}
    assert {
        "matrix.duplicate_group_confirmed",
        "matrix.duplicate_group_unlinked",
        "matrix.duplicate_group_split",
        "matrix.cascade_confirmed",
    } <= actions


def test_compliance_item_bulk_guards() -> None:
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    low_item_id = create_api_test_compliance_item(project_id, section_id)
    high_item_id = create_api_test_compliance_item(
        project_id,
        section_id,
        risk_level="high",
        is_mandatory=True,
    )

    blocked_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/bulk-confirm",
        json={"item_ids": [high_item_id], "reason": "测试禁止批量确认高风险项"},
    )
    assert blocked_response.status_code == 409

    assign_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/bulk-assign",
        json={"item_ids": [low_item_id, high_item_id], "reason": "测试批量指派"},
    )
    assert assign_response.status_code == 200
    assert {item["owner_name"] for item in assign_response.json()} == {"演示管理员"}

    confirm_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/bulk-confirm",
        json={"item_ids": [low_item_id], "reason": "测试批量确认低风险项"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()[0]["status"] == "confirmed"

    with SessionLocal() as db:
        batch_logs = db.scalars(
            select(AuditLog).where(
                AuditLog.project_id == UUID(project_id),
                AuditLog.action.in_(["matrix.items_assigned", "matrix.items_batch_confirmed"]),
            )
        ).all()
        assert len(batch_logs) >= 2


def test_compliance_matrix_excel_export_api() -> None:
    settings.run_tasks_inline = True
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/export-excel",
        json={"risk_level": "low"},
    )
    assert response.status_code == 202
    task = response.json()
    assert task["status"] == "succeeded"
    assert task["output_json"]["export_file_id"]
    assert task["output_json"]["row_count"] >= 1

    export_id = task["output_json"]["export_file_id"]
    export_response = client.get(f"/api/v1/projects/{project_id}/export-files/{export_id}")
    assert export_response.status_code == 200
    export_file = export_response.json()
    assert export_file["status"] == "available"
    assert export_file["sha256"] == task["output_json"]["sha256"]
    assert export_file["file_name"].startswith("合规矩阵快照-")
    assert export_file["source_snapshot_json"]["snapshot_note"] == "只读快照；最新状态以平台为准"

    download_response = client.get(
        f"/api/v1/projects/{project_id}/export-files/{export_id}/download"
    )
    assert download_response.status_code == 200
    assert download_response.content.startswith(b"PK")
    workbook = load_workbook(BytesIO(download_response.content))
    sheet = workbook["合规矩阵快照"]
    assert sheet["A1"].value == "合规矩阵快照"
    assert "最新状态以投标 Agent 平台为准" in sheet["A2"].value
    assert sheet["A7"].value == "序号"
