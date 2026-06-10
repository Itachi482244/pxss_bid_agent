from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

import fitz
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


def build_pdf_bytes(text: str = "投标人须提供有效营业执照。") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    return document.tobytes()


def test_upload_document_and_create_parse_task() -> None:
    settings.run_tasks_inline = False
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    filename = f"测试招标文件-{uuid4().hex}.pdf"

    upload_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/upload",
        data={"doc_type": "tender", "title": "测试招标文件"},
        files={"file": (filename, build_pdf_bytes(), "application/pdf")},
    )

    assert upload_response.status_code == 201
    document = upload_response.json()
    assert document["title"] == "测试招标文件"
    assert document["source_type"] == "upload"
    assert document["status"] == "available"
    assert document["current_version"]["parse_status"] == "pending"

    documents_response = client.get(f"/api/v1/projects/{project_id}/sections/{section_id}/documents")
    assert documents_response.status_code == 200
    assert any(item["id"] == document["id"] for item in documents_response.json())

    parse_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/{document['id']}/parse-tasks",
        json={"parser_name": "test-parser", "parser_version": "0.1.0"},
    )
    assert parse_response.status_code == 202
    parse_task = parse_response.json()
    assert parse_task["parser_type"] == "pdf_text"
    assert parse_task["task"]["status"] == "pending"
    assert parse_task["document_id"] == document["id"]

    repeated_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/{document['id']}/parse-tasks",
        json={"parser_name": "test-parser", "parser_version": "0.1.0"},
    )
    assert repeated_response.status_code == 202
    assert repeated_response.json()["id"] == parse_task["id"]


def test_upload_document_uses_tender_document_size_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.v1.routes.documents.TENDER_DOCUMENT_FILE_MAX_BYTES", 1024 * 1024)
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/upload",
        data={"doc_type": "tender", "title": "过大招标文件"},
        files={"file": ("large.pdf", b"x" * (1024 * 1024 + 1), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "File is too large; max 1 MiB"


def test_public_url_acquisition_records_security_block() -> None:
    settings.run_tasks_inline = False
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/public-url",
        json={
            "source_url": "http://127.0.0.1/private/tender.pdf",
            "source_site": "本机测试",
            "title": "不安全链接",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["validation_status"] == "blocked"
    assert payload["blocked_reason"]
    assert payload["task"]["status"] == "failed"
    assert payload["task"]["error_code"] == "URL_BLOCKED"

    audit_response = client.get(
        f"/api/v1/projects/{project_id}/audit-logs",
        params={"action": "document.public_url_blocked"},
    )
    assert audit_response.status_code == 200
    assert any(item["object_id"] == payload["id"] for item in audit_response.json())


def test_public_url_acquisition_accepts_public_https_url() -> None:
    settings.run_tasks_inline = False
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)

    response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/public-url",
        json={
            "source_url": f"https://example.com/tender/{uuid4().hex}.pdf",
            "source_site": "示例资源站点",
            "title": "公开附件",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["validation_status"] == "allowed"
    assert payload["normalized_url"].startswith("https://example.com/")
    assert payload["task"]["status"] == "pending"
