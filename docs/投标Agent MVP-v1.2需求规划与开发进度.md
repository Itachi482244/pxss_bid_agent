# 投标 Agent MVP-v1.2 需求规划与开发进度

> 更新时间：2026-06-06
> 当前阶段：MVP1.2 已完成，ContextPack 生成/确认链路通过自动化和真实项目闭环验收
> 版本定位：ContextPack First。只把商务/资格草稿生成前的上下文包做稳定、可预览、可审计、可确认。
> 后续交接：基于 ContextPack 的章节草稿生成、覆盖检查、事实校验、审阅和 Word 导出进入 MVP1.3；RAG/Embedding/Rerank 进入 MVP1.4。

## 1. 版本目标

MVP1.2 不追求“直接生成标书正文”，而是先把 ContextPack 做成可靠的生成前输入层。它要回答清楚：

1. 后续模型生成前，允许使用哪些项目字段、矩阵项、证据、资格结论、风险和人工确认记录。
2. 缺证据、缺字段、参标建议未确认、No-Go、矩阵未收敛时，系统该阻塞、警告还是允许继续。
3. 生成上下文是否可预览、可确认、可复盘，是否能被 MVP1.3 的目录/章节草稿能力稳定消费。

MVP1.2 的交付物是一份已确认的 `DraftContextPack`，以及按章节拆分的 `DraftSectionContextPack`。草稿正文不是本版本验收范围。

## 2. 核心原则

1. ContextPack 不依赖 RAG。只使用当前系统已有的项目字段、招标文件版本、合规矩阵、已绑定企业资料、无需绑定说明、资格预评估和人工确认。
2. 硬字段确定性写入。项目名称、招标人、截止时间、公司名称、证书编号、人员、金额和日期不交给模型自由发挥。
3. 缺失内容显式进入 `missing_facts` 或 readiness check，不允许在上下文中伪装成已确认事实。
4. ContextPack 可以预览，但确认必须满足资格门禁：至少完成资格预评估并人工确认参标建议。
5. No-Go 或仍有阻断项时，ContextPack 可以作为风险记录存在，但不得被误认为正式可生成输入。
6. 章节拆分只生成章节上下文和约束，不生成 `DraftBlock`。

## 3. 不纳入 MVP1.2

以下能力不进入 MVP1.2：

1. 基于 ContextPack 的章节正文草稿生成。
2. 结构化 `DraftBlock` 生成、block 审阅、覆盖检查和生成后事实校验。
3. Word 导出与正式标书版本交付。
4. 企业资料真实 pgvector RAG。
5. Embedding / Rerank 调用链。
6. 自动证据推荐和语义匹配。
7. 技术标核心章节生成。
8. 净化产品选型、图纸/OCR、多 Agent、报价辅助、自动报名、自动签章和自动提交。

其中第 1 到第 3 项进入 MVP1.3；第 4 到第 6 项进入 MVP1.4；其余能力进入长期规划。

## 4. 前置依赖

MVP1.2 依赖 MVP1.1 已完成能力：

1. 项目、标段、文件、文档版本和解析 chunk。
2. 合规矩阵生成、矩阵审阅、人工补漏、相似补票和重复项收敛。
3. 高风险、强制项、资格项的人工确认和原文核对。
4. 企业资料库、人工证据绑定和无需绑定说明。
5. 资格预评估、Go/Conditional Go/No-Go 参标建议和人工确认。
6. 审计日志、提交前核验和模型配置基础设施。

## 5. 主流程

MVP1.2 主流程如下：

1. 用户在项目工作台进入 ContextPack 区域。
2. 系统读取项目字段、标段、当前招标文件版本、合规矩阵、证据绑定和资格预评估状态。
3. 用户点击“预览”，系统生成 ContextPack Preview，展示来源、矩阵摘要、绑定证据、缺项、风险和章节计划。
4. 如果尚未生成资格预评估，系统允许预览，但提示先进入资格预评估。
5. 如果参标建议未人工确认，系统阻止确认 ContextPack，并给出“去资格预评估确认”的处理入口。
6. 如果存在缺证据、待确认矩阵项、No-Go 或关键字段缺失，readiness 输出 `warn` 或 `block`，并逐条给出处理动作。
7. 用户确认 ContextPack 后，系统落库 `draft_context_packs` 和 `draft_section_context_packs`，旧 ContextPack 标记为 `superseded`。
8. 后续 MVP1.3 只消费已确认且未失效的 ContextPack，不绕过本版本的门禁。

## 6. ContextPack Schema

ContextPack 采用版本化 JSON 结构，至少包含：

```json
{
  "schema_version": "1.0",
  "project_facts": {},
  "bid_section": {},
  "source_document": {},
  "generation_scope": {},
  "qualification_decision": {},
  "matrix_summary": {},
  "matrix_items": [],
  "bound_evidence": [],
  "missing_facts": [],
  "manual_notes": [],
  "risk_acceptances": [],
  "output_constraints": {},
  "audit": {}
}
```

关键约束：

1. `matrix_items` 只放当前版本下有效且可追溯的条目。
2. `bound_evidence` 只放人工已绑定、权限允许、未解除的企业资料证据。
3. `missing_facts` 必须说明字段、原因、建议处理方式和所属章节。
4. `qualification_decision` 必须记录建议、状态、确认人、确认时间和理由。
5. `outline_plan_json.sections` 只描述章节计划和章节上下文范围，不代表已生成正文。

## 7. 需求范围

### P0：ContextPack 主链路

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 上下文准备度检查 | 输出 pass/warn/block、阻断原因和处理建议 | 已完成 | 已覆盖资格门禁、缺证据、矩阵未确认、项目字段缺失和 No-Go |
| 资格门禁 | 确认 ContextPack 前必须有人工确认的参标建议 | 已完成 | 未生成/未确认参标建议时阻塞确认；Conditional Go 警告；No-Go 标记 block |
| ContextPack 预览 | 展示将被后续生成使用的项目、矩阵、证据、缺项、风险和章节计划 | 已完成 | `context-pack/preview` 接口和前端入口已存在 |
| ContextPack 确认 | 落库已确认上下文包，并废弃旧包 | 已完成 | `draft_context_packs.status=confirmed`，旧包 `superseded` |
| SectionContextPack | 按章节拆分上下文范围、约束和缺项 | 已完成 | `draft_section_context_packs` 作为 MVP1.3 输入 |
| TemplateProfile | 用工程类商务/资格章节模板约束章节计划 | 已完成 | 只约束结构和字段，不负责生成正文 |
| 审计快照 | 保存确认人、确认时间、来源摘要和 readiness 结果 | 已完成 | 君山燃气和明珠公寓真实样本已回归 |

### P1：体验与收敛

| 模块 | 需求 | 状态 | 说明 |
| --- | --- | --- | --- |
| 阻断项处理入口 | 每个 readiness check 都能跳转到对应处理页面 | 已完成 | 缺证据、资格、矩阵、项目字段和企业资料均有可执行入口 |
| 缺项集中展示 | 将缺字段、缺证据、待确认风险集中展示 | 已完成 | 完整预览统一展示准备度、待补事实和处理动作 |
| 证据去重 | 等价资料不重复绑定或重复展示 | 已完成 | 单项去重、全局聚合，并保留全部条款关联 |
| 任务轮询收敛 | 陈旧任务不能导致页面永久自动刷新 | 已完成 | 超过 1 小时未更新即停止轮询并清除恢复状态 |
| 真实项目闭环 | 用君山燃气和明珠公寓验证正常/复杂场景 | 已完成 | 君山 32 条、明珠 473 条矩阵均完成 ContextPack 闭环 |
| 单元测试 | 固定 ContextPack API、异常路径、明珠资料包回归 | 已完成 | 后端完整测试 140 项通过 |

## 8. 异常处理和收敛规则

| 场景 | 系统处理 | 1.2 是否允许确认 ContextPack |
| --- | --- | --- |
| 未运行资格预评估 | 允许预览，readiness block，提示先运行资格预评估 | 不允许 |
| 参标建议未人工确认 | readiness block，提示先确认 Go/No-Go | 不允许 |
| 参标建议为 Conditional Go | readiness warn，保留缺材料/待确认事项 | 允许 |
| 参标建议为 No-Go | readiness block，标记风险，不作为正式生成输入 | 允许作为风险快照，但后续生成需 1.3 明确内部草稿风险接受 |
| 高风险/强制/资格项未确认 | readiness block，跳回矩阵审阅 | 不允许 |
| 资格项缺企业资料证据 | readiness block，跳回证据绑定或资格预评估 | 不允许 |
| 项目关键字段缺失 | readiness warn/block，进入 `missing_facts` | 视字段风险而定 |
| 已人工绑定证据但规则无法自动判满 | 进入资格预评估待确认，不再作为缺证据阻断 | 允许用户人工确认后继续 |
| 重复企业资料或重复绑定 | 合并展示，阻止等价重复绑定 | 不影响已确认的唯一证据 |
| 文档版本缺失或过期 | 标记 warn/block，提示重新解析或重建矩阵 | 视影响范围而定 |
| ContextPack 已存在 | 新确认版本生效，旧版本 `superseded` | 允许 |

## 9. 数据与接口

MVP1.2 实际使用对象：

1. `draft_context_packs`：ContextPack 快照、schema 版本、readiness、状态和确认信息。
2. `draft_section_context_packs`：章节级上下文裁剪结果。
3. `compliance_evidence_bindings`：已绑定企业资料证据。
4. `qualification_decisions`：参标建议和人工确认记录。
5. `audit_logs`：预览、确认、阻断处理和证据绑定动作留痕。

MVP1.2 验收接口：

1. `POST /projects/{project_id}/sections/{section_id}/business-draft/context-pack/preview`
2. `GET /projects/{project_id}/sections/{section_id}/business-draft/context-pack`
3. `POST /projects/{project_id}/sections/{section_id}/business-draft/context-pack`
4. 资格预评估相关接口：run/generate/confirm decision。
5. 企业资料搜索、绑定、解除和矩阵摘要接口。

以下接口属于 MVP1.3 能力，当前保留兼容但不作为 1.2 验收入口：

1. `POST .../context-pack/{context_pack_id}/generate`
2. `POST .../context-pack/{context_pack_id}/generate-async`
3. `POST .../context-pack/{context_pack_id}/coverage-review`
4. `GET .../business-draft/blocks`
5. 结构化 block 审阅、事实校验和 Word 导出接口。

## 10. 验收标准

MVP1.2 按以下标准验收：

1. 用户可以在生成前看到完整 ContextPack 预览。
2. ContextPack 明确展示来源文件版本、矩阵摘要、已绑定证据、缺项、资格结论和风险。
3. 未运行资格预评估或参标建议未确认时，不能确认 ContextPack。
4. 缺证据、矩阵未确认、No-Go 等阻断项均有明确处理动作。
5. 已人工绑定的企业资料不会重复展示为多个等价证据，也不会仍被当成缺证据阻断。
6. ContextPack 确认后生成章节级 SectionContextPack，并废弃旧版本。
7. ContextPack 中的缺事实只以 `missing_facts` 形式出现，不被包装成确定性事实。
8. 君山燃气项目可以完成资格处理、证据绑定、资格预评估、ContextPack 预览和确认闭环。
9. 明珠公寓项目在全矩阵确认且资料绑定后，流程状态和 ContextPack readiness 符合预期。
10. 单元测试和浏览器真实测试覆盖正常、缺证据、重复资料、人工绑定后重新评估和复杂样本。

## 11. 开发进度

| 范围 | 状态 | 说明 |
| --- | --- | --- |
| 版本边界 | 已调整 | 1.2 只做 ContextPack 预览/确认；草稿生成进入 1.3；RAG 进入 1.4 |
| 文档规划 | 已完成 | 本文档为规划与进度统一文档 |
| 数据模型 | 已完成 | `draft_context_packs`、`draft_section_context_packs` 已落库 |
| 后端 ContextPack API | 已完成 | 预览、列表、确认、硬门禁、章节拆分和版本替换均已验证 |
| 资格/证据联动 | 已完成 | 绑定、解除和无需绑定均自动重跑资格预评估并失效旧决策 |
| 前端 ContextPack 区域 | 已完成 | 完整预览、动作跳转、预览后确认门禁和 1.3 能力提示已完成 |
| 自动化测试 | 已完成 | 后端 140 项、Ruff 和前端生产构建全部通过 |
| 浏览器真实测试 | 已完成 | 君山燃气与明珠公寓均完成预览和确认，控制台无错误 |

## 12. 与 MVP1.3 的交接

MVP1.3 从已确认 ContextPack 开始，不重新处理上游矩阵和证据绑定：

1. MVP1.2 负责 `context_json`、`outline_plan_json` 和 `section_context_packs`。
2. MVP1.3 负责基于这些输入生成目录、章节草稿、结构化 block、覆盖检查、事实校验、审阅和导出。
3. MVP1.3 不应绕过 1.2 的资格门禁和 readiness 结论。
4. MVP1.4 的 RAG 只能增强候选证据，不直接替代 1.2 的人工绑定和 ContextPack 确认。
