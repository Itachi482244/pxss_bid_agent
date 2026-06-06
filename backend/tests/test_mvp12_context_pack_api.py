from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import ComplianceItem
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


def test_mvp12_context_pack_preview_confirm_and_supersede_without_draft_blocks() -> None:
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    base = f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft"
    payload = {
        "profile_id": "engineering_construction_business_v1",
        "section_types": [
            "bid_letter",
            "bid_commitment",
            "qualification_performance_summary",
            "priced_boq",
        ],
    }

    decision_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/qualification-decision/generate"
    )
    assert decision_response.status_code == 200
    decision = decision_response.json()
    confirm_decision_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/"
            f"qualification-decision/{decision['id']}/confirm"
        ),
        json={"reason": "测试确认参标建议，允许进入 ContextPack"},
    )
    assert confirm_decision_response.status_code == 200
    assert confirm_decision_response.json()["status"] == "confirmed"

    with SessionLocal() as db:
        items = list(
            db.scalars(
                select(ComplianceItem).where(
                    ComplianceItem.project_id == UUID(project_id),
                    ComplianceItem.section_id == UUID(section_id),
                    ComplianceItem.deleted_at.is_(None),
                )
            ).all()
        )
        for item in items:
            item.status = "confirmed"
            explanation = dict(item.explanation_json or {})
            explanation["enterprise_evidence_not_required"] = True
            explanation["enterprise_evidence_not_required_reason"] = "MVP1.2 ContextPack API 测试已人工核验"
            item.explanation_json = explanation
        db.commit()

    blocks_before_response = client.get(f"{base}/blocks")
    assert blocks_before_response.status_code == 200
    block_ids_before = {item["id"] for item in blocks_before_response.json()}

    preview_response = client.post(f"{base}/context-pack/preview", json=payload)
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["profile_id"] == "engineering_construction_business_v1"
    assert preview["schema_version"] == "1.0"
    assert preview["readiness_status"] in {"pass", "warn", "block"}
    assert preview["context_json"]["matrix_summary"]["total"] > 0
    assert preview["context_json"]["qualification_decision"]["status"] == "confirmed"
    assert isinstance(preview["context_json"]["bound_evidence"], list)
    assert isinstance(preview["context_json"]["missing_facts"], list)
    readiness_checks = preview["readiness_json"]["checks"]
    assert all(check.get("summary") and check.get("action") for check in readiness_checks)
    assert not [
        check
        for check in readiness_checks
        if check["status"] == "block" and check["code"] != "qualification.no_go_confirmed"
    ]
    section_types = [item["section_type"] for item in preview["outline_plan_json"]["sections"]]
    assert set(section_types) == set(payload["section_types"])

    create_response = client.post(f"{base}/context-pack", json=payload)
    assert create_response.status_code == 200
    context_pack = create_response.json()
    assert context_pack["status"] == "confirmed"
    assert context_pack["readiness_status"] == preview["readiness_status"]
    assert len(context_pack["section_context_packs"]) == len(payload["section_types"])
    assert context_pack["outline_plan_json"]["sections"][0]["section_type"] == "bid_letter"
    assert all(section_pack["context_json"]["section"] for section_pack in context_pack["section_context_packs"])

    blocks_after_first_context_pack = client.get(f"{base}/blocks")
    assert blocks_after_first_context_pack.status_code == 200
    assert {item["id"] for item in blocks_after_first_context_pack.json()} == block_ids_before

    second_payload = {
        "profile_id": "engineering_construction_business_v1",
        "section_types": ["bid_letter", "bid_commitment"],
    }
    second_create_response = client.post(f"{base}/context-pack", json=second_payload)
    assert second_create_response.status_code == 200
    second_context_pack = second_create_response.json()
    assert second_context_pack["id"] != context_pack["id"]
    assert len(second_context_pack["section_context_packs"]) == len(second_payload["section_types"])

    list_response = client.get(f"{base}/context-pack")
    assert list_response.status_code == 200
    active_context_packs = list_response.json()
    assert active_context_packs
    assert active_context_packs[0]["id"] == second_context_pack["id"]
    assert context_pack["id"] not in {item["id"] for item in active_context_packs}

    blocks_after_second_context_pack = client.get(f"{base}/blocks")
    assert blocks_after_second_context_pack.status_code == 200
    assert {item["id"] for item in blocks_after_second_context_pack.json()} == block_ids_before
