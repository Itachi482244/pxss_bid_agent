from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import AsyncTask, AuditLog, Document, FileAcquisitionTask, ParseTask
from app.services import file_acquisition
from app.services.file_acquisition import DownloadedFile, execute_file_acquisition_task
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


def test_file_acquisition_worker_downloads_file_and_creates_parse_task(monkeypatch) -> None:
    settings.run_tasks_inline = False
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    source_url = f"https://example.com/tender/{uuid4().hex}.pdf"

    response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/public-url",
        json={
            "source_url": source_url,
            "source_site": "示例资源站点",
            "title": "Worker 下载附件",
        },
    )
    assert response.status_code == 202
    acquisition_payload = response.json()
    task_id = UUID(acquisition_payload["task"]["id"])

    def fake_fetch_public_file(url: str, *, max_redirects: int = 5) -> DownloadedFile:
        assert url == source_url
        assert max_redirects == 5
        return DownloadedFile(
            final_url=url,
            filename="worker-tender.pdf",
            content_type="application/pdf",
            content_length=26,
            http_status=200,
            redirect_chain=[],
            data=b"%PDF-1.4\nworker tender file",
        )

    monkeypatch.setattr(file_acquisition, "fetch_public_file", fake_fetch_public_file)

    with SessionLocal() as db:
        result = execute_file_acquisition_task(db, task_id)
        assert result["status"] == "succeeded"
        document_id = UUID(result["document_id"])

        acquisition = db.scalar(
            select(FileAcquisitionTask).where(FileAcquisitionTask.task_id == task_id)
        )
        assert acquisition is not None
        assert acquisition.target_document_id == document_id
        assert acquisition.http_status == 200
        assert acquisition.content_length == 26

        task = db.get(AsyncTask, task_id)
        assert task is not None
        assert task.status == "succeeded"
        assert task.progress == 100
        assert task.output_json is not None
        assert task.output_json["document_id"] == str(document_id)

        document = db.get(Document, document_id)
        assert document is not None
        assert document.source_type == "public_url"
        assert document.status == "parsing"
        assert document.current_version_id is not None

        parse_task = db.scalar(select(ParseTask).where(ParseTask.document_id == document_id))
        assert parse_task is not None
        assert parse_task.parser_type == "pdf_text"

        audit_actions = db.scalars(
            select(AuditLog.action).where(AuditLog.object_id.in_([document_id, parse_task.id]))
        ).all()
        assert "document.public_url_downloaded" in audit_actions
        assert "document.parse_started" in audit_actions

        repeated = execute_file_acquisition_task(db, task_id)
        assert repeated["status"] == "already_succeeded"
        document_count = db.scalar(select(func.count(Document.id)).where(Document.source_url == source_url))
        assert document_count == 1
