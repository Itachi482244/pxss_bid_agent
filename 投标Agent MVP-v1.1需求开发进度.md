# 投标 Agent MVP-v1.1 需求开发进度

> 更新时间：2026-05-25
> 当前阶段：MVP1.1 P0 + P1 已完成开发，项目级回归通过
> 版本定位：在 MVP1.0 可试用闭环之上，引入受控 AI 能力，增强合规矩阵的语义拆分、分类、来源核对与人工审阅效率。

## 1. 总体状态

MVP1.1 当前已完成 P0 与 P1 主体开发，并已通过 `make mvp1-check` 回归。最近代码提交：`636c7bd test: cover mvp1.1 matrix review p1 flows`。

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
10. 黄金样本、模型路径和 P1 审阅纠错回归测试补强。

当前明确不进入 MVP1.1 的能力：

1. pgvector RAG。
2. Embedding / Rerank 接入。
3. 技术标核心章节生成。
4. 多 Agent 编排。
5. 产品选型、图纸、报价、OCR、自动提交。

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
9. `backend/tests/test_model_config_api.py`：模型配置、加密、连接测试和 DB 优先级回归。
10. `backend/tests/test_prompt_registry.py`：prompt registry 单元测试。
11. `backend/tests/test_compliance_generation_worker.py`：fake LLM 抽取、污染过滤、缺来源降级测试。
12. `backend/tests/test_project_api.py`：P1 人工补漏、相似补票、Diff、关联组和级联确认回归测试。
13. `backend/migrations/versions/f6a1c8d9e2b3_add_ai_model_configs.py`：模型配置表迁移。
14. `backend/migrations/versions/a9d4e7f2c8b1_add_compliance_review_p1_fields.py`：P1 稳定字段迁移。

前端新增/调整：

1. `frontend/src/api/bid.ts`：扩展 `ComplianceItem` 类型。
2. `frontend/src/pages/App.tsx`：新增“矩阵审阅”视图、工作流入口、审阅筛选、定位、人工补漏、相似补票和关联组操作。
3. `frontend/src/pages/app.css`：新增矩阵审阅视图和 Diff 高亮样式。
4. `frontend/vite.config.ts`：拆分 `index`、`react-vendor`、`antd-vendor`、`utils-vendor`，处理 Vite chunk 体积提示。

## 5. 当前验证结果

后端全量测试：

```bash
cd backend && .venv/bin/pytest -q
```

结果：

```text
43 passed, 5 warnings in 14.41s
```

前端构建：

```bash
cd frontend && npm run build
```

结果：构建通过；入口应用 chunk 已拆分为 `index`、`react-vendor`、`antd-vendor`、`utils-vendor`，不再触发 Vite chunk 体积提示。

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

## 7. P2 / MVP1.2 顺延清单

以下内容不建议塞回 MVP1.1 P0：

1. pgvector RAG。
2. 企业资料向量化检索。
3. `BAAI/bge-large-zh-v1.5` embedding 接入。
4. `BAAI/bge-reranker-large` rerank 接入。
5. 技术标核心章节生成。
6. 净化设备产品选型。
7. 图纸/示意图辅助。
8. 多 Agent 编排和 Agent 输入输出 schema 平台化。
9. OCR 和复杂补遗版本链。

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

MVP1.1 P1 已完成“重复项关联、人工划选补漏、相似补票、差异高亮、级联确认和高风险确认防误触”的主体能力，并已补齐后端回归测试。

下一步建议不继续扩功能，先做前端浏览器冒烟和交互打磨，确认矩阵审阅页的划选、新增、补票、关联组操作在真实页面中足够顺手。
