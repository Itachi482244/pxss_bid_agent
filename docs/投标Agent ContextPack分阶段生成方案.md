# 投标 Agent ContextPack 分阶段生成方案

> 更新时间：2026-06-04
> 适用版本：MVP1.2
> 目标：说明商务/资格草稿生成时，如何分阶段构建 ContextPack，并让 LLM 在受控目录和章节上下文中生成结构化标书内容。

## 1. 结论

MVP1.2 不应一次性把所有项目、矩阵、证据和企业资料塞给 LLM 生成整本商务/资格标书。

推荐采用分阶段链路：

```text
TemplateProfile
  -> GlobalContextPack
    -> OutlinePlan
      -> SectionContextPack
        -> DraftBlock
          -> CoverageReview
```

其中：

1. `TemplateProfile` 定义生成边界和章节骨架。
2. `GlobalContextPack` 汇总全局项目、矩阵、证据和风险摘要。
3. `OutlinePlan` 是受控目录计划，不是 LLM 自由发挥的目录。
4. `SectionContextPack` 按章节裁剪上下文。
5. `DraftBlock` 是结构化生成稿的最小审阅单位。
6. `CoverageReview` 做全文覆盖、事实一致性和风险检查。

## 2. 设计目标

1. 控制上下文长度，避免大上下文导致遗漏、混写和不可复盘。
2. 让每个章节有明确输入、输出、证据和风险边界。
3. 支持章节级重试、章节级审阅和章节级导出。
4. 保证每个生成段落都能回链合规条目、招标原文和企业证据。
5. 为 MVP1.3 的 RAG 预留 `candidate_evidence` 扩展位。

## 3. 非目标

MVP1.2 不做以下事情：

1. 不接真实 RAG、Embedding 或 Rerank。
2. 不让 LLM 自由决定整本标书结构。
3. 不直接生成不可追踪的完整 Word。
4. 不生成技术标核心章节。
5. 不做净化产品选型、图纸、OCR、多 Agent 或报价。

## 4. 模板定位

ContextPack 需要模板约束，但不应被某一份 Word 模板绑死。

模板分三层：

| 层级 | 名称 | 作用 |
| --- | --- | --- |
| 生成规则模板 | `TemplateProfile` | 定义章节、必填字段、证据要求、输出格式和禁止事项 |
| 结构化生成稿 | `DraftSection` / `DraftBlock` | 保存模型生成结果和审阅状态 |
| Word 导出模板 | `.docx` 模板 | 负责页眉页脚、目录、样式、表格和最终排版 |

优先级：

1. 招标文件明确给出的投标文件格式优先。
2. 项目选择的 `TemplateProfile` 次之。
3. 系统默认商务/资格模板作为兜底。

LLM 可以辅助修订目录标题、合并相近章节、补充章节说明，但不能绕过招标文件格式和默认模板骨架。

## 5. 阶段一：GlobalContextPack

`GlobalContextPack` 用于生成目录计划和全局约束，只放粗粒度信息。

建议字段：

```json
{
  "schema_version": "1.0",
  "project": {
    "project_name": "",
    "bid_section_name": "",
    "tenderer": "",
    "deadline": "",
    "budget": "",
    "industry": ""
  },
  "source_document": {
    "document_id": "",
    "version_id": "",
    "version_status": "current"
  },
  "template_profile": {
    "template_id": "",
    "template_version": "",
    "default_sections": []
  },
  "matrix_summary": {
    "total": 0,
    "confirmed": 0,
    "high_risk": 0,
    "mandatory": 0,
    "qualification": 0,
    "missing_evidence": 0
  },
  "risk_summary": [],
  "available_evidence_summary": [],
  "missing_facts": [],
  "generation_constraints": []
}
```

Global 阶段不放大量证据原文，不生成正文。

## 6. 阶段二：OutlinePlan

`OutlinePlan` 是目录计划，也是后续每章生成的任务清单。

生成方式：

1. 规则先解析招标文件格式要求。
2. 系统加载默认 `TemplateProfile`。
3. 系统把矩阵摘要、章节类型和必填字段交给 LLM。
4. LLM 只允许在约束内建议目录和章节映射。
5. 系统校验目录计划。
6. 用户预览并确认目录计划。

章节计划建议字段：

```json
{
  "outline_plan_id": "uuid",
  "source": "tender_format + template_profile + llm_suggestion",
  "sections": [
    {
      "section_id": "qualification_response",
      "title": "资格响应文件",
      "section_type": "qualification",
      "required": true,
      "source_basis": "招标文件格式要求",
      "order_index": 10,
      "compliance_item_ids": [],
      "required_fields": [],
      "evidence_required": true,
      "output_format": "structured_blocks",
      "review_policy": "manual_required"
    }
  ]
}
```

OutlinePlan 校验规则：

1. 招标文件要求的章节不得缺失。
2. 强制项和资格项必须至少映射到一个章节。
3. 没有证据的章节必须标记 `evidence_gap`。
4. 高风险章节必须标记 `manual_required`。
5. 目录计划必须可预览、可编辑、可重新生成。

## 7. 阶段三：SectionContextPack

`SectionContextPack` 是生成某一章的精确输入。

每个章节单独构建上下文：

```json
{
  "section_context_pack_id": "uuid",
  "outline_plan_id": "uuid",
  "section": {
    "section_id": "qualification_response",
    "title": "资格响应文件",
    "section_type": "qualification"
  },
  "project_facts": {},
  "matrix_items": [],
  "bound_evidence": [],
  "manual_notes": [],
  "risk_acceptances": [],
  "missing_facts": [],
  "candidate_evidence": [],
  "output_schema": {},
  "forbidden_claims": []
}
```

裁剪规则：

1. 只放本章需要覆盖的矩阵项。
2. 只放本章可引用的已绑定证据。
3. 本章缺失的字段进入 `missing_facts`。
4. 本章不能承诺的内容进入 `forbidden_claims`。
5. MVP1.3 的候选证据只能进入 `candidate_evidence`，人工确认后才进入 `bound_evidence`。

## 8. 阶段四：DraftBlock

LLM 输出结构化 `DraftBlock`，不直接输出整份 Word。

建议字段：

```json
{
  "block_id": "uuid",
  "section_id": "qualification_response",
  "block_type": "paragraph",
  "content": "",
  "covers_compliance_item_ids": [],
  "uses_evidence_ids": [],
  "source_chunk_ids": [],
  "fact_claims": [],
  "missing_fact_placeholders": [],
  "risk_flags": [],
  "review_status": "pending"
}
```

生成约束：

1. 每个 block 必须声明覆盖哪些合规项。
2. 每个事实性陈述必须引用证据或进入待确认。
3. 不能使用 SectionContextPack 之外的事实。
4. 缺证据时生成占位或待补说明，不包装成已确认事实。
5. 输出必须通过 schema 校验，否则进入重试或人工处理。

## 9. 阶段五：CoverageReview

章节生成完成后，系统做全文级检查。

检查项：

1. 强制项覆盖率。
2. 资格项覆盖率。
3. 高风险项处理状态。
4. 已绑定证据引用率。
5. 项目名称、日期、单位名称、证书编号、人员、业绩跨章节一致性。
6. 重复段落和冲突表述。
7. 待确认占位数量。
8. Word 导出前风险快照。

输出示例：

```json
{
  "coverage_review_id": "uuid",
  "status": "block",
  "summary": {
    "mandatory_coverage": "96%",
    "qualification_coverage": "88%",
    "missing_fact_count": 6,
    "fact_conflict_count": 1
  },
  "issues": []
}
```

## 10. UI 建议

MVP1.2 建议提供四个页面或面板：

1. 生成准备页：展示准备度检查、缺项、风险和推荐处理动作。
2. 目录计划页：展示 OutlinePlan，允许用户确认、调整、重新生成。
3. 章节生成页：按章节展示状态、生成、重试和校验结果。
4. 草稿审阅页：左侧结构化正文，右侧合规条目、证据和问题队列。

核心交互原则：

1. 用户先确认目录，再逐章生成。
2. 每章可独立重试，不影响其他章节。
3. 所有 block 可定位到矩阵项和证据。
4. 未解决 blocker 时不能导出正式版本。

## 11. 接口建议

```text
POST /projects/{project_id}/draft/global-context-pack/preview
POST /projects/{project_id}/draft/outline-plan
PATCH /draft-outline-plans/{outline_plan_id}
POST /draft-outline-plans/{outline_plan_id}/confirm
POST /draft-outline-plans/{outline_plan_id}/sections/{section_id}/context-pack
POST /section-context-packs/{section_context_pack_id}/generate
GET /drafts/{draft_id}/review
POST /drafts/{draft_id}/coverage-review
POST /drafts/{draft_id}/export-word
```

## 12. 数据对象建议

1. `template_profiles`
2. `draft_global_context_packs`
3. `draft_outline_plans`
4. `draft_section_context_packs`
5. `draft_sections`
6. `draft_blocks`
7. `draft_block_links`
8. `draft_coverage_reviews`
9. `draft_review_actions`

## 13. 异常收敛

| 场景 | 处理方式 |
| --- | --- |
| 招标文件无明确格式 | 使用默认商务/资格 TemplateProfile |
| 未生成资格预评估结论 | 允许预览 ContextPack，但不允许确认 ContextPack |
| 参标建议未人工确认 | 阻塞 ContextPack 确认和草稿生成，回到资格预评估确认 |
| 参标建议为 Conditional Go | ContextPack 标记 warn，章节上下文保留缺材料/待复核事项 |
| 参标建议为 No-Go | ContextPack 标记 block，只有填写风险接受说明后才能生成内部草稿 |
| 目录计划缺少强制项 | 阻塞确认，提示补充章节映射 |
| 章节上下文无证据 | 生成占位或待补说明，不生成确定性段落 |
| SectionContextPack 超长 | 章节内再按条目组拆分生成 |
| 模型输出不符合 schema | 重试一次，仍失败则进入人工处理 |
| 事实冲突 | 标记 block，不允许审阅通过 |
| 章节生成失败 | 章节级失败，不影响其他章节 |
| DraftBlock 未人工通过 | 提交前核验标记 block，正式导出前必须逐 block 审阅通过 |
| Word 导出前仍有 blocker | 只允许导出内部草稿，并记录风险接受说明 |

## 14. 验收标准

1. 系统能从项目、矩阵、证据和模板生成 GlobalContextPack。
2. 系统能生成并校验 OutlinePlan。
3. 用户能预览和确认目录计划。
4. 系统能按章节生成 SectionContextPack。
5. LLM 能按 SectionContextPack 输出结构化 DraftBlock。
6. 每个 DraftBlock 都能回链合规项和证据。
7. 章节可独立重试、独立审阅。
8. 全文 CoverageReview 能发现未覆盖强制项、缺证据和事实冲突。
9. Word 导出只基于审阅通过的结构化稿。
10. 全流程写入审计日志，能复盘“哪一段文字基于哪个上下文生成”。
