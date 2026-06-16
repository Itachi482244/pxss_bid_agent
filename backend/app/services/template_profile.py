from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_TEMPLATE_PROFILE_ID = "engineering_construction_business_v1"

_SECTION_DEFINITIONS: dict[str, dict[str, Any]] = {
    "business_cover": {
        "title": "商务标封面",
        "required": True,
        "generation_mode": "fixed_form",
        "required_fields": ["project_name", "bidder_name", "legal_representative_name", "bid_date"],
        "covers_item_types": ["format"],
    },
    "business_directory": {
        "title": "商务标目录",
        "required": True,
        "generation_mode": "deterministic",
        "required_fields": ["project_name"],
        "covers_item_types": ["format"],
    },
    "legal_representative_identity": {
        "title": "法定代表人身份证明书",
        "required": True,
        "generation_mode": "fixed_form",
        "required_fields": [
            "bidder_name",
            "bidder_address",
            "legal_representative_name",
            "legal_representative_title",
            "bid_date",
        ],
        "covers_item_types": ["qualification", "format"],
    },
    "authorization_letter": {
        "title": "授权委托书",
        "required": True,
        "generation_mode": "fixed_form",
        "required_fields": [
            "project_name",
            "bidder_name",
            "legal_representative_name",
            "authorized_agent_name",
            "bid_date",
        ],
        "covers_item_types": ["format", "mandatory_response"],
    },
    "bid_letter": {
        "title": "投标函",
        "required": True,
        "generation_mode": "fixed_form",
        "required_fields": [
            "project_name",
            "tenderer_name",
            "tender_project_no",
            "bid_price_amount",
            "construction_period_days",
            "quality_standard",
            "project_manager_name",
            "bid_date",
        ],
        "covers_item_types": ["mandatory_response", "deadline", "format"],
    },
    "bid_letter_appendix": {
        "title": "投标函附录",
        "required": True,
        "generation_mode": "structured_table",
        "required_fields": [
            "construction_period_days",
            "quality_standard",
            "warranty_period",
            "performance_bond",
        ],
        "covers_item_types": ["mandatory_response", "format"],
    },
    "bid_security": {
        "title": "投标保证金",
        "required": False,
        "generation_mode": "attachment_placeholder",
        "required_fields": ["bid_security_amount", "bid_security_form"],
        "covers_item_types": ["mandatory_response", "format"],
    },
    "bid_commitment": {
        "title": "投标承诺书",
        "required": True,
        "generation_mode": "generated_paragraph",
        "required_fields": ["project_name", "tenderer_name", "bidder_name", "bid_date"],
        "covers_item_types": ["mandatory_response", "reference_info", "other"],
    },
    "consortium_agreement": {
        "title": "联合体协议书",
        "required": False,
        "generation_mode": "conditional_form",
        "required_fields": ["is_consortium"],
        "covers_item_types": ["qualification", "mandatory_response"],
    },
    "bid_price_cover": {
        "title": "投标总价封面",
        "required": True,
        "generation_mode": "fixed_form",
        "required_fields": ["project_name", "tenderer_name", "bid_price_amount", "bidder_name", "bid_date"],
        "covers_item_types": ["format", "mandatory_response"],
    },
    "boq_pricing_explanation": {
        "title": "工程量清单报价说明",
        "required": True,
        "generation_mode": "generated_paragraph",
        "required_fields": ["project_name", "project_scope", "bid_price_amount", "quality_standard"],
        "covers_item_types": ["scoring", "mandatory_response", "format"],
    },
    "priced_boq": {
        "title": "已标明价格的工程量清单",
        "required": True,
        "generation_mode": "external_attachment",
        "required_fields": ["boq_file"],
        "covers_item_types": ["mandatory_response", "format"],
    },
    "other_business_materials": {
        "title": "其他投标资料",
        "required": False,
        "generation_mode": "attachment_placeholder",
        "required_fields": [],
        "covers_item_types": ["other", "reference_info"],
    },
    "qualification_performance_summary": {
        "title": "资格业绩汇总表",
        "required": False,
        "generation_mode": "structured_table",
        "required_fields": ["bidder_name"],
        "covers_item_types": ["qualification", "scoring"],
    },
    "qualification_other_materials": {
        "title": "资格审查其他资料",
        "required": False,
        "generation_mode": "attachment_placeholder",
        "required_fields": [],
        "covers_item_types": ["qualification"],
    },
    "bidder_basic_info": {
        "title": "投标人基本情况表",
        "required": False,
        "generation_mode": "structured_table",
        "required_fields": [
            "bidder_name",
            "bidder_address",
            "legal_representative_name",
            "unified_social_credit_code",
        ],
        "covers_item_types": ["qualification", "format"],
    },
    "financial_status": {
        "title": "近年财务状况表",
        "required": False,
        "generation_mode": "attachment_placeholder",
        "required_fields": ["financial_report_years"],
        "covers_item_types": ["qualification", "scoring"],
    },
    "scoring_performance_summary": {
        "title": "评分业绩汇总表",
        "required": False,
        "generation_mode": "structured_table",
        "required_fields": ["bidder_name"],
        "covers_item_types": ["scoring", "qualification"],
    },
    "project_management_team": {
        "title": "项目管理班子配备情况表",
        "required": False,
        "generation_mode": "structured_table",
        "required_fields": ["project_manager_name", "project_manager_id_no"],
        "covers_item_types": ["qualification", "mandatory_response", "scoring"],
    },
    "project_manager_resume": {
        "title": "项目负责人简历表",
        "required": False,
        "generation_mode": "structured_table",
        "required_fields": ["project_manager_name", "project_manager_id_no"],
        "covers_item_types": ["qualification", "scoring"],
    },
    "team_supporting_materials": {
        "title": "班子辅助说明资料",
        "required": False,
        "generation_mode": "attachment_placeholder",
        "required_fields": [],
        "covers_item_types": ["qualification", "scoring"],
    },
    "gas_project_understanding": {
        "title": "项目理解与招标要求响应",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name", "construction_period_days", "quality_standard"],
        "covers_item_types": ["technical_response", "mandatory_response", "reference_info"],
    },
    "gas_epc_organization": {
        "title": "EPC总承包组织与设计施工协同",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name"],
        "covers_item_types": ["technical_response", "mandatory_response"],
    },
    "gas_limit_design_cost_control": {
        "title": "限额设计与施工图预算控制",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name", "bid_price_amount"],
        "covers_item_types": ["technical_response", "scoring", "mandatory_response"],
    },
    "gas_pipeline_construction_method": {
        "title": "中压GB1燃气管道施工组织方案",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name"],
        "covers_item_types": ["technical_response"],
    },
    "gas_material_procurement_quality": {
        "title": "管材、阀门及设备采购质量控制",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name"],
        "covers_item_types": ["technical_response", "mandatory_response"],
    },
    "gas_trench_connection_backfill_restore": {
        "title": "沟槽开挖、管道连接、防腐、回填及路面恢复",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name"],
        "covers_item_types": ["technical_response"],
    },
    "gas_pressure_test_purge_acceptance": {
        "title": "压力试验、吹扫、置换、验收移交",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name", "quality_standard"],
        "covers_item_types": ["technical_response", "mandatory_response"],
    },
    "gas_existing_pipeline_traffic_safety": {
        "title": "既有管线保护、交通组织与安全文明施工",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name"],
        "covers_item_types": ["technical_response", "mandatory_response"],
    },
    "gas_schedule_resource_plan": {
        "title": "进度计划与资源配置",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name", "construction_period_days"],
        "covers_item_types": ["technical_response", "deadline", "mandatory_response"],
    },
    "gas_completion_handover_service": {
        "title": "缺陷责任期服务和竣工资料移交",
        "required": False,
        "generation_mode": "technical_generated_paragraph",
        "required_fields": ["project_name", "warranty_period"],
        "covers_item_types": ["technical_response", "mandatory_response"],
    },
}

_ENGINEERING_PROFILE: dict[str, Any] = {
    "profile_id": DEFAULT_TEMPLATE_PROFILE_ID,
    "profile_name": "工程类施工商务/资格标书通用模板",
    "version": "1.0",
    "generation_mode": "staged_context_pack",
    "applicable_project_types": [
        "工程施工",
        "房建工程",
        "市政工程",
        "老旧小区改造",
        "装饰装修",
        "安装工程",
    ],
    "source_priority": [
        "招标文件明确格式",
        "项目选择的 TemplateProfile",
        "系统默认工程类商务/资格模板",
    ],
    "volumes": [
        {
            "volume_id": "business_bid",
            "title": "投标文件商务标格式",
            "required": True,
            "sections": [
                "business_cover",
                "business_directory",
                "legal_representative_identity",
                "authorization_letter",
                "bid_letter",
                "bid_letter_appendix",
                "bid_security",
                "bid_commitment",
                "consortium_agreement",
                "bid_price_cover",
                "boq_pricing_explanation",
                "priced_boq",
                "other_business_materials",
            ],
        },
        {
            "volume_id": "qualification_review",
            "title": "投标文件资格审查资料",
            "required": False,
            "sections": ["qualification_performance_summary", "qualification_other_materials"],
        },
        {
            "volume_id": "credit_bid",
            "title": "投标文件资信标",
            "required": False,
            "sections": [
                "bidder_basic_info",
                "financial_status",
                "scoring_performance_summary",
                "project_management_team",
                "project_manager_resume",
                "team_supporting_materials",
            ],
        },
        {
            "volume_id": "technical_bid",
            "title": "投标文件技术标",
            "required": False,
            "sections": [
                "gas_project_understanding",
                "gas_epc_organization",
                "gas_limit_design_cost_control",
                "gas_pipeline_construction_method",
                "gas_material_procurement_quality",
                "gas_trench_connection_backfill_restore",
                "gas_pressure_test_purge_acceptance",
                "gas_existing_pipeline_traffic_safety",
                "gas_schedule_resource_plan",
                "gas_completion_handover_service",
            ],
        },
    ],
    "section_definitions": _SECTION_DEFINITIONS,
    "global_required_fields": [
        "project_name",
        "tenderer_name",
        "bidder_name",
        "bidder_address",
        "legal_representative_name",
        "bid_date",
        "tender_project_no",
        "bid_deadline",
        "bid_price_amount",
        "project_manager_name",
        "project_manager_id_no",
        "construction_period_days",
        "quality_standard",
    ],
    "hard_blockers": [
        "招标文件明确要求的商务标章节缺失",
        "投标函中的投标总价大小写不一致",
        "投标总价与报价汇总表不一致",
        "法定代表人或授权代理人信息缺失",
        "投标保证金要求未响应且无人工说明",
        "强制资格项无证据且未标记为待补",
        "关键人员证书或社保证据缺失且未说明",
    ],
}

_PROFILES = {
    DEFAULT_TEMPLATE_PROFILE_ID: _ENGINEERING_PROFILE,
}


def get_template_profile(profile_id: str | None = None) -> dict[str, Any]:
    resolved_profile_id = profile_id or DEFAULT_TEMPLATE_PROFILE_ID
    if resolved_profile_id not in _PROFILES:
        raise ValueError(f"Unsupported template profile: {resolved_profile_id}")
    return deepcopy(_PROFILES[resolved_profile_id])


def iter_profile_sections(profile: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    definitions = profile.get("section_definitions") or {}
    order_index = 0
    for volume in profile.get("volumes") or []:
        for section_type in volume.get("sections") or []:
            definition = definitions.get(section_type)
            if not definition:
                continue
            order_index += 10
            section = deepcopy(definition)
            section["section_type"] = section_type
            section["volume_id"] = volume.get("volume_id")
            section["volume_title"] = volume.get("title")
            section["volume_required"] = bool(volume.get("required"))
            section["order_index"] = order_index
            sections.append(section)
    return sections
