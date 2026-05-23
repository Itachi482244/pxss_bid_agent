from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from docx import Document as WordDocument
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import AsyncTask, ComplianceItem
from app.parsers.word import parse_docx_bytes
from app.services.compliance_generation import _rule_extract, execute_compliance_matrix_generation_task
from app.services.document_parse import execute_document_parse_task
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


def build_qualification_docx_bytes() -> bytes:
    document = WordDocument()
    document.add_heading("测试燃气项目（EPC）", level=1)
    document.add_paragraph("1.4 招标范围：建设规模范围内的设计、施工总承包，包括验收及缺陷责任期服务。")
    document.add_paragraph("1.6 保修要求：按国务院2000年279号令相关规定及合同约定进行施工质量保修。")
    document.add_paragraph("1.7 缺陷责任期：24个月。")
    document.add_paragraph("1.8 标段划分：本项目分为一个标段。")
    document.add_paragraph("1.9 技术响应要求：洁净设备应提供产品样本、检测报告和安装调试验收方案。")
    document.add_paragraph("2.资格要求")
    document.add_paragraph("2.1 具有独立法人资格并依法取得企业营业执照，营业执照处于有效期；")
    document.add_paragraph("2.2 须具备市政公用工程施工总承包贰级及以上资质，安全生产许可证处于有效期；")
    document.add_paragraph("2.3 拟任施工项目负责人具备市政公用工程专业二级及以上注册建造师资格，以联合体投标的，拟任工程总承包项目负责人须为联合体牵头人单位人员。")
    document.add_paragraph("2.4 本次招标接受联合体投标。")
    document.add_paragraph("2.8 类似工程业绩要求：")
    document.add_paragraph("？不要求")
    document.add_paragraph("3.资格审查")
    document.add_paragraph("采用资格后审方式")
    document.add_paragraph("4.评标办法")
    document.add_paragraph("本招标项目采用湘建监督[2024]34号文件规定的综合评估法。")
    document.add_paragraph("6.投标文件的递交")
    document.add_paragraph("6.1 电子投标文件递交的截止时间为2025年12月11日9时30分。")
    document.add_paragraph("8.行政监督")
    document.add_paragraph("本次招标项目招标投标监督机构为岳阳市君山区建设工程招投标管理办公室，电话0730-8178006。")

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_cleanroom_public_notice_docx_bytes() -> bytes:
    document = WordDocument()
    document.add_heading("净化运维服务托管项目公开招标公告", level=1)
    document.add_paragraph(
        "项目概况\n"
        "净化运维服务托管招标项目的潜在投标人应在登录“邢台市公共资源交易网”"
        "选择“市级交易响应方登录”→“邢台市公共资源交易平台”自行下载招标文件。"
        "获取招标文件，并于2026年06月12日 09点00分（北京时间）前递交投标文件。"
    )
    document.add_paragraph("一、项目基本情况")
    document.add_paragraph("采购需求：序号 标的名称 预算金额（万元） 服务期限 简要技术需求或服务要求1 净化区域运维服务托管项目 180 三年 详见采购需求")
    document.add_paragraph("合同履行期限：三年，合同一年一签。")
    document.add_paragraph("本项目不接受联合体投标。")
    document.add_paragraph("二、申请人的资格要求：")
    document.add_paragraph("1.满足《中华人民共和国政府采购法》第二十二条规定；")
    document.add_paragraph(
        "2.落实政府采购政策需满足的资格要求：1.满足《中华人民共和国政府采购法》第二十二条规定；"
        "2.1本项目专门面向小微企业采购，投标人须为小微企业；"
        "2.2其他落实政府采购政策的资格要求（如有）： 无 ；"
        "2.3通过“信用中国”网站和中国政府采购网查询信用记录，被列入失信被执行人、"
        "重大税收违法案件当事人名单、政府采购严重违法失信行为记录名单的供应商，没有资格参加本项目的采购活动。"
    )
    document.add_paragraph(
        "3.本项目的特定资格要求：（1）供应商须具备建设行政主管部门颁发的"
        "建筑装修装饰工程专业承包贰级及以上资质、电子与智能化工程专业承包贰级及以上资质、"
        "建筑机电安装工程专业承包叁级及以上资质且具备有效的安全生产许可证； "
        "（2）供应商拟派项目经理须具备机电工程专业贰级及以上注册建造师执业资格，"
        "具备有效的安全生产考核(B 类)合格证书，且未担任其他在施建设工程项目的项目经理。"
    )
    document.add_paragraph("三、获取招标文件")
    document.add_paragraph("时间：2026年05月21日至2026年05月27日,每天上午00:00至12:00,下午12:00至23:59")
    document.add_paragraph("地点：登录“邢台市公共资源交易网”自行下载招标文件。")
    document.add_paragraph("四、提交投标文件截止时间、开标时间和地点")
    document.add_paragraph("2026年06月12日 09点00分（北京时间）")

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def normalized_requirement_key(text: str) -> str:
    return re.sub(r"[\s，。；;：:（）()、]+", "", text)


def test_cleanroom_notice_rule_fallback_atomizes_and_deduplicates_requirements() -> None:
    chunks = parse_docx_bytes(build_cleanroom_public_notice_docx_bytes())
    heading_by_text = {chunk.content_text: chunk.heading_path for chunk in chunks}
    assert heading_by_text["三、获取招标文件"].endswith("三、获取招标文件")
    assert "特定资格要求" not in (heading_by_text["三、获取招标文件"] or "")

    candidates = _rule_extract(chunks)  # type: ignore[arg-type]
    texts = [item.requirement_text for item in candidates]
    joined = "\n".join(texts)
    normalized_texts = [normalized_requirement_key(text) for text in texts]

    assert "净化运维服务托管项目公开招标公告" not in texts
    assert "3.本项目的特定资格要求" not in joined.replace("\n", "")
    assert not any("三、获取招标文件" in text and "特定资格要求" in text for text in texts)
    assert not any("2.2其他落实政府采购政策" in text for text in texts)
    assert not any("邢台市公共资源交易网" in text and item.item_type != "deadline" for item, text in zip(candidates, texts))
    assert len(normalized_texts) == len(set(normalized_texts))
    assert all(len(text) <= 180 for text in texts)

    assert any("建筑装修装饰工程专业承包贰级及以上资质" in text for text in texts)
    electronic_qualification = next(
        item for item in candidates if "电子与智能化工程专业承包贰级及以上资质" in item.requirement_text
    )
    assert electronic_qualification.item_type == "qualification"
    assert any("建筑机电安装工程专业承包叁级及以上资质" in text for text in texts)
    assert any("有效的安全生产许可证" in text for text in texts)
    assert any("拟派项目经理" in text and "注册建造师" in text for text in texts)
    assert any("安全生产考核" in text and "B 类" in text for text in texts)
    assert any("未担任其他在施建设工程项目" in text for text in texts)
    assert any("小微企业" in text for text in texts)
    assert any("不接受联合体投标" in text for text in texts)
    assert any("信用中国" in text and "没有资格参加" in text for text in texts)

    submit_deadlines = [
        item for item in candidates if item.item_type == "deadline" and "2026年06月12日" in item.requirement_text
    ]
    assert len(submit_deadlines) == 1

    qualification_count = sum(1 for item in candidates if item.item_type == "qualification")
    assert qualification_count >= 8


def test_compliance_matrix_generation_creates_items_from_word_chunks(monkeypatch) -> None:
    settings.run_tasks_inline = False
    monkeypatch.setattr(settings, "llm_provider", "mock")
    monkeypatch.setattr(settings, "llm_api_key", "")
    from app.worker import run_compliance_matrix_generation_task, run_document_parse_task

    monkeypatch.setattr(run_document_parse_task, "delay", lambda task_id: None)
    monkeypatch.setattr(run_compliance_matrix_generation_task, "delay", lambda task_id: None)

    client = TestClient(app)
    project_id, section_id = get_seed_project_and_section(client)
    filename = f"资格要求-{uuid4().hex}.docx"

    upload_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/upload",
        data={"doc_type": "tender", "title": "资格要求测试"},
        files={
            "file": (
                filename,
                build_qualification_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert upload_response.status_code == 201
    document = upload_response.json()

    parse_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/documents/{document['id']}/parse-tasks",
        json={"parser_name": "word-parser", "parser_version": "0.1.0"},
    )
    assert parse_response.status_code == 202
    with SessionLocal() as db:
        parse_result = execute_document_parse_task(db, UUID(parse_response.json()["task"]["id"]))
        assert parse_result["status"] == "succeeded"

    generate_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/generate",
        json={"document_version_id": document["current_version_id"]},
    )
    assert generate_response.status_code == 202
    generation_task_payload = generate_response.json()

    with SessionLocal() as db:
        result = execute_compliance_matrix_generation_task(db, UUID(generation_task_payload["id"]))
        assert result["status"] == "succeeded"
        assert result["provider"] == "rules"
        assert result["created_count"] >= 5

        task = db.get(AsyncTask, UUID(generation_task_payload["id"]))
        assert task is not None
        assert task.status == "succeeded"
        assert task.output_json is not None
        assert task.output_json["created_count"] >= 5

        items = db.scalars(
            select(ComplianceItem).where(
                ComplianceItem.source_version_id == UUID(document["current_version_id"]),
                ComplianceItem.deleted_at.is_(None),
            )
        ).all()
        texts = "\n".join(item.requirement_text for item in items)
        assert "营业执照" in texts
        assert "市政公用工程施工总承包贰级" in texts
        assert "联合体投标" in texts
        assert "联合体牵头人单位人员" in texts
        assert "保修要求" in texts
        assert "缺陷责任期" in texts
        assert "洁净设备" in texts
        assert "采用资格后审方式" in texts
        assert "综合评估法" in texts
        assert any(item.item_type == "technical_response" for item in items)
        assert any(item.item_type == "deadline" for item in items)
        assert any(item.item_type == "scoring" for item in items)
        assert any(item.item_type == "reference_info" for item in items)
        assert all(not item.is_batch_confirm_allowed for item in items if item.risk_level == "high")
        high_risk_item = next(item for item in items if item.risk_level == "high")
        assert high_risk_item.explanation_json is not None
        assert high_risk_item.explanation_json["rule_reason"]
        assert high_risk_item.explanation_json["risk_reason"]
        assert high_risk_item.explanation_json["batch_confirm_reason"] == (
            "高风险项不允许批量确认，必须逐条核验来源和响应证据。"
        )

        repeated = execute_compliance_matrix_generation_task(db, UUID(generation_task_payload["id"]))
        assert repeated["status"] == "succeeded"
        assert repeated["updated_count"] >= 5

    matrix_response = client.get(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items",
        params={"limit": 500},
    )
    assert matrix_response.status_code == 200
    generated_api_items = [
        item
        for item in matrix_response.json()
        if item["source_version_id"] == document["current_version_id"]
    ]
    assert generated_api_items
    api_high_risk = next(item for item in generated_api_items if item["risk_level"] == "high")
    assert api_high_risk["source_content_text"]
    assert api_high_risk["source_chunk_index"] is not None
    assert api_high_risk["rule_explanation"]["risk_reason"]
    assert api_high_risk["rule_explanation"]["batch_confirm_reason"] == (
        "高风险项不允许批量确认，必须逐条核验来源和响应证据。"
    )

    blocked_bulk_response = client.post(
        f"/api/v1/projects/{project_id}/sections/{section_id}/compliance-items/bulk-confirm",
        json={"item_ids": [api_high_risk["id"]], "reason": "测试高风险项不可批量确认"},
    )
    assert blocked_bulk_response.status_code == 409
