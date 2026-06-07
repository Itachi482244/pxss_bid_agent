# 投标 Agent RAG 前置地基梳理

> 更新时间：2026-06-07
> 目的：在进入 MVP1.5（企业资料 RAG / Embedding / Rerank）之前，盘点并夯实基础，避免被 1.5 直接放大的结构性问题。
> 方式：问答式逐条确认，每条结论实时回写本文件。

## 0. 现状基线（事实）

- 后端测试：**162 项全绿**（`pytest`，约 14s）。
- RAG 脚手架已存在：
  - `models/retrieval.py`：`EnterpriseMaterialChunk`（`pgvector` 向量列 `Vector(16)` + `embedding_json` + `data_level` 权限分级）。
  - 迁移 `c52e8f1a6d44`：建表 + `CREATE EXTENSION IF NOT EXISTS vector`（pgvector 不可用时有 graceful fallback）。
  - `services/material_retrieval.py`：分块、关键词检索、余弦、混合打分、按 `data_level` 权限过滤、推荐理由、资料状态提示。
  - `ai_model_configs` 已预留能力位 `capability IN ('chat','embedding','rerank')`。
- 已知短板：
  - embedding 为 `pseudo_embedding`（16 维 sha256 mock）；检索为 Python 端 O(n) 暴力；`embedding_vector` 向量列实际未用于检索；维度 `EMBEDDING_DIMENSIONS=16` 写死；无 ANN 索引（ivfflat/hnsw）。
  - `llm_gateway.py` 仅有 `chat_completion`，无 embedding/rerank 运行时网关。
  - 前端：`App.tsx` 约 10761 行单文件；无前端自动化测试；无 lint 脚本。

## 1. 候选地基项（待逐条确认）

| 编号 | 事项 | 初判优先级 | 结论 |
| --- | --- | --- | --- |
| ① | 检索网关抽象（embedding / rerank，复用 chat 的超时/审计/降级基础设施） | 高（RAG 前） | **不前置，并入 1.5** |
| ② | 向量检索真实化接缝（可切换 mock/pg-ANN、维度配置化、启用 ANN 索引） | 高（RAG 前） | **不前置，并入 1.5** |
| ③ | 前端护栏（候选抽屉独立组件 + 最小 vitest 单测兜底） | 中（RAG 前） | **采纳（本轮做）** |
| — | chunk 切分质量 / 混合权重 / rerank 理由 / 候选 UI / 评测集 | 属 1.5 本身 | 不前置 |
| — | `compliance_generation.py`(5051) / `projects.py`(4775) 拆分 | 可延后 | 不前置 |

## 2. 逐条结论

### ① 检索网关抽象 —— 决定：不前置，并入 MVP1.5

- 决策：现在**不**单独搭 embedding/rerank 运行时网关骨架。
- 理由：网关抽象与真实 embedding/rerank provider 强耦合，提前只搭 mock-only 骨架价值有限；等 1.5 接真实模型时，连同超时 / `model_invocation` 审计 / 失败降级一并设计更自然，避免返工。
- 影响：1.5 的"网关 + 降级"工作量保留在 1.5 内；本轮地基不动 `llm_gateway`。

### ② 向量检索真实化接缝 —— 决定：不前置，并入 MVP1.5

- 决策：现在**不**单独改造维度配置化 / pgvector DB 端检索 / ANN 索引。
- 理由：向量维度会随真实中文 embedding 模型（768/1024 维）变化，现在用 16 维 mock 提前接 pgvector + ANN 索引，到 1.5 仍需重建索引与迁移；与其分两次改，不如 1.5 接真实模型时一次到位。
- 影响：1.5 需明确包含：维度配置化、`search_material_hits` 走 pgvector DB 端向量距离、ANN 索引（ivfflat/hnsw）迁移、`embedding_vector` 列真正参与检索。本轮保持现有 mock 检索路径不动。

### ③ 前端护栏 —— 决定：本轮采纳（轻量护栏）

- 决策：做"轻量护栏 A"，不强拆现有巨石。
- 范围：
  1. 引入最小 `vitest`（仅纯函数，无需 DOM）+ `test` 脚本。
  2. 把以下已写好的关键纯逻辑从 `App.tsx` 的 `useMemo` 中抽成可导出纯函数并补单测兜底：看板聚合 `dashboardStats`、草稿块过滤计数 `draftBlockFilterCounts`、首页分组过滤 `filteredHomeProjects`。
  3. 约定：MVP1.5 的"候选证据抽屉"做成独立组件（照 `ContextPackPreviewDrawer`），不再堆进 `App.tsx`。
- 理由：前端零测试、回归靠手动浏览器走查，纯逻辑最易回归也最该自动化；抽离纯函数顺带让 `App.tsx` 略瘦身、为 1.5 留出干净接缝。

## 3. 本轮 RAG 前置地基行动清单

1. **（③）** 引入 vitest，抽离并单测 `dashboardStats` / `draftBlockFilterCounts` / `filteredHomeProjects`。
2. **（③）** 在 MVP1.5 文档中固化"候选抽屉独立组件"约定。
3. **（①②）** 不前置，作为 MVP1.5 范围内的明确条目（网关+降级、向量真实化+ANN 索引）。
