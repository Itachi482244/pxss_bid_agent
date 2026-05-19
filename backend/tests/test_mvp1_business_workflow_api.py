from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from scripts.seed_dev_data import seed


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def get_seed_project_and_section(client: TestClient) -> tuple[str, str]:
    projects = client.get("/api/v1/projects").json()
    project = next(item for item in projects if item["name"] == "智慧园区弱电工程投标")
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    return project["id"], sections[0]["id"]


def test_material_chunks_search_and_data_level_filter() -> None:
    client = TestClient(app)
    unique_query = f"MVP1CONFIDENTIAL{uuid4().hex[:8].upper()}"
    public_query = f"MVP1PUBLIC{uuid4().hex[:8].upper()}"

    public_response = client.post(
        "/api/v1/enterprise/materials",
        json={
            "material_type": "business_template",
            "name": f"公开商务响应模板 {public_query}",
            "data_level": "internal",
            "verification_status": "confirmed",
            "evidence_text": f"{public_query} 可用于商务标承诺响应和保修条款响应。",
        },
    )
    assert public_response.status_code == 201
    public_material = public_response.json()

    restricted_response = client.post(
        "/api/v1/enterprise/materials",
        json={
            "material_type": "business_template",
            "name": f"敏感商务响应模板 {unique_query}",
            "data_level": "confidential",
            "verification_status": "confirmed",
            "evidence_text": f"{unique_query} 仅允许授权上下文召回。",
        },
    )
    assert restricted_response.status_code == 201
    restricted_material = restricted_response.json()

    chunks_response = client.get(f"/api/v1/enterprise/materials/{public_material['id']}/chunks")
    assert chunks_response.status_code == 200
    chunks = chunks_response.json()
    assert chunks
    assert chunks[0]["enterprise_material_id"] == public_material["id"]
    assert chunks[0]["token_count"] > 0

    default_search = client.get(
        "/api/v1/enterprise/materials/search",
        params={"query": unique_query, "limit": 10},
    )
    assert default_search.status_code == 200
    assert all(item["id"] != restricted_material["id"] for item in default_search.json())

    restricted_search = client.get(
        "/api/v1/enterprise/materials/search",
        params={"query": unique_query, "include_restricted": True, "limit": 10},
    )
    assert restricted_search.status_code == 200
    restricted_results = restricted_search.json()
    hit = next(item for item in restricted_results if item["id"] == restricted_material["id"])
    assert hit["chunk_id"]
    assert hit["data_level_allowed"] is True

    rebuild_response = client.post(f"/api/v1/enterprise/materials/{public_material['id']}/chunks/rebuild")
    assert rebuild_response.status_code == 200
    assert rebuild_response.json()[0]["enterprise_material_id"] == public_material["id"]


def test_business_draft_decision_fact_check_export_and_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_objects: dict[str, bytes] = {}

    def fake_put_object_bytes(**kwargs: object) -> None:
        stored_objects[str(kwargs["object_key"])] = kwargs["data"]  # type: ignore[index]

    def fake_get_object_bytes(*, bucket: str, object_key: str) -> bytes:
        return stored_objects[object_key]

    monkeypatch.setattr("app.services.business_draft.put_object_bytes", fake_put_object_bytes)
    monkeypatch.setattr("app.api.v1.routes.projects.get_object_bytes", fake_get_object_bytes)
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_api_key", "")

    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)

    material_response = client.post(
        "/api/v1/enterprise/materials",
        json={
            "material_type": "license",
            "name": f"MVP1 有效营业执照 {uuid4().hex[:6]}",
            "issuing_authority": "岳阳市市场监督管理局",
            "certificate_no": "91430600MVP10001",
            "valid_until": "2030-12-31",
            "data_level": "internal",
            "verification_status": "confirmed",
            "evidence_text": "营业执照载明企业主体资格有效，统一社会信用代码 91430600MVP10001。",
        },
    )
    assert material_response.status_code == 201
    material = material_response.json()

    items_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items"
    )
    assert items_response.status_code == 200
    compliance_item = next(
        item for item in items_response.json() if "营业执照" in item["requirement_text"]
    )

    bind_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}"
            f"/compliance-items/{compliance_item['id']}/evidence-bindings"
        ),
        json={
            "enterprise_material_id": material["id"],
            "reason": "用于商务标资格响应证据",
            "confidence_score": "0.9500",
        },
    )
    assert bind_response.status_code == 201

    decision_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/qualification-decision/generate"
    )
    assert decision_response.status_code == 200
    decision = decision_response.json()
    assert decision["recommendation"] in {"go", "conditional_go", "no_go"}
    assert decision["summary"]

    confirm_decision_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}"
            f"/qualification-decision/{decision['id']}/confirm"
        ),
        json={"reason": "项目经理确认参标建议"},
    )
    assert confirm_decision_response.status_code == 200
    assert confirm_decision_response.json()["status"] == "confirmed"

    generate_draft_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/chapters/generate",
        json={"force": True},
    )
    assert generate_draft_response.status_code == 200
    chapters = generate_draft_response.json()
    assert chapters
    qualification_chapter = next(item for item in chapters if item["chapter_type"] == "qualification_response")
    assert qualification_chapter["evidence_refs"]
    assert qualification_chapter["fact_checks"]
    assert material["name"] in qualification_chapter["content_text"]

    unknown_fact = "FAKECERT9999"
    update_response = client.patch(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/chapters/"
            f"{qualification_chapter['id']}"
        ),
        json={
            "content_text": f"{qualification_chapter['content_text']}\n新增待核验编号：{unknown_fact}",
            "reason": "测试人工编辑后事实性校验",
        },
    )
    assert update_response.status_code == 200
    updated_chapter = update_response.json()
    assert unknown_fact not in updated_chapter["content_text"]
    assert "[请人工确认]" in updated_chapter["content_text"]
    assert any(check["check_status"] == "unverified" for check in updated_chapter["fact_checks"])

    export_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/export-word"
    )
    assert export_response.status_code == 200
    export_file = export_response.json()
    assert export_file["export_type"] == "business_draft_word"
    assert export_file["file_name"].endswith(".docx")
    assert stored_objects

    download_response = client.get(
        f"/api/v1/projects/{project_id}/export-files/{export_file['id']}/download"
    )
    assert download_response.status_code == 200
    assert (
        download_response.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert download_response.content.startswith(b"PK")

    approval_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/approval-tasks",
        params={"status": "pending"},
    )
    assert approval_response.status_code == 200
    tasks = approval_response.json()
    chapter_task = next(
        item
        for item in tasks
        if item["related_object_type"] == "business_draft_chapter"
        and item["related_object_id"] == qualification_chapter["id"]
    )

    approve_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/approval-tasks/"
            f"{chapter_task['id']}/decision"
        ),
        json={"action": "approve", "reason": "章节内容和证据已复核"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"

    refreshed_chapters = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/chapters"
    ).json()
    approved_chapter = next(item for item in refreshed_chapters if item["id"] == qualification_chapter["id"])
    assert approved_chapter["status"] == "approved"

    submit_task_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/approval-tasks",
        json={
            "task_type": "submit_confirmation",
            "title": "提交前人工确认",
            "description": "确认商务标草稿、资格建议和导出文件均已复核。",
        },
    )
    assert submit_task_response.status_code == 201
    assert submit_task_response.json()["status"] == "pending"
