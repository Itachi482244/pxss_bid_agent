from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import BidSection, ComplianceItem, Document, DocumentChunk, Project
from scripts.seed_dev_data import seed


CLEANROOM_PROJECT_NAME = "洁净车间净化设备采购与安装项目"


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def get_cleanroom_project_and_section(client: TestClient) -> tuple[str, str]:
    projects = client.get("/api/v1/projects", params={"limit": 200}).json()
    project = next(item for item in projects if item["name"] == CLEANROOM_PROJECT_NAME)
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    return project["id"], sections[0]["id"]


def create_unbound_cleanroom_mandatory_item(project_id: str, section_id: str) -> UUID:
    with SessionLocal() as db:
        project = db.get(Project, UUID(project_id))
        section = db.get(BidSection, UUID(section_id))
        assert project is not None
        assert section is not None
        document = db.scalar(
            select(Document).where(
                Document.project_id == project.id,
                Document.section_id == section.id,
                Document.doc_type == "tender",
                Document.current_version_id.is_not(None),
            )
        )
        assert document is not None
        chunk = db.scalar(
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.document_version_id == document.current_version_id,
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )
        assert chunk is not None

        item = ComplianceItem(
            tenant_id=project.tenant_id,
            project_id=project.id,
            section_id=section.id,
            source_document_id=document.id,
            source_version_id=document.current_version_id,
            source_chunk_id=chunk.id,
            source_page_no=chunk.page_no,
            item_type="mandatory_response",
            requirement_text=(
                f"MVP1 P0 回归项 {uuid4().hex[:8]}：须提供洁净设备检测报告作为强制响应证据。"
            ),
            normalized_requirement=f"mvp1_p0_unbound_mandatory_{uuid4().hex}",
            response_suggestion="该测试项用于验证证据绑定后提交前核验缺证据数量下降。",
            evidence_text=chunk.content_text,
            explanation_json={
                "rule_code": "TEST-MVP1-P0-GOLDEN",
                "rule_reason": "黄金样本回归测试注入项。",
                "risk_reason": "强制项缺证据应阻塞提交前核验。",
                "extraction_provider": "test",
            },
            status="needs_material",
            risk_level="high",
            is_mandatory=True,
            is_batch_confirm_allowed=False,
            owner_user_id=project.created_by,
            confidence_score=Decimal("0.9000"),
            created_by=project.created_by,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item.id


def test_mvp1_cleanroom_golden_regression_preflight_evidence_approval_and_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_objects: dict[str, bytes] = {}

    def fake_put_object_bytes(**kwargs: object) -> None:
        stored_objects[str(kwargs["object_key"])] = kwargs["data"]  # type: ignore[index]

    monkeypatch.setattr("app.services.business_draft.put_object_bytes", fake_put_object_bytes)
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_api_key", "")

    client = TestClient(app)
    project_id, section_id = get_cleanroom_project_and_section(client)
    injected_item_id = create_unbound_cleanroom_mandatory_item(project_id, section_id)

    documents_response = client.get(f"/api/v1/projects/{project_id}/sections/{section_id}/documents")
    assert documents_response.status_code == 200
    documents = documents_response.json()
    tender_document = next(item for item in documents if item["doc_type"] == "tender")
    assert tender_document["current_version"]["parse_status"] in {"succeeded", "frozen"}

    items_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items",
        params={"limit": 300},
    )
    assert items_response.status_code == 200
    items = items_response.json()
    item_types = {item["item_type"] for item in items}
    assert {"qualification", "mandatory_response", "technical_response", "scoring", "deadline"}.issubset(
        item_types
    )
    assert all(item["source_version_id"] for item in items)
    assert all(item["priority_rank"] in {0, 1, 2, 3} for item in items)
    technical_item = next(item for item in items if item["item_type"] == "technical_response")
    assert technical_item["priority_label"].startswith("P")
    assert technical_item["priority_reason"]

    before_preflight_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/preflight-check"
    )
    assert before_preflight_response.status_code == 200
    before_preflight = before_preflight_response.json()
    assert before_preflight["status"] == "block"
    assert before_preflight["matrix_outdated"] is False
    assert before_preflight["mandatory_missing_evidence_count"] >= 1
    assert any(item["code"] == "mandatory_evidence" and item["status"] == "block" for item in before_preflight["checks"])

    search_response = client.get(
        "/api/v1/enterprise/materials/search",
        params={"query": "洁净设备 检测报告 过滤效率 ISO 7", "material_type": "test_report", "limit": 50},
    )
    assert search_response.status_code == 200
    search_results = search_response.json()
    recommended_report = next(item for item in search_results if item["material_type"] == "test_report")
    assert recommended_report["recommend_reason"]
    assert recommended_report["matched_terms"]
    assert recommended_report["material_status_hint"]

    bind_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}"
            f"/compliance-items/{injected_item_id}/evidence-bindings"
        ),
        json={
            "enterprise_material_id": recommended_report["id"],
            "evidence_text": recommended_report["snippet"] or recommended_report["evidence_text"],
            "confidence_score": "0.9100",
            "reason": "MVP1 P0 黄金样本回归：绑定检测报告证据",
        },
    )
    assert bind_response.status_code == 201

    after_preflight_response = client.get(f"/api/v1/projects/{project_id}/sections/{section_id}/preflight-check")
    assert after_preflight_response.status_code == 200
    after_preflight = after_preflight_response.json()
    assert after_preflight["status"] == "block"
    assert (
        after_preflight["mandatory_missing_evidence_count"]
        == before_preflight["mandatory_missing_evidence_count"] - 1
    )
    assert after_preflight["suggested_actions"]

    draft_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/chapters/generate",
        json={"force": True},
    )
    assert draft_response.status_code == 200
    assert draft_response.json()

    blocked_export_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/export-word"
    )
    assert blocked_export_response.status_code == 409

    export_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/export-word",
        json={"risk_acceptance_reason": "MVP1 P0 回归：仅作为内部草稿导出，阻塞项后续人工复核。"},
    )
    assert export_response.status_code == 200
    export_file = export_response.json()
    assert export_file["source_snapshot_json"]["preflight_status"] == "block"
    assert export_file["source_snapshot_json"]["internal_draft"] is True
    assert "P0 回归" in export_file["source_snapshot_json"]["risk_acceptance_reason"]
    assert stored_objects

    blocked_approval_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/approval-tasks",
        json={
            "task_type": "submit_confirmation",
            "title": "MVP1 P0 提交确认回归",
            "description": "验证阻塞状态下提交确认必须填写风险接受说明。",
        },
    )
    assert blocked_approval_response.status_code == 409

    approval_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/approval-tasks",
        json={
            "task_type": "submit_confirmation",
            "title": "MVP1 P0 提交确认回归",
            "description": "验证阻塞状态下提交确认必须保存 preflight 快照。",
            "risk_acceptance_reason": "MVP1 P0 回归：审批人知悉仍有阻塞项，仅进入内部试用复核。",
        },
    )
    assert approval_response.status_code == 201
    approval_task = approval_response.json()
    snapshot = approval_task["evidence_snapshot_json"]
    assert snapshot["preflight_status"] == "block"
    assert snapshot["blocking_summary"]
    assert "P0 回归" in snapshot["risk_acceptance_reason"]
