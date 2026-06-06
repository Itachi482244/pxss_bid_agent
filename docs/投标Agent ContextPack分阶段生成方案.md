# 投标 Agent ContextPack 分阶段生成方案

> 更新时间：2026-06-06
> 适用版本：MVP1.2 负责 ContextPack 预览/生成/确认；MVP1.3 负责基于 ContextPack 的目录和章节草稿生成。
> 目标：说明如何分阶段构建受控上下文，让后续 LLM 生成在可追溯、可校验、可阻断的输入之上运行。

## 1. 总体判断

ContextPack 应该分阶段构建，而不是一次性把所有项目、矩阵、证据和企业资料塞给 LLM。

推荐链路：

```text
Project + BidSection + Matrix + Evidence + QualificationDecision
  -> GlobalContextPack
    -> OutlinePlan
      -> SectionContextPack
        -> DraftBlock
          -> Review / FactCheck / Export
```

版本边界：

1. MVP1.2 做到 `GlobalContextPack`、`OutlinePlan` 和 `SectionContextPack` 可预览、可确认、可审计。
2. MVP1.3 从已确认的 `SectionContextPack` 开始生成 `DraftBlock`，再做覆盖检查、事实校验、审阅和导出。
3. MVP1.4 的 RAG/Embedding/Rerank 只增强候选证据来源，不直接绕过人工绑定。

## 2. 为什么要分阶段

分阶段 ContextPack 的价值：

1. 降低上下文噪音：目录生成只需要粗粒度信息，章节生成才需要细粒度证据。
2. 让异常更收敛：资格未确认、缺证据、缺字段、No-Go 都能在生成前被发现。
3. 便于人工确认：用户可以先确认“模型将使用什么”，再进入“模型如何表达”。
4. 便于审计复盘：每次生成都能追溯到固定版本的 ContextPack。
5. 便于后续接 RAG：候选证据只进入候选区，人工确认后才进入正式 `bound_evidence`。

## 3. 不做的事

MVP1.2 不做：

1. 不生成商务/资格正文草稿。
2. 不生成结构化 `DraftBlock`。
3. 不做覆盖检查、事实校验和 Word 导出。
4. 不接真实 RAG、Embedding 或 Rerank。
5. 不让模型自动补齐证据或自动判断企业资质真实性。

MVP1.3 才开始做正文草稿生成；MVP1.4 才开始做 RAG 证据推荐。

## 4. TemplateProfile 的角色

ContextPack 需要模板约束，但不应被某一份 Word 模板绑死。

`TemplateProfile` 的作用是：

1. 定义商务/资格章节类型、默认顺序和适用场景。
2. 定义每个章节需要哪些矩阵项、证据和项目字段。
3. 定义输出约束，例如不得编造证书编号、人员、金额和日期。
4. 为 MVP1.3 的 prompt 和 schema 提供稳定输入。

`TemplateProfile` 在 MVP1.2 不负责生成正文，只负责让 `outline_plan_json` 和 `section_context_packs` 有结构。

## 5. 阶段一：GlobalContextPack

`GlobalContextPack` 是全局粗粒度上下文，用于确定生成范围和目录计划。

建议包含：

```json
{
  "project_facts": {
    "project_name": "",
    "purchaser": "",
    "agency": "",
    "budget_amount": "",
    "bid_deadline_at": "",
    "region_code": "",
    "industry_code": ""
  },
  "source_document": {
    "document_id": "",
    "current_version_id": "",
    "parser_name": "",
    "parser_version": ""
  },
  "qualification_decision": {
    "recommendation": "go|conditional_go|no_go",
    "status": "confirmed",
    "summary": "",
    "confirmed_by": "",
    "confirmed_at": ""
  },
  "matrix_summary": {
    "total": 0,
    "confirmed": 0,
    "high_risk": 0,
    "missing_evidence": 0
  },
  "bound_evidence": [],
  "missing_facts": [],
  "readiness_json": {}
}
```

MVP1.2 验收重点：

1. 数据来源固定。
2. 资格门禁明确。
3. 缺项和阻断项明确。
4. 已绑定证据去重。
5. 预览与确认结果一致。

## 6. 阶段二：OutlinePlan

`OutlinePlan` 是目录和章节计划。

来源优先级：

1. TemplateProfile 默认章节。
2. 招标文件中明确要求的响应文件组成。
3. 合规矩阵中出现的资格、商务、格式和承诺类条目。
4. 用户通过 API 或 UI 明确选择的 `section_types`。

示例：

```json
{
  "sections": [
    {
      "section_type": "bid_letter",
      "title": "投标函",
      "required_matrix_item_ids": [],
      "required_evidence_types": [],
      "missing_fact_fields": []
    },
    {
      "section_type": "qualification_performance_summary",
      "title": "资格及业绩响应",
      "required_matrix_item_ids": [],
      "required_evidence_types": ["qualification", "personnel", "performance"],
      "missing_fact_fields": []
    }
  ]
}
```

MVP1.2 只确认目录计划，不让模型写正文。

## 7. 阶段三：SectionContextPack

`SectionContextPack` 是章节级精确输入。

每个 SectionContextPack 应包含：

1. 章节类型、标题和排序。
2. 相关矩阵项。
3. 相关已绑定证据。
4. 相关缺事实。
5. 章节输出约束。
6. 章节风险提示。

示例：

```json
{
  "section_type": "qualification_performance_summary",
  "title": "资格及业绩响应",
  "matrix_items": [],
  "bound_evidence": [],
  "missing_facts": [],
  "constraints": [
    "不得编造证书编号",
    "不得声称未绑定的人员或业绩已经满足要求"
  ]
}
```

MVP1.2 验收重点：

1. 每个计划章节都有章节上下文。
2. 章节上下文只包含与章节相关的矩阵项和证据。
3. 缺证据和缺事实保留在章节上下文内。
4. 章节上下文可被 MVP1.3 直接消费。

## 8. 阶段四：DraftBlock（MVP1.3）

MVP1.3 才生成结构化 `DraftBlock`。

DraftBlock 输出要求：

1. 不直接输出整份 Word。
2. 每个 block 带 `compliance_item_ids` 和 `evidence_binding_ids`。
3. 无证据内容标记 `needs_evidence`。
4. 无法验证事实标记 `needs_fact`。
5. 人工审阅后才能进入正式导出。

## 9. 异常处理

| 场景 | MVP1.2 处理 | MVP1.3 处理 |
| --- | --- | --- |
| 未生成资格预评估 | 允许预览，阻止确认 ContextPack | 不允许生成 |
| 参标建议未确认 | 阻止确认 ContextPack | 不允许生成 |
| Conditional Go | ContextPack warn | 允许生成，提交前复核 |
| No-Go | ContextPack block | 只允许风险接受后的内部草稿 |
| 缺企业资料证据 | ContextPack block，回到证据绑定 | 不允许正式草稿 |
| 缺项目字段 | 写入 `missing_facts` | 生成占位或待确认 |
| 章节上下文过长 | 记录需要再拆分 | 章节内按条目组拆分生成 |
| 模型输出失败 | 不涉及 | 重试或不保存有效草稿 |

## 10. 前端信息架构

MVP1.2 页面重点：

1. ContextPack 状态：未生成、已预览、已确认、阻断。
2. 资格门禁：未评估、未确认、Conditional Go、No-Go。
3. 准备度检查：缺证据、缺字段、矩阵未确认、版本风险。
4. 章节计划：将生成哪些章节，但不展示正文。
5. 操作按钮：预览、确认 ContextPack、去处理阻断项。

MVP1.3 页面重点：

1. 基于 ContextPack 生成目录和章节草稿。
2. 草稿 block 审阅和双向定位。
3. 覆盖检查、事实校验和 Word 导出。

## 11. 验收标准

MVP1.2 验收：

1. 系统能从项目、矩阵、证据和资格结论生成 GlobalContextPack。
2. 系统能展示 readiness pass/warn/block 和处理动作。
3. 系统能生成 OutlinePlan。
4. 系统能按章节生成 SectionContextPack。
5. 系统能确认 ContextPack，并 supersede 旧版本。
6. 未确认资格结论时不能确认 ContextPack。
7. 缺证据和缺事实不会被写成确定性事实。

MVP1.3 验收：

1. 系统能按 SectionContextPack 输出结构化 DraftBlock。
2. 每个 DraftBlock 都能回链合规项和证据。
3. 覆盖检查和事实校验能发现未收敛内容。
4. 审阅通过后才能导出 Word。
