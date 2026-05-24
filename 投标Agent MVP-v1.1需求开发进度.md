# 投标 Agent MVP-v1.1 需求开发进度

> 更新时间：2026-05-24  
> 当前阶段：MVP1.1 P0 已完成开发与自动化验证  
> 版本定位：在 MVP1.0 可试用闭环之上，引入受控 AI 能力，增强合规矩阵的语义拆分、分类、来源核对与人工审阅效率。

## 1. 总体状态

MVP1.1 当前已进入 P0 功能完成状态。

本阶段完成的核心能力：

1. Chat/LLM 模型配置中心。
2. PromptOps registry 初版。
3. 合规矩阵 AI 抽取增强链路。
4. 模型输出结构化校验与规则兜底。
5. 合规矩阵原文审阅视图第一版。
6. 黄金样本和模型路径回归测试补强。

当前明确未进入 MVP1.1 P0 的能力：

1. 重复项状态级联。
2. 人工划选原文补漏。
3. 相似补票和文本 Diff 高亮。
4. pgvector RAG。
5. Embedding / Rerank 接入。
6. 技术标核心章节生成。
7. 多 Agent 编排。
8. 产品选型、图纸、报价、自动提交。

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

## 3. 本轮代码落点

后端新增/调整：

1. `backend/app/prompts/registry.py`：PromptOps registry。
2. `backend/app/prompts/__init__.py`：prompt 模块导出。
3. `backend/app/services/compliance_generation.py`：合规矩阵 AI 抽取、结构化校验、降级保护。
4. `backend/app/schemas/project.py`：扩展 `ComplianceItemRead` 只读字段。
5. `backend/app/api/v1/routes/projects.py`：从 `explanation_json` 暴露审阅字段。
6. `backend/tests/test_prompt_registry.py`：prompt registry 单元测试。
7. `backend/tests/test_compliance_generation_worker.py`：fake LLM 抽取、污染过滤、缺来源降级测试。

前端新增/调整：

1. `frontend/src/api/bid.ts`：扩展 `ComplianceItem` 类型。
2. `frontend/src/pages/App.tsx`：新增“矩阵审阅”视图、工作流入口、审阅筛选和定位交互。
3. `frontend/src/pages/app.css`：新增矩阵审阅视图样式。

## 4. 当前验证结果

后端全量测试：

```bash
cd backend && .venv/bin/pytest -q
```

结果：

```text
43 passed, 5 warnings in 12.24s
```

前端构建：

```bash
cd frontend && npm run build
```

结果：构建通过。

备注：Vite 有 chunk 体积提示，属于当前单页应用体积提示，不影响本轮功能可用性。

## 5. P1 待开发清单

P1 的重点不是继续扩大模型能力，而是把“人工审阅纠错闭环”补起来。

建议优先级：

1. 重复项关联与状态级联。
2. 人工划选原文新增合规项。
3. 相同/相似文本补票提示。
4. 相似片段差异高亮。
5. 审阅视图 hover 展开完整条目和来源解释。
6. 高风险确认增加“已核对原文”确认要求。
7. 审阅页疑似未覆盖 chunk 提示。

## 6. P2 / MVP1.2 顺延清单

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

## 7. MVP1.1 P0 验收口径

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

## 8. 当前结论

MVP1.1 P0 已经完成“模型安全接入 + 合规矩阵 AI 增强 + 原文审阅第一版 + 回归验证”的目标。

下一步建议进入 MVP1.1 P1，优先补“重复项关联、人工划选补漏、相似补票、差异高亮”这一组人工审阅增强能力。它们会直接提升合规矩阵的可信度和业务人员的纠错效率，比继续扩展生成类能力更适合当前阶段。
