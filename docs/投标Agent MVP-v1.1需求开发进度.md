# 投标 Agent MVP-v1.1 需求开发进度

> 更新时间：2026-06-02
> 当前阶段：MVP1.1 P0 + P1 + P1 追加 fork/join 性能需求已完成开发，明珠公寓真实 PDF 全链路验收通过
> 版本定位：在 MVP1.0 可试用闭环之上，引入受控 AI 能力，增强合规矩阵的语义拆分、分类、来源核对与人工审阅效率。

## 1. 总体状态

MVP1.1 当前已完成 P0、既有 P1 与 P1 追加的矩阵 fork/join 性能需求。最近实现提交：`4ccbd41 feat: add matrix fork join task center`。

本轮已使用 `deepseek-v4-pro` 对“明珠公寓老旧小区综合改造提升项目”招标 PDF 跑完整合规矩阵生成，最终任务 `6ee54ccf-28e9-4fa9-971e-09f994fd4a81` 成功，质量报告 `4472a33f-b34d-4423-b6db-9b97e0d407c1` 为 `passed`，`issues_json` 为空。

本阶段完成的核心能力：

1. Chat/LLM 模型配置中心。
2. PromptOps registry 初版。
3. 合规矩阵 AI 抽取增强链路。
4. 模型输出结构化校验与规则兜底。
5. 合规矩阵原文审阅视图。
6. 重复项关联与状态级联。
7. 人工划选原文补漏。
8. 相同/相似片段补票和文本 Diff 高亮。
9. 高风险/强制/资格项确认前原文核对闸口。
10. 合规矩阵生成按语义章节有界并发抽取，fork/join 汇总候选项、质量问题和章节摘要。
11. 后台任务中心和解析/矩阵生成进度展示，让用户能看到当前阶段、并发数、完成章节数、剩余章节和下一步动作。
12. 章节规划、章节抽取、覆盖复核的超时/JSON/schema 失败容错与质量报告落库。
13. 黄金样本、模型路径、P1 审阅纠错和 fork/join 回归测试补强。

当前明确不进入 MVP1.1 的能力：

1. pgvector RAG。
2. Embedding / Rerank 接入。
3. 技术标核心章节生成。
4. 多 Agent 编排。
5. 产品选型、图纸、报价辅助和 OCR。
6. 自动提交不进入自动执行范围，仅作为长期外部集成议题。

## 2. P0 开发进度

| 模块 | 目标 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| 模型配置中心 | 设置页配置 `base_url`、`api_key`、`simple_model`、`complex_model`、启用状态和超时 | 已完成 | 配置写入 DB，API Key AES-256-GCM 加密存储，模型调用优先 DB 配置，环境变量兜底 |
| PromptOps registry | 模型任务 prompt 版本化、集中管理、可测试 | 已完成 | 已新增 `compliance_extract@1.1.0`、`requirement_risk_assess@1.1.0` |
| 合规矩阵 AI 抽取 | 规则预清洗后调用模型拆分/分类，再由规则复核 | 已完成 | 模型不可用、JSON/schema 失败、缺来源或无有效候选时降级规则兜底 |
| 输出结构化校验 | 模型输出必须有来源、类型、风险、置信度、理由和人工复核提示 | 已完成 | 新增 `classification_reason`、`split_reason`、`source_quote`、`review_hint`、`needs_human_review` |
| 污染项过滤 | 标题、联系方式、采购人/代理机构信息不得进入矩阵 | 已完成 | 模型路径和规则路径均保留过滤保护 |
| 低置信度/冲突保护 | 低置信度或模型/规则冲突项不能悄悄当作高可信结果 | 已完成 | 标记为需要人工复核，并在审阅视图展示提示 |
| 矩阵审阅视图 | 左侧原文 chunk，右侧矩阵项队列，支持定位和筛选 | 已完成第一版 | 第一版为 chunk 级定位，不做字符级 offset 或 PDF 坐标 |
| 审阅筛选与进度 | 支持未确认、高风险、强制项、缺证据过滤 | 已完成 | 顶部展示已确认进度和高风险确认进度 |
| 黄金样本回归 | 覆盖模型成功、失败降级、污染过滤、来源完整性 | 已完成基础测试 | 使用 fake LLM 覆盖模型路径，不依赖真实远程模型 |

## 3. P1 开发进度

| 模块 | 目标 | 当前状态 | 说明 |
| --- | --- | --- | --- |
| 审阅聚合接口 | 统一返回原文 chunks、矩阵项、统计、疑似未覆盖 chunk 和重复关联组 | 已完成 | 新增 `matrix-review` 只读接口，减少前端多接口拼装不一致 |
| 稳定关联字段 | 支持 `dedup_key`、`duplicate_group_id`、人工划选 offset 和来源创建方式 | 已完成 | 已新增 Alembic 迁移，核心状态不再依赖 `explanation_json` |
| 人工划选补漏 | 审核人从原文新增合规项并保留来源 | 已完成 | 新增 `compliance-items/from-source`，保存 selected text、offset、chunk 来源和审计 |
| 相似补票 | 新增条目后提示全文相同/相近片段并逐个确认 | 已完成 | 使用归一化、包含匹配和 `difflib`，不接 pgvector |
| 文本 Diff 高亮数据 | 帮助业务人员识别相似片段差异 | 已完成 | 后端返回 equal/insert/delete/replace segments，前端可渲染新增/缺失/替换 |
| 重复项关联 | 疑似重复只提示，人工确认后才启用联动 | 已完成 | 支持确认关联组、解除联动、拆分新组 |
| 级联确认 | 同组确认状态同步并返回影响数量 | 已完成 | 风险等级、强制属性、条目类型不自动级联 |
| 高风险确认防误触 | 高风险、强制项、资格项确认前必须核对原文 | 已完成 | 前后端均校验 `source_verified` |
| P1 回归测试 | 锁定人工补漏、相似补票、Diff、关联组和级联确认 | 已完成 | 已补充 `test_project_api.py` P1 专项测试 |
| 远程模型 fork/join | 矩阵生成按语义章节有界并发抽取并在父任务 join 汇总 | 已完成 | 默认最大并发 4，可配置开关、最大并发和最小章节数；子章节独立 DB session，父任务统一去重、质量门禁和入库 |
| 后台任务中心 | 长耗时解析/矩阵生成以任务页展示进度和下一步动作 | 已完成 | 前端调用矩阵生成时传 `async_processing: true`，即使开发环境 `RUN_TASKS_INLINE=true` 也会后台执行并立即返回任务 ID |
| 质量门禁处理页 | 质量报告阻断时从矩阵审阅中独立出来处理 | 已完成 | 展示阻断/提示项、定位章节、重抽段落、重新规划、重新生成矩阵等操作入口 |
| 大文件真实验收 | 用明珠公寓招标 PDF 跑完整矩阵并校验质量报告 | 已完成 | 最终报告 `passed` 且 `issues_json=[]`，关键条目抽查覆盖合同价格形式、质量保证金、工期履约保证金、报价金额、授权委托书、项目经理证书编号 |

## 4. 本轮代码落点

后端新增/调整：

1. `backend/app/models/ai_config.py`：模型配置表。
2. `backend/app/services/model_config.py`、`backend/app/services/model_config_crypto.py`：模型配置解析和 API Key 加解密。
3. `backend/app/api/v1/routes/system.py`：模型配置读写和连接测试接口。
4. `backend/app/prompts/registry.py`：PromptOps registry。
5. `backend/app/prompts/__init__.py`：prompt 模块导出。
6. `backend/app/services/compliance_generation.py`：合规矩阵 AI 抽取、结构化校验、降级保护。
7. `backend/app/schemas/project.py`：扩展矩阵审阅、人工补漏、相似补票、关联组和确认请求/返回结构。
8. `backend/app/api/v1/routes/projects.py`：矩阵审阅聚合、人工新增、相似候选、补票应用、关联组确认/解除/拆分和级联确认。
9. `backend/app/api/v1/routes/tasks.py`：新增任务列表查询，支持项目、标段、任务类型、active 状态和分页限制过滤。
10. `backend/app/core/config.py`：新增 `MATRIX_FORK_JOIN_ENABLED`、`MATRIX_FORK_JOIN_MAX_WORKERS`、`MATRIX_FORK_JOIN_MIN_SECTIONS`。
11. `backend/app/services/llm_gateway.py`：远程模型调用增加 wall timeout，避免 HTTP 客户端底层长期挂起。
12. `backend/tests/test_model_config_api.py`：模型配置、加密、连接测试和 DB 优先级回归。
13. `backend/tests/test_prompt_registry.py`：prompt registry 单元测试。
14. `backend/tests/test_compliance_generation_worker.py`：fake LLM 抽取、污染过滤、缺来源降级、fork/join 并发、章节规划复用和文本守卫补齐测试。
15. `backend/tests/test_project_api.py`：P1 人工补漏、相似补票、Diff、关联组和级联确认回归测试。
16. `backend/migrations/versions/f6a1c8d9e2b3_add_ai_model_configs.py`：模型配置表迁移。
17. `backend/migrations/versions/a9d4e7f2c8b1_add_compliance_review_p1_fields.py`：P1 稳定字段迁移。

前端新增/调整：

1. `frontend/src/api/bid.ts`：扩展 `ComplianceItem` 类型。
2. `frontend/src/pages/App.tsx`：新增“矩阵审阅”视图、工作流入口、审阅筛选、定位、人工补漏、相似补票、关联组操作、任务中心、质量门禁处理页和导入任务状态恢复。
3. `frontend/src/pages/app.css`：新增矩阵审阅视图、Diff 高亮、后台任务面板和任务中心样式。
4. `frontend/vite.config.ts`：拆分 `index`、`react-vendor`、`antd-vendor`、`utils-vendor`，处理 Vite chunk 体积提示。

## 5. 当前验证结果

后端合规生成专项测试：

```bash
cd backend && .venv/bin/pytest tests/test_compliance_generation_worker.py -q
```

结果：

```text
79 passed, 5 warnings in 4.26s
```

前端构建：

```bash
cd frontend && npm run build
```

结果：构建通过；入口应用 chunk 已拆分为 `index`、`react-vendor`、`antd-vendor`、`utils-vendor`。

明珠公寓真实 PDF 全链路验收：

```text
项目：明珠公寓老旧小区综合改造提升项目
文档版本：034a5b5a-f2cb-44e1-9565-f1f59f1cdeb7
模型：deepseek-v4-pro
任务：6ee54ccf-28e9-4fa9-971e-09f994fd4a81
执行模式：fork_join，最大并发 4，语义章节 27
结果：succeeded，candidate_count=472，created_count=307，updated_count=165
质量报告：4472a33f-b34d-4423-b6db-9b97e0d407c1，status=passed，issues_json=[]
```

关键条目抽查已覆盖：

1. 合同价格形式：固定单价合同 / 单价合同。
2. 质量保证金：剩余 1.5% 留作质量保证金，缴纳方式同投标担保。
3. 质量保证金：采用缴纳形式同投标担保，保证金额为 1.5% 的工程款。
4. 工期履约保证金：逾期未提交施工组织设计，每逾期一日扣罚 1000 元。
5. 响应函报价金额：人民币大写和 RMB 小写，大小写不一致以大写为准。
6. 授权委托书：代理人信息、代理时限、代理人身份证复印件。
7. 项目经理信息：建造师注册证书号、建造师执业印章号、安全生产考核合格证书号。

P1 专项测试：

```bash
cd backend && .venv/bin/pytest -q \
  tests/test_project_api.py::test_matrix_review_p1_manual_source_similar_candidates_and_apply \
  tests/test_project_api.py::test_matrix_review_p1_duplicate_group_unlink_split_and_cascade_confirmation
```

结果：

```text
2 passed, 5 warnings in 2.27s
```

## 6. P1 验收口径

P1 的重点不是继续扩大模型能力，而是把“人工审阅纠错闭环”补起来。

当前 P1 可按以下标准验收：

1. 审阅聚合接口能返回原文、矩阵项、统计和疑似未覆盖 chunk。
2. 审核人可从原文新增矩阵项，且保留 chunk、选中文本和 offset。
3. 新增条目后能提示相同/相近片段，并支持逐个补票。
4. 相似片段返回 Diff segments，前端可展示差异。
5. 同一要求多处出现时先进入疑似关联，人工确认后才启用级联。
6. 同组确认状态能级联同步，并提示影响条目数量。
7. 解除联动后的条目不会被后续级联覆盖。
8. 关联组可拆分为独立组。
9. 高风险、强制项、资格项确认前必须核对原文。
10. 关键动作均写入审计。
11. 大文件矩阵生成能作为异步任务展示阶段、进度、并发数、完成章节和剩余章节。
12. 质量门禁阻断时有独立处理页和明确操作入口，不再要求用户混在矩阵审阅里猜下一步。
13. 章节规划、章节抽取或覆盖复核出现模型空响应、JSON/schema 失败、超时或网关错误时，能进入重试、复用已有规划或质量报告路径，不再裸露为无上下文错误。

## 7. MVP1.2、MVP1.3、MVP1.4 与长期规划顺延清单

以下内容不建议塞回 MVP1.1。MVP1.2 只承接 ContextPack 预览、生成、确认和准备度门禁：

1. 商务/资格生成上下文包预览。
2. ContextPack readiness pass/warn/block 和处理动作。
3. 资格预评估与参标建议确认门禁。
4. 已绑定证据、缺事实和风险记录快照。
5. SectionContextPack 章节上下文确认。

MVP1.3 承接基于 ContextPack 的商务/资格草稿生成闭环：

1. 分章节提示词。
2. 结构化商务/资格生成稿。
3. DraftBlock 审阅。
4. 覆盖检查、事实校验和 Word 导出前风险快照。

MVP1.4 承接 ContextPack 的上游证据增强能力：

1. pgvector RAG。
2. 企业资料向量化检索。
3. `BAAI/bge-large-zh-v1.5` embedding 接入。
4. `BAAI/bge-reranker-large` rerank 接入。
5. 候选证据推荐、解释和人工绑定。

以下能力进入长期规划，不排入具体 MVP 版本：

1. 技术标核心章节生成。
2. 净化设备产品选型。
3. 图纸/示意图辅助。
4. OCR 和复杂补遗版本链。
5. 多 Agent 编排和 Agent 输入输出 schema 平台化。
6. 报价辅助。
7. 自动报名、自动签章和自动提交等外部系统集成。

## 8. MVP1.1 P0 验收口径

P0 可以按以下标准验收：

1. 模型配置可在设置页保存、测试和兜底。
2. 模型 prompt 有明确版本号和 registry。
3. 合规矩阵生成可走模型增强路径。
4. 模型不可用时，规则兜底仍可生成矩阵。
5. 模型输出缺来源、低置信度或与规则冲突时，不会静默污染高可信矩阵。
6. 矩阵项能展示分类理由、拆分理由、来源摘录和人工复核提示。
7. 审阅视图能左右对照原文 chunk 和矩阵项。
8. 审阅视图能按未确认、高风险、强制项、缺证据筛选。
9. 点击条目能定位来源 chunk，点击来源 chunk 能定位条目。
10. 自动化测试和前端构建通过。

## 9. 当前结论

MVP1.1 P0 已完成“模型安全接入 + 合规矩阵 AI 增强 + 原文审阅第一版 + 回归验证”的目标。

MVP1.1 P1 已完成“重复项关联、人工划选补漏、相似补票、差异高亮、级联确认、高风险确认防误触、fork/join 并发矩阵生成、任务中心和质量门禁处理页”的主体能力，并已补齐后端回归测试。

明珠公寓真实 PDF 已完成完整矩阵生成和质量门禁验收，最终质量报告通过且无剩余质量问题。下一步建议进入 MVP1.2：商务/资格 ContextPack 预览、生成、确认和准备度门禁；MVP1.3 承接基于 ContextPack 的结构化草稿生成和审阅导出；MVP1.4 再接企业资料 RAG、Embedding/Rerank 和候选证据推荐。技术标、净化产品选型、图纸/OCR、多 Agent 和报价辅助进入长期规划，不再继续往 MVP1.1 塞新功能。
