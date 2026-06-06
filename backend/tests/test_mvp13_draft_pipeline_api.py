"""MVP1.3 acceptance tests for the ContextPack-driven draft pipeline.

Covers the fixed-sample scenarios required by 投标Agent MVP-v1.3 §9.10:
normal generation, outline selection, generation gating (unconfirmed
qualification / readiness=block rejection), internal draft via risk
acceptance, model-failure degradation, manual edit + re-fact-check, and
export gating. Personnel/track-record fact rules (#7) are unit tested.

The scaffold reuses the Mingzhu mock enterprise data (fully bound evidence +
confirmable ContextPack) from ``test_mingzhu_mock_enterprise_data``.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import (
    BusinessDraftChapter,
    ComplianceItem,
    DraftContextPack,
    QualificationDecision,
    Tenant,
    User,
)
from app.services.business_draft import (
    _performance_fact_candidates,
    _personnel_fact_candidates,
)
from scripts.seed_dev_data import (
    DEMO_TENANT_CODE,
    DEMO_USER_EXTERNAL_ID,
    seed,
    seed_mingzhu_mock_enterprise_data,
)
from test_mingzhu_mock_enterprise_data import _add_mingzhu_project_with_items

API = "/api/v1"
SECTION_TYPES = ["bid_letter", "bid_commitment", "qualification_performance_summary"]


def setup_module() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def _base(project_id: str, section_id: str) -> str:
    return f"{API}/projects/{project_id}/sections/{section_id}/business-draft"


def _prepare_confirmed_context_pack(
    client: TestClient,
    *,
    section_types: list[str] | None = None,
    force_recommendation: str = "go",
) -> tuple[str, str, dict]:
    """Build a project with bound evidence and a confirmed ContextPack.

    Items are confirmed and the qualification recommendation is forced so the
    normal path is deterministic regardless of the auto evaluation outcome.
    """
    project_id, section_id = _add_mingzhu_project_with_items()
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.code == DEMO_TENANT_CODE))
        user = db.scalar(select(User).where(User.external_id == DEMO_USER_EXTERNAL_ID))
        assert tenant is not None and user is not None
        seed_mingzhu_mock_enterprise_data(db, tenant, user)
        items = db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.project_id == UUID(project_id),
                ComplianceItem.section_id == UUID(section_id),
            )
        ).all()
        for item in items:
            item.status = "confirmed"
        db.commit()

    decision = client.post(
        f"{API}/projects/{project_id}/sections/{section_id}/qualification-decision/generate"
    ).json()
    with SessionLocal() as db:
        row = db.get(QualificationDecision, UUID(decision["id"]))
        assert row is not None
        row.recommendation = force_recommendation
        db.commit()
    confirm = client.post(
        f"{API}/projects/{project_id}/sections/{section_id}/"
        f"qualification-decision/{decision['id']}/confirm",
        json={"reason": "MVP1.3 草稿链路测试：确认参标建议"},
    )
    assert confirm.status_code == 200, confirm.text

    cp = client.post(
        f"{_base(project_id, section_id)}/context-pack",
        json={
            "profile_id": "engineering_construction_business_v1",
            "section_types": section_types or SECTION_TYPES,
        },
    )
    assert cp.status_code == 200, cp.text
    context_pack = cp.json()
    assert context_pack["status"] == "confirmed"
    return project_id, section_id, context_pack


# --- #1/#3/#4/#5/#8 normal structured generation with per-clause backlinks ---


def test_generate_produces_per_clause_blocks_with_backlinks() -> None:
    client = TestClient(app)
    project_id, section_id, context_pack = _prepare_confirmed_context_pack(client)

    result = client.post(
        f"{_base(project_id, section_id)}/context-pack/{context_pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["chapters"], "expected at least one generated chapter"
    blocks = body["blocks"]
    assert blocks, "expected structured draft blocks"

    block_types = {block["block_type"] for block in blocks}
    assert "heading" in block_types
    assert "paragraph" in block_types, "per-clause paragraph blocks must exist"

    # Each clause (paragraph) block links back to exactly one matrix item (#5/#8).
    clause_blocks = [b for b in blocks if b["block_type"] == "paragraph"]
    assert clause_blocks
    for block in clause_blocks:
        item_ids = block["links_json"].get("compliance_item_ids") or []
        assert len(item_ids) == 1, "clause block must backlink a single matrix item"

    # At least one clause block carries an enterprise evidence backlink (#5).
    assert any(
        block["links_json"].get("evidence_binding_ids") for block in clause_blocks
    ), "expected a clause block linked to bound evidence"

    coverage = body["coverage_review"]
    rate = coverage["summary_json"]["coverage_rate"]
    assert 0.0 <= rate <= 1.0, f"coverage_rate out of range: {rate}"

    # Blocks are retrievable for the review view and keep their backlinks.
    listed = client.get(f"{_base(project_id, section_id)}/blocks")
    assert listed.status_code == 200
    assert len(listed.json()) == len(blocks)


# --- #2 outline preview + human selection of section scope ---


def test_outline_plan_and_section_selection_is_honored() -> None:
    client = TestClient(app)
    _, _, full = _prepare_confirmed_context_pack(client, section_types=SECTION_TYPES)
    assert full["outline_plan_json"], "ContextPack must expose an editable outline plan"
    full_section_count = len(full["section_context_packs"])

    _, _, subset = _prepare_confirmed_context_pack(client, section_types=["bid_letter"])
    subset_section_count = len(subset["section_context_packs"])
    assert subset_section_count >= 1
    assert subset_section_count < full_section_count, (
        "selecting fewer section types must shrink the generated section context packs"
    )


# --- #1 generation gating: unconfirmed qualification is rejected ---


def test_generate_rejected_when_qualification_not_confirmed() -> None:
    client = TestClient(app)
    project_id, section_id, context_pack = _prepare_confirmed_context_pack(client)
    with SessionLocal() as db:
        decision = db.scalar(
            select(QualificationDecision).where(
                QualificationDecision.project_id == UUID(project_id),
                QualificationDecision.section_id == UUID(section_id),
                QualificationDecision.status != "superseded",
            )
        )
        assert decision is not None
        decision.status = "draft"
        db.commit()

    result = client.post(
        f"{_base(project_id, section_id)}/context-pack/{context_pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )
    assert result.status_code == 409
    assert "参标建议" in result.json()["detail"]


# --- #9 readiness=block rejected without risk acceptance; internal draft allowed ---


def test_blocked_context_pack_requires_internal_draft_flag() -> None:
    client = TestClient(app)
    project_id, section_id, context_pack = _prepare_confirmed_context_pack(client)
    with SessionLocal() as db:
        pack = db.get(DraftContextPack, UUID(context_pack["id"]))
        assert pack is not None
        pack.readiness_status = "block"
        db.commit()

    rejected = client.post(
        f"{_base(project_id, section_id)}/context-pack/{context_pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )
    assert rejected.status_code == 409
    assert "阻塞" in rejected.json()["detail"]

    internal = client.post(
        f"{_base(project_id, section_id)}/context-pack/{context_pack['id']}/generate",
        json={"allow_blocked_internal_draft": True},
    )
    assert internal.status_code == 200, internal.text
    chapters = internal.json()["chapters"]
    assert chapters
    with SessionLocal() as db:
        chapter = db.scalar(
            select(BusinessDraftChapter).where(
                BusinessDraftChapter.project_id == UUID(project_id),
                BusinessDraftChapter.section_id == UUID(section_id),
                BusinessDraftChapter.status != "superseded",
            )
        )
        assert chapter is not None
        assert chapter.generated_from_json.get("internal_draft") is True


# --- #7 manual edit recomposes chapter text and re-runs fact checks ---


def test_manual_block_edit_recomposes_chapter_and_reruns_fact_check() -> None:
    client = TestClient(app)
    project_id, section_id, context_pack = _prepare_confirmed_context_pack(client)
    generated = client.post(
        f"{_base(project_id, section_id)}/context-pack/{context_pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    ).json()
    paragraph = next(b for b in generated["blocks"] if b["block_type"] == "paragraph")

    edited = client.patch(
        f"{_base(project_id, section_id)}/blocks/{paragraph['id']}",
        json={
            "review_status": "approved",
            "content_text": "招标要求：人工修订后的条款响应\n响应草稿：我方已据实修订本条款。",
            "reason": "人工修订条款表述",
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["review_status"] == "approved"

    with SessionLocal() as db:
        chapter = db.get(BusinessDraftChapter, UUID(paragraph["chapter_id"]))
        assert chapter is not None
        assert "人工修订后的条款响应" in chapter.content_text
        assert chapter.edit_reason == "人工修订条款表述"
        assert chapter.fact_check_status in {"verified", "unverified"}


# --- #9 export gating: blocked preflight rejects clean export, internal draft ok ---


def test_export_word_gated_until_blocks_resolved_or_risk_accepted() -> None:
    client = TestClient(app)
    project_id, section_id, context_pack = _prepare_confirmed_context_pack(client)
    client.post(
        f"{_base(project_id, section_id)}/context-pack/{context_pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )

    # Freshly generated blocks are not approved -> preflight blocks the export.
    blocked = client.post(f"{_base(project_id, section_id)}/export-word", json={})
    assert blocked.status_code == 409

    # Risk acceptance allows an internal draft export.
    accepted = client.post(
        f"{_base(project_id, section_id)}/export-word",
        json={"risk_acceptance_reason": "内部草稿，风险已知悉并接受"},
    )
    assert accepted.status_code == 200, accepted.text
    snapshot = accepted.json()["source_snapshot_json"]
    assert snapshot["risk_acceptance_reason"] == "内部草稿，风险已知悉并接受"

    # Approving every block clears the structured-review preflight gate.
    blocks = client.get(f"{_base(project_id, section_id)}/blocks").json()
    for block in blocks:
        client.patch(
            f"{_base(project_id, section_id)}/blocks/{block['id']}",
            json={"review_status": "approved", "reason": "审阅通过"},
        )
    preflight = client.get(
        f"{API}/projects/{project_id}/sections/{section_id}/preflight-check"
    ).json()
    block_review = next(
        (c for c in preflight["checks"] if c["code"] == "draft_block_review"), None
    )
    assert block_review is not None
    assert block_review["status"] == "pass"


# --- §7 model-failure degradation on the LLM-backed legacy chapter path ---


def test_chapter_generation_degrades_to_template_on_model_failure(monkeypatch) -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)

    from app.services.llm_gateway import LLMGatewayError

    def _boom(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise LLMGatewayError("simulated model failure")

    monkeypatch.setattr("app.services.business_draft.chat_completion", _boom)
    result = client.post(
        f"{_base(project_id, section_id)}/chapters/generate",
        json={},
    )
    assert result.status_code == 200, result.text
    chapters = result.json()
    assert chapters, "model failure must still yield a template-backed draft"
    with SessionLocal() as db:
        rows = db.scalars(
            select(BusinessDraftChapter).where(
                BusinessDraftChapter.project_id == UUID(project_id),
                BusinessDraftChapter.section_id == UUID(section_id),
                BusinessDraftChapter.status != "superseded",
            )
        ).all()
        assert rows
        assert all(
            row.generated_from_json.get("generator") == "template" for row in rows
        )


# --- #7 personnel / track-record fact detection rules (pure functions) ---


def test_personnel_fact_candidates_detect_names_ids_and_certs() -> None:
    text = (
        "项目经理：王建安，身份证号330102198806168888，"
        "注册建造师证号为GD201912345678；项目总工由李工负责。"
    )
    facts = _personnel_fact_candidates(text)
    assert ("person_name", "王建安") in facts
    assert ("person_name", "330102198806168888") in facts
    assert ("certificate_no", "GD201912345678") in facts
    # Filler words after a role keyword must not be captured as a name.
    assert ("person_name", "我方") not in facts


def test_performance_fact_candidates_detect_amount_and_contract() -> None:
    text = "类似工程：《某老旧小区改造工程》，合同金额：325.5万元，业主满意。"
    facts = _performance_fact_candidates(text)
    assert ("amount", "325.5万元") in facts
    assert ("other", "某老旧小区改造工程") in facts
