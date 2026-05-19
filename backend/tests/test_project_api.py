from __future__ import annotations

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
from sqlalchemy import select

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

    audit_response = client.get(
        f"/api/v1/projects/{project_id}/audit-logs",
        params={"action": "seed.dev_data_created"},
    )
    assert audit_response.status_code == 200
    audit_logs = audit_response.json()
    assert len(audit_logs) >= 1
    assert any(item["action"] == "seed.dev_data_created" for item in audit_logs)


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
        version = db.get(DocumentVersion, document.current_version_id)
        assert version is not None
        chunk = db.scalar(
            select(DocumentChunk).where(
                DocumentChunk.document_version_id == version.id,
            )
        )
        assert chunk is not None
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

    confirm_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/{item_id}/confirm",
        json={"reason": "测试单条确认"},
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
