# 投标 Agent MVP-v1.3 需求规划与开发进度

> 更新时间：2026-06-06
> 当前阶段：需求边界已确认，待 MVP1.2 ContextPack 生成/确认链路稳定后启动
> 版本定位：基于已确认 ContextPack 的商务/资格章节草稿生成、审阅、事实校验和导出闭环。
> 明确不做：不接真实 RAG、Embedding 或 Rerank；这些进入 MVP1.4。

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

其中第 1 到第 3 项进入 MVP1.4；其余进入长期规划。

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
| 目录生成/确认 | 基于 ContextPack 和 TemplateProfile 生成章节目录 | 未开始 | 可复用 MVP1.2 outline_plan，允许人工调整 |
| 分章节 prompt | 每个章节独立 prompt、输入变量和输出 schema | 首版已有基础，待按 1.3 验收加固 | 不使用单一大 prompt 生成整本标书 |
| DraftBlock 生成 | 输出 heading、paragraph、table、list、placeholder | 首版已有基础，待加固 | 每个 block 记录条目、证据、缺项和来源 |
| 生成门禁 | 未确认 ContextPack 或 readiness block 时阻止正式草稿 | 部分已有，待产品化 | block 只允许内部草稿风险接受 |
| 异步生成 | 大项目走任务队列，前端展示进度和失败原因 | 首版已有基础，待加固 | 失败不保存为有效草稿 |
| 审计与快照 | 保存模型输入摘要、输出、版本、人工原因 | 首版已有基础，待加固 | 支持复盘和回滚 |

### P1：生成后检查和审阅

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 覆盖检查 | 检查强制项、高风险项、资格项是否被覆盖 | 首版已有基础，待加固 | 输出 coverage rate、证据引用率和质量分 |
| 事实校验 | 校验项目名、金额、日期、单位名、证书编号、人员和业绩 | 部分已有 | 人员/业绩细分规则需补 |
| 左右对照审阅 | 左侧草稿正文，右侧合规条目队列 | 首版已有基础，待加固 | 支持 block 与矩阵互相定位 |
| 审阅状态 | 区分已覆盖、缺证据、待补事实、已批准、驳回 | 首版已有基础 | 导出前必须收敛关键状态 |
| 人工修改 | 修改章节或 block 时记录差异和原因 | 首版已有基础 | 修改后触发事实校验 |
| Word 导出 | 基于审阅通过的结构化稿导出 Word | 首版已有基础 | 未通过时只能内部草稿或拒绝导出 |

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

当前为规划完成、待 MVP1.2 稳定后启动状态；部分底层能力已有早期实现，但需按 1.3 口径重新验收。

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| 版本边界 | 已确认 | 1.3 做 ContextPack 驱动的草稿生成，不做 RAG |
| 需求规划 | 已完成 | 本文档为规划与进度统一文档 |
| 后端生成接口 | 首版已有，待加固 | 当前已有同步/异步生成、coverage、block 接口 |
| 前端草稿入口 | 待 1.2 稳定后重新开放 | 1.2 阶段按钮仅提示 1.3 |
| 单元测试 | 待重排 | 从 1.2 测试中迁出草稿生成验收 |
| 浏览器测试 | 未开始 | 待 1.3 生成交互稳定后补 |

## 11. 与 MVP1.4 的交接

MVP1.4 将增强证据召回，不改变 1.3 的生成边界：

1. MVP1.4 推荐候选证据，人工确认后进入 `bound_evidence`。
2. MVP1.3 只引用 `bound_evidence` 和已确认 ContextPack，不直接引用未确认候选。
3. RAG 失败时，MVP1.2/1.3 的手工证据绑定和草稿生成仍应可用。
