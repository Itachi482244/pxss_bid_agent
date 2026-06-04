# 投标 Agent MVP-v1.2 需求规划与开发进度

> 更新时间：2026-06-04
> 当前阶段：MVP1.2 主链路和审阅闭环首版完成，进入真实样本验收
> 版本定位：ContextPack First。先把商务/资格草稿生成前的上下文输入做稳定、可预览、可审计、可校验，不在本版本接入真实 RAG、Embedding 或 Rerank。
> 功能方案：详见《投标Agent ContextPack分阶段生成方案》。

## 1. 版本目标

MVP1.2 的目标不是“让模型直接写完整标书”，而是建立一套稳定的商务/资格草稿生成上下文包能力，让后续所有生成都基于同一份可追溯输入。

本版本要回答清楚三个问题：

1. 模型生成前，到底允许使用哪些项目、矩阵、证据、风险和人工确认信息。
2. 缺少证据、字段冲突、矩阵未确认、版本过期时，系统应该阻塞、提示还是生成待确认占位。
3. 生成出来的商务/资格草稿如何回链到合规条目、招标原文、企业证据和人工确认记录。

## 2. 核心原则

1. ContextPack 不强依赖 RAG。它只使用当前系统已经存在的项目字段、合规矩阵、已确认条目、已绑定证据、风险接受说明和审批状态。
2. 硬字段用确定性填充。项目名称、招标人、投标截止、公司名称、证书编号、日期等不交给模型自由发挥。
3. 段落表达由模型生成候选稿。资格响应、商务偏离、承诺函等正文可以由模型生成，但必须引用 ContextPack 内的证据和矩阵项。
4. 缺失内容显式待补。没有证据、没有确认、事实冲突或上下文过期时，不允许模型编造。
5. Word 只是导出格式。系统内部先保存结构化生成稿，审阅通过后再导出 Word。

## 3. 不纳入 MVP1.2

以下能力不进入 MVP1.2：

1. 企业资料真实 pgvector RAG。
2. Embedding / Rerank 调用链。
3. 自动证据推荐和语义匹配。
4. 技术标核心章节生成。
5. 净化产品选型、参数匹配和候选配置。
6. 图纸/示意图辅助。
7. OCR、复杂补遗版本链。
8. 多 Agent 编排。
9. 报价辅助、自动报名、自动签章和自动提交。

其中第 1 到第 3 项进入 MVP1.3；其余能力进入长期规划。

## 4. 前置依赖

MVP1.2 依赖 MVP1.1 已完成的能力：

1. 项目、标段、文件、文档版本和解析 chunk。
2. 合规矩阵生成、矩阵审阅、人工补漏和相似补票。
3. 高风险、强制项、资格项确认前原文核对。
4. 企业资料库和人工证据绑定。
5. 资格预评估、提交前核验、风险接受说明和审批快照。
6. 模型配置中心、PromptOps registry、模型调用审计。

## 5. 主流程

MVP1.2 主流程采用分阶段 ContextPack 方案：

1. 用户进入商务/资格草稿生成入口。
2. 系统检查矩阵确认、证据绑定和资格预评估状态。
3. 如果尚未生成或确认参标建议，系统引导用户先运行资格预评估并确认 Go/No-Go。
4. 系统允许提前生成 ContextPack 预览，用于查看缺项、风险、证据和将要生成的章节。
5. 只有已人工确认 Go 或 Conditional Go 时，才允许确认正式 ContextPack。
6. 已确认 No-Go 时，ContextPack 标记为 block；仅允许在风险接受后生成内部草稿。
7. 系统按章节构建 prompt 输入。
8. 模型生成结构化草稿 block。
9. 系统执行生成后校验。
10. 用户进入生成稿审阅视图。
11. 审阅通过后再进入 Word 导出或审批流。

## 6. ContextPack Schema

ContextPack 建议采用版本化 JSON 结构，至少包含以下字段：

```json
{
  "schema_version": "1.0",
  "context_pack_id": "uuid",
  "project": {},
  "bid_section": {},
  "source_document": {},
  "generation_scope": {},
  "qualification_decision": {},
  "matrix_items": [],
  "bound_evidence": [],
  "manual_notes": [],
  "risk_acceptances": [],
  "approval_state": {},
  "missing_facts": [],
  "output_constraints": {},
  "audit": {}
}
```

关键约束：

1. `matrix_items` 只放已确认或允许进入生成的条目。
2. `bound_evidence` 只放人工已绑定、权限允许、未过期或已说明风险的证据。
3. `manual_notes` 必须记录填写人、时间、适用条目和原因。
4. `missing_facts` 必须进入生成稿占位或审阅队列。
5. `output_constraints` 定义章节、格式、禁止事项和引用规则。

## 7. 需求范围

### P0：ContextPack 和结构化草稿主链路

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 上下文包准备度检查 | 检查项目字段、文档版本、矩阵确认、证据绑定、风险接受和审批状态 | 首版完成 | 已输出 pass/warn/block、阻塞原因和处理建议；审批状态和风险接受可继续细化 |
| 资格门禁 | ContextPack 确认和正式草稿生成前必须已有人工确认的参标建议 | 已完成 | 未生成/未确认参标建议时阻塞 ContextPack 确认；Conditional Go 警告；No-Go 仅允许内部草稿 |
| ContextPack 生成 | 基于现有数据组装版本化上下文包 | 首版完成 | 已落 `draft_context_packs`，不调用 RAG，不自动找证据 |
| ContextPack 预览 | 展示将进入模型的矩阵项、证据、风险、缺项和章节范围 | 已完成 | 已提供预览 API 和前端入口 |
| 章节范围选择 | 支持投标函、资格响应、商务偏离、承诺函、企业资质、人员、业绩等章节 | 首版完成 | TemplateProfile 驱动默认章节，也支持 API 传入 `section_types` |
| 分章节 prompt | 每个章节有独立 prompt、输入变量和输出 schema | 首版完成 | 已注册 `business_draft_section@1.2.0`，输出 schema 约束 DraftBlock；LLM 分章节改写接入待增强 |
| 结构化草稿生成 | 输出章节、段落、表格 block，而不是直接生成 Word | 首版完成 | 已落 `draft_section_context_packs` 和 `draft_blocks`，block 记录条目、证据和缺项 |
| 生成后校验 | 校验强制项覆盖、证据引用、项目名称、日期、人员、证书编号等事实 | 首版完成 | 已接 CoverageReview 和旧事实校验；人员/业绩等细分规则待增强 |
| 审计和快照 | 保存 ContextPack、模型调用、生成稿和校验结果 | 首版完成 | 已保存 ContextPack、章节、block、coverage review 和审计日志 |

### P1：生成稿审阅和导出闭环

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 左右对照审阅 | 左侧生成稿，右侧合规条目队列 | 首版完成 | 商务标章节页展示 ContextPack 摘要、结构化 block 审阅、coverage 和可跳转的条款/原文追溯 |
| 双向定位 | 点击条目定位正文 block，点击正文展示覆盖条目和证据 | 首版完成 | 矩阵条款可跳回覆盖它的草稿 block；block 可跳转矩阵、原文抽屉和矩阵审阅台 |
| 审阅状态 | 区分已覆盖、未覆盖、证据不足、待确认、无需写入正文 | 首版完成 | DraftBlock 已区分 covered、needs_evidence、needs_fact、approved、rejected，并支持更新审阅状态 |
| 人工修改 | 用户修改生成稿时记录差异和原因 | 首版完成 | 章节编辑和 block 内容编辑均记录原因与审计；block 内容修改会同步章节正文并重新事实校验 |
| Word 导出 | 基于审阅通过的结构化稿导出 Word | 首版完成 | 有 MVP1.2 DraftBlock 时，未全部人工通过会进入提交前核验 block；填写风险接受后仅可导出内部草稿 |
| 回归样本 | 固定一个商务/资格草稿生成回归样本 | 首版完成 | 已新增 MVP1.2 ContextPack API 回归测试，并保留旧商务工作流回归 |

### P2：体验增强

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 章节模板库 | 为常见商务/资格章节沉淀模板骨架 | 首版完成 | 已新增工程类商务/资格 `TemplateProfile` 运行时配置 |
| 草稿差异对比 | 支持同一章节不同版本对比 | 首版完成 | 章节页基于审计日志展示最近一次章节/block 修改前后摘要、字数变化和修改原因 |
| 生成质量评分 | 输出覆盖率、证据引用率、待确认数和事实风险数 | 首版完成 | CoverageReview 已输出 `coverage_rate`、`evidence_reference_rate`、缺证/待补计数和 `quality_score` |

## 8. 异常处理和收敛规则

| 场景 | 系统处理 | 是否允许生成 |
| --- | --- | --- |
| 项目关键字段缺失 | 标记 block，提示补齐字段 | 仅允许生成带占位的内部草稿 |
| 文档版本过期 | 提示重新生成矩阵或填写风险接受说明 | 默认不允许 |
| 高风险项未确认 | 引导回矩阵审阅或风险处理 | 不允许 |
| 强制项无证据 | 标记证据不足，进入待补队列 | 不允许生成正式候选段落 |
| 未运行资格预评估 | ContextPack 预览可用，但确认 ContextPack 和草稿生成入口指向资格预评估 | 不允许确认 ContextPack |
| 参标建议未确认 | 阻塞 ContextPack 确认和草稿生成，要求人工确认 Go/No-Go | 不允许 |
| 参标建议为 Conditional Go | ContextPack 标记 warn，草稿保留缺材料/待复核事项 | 允许生成，提交前必须复核 |
| 参标建议为 No-Go | ContextPack 标记 block，生成前必须填写风险接受说明 | 仅允许内部草稿 |
| 证据已过期 | 标记高风险，要求替换或人工说明 | 仅允许内部草稿 |
| 上下文包超长 | 按章节拆分生成，保留总览摘要 | 允许 |
| 模型调用失败 | 记录失败原因，支持重试 | 不保存为有效草稿 |
| 模型输出 schema 失败 | 进入结构化修复或重试 | 不保存为有效草稿 |
| 生成事实与证据冲突 | 标记事实冲突，进入人工确认 | 不允许审阅通过 |

## 9. 数据与接口建议

已新增或建议扩展以下对象：

1. `draft_context_packs`：已新增，用于上下文包快照、schema 版本、来源摘要、状态。
2. `draft_section_context_packs`：已新增，用于章节级上下文裁剪。
3. `draft_blocks`：已新增，用于段落、表格、清单等结构化 block。
4. `draft_coverage_reviews`：已新增，用于覆盖检查和生成后收敛。
5. `draft_generation_tasks`：暂未新增，当前生成仍是同步接口；后续大文档可异步化。
6. `draft_block_links`：暂未单独建表，首版合并在 `draft_blocks.links_json`。
7. `draft_review_actions`：暂未新增，后续做 block 级审阅动作时补。

首版实际 API：

1. `POST /projects/{project_id}/sections/{section_id}/business-draft/context-pack/preview`
2. `GET /projects/{project_id}/sections/{section_id}/business-draft/context-pack`
3. `POST /projects/{project_id}/sections/{section_id}/business-draft/context-pack`
4. `POST /projects/{project_id}/sections/{section_id}/business-draft/context-pack/{context_pack_id}/generate`
5. `POST /projects/{project_id}/sections/{section_id}/business-draft/context-pack/{context_pack_id}/coverage-review`
6. `GET /projects/{project_id}/sections/{section_id}/business-draft/blocks`
7. 旧章节编辑、事实校验和 Word 导出接口继续保留。

## 10. 验收标准

MVP1.2 可按以下标准验收：

1. 用户能在生成前看到完整 ContextPack 预览。
2. ContextPack 能明确显示数据来源、文档版本、矩阵条目、证据、风险和缺项。
3. 没有已绑定证据的事实不会被模型编造成确定性陈述。
4. 每个生成 block 都能回链到合规条目和证据。
5. 强制项、高风险项和资格项未处理时不会静默进入生成稿。
6. 生成后校验能发现项目名、日期、证书编号、人员、业绩等关键事实异常。
7. 审阅视图能支持正文和合规条目的双向定位。
8. 审阅动作、人工修改、风险接受和 Word 导出都写入审计。
9. Word 导出只基于审阅通过的结构化稿。
10. 固定样本回归能覆盖正常生成、缺证据、字段缺失、版本过期和模型失败。

## 11. 开发进度

当前为 MVP1.2 主链路、审阅闭环和体验增强首版完成状态。

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| 版本边界 | 已确认 | 1.2 只做 ContextPack 和商务/资格草稿链路，不接 RAG/Embedding |
| 需求规划 | 已完成 | 本文档为规划与进度统一文档 |
| 数据模型设计 | 已完成首版 | 新增 ContextPack、SectionContextPack、DraftBlock、CoverageReview |
| 后端接口 | 已完成首版 | 已支持预览、落库、生成、coverage review、block 查询和 block 审阅导出门禁；ContextPack readiness 已纳入资格门禁 |
| 前端页面 | 已完成首版 | 商务标章节页新增 ContextPack 摘要条、block 审阅、双向定位、差异摘要和操作入口；未确认参标建议时禁用确认/生成入口；未审阅 block 导出会提示内部草稿风险接受 |
| PromptOps | 首版完成 | TemplateProfile、结构化 schema 和 `business_draft_section@1.2.0` 已落；LLM 分章节改写待增强 |
| 自动化测试 | 已完成首版 | `test_mvp12_context_pack_api.py` 覆盖资格门禁、block 审阅门禁和 ContextPack 生成链路；明珠公寓资料包测试覆盖无资格结论阻塞 ContextPack 确认 |
| 真实样本验收 | 已完成首版 | 明珠公寓样本已生成模拟企业资料并验证矩阵确认、证据绑定、资格前置和 ContextPack 准备度 |

本次验证结果：

1. `backend/.venv/bin/pytest backend/tests/test_mingzhu_mock_enterprise_data.py backend/tests/test_enterprise_api.py backend/tests/test_mvp12_context_pack_api.py backend/tests/test_mvp1_business_workflow_api.py backend/tests/test_prompt_registry.py -q`：15 passed。
2. `npm run build`：通过。
3. Codex Python `py_compile`：新增后端模型、服务、schema、路由和测试文件通过。

## 12. 与 MVP1.3 的交接

MVP1.2 交付后，MVP1.3 可以在不重写生成链路的前提下增强上游证据来源：

1. MVP1.2 定义 `bound_evidence`、`missing_facts` 和 `candidate_evidence` 扩展位。
2. MVP1.3 的 RAG 只负责推荐候选证据，不直接生成草稿。
3. 候选证据必须人工确认后，才能进入 `bound_evidence` 并参与正式生成。
4. RAG 检索质量不应影响 ContextPack 主链路可用性。
