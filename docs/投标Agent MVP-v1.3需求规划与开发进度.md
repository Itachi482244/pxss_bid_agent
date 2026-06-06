# 投标 Agent MVP-v1.3 需求规划与开发进度

> 更新时间：2026-06-06
> 当前阶段：核心链路已开发完成并通过验收测试；剩浏览器端联调与章节级目录编辑增强
> 版本定位：基于已确认 ContextPack 的商务/资格章节草稿生成、审阅、事实校验和导出闭环。
> 明确不做：不接真实 RAG、Embedding 或 Rerank；这些进入 MVP1.5。

## 1. 版本目标

MVP1.3 的目标是让模型在 MVP1.2 已确认的 ContextPack 上工作，生成可审阅、可追溯、可校验的商务/资格章节草稿。

本版本要解决的问题：

1. 先基于 GlobalContextPack 生成目录/章节计划，再基于 SectionContextPack 逐章生成内容。
2. 草稿必须保存为结构化章节和 `DraftBlock`，而不是直接生成整份 Word。
3. 每个段落、表格和清单都要回链到矩阵项、招标原文和已绑定证据。
4. 生成后必须做覆盖检查和事实校验，未覆盖、缺证据、事实冲突进入人工审阅。
5. 审阅通过后才能导出 Word；No-Go 或阻断状态下只允许内部草稿并记录风险接受。

## 2. 核心原则

1. 只消费已确认的 ContextPack，不临时绕过资格预评估、矩阵确认和证据绑定。
2. 大模型只负责表达、归纳和章节组织，不负责创造事实。
3. 硬字段和可验证事实来自 ContextPack，生成结果不得与来源冲突。
4. 缺证据、缺事实和未确认风险必须保留占位或审阅状态。
5. Word 是导出格式，结构化章节和 block 才是主要审阅对象。

## 3. 不纳入 MVP1.3

以下能力不进入 MVP1.3：

1. 企业资料真实 pgvector RAG。
2. Embedding / Rerank 调用链。
3. 自动候选证据推荐和语义绑定。
4. 技术标核心章节生成。
5. 净化产品选型、图纸/OCR、多 Agent、报价辅助、自动报名、自动签章和自动提交。

其中第 1 到第 3 项进入 MVP1.5；其余进入长期规划。

## 4. 前置依赖

MVP1.3 依赖：

1. MVP1.2 ContextPack schema 稳定，且具备 `context_json`、`outline_plan_json` 和 `section_context_packs`。
2. 参标建议已人工确认，ContextPack readiness 有明确 pass/warn/block 结论。
3. 矩阵项、证据绑定、缺事实和风险记录已在 ContextPack 中完整呈现。
4. TemplateProfile 已能描述工程类商务/资格章节类型、默认顺序和输出约束。
5. 审计日志、模型调用记录和 PromptOps registry 可用。

## 5. 主流程

MVP1.3 主流程如下：

1. 用户选择已确认的 ContextPack，点击“生成商务/资格草稿”。
2. 如果 ContextPack readiness 为 block，系统要求用户处理阻断；如确需继续，只能选择“风险接受后生成内部草稿”。
3. 系统基于 GlobalContextPack 生成或确认章节目录。
4. 系统按目录逐章构建 SectionContextPack，并调用章节 prompt。
5. 模型输出结构化 `DraftBlock`，每个 block 带来源链接、证据链接和审阅状态。
6. 系统自动执行覆盖检查和事实校验。
7. 用户在左右对照审阅视图中处理未覆盖、缺证据、待确认和事实冲突。
8. 全部关键 block 审阅通过后，允许导出 Word 或进入审批流。

## 6. 需求范围

### P0：结构化草稿生成

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 目录生成/确认 | 基于 ContextPack 和 TemplateProfile 生成章节目录 | 部分完成 | outline_plan 可预览，支持 section_types 选择；章节级增删改排序待补 |
| 分章节 prompt | 每个章节独立 prompt、输入变量和输出 schema | 已完成 | 逐 SectionContextPack 生成，不使用单一大 prompt |
| DraftBlock 生成 | 输出 heading、paragraph、table、list、placeholder | 已完成 | 逐条款 block，记录条目、证据、缺项和来源回链 |
| 生成门禁 | 未确认 ContextPack 或 readiness block 时阻止正式草稿 | 已完成 | block 仅允许内部草稿风险接受（测试守住） |
| 异步生成 | 大项目走任务队列，前端展示进度和失败原因 | 已完成 | 失败不保存为有效草稿 |
| 审计与快照 | 保存模型输入摘要、输出、版本、人工原因 | 已完成 | 生成/编辑/导出均写审计与快照 |

### P1：生成后检查和审阅

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 覆盖检查 | 检查强制项、高风险项、资格项是否被覆盖 | 已完成 | 输出 coverage rate（守住 [0,1]）、证据引用率和质量分 |
| 事实校验 | 校验项目名、金额、日期、单位名、证书编号、人员和业绩 | 已完成 | 已补人员（姓名/身份证/建造师证号）与业绩（合同金额/工程名称）细分规则 |
| 左右对照审阅 | 左侧草稿正文，右侧合规条目队列 | 已完成 | block↔矩阵↔原文↔审阅台双向定位 |
| 审阅状态 | 区分已覆盖、缺证据、待补事实、已批准、驳回 | 已完成 | 导出前由 preflight 收敛关键状态 |
| 人工修改 | 修改章节或 block 时记录差异和原因 | 已完成 | 编辑 block 后重组章节正文并重跑事实校验 |
| Word 导出 | 基于审阅通过的结构化稿导出 Word | 已完成 | 未通过时只能内部草稿（需风险接受说明）或拒绝导出 |

## 7. 异常处理和收敛规则

| 场景 | 系统处理 | 是否允许正式草稿 |
| --- | --- | --- |
| 无已确认 ContextPack | 引导回 MVP1.2 确认 ContextPack | 不允许 |
| ContextPack readiness 为 block | 展示阻断项和处理入口 | 不允许；风险接受后仅内部草稿 |
| ContextPack readiness 为 warn | 允许生成，但缺项进入待确认 | 允许，提交前必须复核 |
| 章节 prompt 失败 | 记录失败，支持重试 | 不保存有效章节 |
| 输出 schema 不合法 | 结构化修复或重试 | 不保存有效 block |
| 无法验证事实 | 标记 `needs_fact`，不得自动批准 | 不允许审阅通过 |
| 缺证据 | 标记 `needs_evidence`，引导回证据绑定 | 不允许正式导出 |
| 用户人工修改 | 写审计并重新检查事实 | 修改后按新状态判断 |

## 8. 数据与接口

MVP1.3 主要对象：

1. `business_draft_chapters`
2. `draft_blocks`
3. `draft_coverage_reviews`
4. `draft_fact_checks`
5. `async_tasks(task_type=business_draft_generate)`
6. `audit_logs`

MVP1.3 主要接口：

1. `POST .../context-pack/{context_pack_id}/generate`
2. `POST .../context-pack/{context_pack_id}/generate-async`
3. `POST .../context-pack/{context_pack_id}/coverage-review`
4. `GET .../business-draft/blocks`
5. `PATCH .../business-draft/blocks/{block_id}`
6. `GET/POST/PATCH .../business-draft/chapters`
7. `POST .../business-draft/chapters/{chapter_id}/fact-check`
8. `POST .../business-draft/export-word`

## 9. 验收标准

MVP1.3 按以下标准验收：

1. 只有已确认 ContextPack 才能进入正式草稿生成。
2. 目录/章节计划可预览和人工调整。
3. 每个章节由对应 SectionContextPack 生成，不使用无边界全量上下文。
4. 生成结果保存为结构化章节和 `DraftBlock`。
5. 每个关键 block 能回链矩阵项、招标原文和企业证据。
6. 缺证据、缺事实、No-Go 风险不会被包装成确定性结论。
7. 覆盖检查和事实校验能发现未覆盖、引用缺失和关键事实异常。
8. 审阅视图支持正文与矩阵项双向定位。
9. 导出 Word 前必须处理关键阻断；内部草稿需要风险接受说明。
10. 固定样本覆盖正常生成、阻断拒绝、内部草稿、模型失败、人工修改和导出门禁。

## 10. 开发进度

核心生成-审阅-导出闭环已开发完成并通过后端验收测试与前端构建；10 条验收标准中 9 条已由自动化用例守住，剩浏览器端交互联调与章节级目录编辑增强。

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| 版本边界 | 已确认 | 1.3 做 ContextPack 驱动的草稿生成，不做 RAG |
| 需求规划 | 已完成 | 本文档为规划与进度统一文档 |
| 后端生成接口 | 已完成 | 同步/异步生成、coverage、逐条款 block、导出门禁均已加固 |
| 前端草稿入口 | 已重新开放 | 草稿生成/结构化 block 审阅/覆盖检查/Word 导出/双向定位全部激活 |
| 单元/验收测试 | 已完成 | `test_mvp13_draft_pipeline_api.py` 9 用例；全量后端 149 passed、ruff 通过、前端构建通过 |
| 章节级目录编辑 | 待补 | 当前支持 section_types 选择；章节增删改排序为后续增强 |
| 浏览器测试 | 未开始 | 待补端到端 UI 联调 |

## 11. 与 MVP1.5 的交接

MVP1.5 将增强证据召回，不改变 1.3 的生成边界：

1. MVP1.5 推荐候选证据，人工确认后进入 `bound_evidence`。
2. MVP1.3 只引用 `bound_evidence` 和已确认 ContextPack，不直接引用未确认候选。
3. RAG 失败时，MVP1.2/1.3 的手工证据绑定和草稿生成仍应可用。
