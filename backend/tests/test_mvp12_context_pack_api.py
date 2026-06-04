from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

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


def test_mvp12_context_pack_preview_generate_blocks_and_coverage() -> None:
    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
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
    confirmed_decision = confirm_decision_response.json()
    assert confirmed_decision["status"] == "confirmed"

    preview_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/context-pack/preview",
        json=payload,
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()
    assert preview["profile_id"] == "engineering_construction_business_v1"
    assert preview["schema_version"] == "1.0"
    assert preview["readiness_status"] in {"pass", "warn", "block"}
    assert preview["context_json"]["matrix_summary"]["total"] > 0
    assert preview["context_json"]["qualification_decision"]["status"] == "confirmed"
    assert preview["context_json"]["qualification_decision"]["recommendation"] in {
        "go",
        "conditional_go",
        "no_go",
    }
    section_types = [item["section_type"] for item in preview["outline_plan_json"]["sections"]]
    assert set(section_types) == set(payload["section_types"])

    create_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/context-pack",
        json=payload,
    )
    assert create_response.status_code == 200
    context_pack = create_response.json()
    assert context_pack["status"] == "confirmed"
    assert context_pack["section_context_packs"]
    assert context_pack["outline_plan_json"]["sections"][0]["section_type"] == "bid_letter"

    blocked_generate_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/"
            f"context-pack/{context_pack['id']}/generate"
        ),
        json={"allow_blocked_internal_draft": False},
    )
    if context_pack["readiness_status"] == "block":
        assert blocked_generate_response.status_code == 409
    else:
        assert blocked_generate_response.status_code == 200

    generate_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/"
            f"context-pack/{context_pack['id']}/generate"
        ),
        json={"allow_blocked_internal_draft": True},
    )
    assert generate_response.status_code == 200
    generated = generate_response.json()
    assert len(generated["chapters"]) == len(context_pack["section_context_packs"])
    assert generated["blocks"]
    assert generated["coverage_review"]["status"] in {"pass", "warn", "block"}
    assert any(
        chapter["outline_json"]["section_type"] == "bid_letter"
        and chapter["generated_from_json"]["context_pack_id"] == context_pack["id"]
        for chapter in generated["chapters"]
    )
    assert any(
        block["links_json"]["context_pack_id"] == context_pack["id"]
        and block["review_status"] in {"covered", "needs_evidence", "needs_fact"}
        for block in generated["blocks"]
    )

    blocks_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/blocks"
    )
    assert blocks_response.status_code == 200
    blocks = blocks_response.json()
    assert any(block["links_json"]["context_pack_id"] == context_pack["id"] for block in blocks)
    editable_block = next(block for block in blocks if block["block_type"] != "heading" and block["chapter_id"])
    edited_block_text = "MVP1.2 测试：人工编辑后的结构化 block 内容。"
    edit_block_response = client.patch(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/"
            f"blocks/{editable_block['id']}"
        ),
        json={
            "review_status": "pending",
            "content_text": edited_block_text,
            "reason": "测试 block 内容修改并同步章节",
        },
    )
    assert edit_block_response.status_code == 200
    assert edit_block_response.json()["content_text"] == edited_block_text
    refreshed_chapters_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/chapters"
    )
    assert refreshed_chapters_response.status_code == 200
    refreshed_chapters = refreshed_chapters_response.json()
    edited_chapter = next(item for item in refreshed_chapters if item["id"] == editable_block["chapter_id"])
    assert edited_chapter["content_text"] == edited_block_text

    preflight_before_review_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/preflight-check"
    )
    assert preflight_before_review_response.status_code == 200
    preflight_before_review = preflight_before_review_response.json()
    block_review_check = next(
        item for item in preflight_before_review["checks"] if item["code"] == "draft_block_review"
    )
    assert block_review_check["status"] == "block"
    assert block_review_check["count"] > 0

    blocked_export_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/export-word"
    )
    assert blocked_export_response.status_code == 409

    for block in blocks:
        update_block_response = client.patch(
            (
                f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/"
                f"blocks/{block['id']}"
            ),
            json={
                "review_status": "approved",
                "reason": "人工确认该 block 已覆盖对应上下文",
            },
        )
        assert update_block_response.status_code == 200
        assert update_block_response.json()["review_status"] == "approved"

    preflight_after_review_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/preflight-check"
    )
    assert preflight_after_review_response.status_code == 200
    preflight_after_review = preflight_after_review_response.json()
    reviewed_block_check = next(
        item for item in preflight_after_review["checks"] if item["code"] == "draft_block_review"
    )
    assert reviewed_block_check["status"] == "pass"
    assert reviewed_block_check["count"] == 0

    export_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/export-word",
        json={"risk_acceptance_reason": "ContextPack block 已审阅通过，其他风险仅作内部草稿复核"},
    )
    assert export_response.status_code == 200
    export_file = export_response.json()
    assert export_file["export_type"] == "business_draft_word"
    assert export_file["source_snapshot_json"]["draft_block_review"]["unresolved"] == 0

    coverage_response = client.post(
        (
            f"/api/v1/projects/{project_id}/sections/{section_id}/business-draft/"
            f"context-pack/{context_pack['id']}/coverage-review"
        )
    )
    assert coverage_response.status_code == 200
    coverage = coverage_response.json()
    assert coverage["context_pack_id"] == context_pack["id"]
    assert coverage["summary_json"]["block_count"] >= len(generated["blocks"])
    assert 0 <= coverage["summary_json"]["quality_score"] <= 100
    assert 0 <= coverage["summary_json"]["coverage_rate"] <= 1
