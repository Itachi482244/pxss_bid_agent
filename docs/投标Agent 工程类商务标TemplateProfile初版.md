# 投标 Agent 工程类商务标 TemplateProfile 初版

> 更新时间：2026-06-04
> 参考样本：`/Users/yaphets/document/未命名文件夹/投标文件`
> 适用范围：工程施工、老旧小区改造、房建/市政/安装等工程类项目的商务/资格草稿生成。

## 1. 样本观察结论

本次参考文件是一个工程类投标包，整体目录分为：

1. 投标文件商务标格式。
2. 投标文件技术标格式。
3. 投标文件资信标格式。

其中商务标主册来自 `[3]施工投标文件（商务标）.PDF` 和 `[4]目录（商务标）.PDF`。商务标目录包含：

1. 法定代表人身份证明书。
2. 授权委托书。
3. 投标函。
4. 投标函附录。
5. 投标保证金。
6. 投标承诺书。
7. 联合体协议书。
8. 投标总价封面。
9. 工程量清单报价说明。
10. 已标明价格的工程量清单。
11. 招标文件要求投标人提交的其他投标资料。

参考文件中还存在与商务/资格生成密切相关的独立材料：

1. `[202]资格审查材料.PDF`：资格业绩材料、资格条件业绩汇总及其他资格审查材料。
2. `[203]商务附件.PDF`：投标保证金、投标承诺书、联合体协议书、投标总价封面、其他投标资料。
3. `[206]资信标.PDF`：投标人基本情况、财务状况、评分业绩、项目管理班子、其他资信资料。
4. `[22]业绩公示汇总表（加分业绩的汇总）.PDF`：评分业绩汇总。
5. `[23]表5 项目管理班子配备情况表.PDF`：项目经理、技术负责人、质量员、安全员等人员配备。

因此，第一版通用模板不应只覆盖“商务标目录”，还应预留资格审查、资信评分、人员班子、业绩汇总等工程类投标常见附件。

## 2. TemplateProfile 定位

`TemplateProfile` 不是 Word 模板，也不是最终正文。它负责定义：

1. 商务/资格标书有哪些卷册和章节。
2. 哪些章节是固定表单，哪些章节是生成段落，哪些章节只接收外部报价文件。
3. 每个章节需要哪些项目字段、企业字段、人员字段、报价字段和证据。
4. 缺失字段、未确认风险、证据不足和不适用章节如何收敛。
5. `GlobalContextPack` 和 `SectionContextPack` 应该如何裁剪上下文。

Word 模板只负责最终排版；`TemplateProfile` 负责生成规则。

## 3. 初版 TemplateProfile

```json
{
  "profile_id": "engineering_construction_business_v1",
  "profile_name": "工程类施工商务/资格标书通用模板",
  "version": "1.0",
  "applicable_project_types": [
    "工程施工",
    "房建工程",
    "市政工程",
    "老旧小区改造",
    "装饰装修",
    "安装工程",
    "EPC项目中的施工投标"
  ],
  "source_priority": [
    "招标文件明确格式",
    "项目选择的TemplateProfile",
    "系统默认工程类商务/资格模板"
  ],
  "generation_mode": "staged_context_pack",
  "volumes": [
    {
      "volume_id": "business_bid",
      "title": "投标文件商务标格式",
      "required": true,
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
        "other_business_materials"
      ]
    },
    {
      "volume_id": "qualification_review",
      "title": "投标文件资格审查资料",
      "required": false,
      "sections": [
        "qualification_cover",
        "qualification_directory",
        "qualification_performance_summary",
        "qualification_other_materials"
      ]
    },
    {
      "volume_id": "credit_bid",
      "title": "投标文件资信标",
      "required": false,
      "sections": [
        "credit_cover",
        "credit_scoring_index",
        "bidder_basic_info",
        "financial_status",
        "scoring_performance_summary",
        "project_management_team",
        "project_manager_resume",
        "technical_leader_resume",
        "team_supporting_materials",
        "credit_other_materials"
      ]
    }
  ],
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
    "bid_price_amount_upper",
    "project_manager_name",
    "project_manager_id_no",
    "construction_period_days",
    "quality_standard"
  ],
  "hard_blockers": [
    "招标文件明确要求的商务标章节缺失",
    "投标函中的投标总价大小写不一致",
    "投标总价与报价汇总表不一致",
    "法定代表人或授权代理人信息缺失",
    "投标保证金要求未响应且无人工说明",
    "强制资格项无证据且未标记为待补",
    "关键人员证书或社保证据缺失且未说明"
  ]
}
```

## 4. 商务标主册章节类型清单

| section_type | 章节名称 | 是否必备 | 生成方式 | 关键输入 |
| --- | --- | --- | --- | --- |
| `business_cover` | 商务标封面 | 必备 | 确定性填充 | 工程名称、投标文件内容、投标人、法定代表人/委托代理人、日期 |
| `business_directory` | 商务标目录 | 必备 | 规则生成 + 人工确认 | OutlinePlan、章节顺序、不适用章节 |
| `legal_representative_identity` | 法定代表人身份证明书 | 必备 | 固定表单填充 | 单位名称、地址、法定代表人姓名、性别、年龄、职务、日期 |
| `authorization_letter` | 授权委托书 | 条件必备 | 固定表单填充 | 法定代表人、代理人、代理期限、项目名称、投标日期 |
| `bid_letter` | 投标函 | 必备 | 固定条款 + 字段填充 | 招标人、招标编号、项目名称、投标报价、工期、履约担保、投标保证金、项目经理 |
| `bid_letter_appendix` | 投标函附录 | 必备 | 表格填充 | 履约保证金、施工准备时间、误期违约、工期、质量、预付款、进度款、保修期 |
| `bid_security` | 投标保证金 | 条件必备 | 附件占位 + 证据绑定 | 保证金金额、形式、凭证文件、有效性说明 |
| `bid_commitment` | 投标承诺书 | 常见必备 | 固定承诺条款 + 字段填充 | 招标人、项目名称、招标编号、投标人、传真、邮箱、日期 |
| `consortium_agreement` | 联合体协议书 | 条件章节 | 条件生成 | 是否联合体、牵头人、成员、职责分工；非联合体时输出“无”或不适用说明 |
| `bid_price_cover` | 投标总价封面 | 必备 | 固定表单填充 | 招标人、工程名称、投标总价小写、大写、投标人、日期 |
| `boq_pricing_explanation` | 工程量清单报价说明 | 必备 | 模板段落 + 项目事实填充 | 工程概况、投标范围、编制依据、质量、工期、费率、其他承诺 |
| `priced_boq` | 已标明价格的工程量清单 | 工程类必备 | 外部报价表导入/绑定 | 清单计价文件、报价汇总、单位工程、分部分项、措施项目、工料机分析 |
| `other_business_materials` | 其他投标资料 | 条件章节 | 占位 + 人工上传 | 招标文件要求、补充材料、人工说明 |

## 5. 已标明价格的工程量清单子类型

参考样本中，报价清单是一组 PDF 表格，通常不适合由 LLM 生成正文，应作为外部报价文件或结构化报价数据导入，再进入 ContextPack 摘要和校验。

| section_type | 表名 | 关键字段 |
| --- | --- | --- |
| `project_quote_summary` | 表1-1-1 工程项目报价汇总表 | 单位工程费、整体措施费、其他费用、税金、总报价、大写金额 |
| `unit_quote_summary` | 表1-1-2 单位工程报价汇总表 | 单位工程名称、分部分项、措施项目、规费、税金、总报价 |
| `subsection_bill_pricing` | 表1-2 分部分项工程量清单及计价表 | 项目编码、项目名称、项目特征、单位、工程量、综合单价、合价 |
| `organization_measure_overall` | 表1-3-A 组织措施项目（整体）清单及计价表 | 措施项目、数量、金额 |
| `organization_measure_professional` | 表1-3-B 组织措施项目（专业）清单及计价表 | 专业措施项目、金额 |
| `technical_measure_pricing` | 表1-3-C 技术措施项目清单及计价表 | 项目编码、项目名称、工程量、综合单价、人工费、机械费、管理费 |
| `safe_civilized_measure_pricing` | 表1-3-A-1 安全文明施工措施项目清单及计价表 | 安全施工、文明施工、环境保护、临时设施等费用 |
| `other_item_pricing` | 表1-4 其他项目清单及计价表 | 其他项目费用 |
| `daywork_pricing` | 表1-4-1 计日工表 | 人工、材料、机械计日工 |
| `general_contract_service_fee` | 表1-4-2 总承包服务费计价表 | 服务项目、费率、金额 |
| `labor_price_table` | 表1-5 主要工日价格表 | 工种、单位、数量、单价 |
| `material_price_table` | 表1-6 主要材料及设备价格表 | 编码、材料/设备名称、规格型号、单位、数量、单价 |
| `machinery_price_table` | 表1-7 主要机械台班价格表 | 机械设备名称、单位、数量、单价 |
| `unit_price_analysis` | 表2-1 分部分项工程量清单综合单价分析表 | 人工费、材料费、机械费、管理费、利润、风险、小计 |
| `measure_item_analysis` | 表2-2 措施项目清单分析表 | 措施项目明细和费用构成 |
| `resource_analysis` | 表2-3 综合单价工料机分析表 | 工料机组成、消耗量、单价 |
| `measure_resource_analysis` | 表2-4 措施项目工料机分析表 | 措施项目工料机组成 |
| `temporary_facility_cost_analysis` | 表2-5 临时宿舍取暖降温等费用分析表 | 费用名称、数量、单价、合价 |

## 6. 资格/资信可选章节类型清单

这些章节不一定属于商务标主册，但在工程类投标中经常与商务/资格生成共用上下文。

| section_type | 章节名称 | 是否必备 | 生成方式 | 关键输入 |
| --- | --- | --- | --- | --- |
| `qualification_cover` | 资格审查资料封面 | 条件必备 | 固定表单填充 | 工程名称、投标人、日期 |
| `qualification_directory` | 资格审查目录 | 条件必备 | 规则生成 | 资格业绩、其他资料 |
| `qualification_performance_summary` | 资格业绩汇总表 | 条件章节 | 表格填充 + 证据绑定 | 项目名称、业主、规模、合同价、开竣工日期、证明材料位置 |
| `qualification_other_materials` | 资格审查其他资料 | 条件章节 | 附件绑定 | 招标文件要求、证照、承诺、说明 |
| `credit_scoring_index` | 评分索引表 | 条件章节 | 规则生成 + 人工确认 | 评审因素、分值、页码、证明材料 |
| `bidder_basic_info` | 投标人基本情况表 | 常见章节 | 表格填充 + 证据绑定 | 注册地址、联系方式、组织结构、资质等级、营业执照、开户信息、经营范围 |
| `financial_status` | 近年财务状况表 | 条件章节 | 表格/附件绑定 | 年份、审计报告、资产负债、收入、利润等 |
| `scoring_performance_summary` | 评分业绩汇总表 | 条件章节 | 表格填充 + 证据绑定 | 企业业绩、项目经理业绩、证明材料位置 |
| `project_management_team` | 项目管理班子配备情况表 | 工程类常见必备 | 表格填充 + 证据绑定 | 岗位、姓名、身份证、职称、证书、证号、专业、到位承诺率 |
| `project_manager_resume` | 项目负责人简历表 | 条件章节 | 表格填充 + 证据绑定 | 项目经理经历、证书、社保、业绩 |
| `technical_leader_resume` | 项目技术负责人简历表 | 条件章节 | 表格填充 + 证据绑定 | 技术负责人经历、职称、证书、社保 |
| `team_supporting_materials` | 班子辅助说明资料 | 条件章节 | 附件绑定 | 聘用合同、社保、证书、职称材料 |

## 7. 字段包建议

### 7.1 项目字段

1. `project_name`
2. `tender_project_no`
3. `tenderer_name`
4. `bid_section_name`
5. `project_location`
6. `project_scope`
7. `bid_deadline`
8. `bid_date`
9. `quality_standard`
10. `construction_period_days`

### 7.2 投标人字段

1. `bidder_name`
2. `bidder_address`
3. `postal_code`
4. `contact_name`
5. `contact_phone`
6. `fax`
7. `email`
8. `website`
9. `legal_representative_name`
10. `legal_representative_title`
11. `legal_representative_id_no`
12. `authorized_agent_name`
13. `authorized_agent_id_no`
14. `authorization_start_date`
15. `authorization_end_date`

### 7.3 报价字段

1. `bid_price_amount`
2. `bid_price_amount_upper`
3. `bid_security_amount`
4. `bid_security_amount_upper`
5. `performance_security_policy`
6. `risk_control_price_delta_policy`
7. `boq_summary_total`
8. `boq_file_ids`
9. `pricing_basis`
10. `tax_policy`

### 7.4 人员字段

1. `project_manager`
2. `technical_leader`
3. `quality_officer`
4. `safety_officers`
5. `constructor`
6. `document_controller`
7. `material_officer`
8. `cost_engineer`
9. `attendance_commitment`
10. `social_security_evidence`

### 7.5 业绩字段

1. `performance_owner`
2. `performance_project_name`
3. `construction_unit`
4. `building_area`
5. `contract_amount`
6. `start_date`
7. `completion_date`
8. `technical_metrics`
9. `evidence_materials`
10. `evidence_location`

## 8. ContextPack 使用规则

### GlobalContextPack

放入：

1. 项目基本信息。
2. 商务标目录要求。
3. 投标人基础信息摘要。
4. 报价总价摘要。
5. 资格/资信可选卷册摘要。
6. 风险和缺项摘要。

不放入：

1. 大量清单明细。
2. 人员证书全文。
3. 业绩证明全文。
4. 技术标正文。

### OutlinePlan

规则：

1. 商务标目录中的 1 到 11 项默认生成章节。
2. 联合体协议书根据是否联合体决定生成“无”或具体协议。
3. 资格审查和资信标章节作为可选卷册，由招标文件要求或用户选择决定。
4. 工程量清单明细只进入目录和摘要，不交给 LLM 逐项生成。
5. 所有强制章节必须有 `source_basis`。

### SectionContextPack

按章节裁剪：

1. 法定代表人身份证明书只需要投标人和法定代表人字段。
2. 授权委托书只需要法定代表人、代理人、项目和授权期限字段。
3. 投标函需要招标人、招标编号、项目名称、报价、工期、担保、项目经理、投标有效期等字段。
4. 报价说明需要工程概况、投标范围、编制依据、质量、工期、费率和其他承诺。
5. 清单计价章节只引用报价文件、总价、汇总表和校验结果。
6. 人员班子章节需要人员、证书、社保、到位承诺和证明材料。
7. 业绩章节需要业绩事实、证明材料和资信标页码。

## 9. 生成方式建议

| 章节类型 | 建议方式 |
| --- | --- |
| 封面、目录、法定代表人证明、授权委托书、投标总价封面 | 确定性填充 |
| 投标函、投标函附录、投标承诺书 | 固定条款 + 字段填充 + 少量模型润色 |
| 工程量清单报价说明 | 模板骨架 + 项目事实 + 模型生成候选段落 |
| 已标明价格的工程量清单 | 外部报价文件导入/绑定，不由 LLM 生成 |
| 资格业绩、评分业绩、项目管理班子 | 表格填充 + 证据绑定 + 模型生成说明 |
| 其他投标资料 | 由招标文件要求驱动，默认占位和人工上传 |

## 10. 校验规则

1. 商务标目录章节是否完整。
2. 投标函报价、投标总价封面、工程项目报价汇总表三者金额是否一致。
3. 投标报价大小写是否一致。
4. 项目名称、招标编号、招标人是否全册一致。
5. 投标日期是否一致。
6. 法定代表人与授权代理人是否同时满足签署要求。
7. 工期、质量标准、履约保证金是否与招标文件要求一致。
8. 联合体章节是否与投标方式一致。
9. 保证金凭证是否存在并可追溯。
10. 业绩汇总表是否绑定中标通知书、合同、竣工验收报告。
11. 项目管理班子是否绑定证书、聘用合同和社保证明。
12. 未适用章节是否有明确“不适用/无/人工说明”。

## 11. 第一版章节类型枚举

```json
[
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
  "project_quote_summary",
  "unit_quote_summary",
  "subsection_bill_pricing",
  "organization_measure_overall",
  "organization_measure_professional",
  "technical_measure_pricing",
  "safe_civilized_measure_pricing",
  "other_item_pricing",
  "daywork_pricing",
  "general_contract_service_fee",
  "labor_price_table",
  "material_price_table",
  "machinery_price_table",
  "unit_price_analysis",
  "measure_item_analysis",
  "resource_analysis",
  "measure_resource_analysis",
  "temporary_facility_cost_analysis",
  "other_business_materials",
  "qualification_cover",
  "qualification_directory",
  "qualification_performance_summary",
  "qualification_other_materials",
  "credit_cover",
  "credit_scoring_index",
  "bidder_basic_info",
  "financial_status",
  "scoring_performance_summary",
  "project_management_team",
  "project_manager_resume",
  "technical_leader_resume",
  "team_supporting_materials",
  "credit_other_materials"
]
```

## 12. 后续样本验证建议

这份初版来自一个工程类施工投标包。后续建议再用以下样本验证和扩展：

1. 一个设备采购类商务/资格标书。
2. 一个服务类商务/资格标书。
3. 一个联合体投标样本。
4. 一个没有独立资信标、把资信材料并入商务标的样本。
5. 一个招标文件明确给出特殊格式表单的样本。

验证重点：

1. 章节类型是否够用。
2. 条件章节是否能收敛。
3. 报价清单是否能只做摘要和附件绑定。
4. 人员、业绩、资格证据是否能进入 SectionContextPack。
5. Word 导出模板是否能复用同一套 `DraftBlock`。
