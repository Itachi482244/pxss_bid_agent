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
from types import SimpleNamespace
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from docx import Document as WordDocument
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import (
    AuditLog,
    BusinessDraftChapter,
    ComplianceItem,
    DraftContextPack,
    DraftFactCheck,
    QualificationDecision,
    Tenant,
    User,
)
from app.services.business_draft import (
    _chapter_label_rows,
    _configure_bid_document,
    _directory_lines,
    _engineering_fact_candidates,
    _fact_supported_by_corpus,
    _performance_fact_candidates,
    _personnel_fact_candidates,
    _sanitize_export_paragraph,
)
from app.services.context_pack import _content_quality_policy
from app.services.context_pack import _build_outline_plan, _build_section_draft_content
from app.services.template_profile import get_template_profile
from scripts.seed_dev_data import (
    DEMO_TENANT_CODE,
    DEMO_USER_EXTERNAL_ID,
    seed,
    seed_mingzhu_mock_enterprise_data,
)
from test_mingzhu_mock_enterprise_data import _add_mingzhu_project_with_items

API = "/api/v1"
SECTION_TYPES = ["bid_letter", "bid_commitment", "qualification_performance_summary"]
INTERNAL_DRAFT_TERMS = [
    "字段填充草稿",
    "响应草稿",
    "已绑定证据",
    "事实性校验",
    "ContextPack",
    "MVP1.3",
    "project_name",
    "bidder_name",
    "legal_representative_name",
    "bid_date",
    "招标要求：",
    "投标响应：",
    "招标文件要求及投标响应",
    "燃气项目模拟-",
]


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
    rendered_text = "\n".join(
        [chapter["content_text"] for chapter in body["chapters"]]
        + [block["content_text"] for block in blocks]
    )
    for term in INTERNAL_DRAFT_TERMS:
        assert term not in rendered_text, f"internal term leaked into bid draft: {term}"

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


def test_word_export_sanitizes_review_only_bid_language() -> None:
    assert _sanitize_export_paragraph("1. 招标要求：类似工程业绩要求：不要求。") is None
    cleaned = _sanitize_export_paragraph(
        "我方响应：根据招标文件（招标项目编号：section-001），本次招标类似工程业绩不作为资格要求"
        "（证据：燃气项目模拟-类似业绩不作资格要求确认）。"
    )
    assert cleaned is not None
    assert "我方响应：" not in cleaned
    assert "招标项目编号：section-001" not in cleaned
    assert "证据：" not in cleaned
    assert "燃气项目模拟-" not in cleaned


def test_word_export_directory_uses_actual_chapter_titles() -> None:
    class Chapter:
        def __init__(self, title: str) -> None:
            self.title = title

    lines = _directory_lines(
        [
            Chapter("商务标封面"),  # type: ignore[list-item]
            Chapter("商务标目录"),  # type: ignore[list-item]
            Chapter("法定代表人身份证明书"),  # type: ignore[list-item]
            Chapter("授权委托书"),  # type: ignore[list-item]
            Chapter("投标函"),  # type: ignore[list-item]
        ]
    )
    assert lines == ["一、法定代表人身份证明书", "二、授权委托书", "三、投标函"]


def test_word_export_detects_label_value_rows_for_form_tables() -> None:
    rows, remaining = _chapter_label_rows(
        [
            "投 标 文 件",
            "项目名称：君山区城区燃气管网改造项目（EPC）",
            "补充说明：",
            "投标人：杭州明筑更新工程有限公司（盖单位章）",
            "1. 我方承诺全面响应招标文件要求。",
        ]
    )
    assert rows == [
        ("项目名称", "君山区城区燃气管网改造项目（EPC）"),
        ("投标人", "杭州明筑更新工程有限公司（盖单位章）"),
    ]
    assert remaining == ["投 标 文 件", "补充说明：", "1. 我方承诺全面响应招标文件要求。"]


def test_word_export_configures_bid_document_style() -> None:
    document = WordDocument()
    _configure_bid_document(document)

    section = document.sections[0]
    assert round(section.left_margin.cm, 1) == 3.0
    assert round(section.right_margin.cm, 1) == 2.5
    assert document.styles["Normal"].font.size.pt == 12
    assert document.styles["Heading 1"].font.bold is True


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


def test_engineering_fact_candidates_detect_unsupported_parameters() -> None:
    text = "本项目柳林洲段5.23km，采用DN160管道，设计压力0.4MPa，按GB1级管理，不得误写为高压输气。"
    facts = _engineering_fact_candidates(text)

    assert ("number", "5.23km") in facts
    assert ("number", "DN160") in facts
    assert ("number", "0.4MPa") in facts
    assert ("other", "GB1级") in facts
    assert ("other", "高压") in facts

    corpus = "招标文件载明：DN160，设计压力0.4MPa，压力管道GB1级，中压A。"
    assert _fact_supported_by_corpus("number", "DN160", corpus) is True
    assert _fact_supported_by_corpus("number", "0.4MPa", corpus) is True
    assert _fact_supported_by_corpus("other", "GB1级", corpus) is True
    assert _fact_supported_by_corpus("number", "5.23km", corpus) is False
    assert _fact_supported_by_corpus("other", "高压", corpus) is False


def test_gas_epc_content_quality_policy_blocks_unverified_engineering_inference() -> None:
    project = SimpleNamespace(
        name="君山区城区燃气管网改造项目（EPC）",
        purchaser="岳阳市君山区城市建设投资有限公司",
        industry_code="燃气",
        region_code="湖南岳阳",
    )
    section = SimpleNamespace(name="城区燃气管网改造 EPC 标段", code="")
    item = SimpleNamespace(
        requirement_text="本项目为中压A燃气管网改造，DN90/DN110/DN160，设计压力0.4MPa，EPC工程总承包。",
        normalized_requirement="燃气管网 EPC 工程总承包",
        response_suggestion="",
        evidence_text="",
        item_type="technical_response",
    )

    policy = _content_quality_policy(project, section, [item])

    assert policy["domain"] == "municipal_gas_pipeline_epc"
    assert any("工程量清单" in rule and "不得" in rule for rule in policy["missing_material_strategy"])
    assert any("实地勘察" in rule for rule in policy["missing_material_strategy"])
    assert any("长输输气" in rule for rule in policy["industry_focus"])
    assert "中压 GB1 燃气管道施工组织方案" in policy["recommended_technical_chapters"]


def _fake_compliance_item(**overrides):
    defaults = {
        "id": uuid4(),
        "item_type": "technical_response",
        "requirement_text": "本项目为中压A燃气管网改造，DN90/DN110/DN160，设计压力0.4MPa，EPC工程总承包。",
        "normalized_requirement": "燃气管网 EPC 工程总承包",
        "response_suggestion": "",
        "evidence_text": "",
        "status": "confirmed",
        "risk_level": "medium",
        "is_mandatory": False,
        "explanation_json": {"enterprise_evidence_not_required": True},
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_gas_epc_outline_auto_adds_technical_bid_sections() -> None:
    profile = get_template_profile("engineering_construction_business_v1")
    project = SimpleNamespace(
        name="君山区城区燃气管网改造项目（EPC）",
        purchaser="岳阳市君山区城市建设投资有限公司",
        industry_code="燃气",
        region_code="湖南岳阳",
    )
    section = SimpleNamespace(name="城区燃气管网改造 EPC 标段", code="")
    item = _fake_compliance_item()
    policy = _content_quality_policy(project, section, [item])

    plan = _build_outline_plan(
        profile=profile,
        items=[item],
        section_types=None,
        content_quality_policy=policy,
    )
    section_types = [section["section_type"] for section in plan["sections"]]

    assert "business_cover" in section_types
    assert "gas_project_understanding" in section_types
    assert "gas_pipeline_construction_method" in section_types
    assert "gas_pressure_test_purge_acceptance" in section_types
    gas_section = next(section for section in plan["sections"] if section["section_type"] == "gas_pipeline_construction_method")
    assert gas_section["volume_title"] == "投标文件技术标"
    assert gas_section["generation_mode"] == "technical_generated_paragraph"


def test_non_gas_outline_does_not_auto_add_gas_technical_sections() -> None:
    profile = get_template_profile("engineering_construction_business_v1")
    project = SimpleNamespace(
        name="明珠公寓老旧小区综合改造提升项目",
        purchaser="杭州市上城区九堡街道明珠公寓业委会",
        industry_code="building-renovation",
        region_code="CN-330102",
    )
    section = SimpleNamespace(name="建安工程一标段", code="")
    item = _fake_compliance_item(
        requirement_text="质量要求：符合现行国家有关工程施工验收规范和标准的合格要求。",
        normalized_requirement="质量要求",
    )
    policy = _content_quality_policy(project, section, [item])

    plan = _build_outline_plan(
        profile=profile,
        items=[item],
        section_types=None,
        content_quality_policy=policy,
    )
    section_types = {section["section_type"] for section in plan["sections"]}

    assert "gas_project_understanding" not in section_types
    assert "gas_pipeline_construction_method" not in section_types


def test_gas_technical_fallback_uses_source_facts_without_route_or_material_invention() -> None:
    context_json = {
        "section": {
            "section_type": "gas_pipeline_construction_method",
            "title": "中压GB1燃气管道施工组织方案",
            "required": False,
            "generation_mode": "technical_generated_paragraph",
            "required_fields": ["project_name"],
        },
        "project_facts": {
            "project_name": "君山区城区燃气管网改造项目（EPC）",
            "construction_period_days": 270,
            "quality_standard": "合格",
        },
        "tender_engineering_facts": {
            "pipeline_lengths": ["13.23km"],
            "pipe_diameters": ["DN90", "DN110", "DN160"],
            "pressure_levels": ["中压A", "0.4MPa"],
            "license_or_standards": ["GB1级"],
            "period_terms": ["270日历日"],
        },
        "matrix_items": [],
        "author_directives": [],
    }
    section_pack = SimpleNamespace(
        context_json=context_json,
        generation_mode="technical_generated_paragraph",
        section_type="gas_pipeline_construction_method",
        title="中压GB1燃气管道施工组织方案",
    )

    content, refs = _build_section_draft_content(section_pack)  # type: ignore[arg-type]

    assert refs == []
    assert "13.23km" in content
    assert "DN160" in content
    assert "0.4MPa" in content
    assert "GB1级" in content
    assert "以施工图" in content or "以招标人最终发布或审定资料为准" in content
    assert "柳林洲段5.23km" not in content
    assert "经实地勘察" not in content
    assert "高压输气" not in content


# --- #2(扩展) 章节级目录编辑：增/删/改名/重排 ---


def _outline_sections(client: TestClient, project_id: str, section_id: str, outline=None):
    payload: dict = {"profile_id": "engineering_construction_business_v1"}
    if outline is not None:
        payload["outline"] = outline
    resp = client.post(f"{_base(project_id, section_id)}/context-pack/preview", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()["outline_plan_json"]["sections"]


def test_outline_override_reorders_renames_and_adds_custom_chapter() -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)

    # 重排（反转）+ 改名第一章 + 末尾新增自定义章节。
    reordered = list(reversed(SECTION_TYPES))
    outline = [{"section_type": st} for st in reordered]
    outline[0]["title"] = "重命名后的开标函"
    outline.append({"section_type": "custom_extra", "title": "我方补充说明", "custom": True})

    sections = _outline_sections(client, project_id, section_id, outline)

    assert [s["section_type"] for s in sections] == reordered + ["custom_extra"]
    assert sections[0]["title"] == "重命名后的开标函"

    custom = sections[-1]
    assert custom["custom"] is True
    assert custom["title"] == "我方补充说明"
    assert custom["generation_mode"] == "manual_placeholder"


def test_outline_removal_shrinks_sections() -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)

    full = _outline_sections(client, project_id, section_id)
    full_types = [s["section_type"] for s in full]
    assert len(full_types) >= 2

    kept = [{"section_type": full_types[0]}]
    trimmed = _outline_sections(client, project_id, section_id, kept)
    assert [s["section_type"] for s in trimmed] == [full_types[0]]


def test_create_with_edited_outline_generates_custom_placeholder_block() -> None:
    client = TestClient(app)
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
        row.recommendation = "go"
        db.commit()
    client.post(
        f"{API}/projects/{project_id}/sections/{section_id}/"
        f"qualification-decision/{decision['id']}/confirm",
        json={"reason": "目录编辑测试：确认参标建议"},
    )

    outline = [
        {"section_type": "bid_letter"},
        {"section_type": "custom_extra", "title": "我方补充说明", "custom": True},
    ]
    cp = client.post(
        f"{_base(project_id, section_id)}/context-pack",
        json={"profile_id": "engineering_construction_business_v1", "outline": outline},
    )
    assert cp.status_code == 200, cp.text
    context_pack = cp.json()
    pack_types = {p["section_type"] for p in context_pack["section_context_packs"]}
    assert pack_types == {"bid_letter", "custom_extra"}

    result = client.post(
        f"{_base(project_id, section_id)}/context-pack/{context_pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )
    assert result.status_code == 200, result.text
    blocks = result.json()["blocks"]
    custom_blocks = [
        b
        for b in blocks
        if b["links_json"].get("section_type") == "custom_extra"
    ]
    assert custom_blocks, "自定义章节应至少生成一个占位块"
    placeholder = next((b for b in custom_blocks if b["block_type"] == "placeholder"), None)
    assert placeholder is not None
    assert "人工新增" in placeholder["content_text"]
    assert placeholder["review_status"] == "needs_fact"


def test_outline_duplicate_section_type_rejected() -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)
    resp = client.post(
        f"{_base(project_id, section_id)}/context-pack/preview",
        json={
            "profile_id": "engineering_construction_business_v1",
            "outline": [
                {"section_type": "bid_letter"},
                {"section_type": "bid_letter"},
            ],
        },
    )
    assert resp.status_code == 422, resp.text


def test_outline_custom_without_title_rejected() -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)
    resp = client.post(
        f"{_base(project_id, section_id)}/context-pack/preview",
        json={
            "profile_id": "engineering_construction_business_v1",
            "outline": [{"section_type": "custom_only", "custom": True}],
        },
    )
    assert resp.status_code == 422, resp.text


def test_outline_unknown_section_type_rejected() -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)
    resp = client.post(
        f"{_base(project_id, section_id)}/context-pack/preview",
        json={
            "profile_id": "engineering_construction_business_v1",
            "outline": [{"section_type": "does_not_exist_section"}],
        },
    )
    assert resp.status_code == 409, resp.text


# --- 指令层（author directives）：风格/侧重/强制措辞 ---


def _create_pack_with_directives(client: TestClient, directives: list[dict]):
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)
    cp = client.post(
        f"{_base(project_id, section_id)}/context-pack",
        json={
            "profile_id": "engineering_construction_business_v1",
            "section_types": SECTION_TYPES,
            "directives": directives,
        },
    )
    assert cp.status_code == 200, cp.text
    return project_id, section_id, cp.json()


def test_directives_attach_to_pack_and_section_context() -> None:
    client = TestClient(app)
    project_id, section_id, pack = _create_pack_with_directives(
        client,
        [
            {"scope": "pack", "directive_type": "style", "text": "语气更正式、简洁。"},
            {
                "scope": "bid_letter",
                "directive_type": "emphasis",
                "text": "突出我方对工期的承诺。",
            },
        ],
    )

    pack_directives = pack["context_json"]["author_directives"]
    assert len(pack_directives) == 2
    assert {d["directive_type"] for d in pack_directives} == {"style", "emphasis"}
    assert all(d.get("id") and d.get("author_user_id") for d in pack_directives)

    # Pack-scoped directive reaches every section; section-scoped only its section.
    bid_letter = next(
        p for p in pack["section_context_packs"] if p["section_type"] == "bid_letter"
    )
    other = next(
        p for p in pack["section_context_packs"] if p["section_type"] != "bid_letter"
    )
    bid_letter_types = {
        d["directive_type"] for d in bid_letter["context_json"]["author_directives"]
    }
    other_types = {
        d["directive_type"] for d in other["context_json"]["author_directives"]
    }
    assert bid_letter_types == {"style", "emphasis"}
    assert other_types == {"style"}


def test_mandatory_text_directive_becomes_needs_confirm_block() -> None:
    client = TestClient(app)
    project_id, section_id, pack = _create_pack_with_directives(
        client,
        [
            {
                "scope": "bid_letter",
                "directive_type": "mandatory_text",
                "text": "我方郑重承诺严格遵守招标文件全部商务条款。",
            }
        ],
    )

    result = client.post(
        f"{_base(project_id, section_id)}/context-pack/{pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )
    assert result.status_code == 200, result.text
    body = result.json()
    mandatory = [
        b
        for b in body["blocks"]
        if (b["links_json"] or {}).get("source") == "author_mandatory_text"
    ]
    assert len(mandatory) == 1, "强制措辞应生成一个独立块"
    block = mandatory[0]
    assert block["review_status"] == "needs_confirm"
    assert "我方郑重承诺" in block["content_text"]

    coverage = body["coverage_review"]
    assert coverage["summary_json"]["mandatory_text_pending_count"] == 1
    assert any(
        issue["code"] == "coverage.mandatory_text_needs_confirm"
        for issue in coverage["issues_json"]
    )


def test_mandatory_text_smuggled_hard_fact_is_flagged_by_fact_check() -> None:
    client = TestClient(app)
    project_id, section_id, pack = _create_pack_with_directives(
        client,
        [
            {
                "scope": "bid_letter",
                "directive_type": "mandatory_text",
                "text": "我方持有证书编号ZZ20260101FAKE9，符合全部资格要求。",
            }
        ],
    )
    result = client.post(
        f"{_base(project_id, section_id)}/context-pack/{pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )
    assert result.status_code == 200, result.text

    with SessionLocal() as db:
        unverified = db.scalars(
            select(DraftFactCheck).where(
                DraftFactCheck.project_id == UUID(project_id),
                DraftFactCheck.section_id == UUID(section_id),
                DraftFactCheck.fact_text == "ZZ20260101FAKE9",
            )
        ).all()
    assert unverified, "强制措辞中夹带的硬事实必须进入事实核查"
    assert all(check.check_status == "unverified" for check in unverified)
    assert all(check.risk_level == "high" for check in unverified)


def test_export_gated_until_mandatory_text_block_confirmed() -> None:
    client = TestClient(app)
    project_id, section_id, pack = _create_pack_with_directives(
        client,
        [
            {
                "scope": "bid_letter",
                "directive_type": "mandatory_text",
                "text": "我方承诺按招标文件要求提供售后服务。",
            }
        ],
    )
    client.post(
        f"{_base(project_id, section_id)}/context-pack/{pack['id']}/generate",
        json={"allow_blocked_internal_draft": False},
    )

    preflight = client.get(
        f"{API}/projects/{project_id}/sections/{section_id}/preflight-check"
    ).json()
    block_review = next(
        c for c in preflight["checks"] if c["code"] == "draft_block_review"
    )
    assert block_review["status"] != "pass", "存在待确认强制措辞时不应放行导出"

    # Confirming (approving) the mandatory-text block is accepted by the API.
    blocks = client.get(f"{_base(project_id, section_id)}/blocks").json()
    mandatory = next(
        b for b in blocks if (b["links_json"] or {}).get("source") == "author_mandatory_text"
    )
    confirmed = client.patch(
        f"{_base(project_id, section_id)}/blocks/{mandatory['id']}",
        json={"review_status": "approved", "reason": "人工确认强制措辞"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["review_status"] == "approved"


def test_lightweight_rebuild_reuses_fact_snapshot_and_supersedes() -> None:
    client = TestClient(app)
    project_id, section_id, pack = _create_pack_with_directives(
        client,
        [{"scope": "pack", "directive_type": "style", "text": "语气正式。"}],
    )
    original_matrix = pack["context_json"]["matrix_items"]

    rebuilt = client.put(
        f"{_base(project_id, section_id)}/context-pack/{pack['id']}/directives",
        json={
            "directives": [
                {"scope": "pack", "directive_type": "emphasis", "text": "突出本地化服务。"},
                {
                    "scope": "bid_letter",
                    "directive_type": "mandatory_text",
                    "text": "我方承诺响应全部商务条款。",
                },
            ]
        },
    )
    assert rebuilt.status_code == 200, rebuilt.text
    new_pack = rebuilt.json()

    assert new_pack["id"] != pack["id"]
    assert new_pack["status"] == "confirmed"
    # Fact snapshot is reused verbatim (no upstream re-query).
    assert new_pack["context_json"]["matrix_items"] == original_matrix
    new_types = {d["directive_type"] for d in new_pack["context_json"]["author_directives"]}
    assert new_types == {"emphasis", "mandatory_text"}

    with SessionLocal() as db:
        prior = db.get(DraftContextPack, UUID(pack["id"]))
        assert prior is not None and prior.status == "superseded"
        audit = db.scalars(
            select(AuditLog).where(
                AuditLog.project_id == UUID(project_id),
                AuditLog.action == "business_draft.context_pack_directives_updated",
            )
        ).all()
        assert audit, "轻量重建必须写审计日志"
        assert audit[-1].after_json.get("lightweight_rebuild") is True

    # Only the new pack survives the active listing.
    listed = client.get(f"{_base(project_id, section_id)}/context-pack").json()
    active_ids = {p["id"] for p in listed}
    assert new_pack["id"] in active_ids
    assert pack["id"] not in active_ids


def test_directive_unknown_scope_rejected() -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)
    resp = client.post(
        f"{_base(project_id, section_id)}/context-pack",
        json={
            "profile_id": "engineering_construction_business_v1",
            "section_types": SECTION_TYPES,
            "directives": [
                {
                    "scope": "no_such_section",
                    "directive_type": "style",
                    "text": "语气正式。",
                }
            ],
        },
    )
    assert resp.status_code == 409, resp.text


def test_directive_invalid_type_rejected() -> None:
    client = TestClient(app)
    project_id, section_id, _ = _prepare_confirmed_context_pack(client)
    resp = client.post(
        f"{_base(project_id, section_id)}/context-pack",
        json={
            "profile_id": "engineering_construction_business_v1",
            "section_types": SECTION_TYPES,
            "directives": [
                {"scope": "pack", "directive_type": "rewrite_facts", "text": "改写事实。"}
            ],
        },
    )
    assert resp.status_code == 422, resp.text
