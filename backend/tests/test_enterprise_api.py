from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models import AuditLog, ComplianceEvidenceBinding, ComplianceItem, Document, DocumentChunk, EnterpriseMaterial
from scripts.seed_dev_data import seed


@pytest.fixture(scope="module", autouse=True)
def prepare_database() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    command.upgrade(config, "head")
    seed()


def test_enterprise_profile_upsert_and_audit_log() -> None:
    client = TestClient(app)
    company_name = f"测试投标企业 {uuid4().hex[:8]}"

    response = client.put(
        "/api/v1/enterprise/profile",
        json={
            "company_name": company_name,
            "unified_social_credit_code": "91430600TEST000001",
            "legal_representative": "张三",
            "registered_address": "岳阳市君山区",
            "business_scope": "市政工程施工；燃气管网改造。",
            "region_preferences": ["湖南省", "岳阳市"],
            "industry_preferences": ["市政", "燃气"],
            "forbidden_rules": ["存在未结清重大诉讼时禁止参标"],
        },
    )

    assert response.status_code == 200
    profile = response.json()
    assert profile["company_name"] == company_name
    assert profile["region_preferences"] == ["湖南省", "岳阳市"]

    read_response = client.get("/api/v1/enterprise/profile")
    assert read_response.status_code == 200
    assert read_response.json()["company_name"] == company_name

    with SessionLocal() as db:
        logs = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "enterprise.profile_updated",
                AuditLog.object_id == UUID(profile["id"]),
            )
        ).all()
        create_logs = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "enterprise.profile_created",
                AuditLog.object_id == UUID(profile["id"]),
            )
        ).all()
        assert logs or create_logs


def test_enterprise_material_crud_and_file_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    stored_objects: list[dict[str, object]] = []

    def fake_put_object_bytes(**kwargs: object) -> None:
        stored_objects.append(kwargs)

    monkeypatch.setattr("app.api.v1.routes.enterprise.put_object_bytes", fake_put_object_bytes)
    client = TestClient(app)

    create_response = client.post(
        "/api/v1/enterprise/materials",
        json={
            "material_type": "qualification",
            "name": "市政公用工程施工总承包二级资质",
            "issuing_authority": "湖南省住房和城乡建设厅",
            "certificate_no": "D243TEST001",
            "valid_until": "2027-12-31",
            "data_level": "internal",
            "verification_status": "pending_confirm",
            "structured_fields": {"qualification_category": "市政公用工程施工总承包", "grade": "二级"},
            "evidence_text": "证书载明资质类别为市政公用工程施工总承包二级。",
        },
    )
    assert create_response.status_code == 201
    material = create_response.json()
    assert material["material_type"] == "qualification"
    assert material["structured_fields"]["grade"] == "二级"

    upload_response = client.post(
        f"/api/v1/enterprise/materials/{material['id']}/file",
        files={"file": ("qualification.txt", b"qualification evidence", "text/plain")},
        data={"reason": "补充资质证书扫描件"},
    )
    assert upload_response.status_code == 200
    uploaded = upload_response.json()
    assert uploaded["file_name"] == "qualification.txt"
    assert uploaded["sha256"]
    assert stored_objects

    update_response = client.patch(
        f"/api/v1/enterprise/materials/{material['id']}",
        json={
            "verification_status": "confirmed",
            "reason": "资质管理员已核对原件",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["verification_status"] == "confirmed"

    list_response = client.get(
        "/api/v1/enterprise/materials",
        params={"material_type": "qualification", "verification_status": "confirmed"},
    )
    assert list_response.status_code == 200
    assert any(item["id"] == material["id"] for item in list_response.json())

    with SessionLocal() as db:
        saved = db.get(EnterpriseMaterial, UUID(material["id"]))
        assert saved is not None
        assert saved.object_key is not None
        logs = db.scalars(
            select(AuditLog).where(
                AuditLog.object_type == "enterprise_material",
                AuditLog.object_id == UUID(material["id"]),
            )
        ).all()
        assert {log.action for log in logs} >= {
            "enterprise.material_created",
            "enterprise.material_file_uploaded",
            "enterprise.material_updated",
        }


def test_cleanroom_presale_material_types_are_searchable() -> None:
    client = TestClient(app)
    unique = f"CLEANROOM-MVP1-{uuid4().hex[:8]}"
    create_response = client.post(
        "/api/v1/enterprise/materials",
        json={
            "material_type": "product_catalog",
            "name": f"洁净设备产品目录 {unique}",
            "data_level": "internal",
            "verification_status": "confirmed",
            "structured_fields": {
                "product_type": "高效过滤器",
                "model": "PXSS-HEPA-01",
                "industry": "cleanroom",
            },
            "evidence_text": f"{unique} 记录洁净设备型号、风量、过滤效率、安装调试和验收参数。",
        },
    )
    assert create_response.status_code == 201
    material = create_response.json()
    assert material["material_type"] == "product_catalog"

    list_response = client.get(
        "/api/v1/enterprise/materials",
        params={"material_type": "product_catalog"},
    )
    assert list_response.status_code == 200
    assert any(item["id"] == material["id"] for item in list_response.json())

    search_response = client.get(
        "/api/v1/enterprise/materials/search",
        params={"query": f"{unique} 检测报告 技术方案 验收", "limit": 10},
    )
    assert search_response.status_code == 200
    search_hit = next(item for item in search_response.json() if item["id"] == material["id"])
    assert search_hit["recommend_reason"]
    assert search_hit["matched_terms"]
    assert search_hit["material_status_hint"]

    chunks_response = client.get(f"/api/v1/enterprise/materials/{material['id']}/chunks")
    assert chunks_response.status_code == 200
    assert chunks_response.json()[0]["enterprise_material_id"] == material["id"]


def test_qualification_evaluation_matches_confirmed_license() -> None:
    client = TestClient(app)
    client.post(
        "/api/v1/enterprise/materials",
        json={
            "material_type": "license",
            "name": "有效营业执照",
            "issuing_authority": "岳阳市市场监督管理局",
            "certificate_no": "91430600EVAL000001",
            "valid_until": "2030-12-31",
            "data_level": "internal",
            "verification_status": "confirmed",
            "evidence_text": "营业执照载明企业主体有效。",
        },
    )
    projects = client.get("/api/v1/projects").json()
    project = next(item for item in projects if item["name"] == "智慧园区弱电工程投标")
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    section = sections[0]

    run_response = client.post(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-evaluations/run"
    )

    assert run_response.status_code == 200
    evaluations = run_response.json()
    license_eval = next(item for item in evaluations if "营业执照" in item["requirement_text"])
    assert license_eval["evaluation_status"] == "satisfied"
    assert license_eval["matched_rule_code"] == "license.exists"
    assert license_eval["matched_material_name"] == "有效营业执照"

    confirm_response = client.post(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-evaluations/{license_eval['id']}/confirm",
        json={"reason": "资质管理员确认营业执照真实有效"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["confirm_reason"] == "资质管理员确认营业执照真实有效"

    with SessionLocal() as db:
        logs = db.scalars(
            select(AuditLog).where(
                AuditLog.object_type == "qualification_evaluation",
                AuditLog.object_id == UUID(license_eval["id"]),
            )
        ).all()
        assert any(log.action == "qualification.evaluation_confirmed" for log in logs)


def test_enterprise_material_search_and_compliance_evidence_binding() -> None:
    client = TestClient(app)
    certificate_no = f"91430600BIND{uuid4().hex[:8].upper()}"
    create_response = client.post(
        "/api/v1/enterprise/materials",
        json={
            "material_type": "license",
            "name": f"绑定测试营业执照 {uuid4().hex[:8]}",
            "issuing_authority": "岳阳市市场监督管理局",
            "certificate_no": certificate_no,
            "valid_until": "2030-12-31",
            "data_level": "internal",
            "verification_status": "confirmed",
            "evidence_text": "营业执照载明企业主体资格有效，可作为资格响应证据。",
        },
    )
    assert create_response.status_code == 201
    material = create_response.json()

    search_response = client.get(
        "/api/v1/enterprise/materials/search",
        params={"query": f"投标人须提供有效营业执照 {certificate_no}", "limit": 10},
    )
    assert search_response.status_code == 200
    search_results = search_response.json()
    hit = next(item for item in search_results if item["id"] == material["id"])
    assert "营业执照" in "".join(hit["matched_terms"]) or hit["recommend_reason"]

    projects = client.get("/api/v1/projects").json()
    project = next(item for item in projects if item["name"] == "智慧园区弱电工程投标")
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    section = sections[0]
    items = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/compliance-items"
    ).json()
    compliance_item = next(item for item in items if "营业执照" in item["requirement_text"])

    bind_response = client.post(
        (
            f"/api/v1/projects/{project['id']}/sections/{section['id']}"
            f"/compliance-items/{compliance_item['id']}/evidence-bindings"
        ),
        json={
            "enterprise_material_id": material["id"],
            "reason": "选用已确认营业执照作为商务标资格响应证据",
            "confidence_score": "0.9200",
        },
    )
    assert bind_response.status_code == 201
    binding = bind_response.json()
    assert binding["enterprise_material_id"] == material["id"]
    assert binding["material_name"] == material["name"]

    list_response = client.get(
        (
            f"/api/v1/projects/{project['id']}/sections/{section['id']}"
            f"/compliance-items/{compliance_item['id']}/evidence-bindings"
        )
    )
    assert list_response.status_code == 200
    assert any(item["id"] == binding["id"] for item in list_response.json())

    refreshed_items = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/compliance-items"
    ).json()
    refreshed_item = next(item for item in refreshed_items if item["id"] == compliance_item["id"])
    assert refreshed_item["enterprise_evidence_count"] >= 1
    assert material["name"] in refreshed_item["enterprise_evidence_summary"]

    with SessionLocal() as db:
        saved = db.get(ComplianceEvidenceBinding, UUID(binding["id"]))
        assert saved is not None
        assert saved.material_snapshot["name"] == material["name"]
        logs = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "matrix.evidence_bound",
                AuditLog.object_id == UUID(binding["id"]),
            )
        ).all()
        assert logs


def test_equivalent_enterprise_materials_are_deduped_for_search_and_binding() -> None:
    client = TestClient(app)
    unique = uuid4().hex[:8].upper()
    certificate_no = f"D243DUP{unique}"
    payload = {
        "material_type": "qualification",
        "name": "市政公用工程施工总承包二级资质",
        "issuing_authority": "湖南省住房和城乡建设厅",
        "certificate_no": certificate_no,
        "valid_until": "2030-12-31",
        "data_level": "internal",
        "verification_status": "confirmed",
        "structured_fields": {"qualification_category": "市政公用工程施工总承包", "grade": "二级"},
        "evidence_text": "证书载明资质类别为市政公用工程施工总承包二级。",
    }
    first_response = client.post("/api/v1/enterprise/materials", json=payload)
    second_response = client.post("/api/v1/enterprise/materials", json=payload)
    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first_material = first_response.json()
    second_material = second_response.json()

    search_response = client.get(
        "/api/v1/enterprise/materials/search",
        params={"query": certificate_no, "material_type": "qualification", "limit": 10},
    )
    assert search_response.status_code == 200
    duplicate_hits = [
        item for item in search_response.json() if item["certificate_no"] == certificate_no
    ]
    assert len(duplicate_hits) == 1

    projects = client.get("/api/v1/projects").json()
    project = next(item for item in projects if item["name"] == "智慧园区弱电工程投标")
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    section = sections[0]
    unique_requirement = f"投标人须具备工程设计综合资质。{unique}"
    with SessionLocal() as db:
        row = db.execute(
            select(Document, DocumentChunk)
            .join(DocumentChunk, DocumentChunk.document_version_id == Document.current_version_id)
            .where(
                Document.project_id == UUID(project["id"]),
                Document.section_id == UUID(section["id"]),
                Document.current_version_id.is_not(None),
                Document.status != "deleted",
            )
            .order_by(Document.updated_at.desc(), DocumentChunk.chunk_index.asc())
            .limit(1)
        ).one()
        document, chunk = row
        compliance_item = ComplianceItem(
            tenant_id=document.tenant_id,
            project_id=document.project_id,
            section_id=document.section_id,
            source_document_id=document.id,
            source_version_id=document.current_version_id,
            source_chunk_id=chunk.id,
            source_page_no=chunk.page_no,
            item_type="qualification",
            requirement_text=unique_requirement,
            normalized_requirement=unique_requirement,
            response_suggestion="绑定企业资质证据后人工确认。",
            evidence_text=unique_requirement,
            explanation_json={"source_quote": unique_requirement},
            status="needs_material",
            risk_level="high",
            is_mandatory=True,
            is_batch_confirm_allowed=False,
            created_by=document.created_by,
        )
        related_compliance_item = ComplianceItem(
            tenant_id=document.tenant_id,
            project_id=document.project_id,
            section_id=document.section_id,
            source_document_id=document.id,
            source_version_id=document.current_version_id,
            source_chunk_id=chunk.id,
            source_page_no=chunk.page_no,
            item_type="mandatory_response",
            requirement_text=f"投标文件须附企业资质证明。{unique}",
            normalized_requirement=f"企业资质证明 {unique}",
            response_suggestion="引用同一份企业资质并人工确认。",
            evidence_text=f"投标文件须附企业资质证明。{unique}",
            explanation_json={"source_quote": f"投标文件须附企业资质证明。{unique}"},
            status="confirmed",
            risk_level="medium",
            is_mandatory=True,
            is_batch_confirm_allowed=False,
            created_by=document.created_by,
        )
        db.add_all([compliance_item, related_compliance_item])
        db.commit()
        item_id = compliance_item.id
        related_item_id = related_compliance_item.id

    bind_url = (
        f"/api/v1/projects/{project['id']}/sections/{section['id']}"
        f"/compliance-items/{item_id}/evidence-bindings"
    )
    initial_run_response = client.post(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-evaluations/run"
    )
    assert initial_run_response.status_code == 200
    initial_evaluation = next(
        item for item in initial_run_response.json() if item["compliance_item_id"] == str(item_id)
    )
    assert initial_evaluation["evaluation_status"] == "needs_material"

    initial_decision_response = client.post(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-decision/generate"
    )
    assert initial_decision_response.status_code == 200
    initial_decision = initial_decision_response.json()
    confirm_initial_decision = client.post(
        (
            f"/api/v1/projects/{project['id']}/sections/{section['id']}/"
            f"qualification-decision/{initial_decision['id']}/confirm"
        ),
        json={"reason": "绑定资料前确认当前资格判断"},
    )
    assert confirm_initial_decision.status_code == 200

    bind_response = client.post(
        bind_url,
        json={
            "enterprise_material_id": first_material["id"],
            "reason": "绑定第一条等价企业资质",
            "confidence_score": "0.9000",
        },
    )
    assert bind_response.status_code == 201
    duplicate_bind_response = client.post(
        bind_url,
        json={
            "enterprise_material_id": second_material["id"],
            "reason": "重复绑定等价企业资质",
            "confidence_score": "0.9000",
        },
    )
    assert duplicate_bind_response.status_code == 409

    evaluations_after_bind = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-evaluations"
    )
    assert evaluations_after_bind.status_code == 200
    evaluation = next(
        item for item in evaluations_after_bind.json() if item["compliance_item_id"] == str(item_id)
    )
    assert evaluation["evaluation_status"] == "pending_confirm"
    assert evaluation["is_blocking"] is False
    assert evaluation["matched_material_name"] == first_material["name"]
    assert evaluation["confirmed_at"] is None

    stale_decision_response = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-decision"
    )
    assert stale_decision_response.status_code == 200
    assert stale_decision_response.json() is None

    with SessionLocal() as db:
        original = db.get(ComplianceEvidenceBinding, UUID(bind_response.json()["id"]))
        assert original is not None
        historical_duplicate = ComplianceEvidenceBinding(
            tenant_id=original.tenant_id,
            project_id=original.project_id,
            section_id=original.section_id,
            compliance_item_id=original.compliance_item_id,
            enterprise_material_id=UUID(second_material["id"]),
            evidence_text=original.evidence_text,
            material_snapshot=original.material_snapshot,
            confidence_score=original.confidence_score,
            bind_reason="历史重复绑定等价企业资质",
            status="active",
            created_by=original.created_by,
        )
        cross_item_binding = ComplianceEvidenceBinding(
            tenant_id=original.tenant_id,
            project_id=original.project_id,
            section_id=original.section_id,
            compliance_item_id=related_item_id,
            enterprise_material_id=original.enterprise_material_id,
            evidence_text=original.evidence_text,
            material_snapshot=original.material_snapshot,
            confidence_score=original.confidence_score,
            bind_reason="同一企业资质关联另一条款",
            status="active",
            created_by=original.created_by,
        )
        db.add_all([historical_duplicate, cross_item_binding])
        db.commit()
        historical_binding_id = historical_duplicate.id
        cross_item_binding_id = cross_item_binding.id

    list_response = client.get(bind_url)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    context_pack_preview_response = client.post(
        (
            f"/api/v1/projects/{project['id']}/sections/{section['id']}/"
            "business-draft/context-pack/preview"
        ),
        json={
            "profile_id": "engineering_construction_business_v1",
            "section_types": ["qualification_performance_summary"],
        },
    )
    assert context_pack_preview_response.status_code == 200
    context_pack_preview = context_pack_preview_response.json()
    equivalent_evidence = [
        item
        for item in context_pack_preview["context_json"]["bound_evidence"]
        if item["certificate_no"] == certificate_no
    ]
    assert len(equivalent_evidence) == 1
    assert set(equivalent_evidence[0]["compliance_item_ids"]) == {
        str(item_id),
        str(related_item_id),
    }
    assert len(equivalent_evidence[0]["binding_ids"]) == 2
    matrix_item = next(
        item
        for item in context_pack_preview["context_json"]["matrix_items"]
        if item["compliance_item_id"] == str(item_id)
    )
    assert matrix_item["bound_evidence_count"] == 1

    refreshed_decision_response = client.post(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-decision/generate"
    )
    assert refreshed_decision_response.status_code == 200
    refreshed_decision = refreshed_decision_response.json()
    confirm_refreshed_decision = client.post(
        (
            f"/api/v1/projects/{project['id']}/sections/{section['id']}/"
            f"qualification-decision/{refreshed_decision['id']}/confirm"
        ),
        json={"reason": "绑定资料后确认刷新后的资格判断"},
    )
    assert confirm_refreshed_decision.status_code == 200

    unbind_response = client.request(
        "DELETE",
        f"{bind_url}/{bind_response.json()['id']}",
        json={"reason": "验证解除绑定后自动重跑资格预评估"},
    )
    assert unbind_response.status_code == 200
    unbind_historical_response = client.request(
        "DELETE",
        f"{bind_url}/{historical_binding_id}",
        json={"reason": "清理历史等价重复绑定并验证资格状态收敛"},
    )
    assert unbind_historical_response.status_code == 200
    evaluations_after_unbind = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-evaluations"
    )
    assert evaluations_after_unbind.status_code == 200
    evaluation_after_unbind = next(
        item
        for item in evaluations_after_unbind.json()
        if item["compliance_item_id"] == str(item_id)
    )
    assert evaluation_after_unbind["evaluation_status"] == "needs_material"
    decision_after_unbind = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/qualification-decision"
    )
    assert decision_after_unbind.status_code == 200
    assert decision_after_unbind.json() is None

    with SessionLocal() as db:
        cross_item_binding = db.get(ComplianceEvidenceBinding, cross_item_binding_id)
        related_compliance_item = db.get(ComplianceItem, related_item_id)
        assert cross_item_binding is not None
        assert related_compliance_item is not None
        db.delete(cross_item_binding)
        db.delete(related_compliance_item)
        db.commit()


def test_compliance_evidence_requirement_can_be_waived() -> None:
    client = TestClient(app)
    projects = client.get("/api/v1/projects").json()
    project = next(item for item in projects if item["name"] == "智慧园区弱电工程投标")
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    section = sections[0]
    unique = uuid4().hex[:8]

    with SessionLocal() as db:
        row = db.execute(
            select(Document, DocumentChunk)
            .join(DocumentChunk, DocumentChunk.document_version_id == Document.current_version_id)
            .where(
                Document.project_id == UUID(project["id"]),
                Document.section_id == UUID(section["id"]),
                Document.current_version_id.is_not(None),
                Document.status != "deleted",
            )
            .order_by(Document.updated_at.desc(), DocumentChunk.chunk_index.asc())
            .limit(1)
        )
        row = row.one_or_none()
        assert row is not None
        document, chunk = row
        assert chunk is not None
        item = ComplianceItem(
            tenant_id=document.tenant_id,
            project_id=document.project_id,
            section_id=document.section_id,
            source_document_id=document.id,
            source_version_id=document.current_version_id,
            source_chunk_id=chunk.id,
            source_page_no=chunk.page_no,
            item_type="mandatory_response",
            requirement_text=f"履约担保：履约担保金额为合同总价的2%。{unique}",
            normalized_requirement=f"履约担保 {unique}",
            response_suggestion="该条默认需要补充担保资料或人工豁免说明。",
            evidence_text="招标文件载明履约担保要求。",
            explanation_json={"source_quote": "履约担保"},
            status="needs_material",
            risk_level="medium",
            is_mandatory=True,
            is_batch_confirm_allowed=False,
            created_by=document.created_by,
        )
        db.add(item)
        db.commit()
        item_id = item.id

    before_preflight = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/preflight-check"
    )
    assert before_preflight.status_code == 200
    before_missing = before_preflight.json()["mandatory_missing_evidence_count"]
    assert before_missing >= 1

    waive_response = client.post(
        (
            f"/api/v1/projects/{project['id']}/sections/{section['id']}"
            f"/compliance-items/{item_id}/evidence-not-required"
        ),
        json={"reason": "该履约担保条款当前仅作为商务承诺响应，暂不绑定企业资料证据"},
    )
    assert waive_response.status_code == 200
    waived_item = waive_response.json()
    assert waived_item["enterprise_evidence_not_required"] is True
    assert waived_item["enterprise_evidence_not_required_reason"] == "该履约担保条款当前仅作为商务承诺响应，暂不绑定企业资料证据"
    assert waived_item["status"] == "pending_confirm"

    after_preflight = client.get(
        f"/api/v1/projects/{project['id']}/sections/{section['id']}/preflight-check"
    )
    assert after_preflight.status_code == 200
    assert after_preflight.json()["mandatory_missing_evidence_count"] == before_missing - 1

    with SessionLocal() as db:
        logs = db.scalars(
            select(AuditLog).where(
                AuditLog.action == "matrix.evidence_not_required",
                AuditLog.object_id == item_id,
            )
        ).all()
        assert logs
        saved_item = db.get(ComplianceItem, item_id)
        if saved_item is not None:
            db.delete(saved_item)
            db.commit()


def test_profile_preferences_and_forbidden_rules_affect_qualification_decision() -> None:
    client = TestClient(app)
    project_name = f"画像策略测试项目 {uuid4().hex[:8]}"
    create_response = client.post(
        "/api/v1/projects",
        json={
            "name": project_name,
            "purchaser": "策略测试采购人",
            "agency": "策略测试代理",
            "region_code": "CN-9999",
            "industry_code": "water-test",
            "section_name": "画像策略标段",
        },
    )
    assert create_response.status_code == 201
    project = create_response.json()
    sections = client.get(f"/api/v1/projects/{project['id']}/sections").json()
    section_id = sections[0]["id"]

    profile_response = client.put(
        "/api/v1/enterprise/profile",
        json={
            "company_name": f"画像策略企业 {uuid4().hex[:8]}",
            "business_scope": "市政工程施工。",
            "region_preferences": ["湖南省"],
            "industry_preferences": ["燃气"],
            "forbidden_rules": [],
        },
    )
    assert profile_response.status_code == 200

    conditional_response = client.post(
        f"/api/v1/projects/{project['id']}/sections/{section_id}/qualification-decision/generate"
    )
    assert conditional_response.status_code == 200
    conditional = conditional_response.json()
    assert conditional["recommendation"] == "conditional_go"
    profile_policy = conditional["reasons_json"]["profile_policy"]
    assert {item["type"] for item in profile_policy["preference_mismatches"]} == {
        "region",
        "industry",
    }
    assert conditional["pending_count"] >= 2

    forbidden_response = client.put(
        "/api/v1/enterprise/profile",
        json={
            "company_name": profile_response.json()["company_name"],
            "business_scope": "市政工程施工。",
            "region_preferences": ["湖南省"],
            "industry_preferences": ["燃气"],
            "forbidden_rules": [f"{project_name} 禁止参标"],
        },
    )
    assert forbidden_response.status_code == 200

    no_go_response = client.post(
        f"/api/v1/projects/{project['id']}/sections/{section_id}/qualification-decision/generate"
    )
    assert no_go_response.status_code == 200
    no_go = no_go_response.json()
    assert no_go["recommendation"] == "no_go"
    forbidden_matches = no_go["reasons_json"]["profile_policy"]["forbidden_matches"]
    assert forbidden_matches
    assert no_go["blocking_count"] >= 1
