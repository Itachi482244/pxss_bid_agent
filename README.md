# 投标 Agent

面向中国招投标场景的专业投标 Agent 项目。当前仓库采用 Web B/S 工作台 + Python 后端 + Docker 中间件的开发模式，已从 MVP1.0 可试用闭环推进到 MVP1.5 P0：模型安全接入、ContextPack、商务/资格草稿、易用性优化、历史资料 OCR/抽取和企业资料检索地基正在逐步落地。

## 产品原则

生成标书前的所有步骤都服务于同一个最高目标：为最终模型生成正式产出提供尽可能完整、干净、可追溯、可校验的上下文。

因此，项目导入、文件解析、原文审阅、合规矩阵、证据绑定、资格预评估、事实校验和审批，不应被理解为孤立流程，而是逐层构建“最终生成上下文包”的工作台：

- 原文和版本让模型知道“依据哪份文件生成”。
- 矩阵和审阅让模型知道“必须响应什么、哪些已确认、哪些有风险”。
- 企业资料和证据绑定让模型知道“能引用什么事实、哪些事实不能编造”。
- 资格评估、事实校验和审批让模型知道“哪些内容可用、哪些内容必须人工兜底”。

模型只应在已确认的上下文包之上生成草稿或最终候选产出，不能绕开上下文直接自由发挥。

## 当前进度

- MVP1.0：通用投标闭环已完成，包括项目导入、文件解析、合规矩阵、企业资料、证据绑定、资格预评估、商务/资格草稿、事实校验、审批导出、审计留痕和提交前核验。
- MVP1.1 P0：已完成模型配置中心、PromptOps registry、合规矩阵 AI 抽取增强、结构化校验、规则降级和矩阵审阅第一版。
- MVP1.1 P1：已完成审阅聚合接口、人工划选补漏、相似补票、Diff 高亮数据、重复项关联、级联确认和高风险确认防误触。
- MVP1.2：ContextPack First，专注商务/资格生成上下文包的预览、生成、确认和准备度门禁。
- MVP1.3：承接基于已确认 ContextPack 的目录/章节草稿生成、结构化生成稿、覆盖检查、事实校验、审阅和 Word 导出。
- MVP1.4：易用性优化已完成 P0 + P1 前端开发，包括首页治理、术语白话化、审阅提效、等待体验和管理看板；浏览器端验收待补，P2 拆分暂缓。
- MVP1.5：企业资料 RAG/Embedding/Rerank 和候选证据推荐阶段已启动；历史文件 OCR/LLM 资料萃取、人工确认、确认后切片、索引健康、索引重建和矩阵项候选证据接口已完成第一版。当前检索地基默认使用 Infinity 服务的 `BAAI/bge-base-zh-v1.5`（中文专精，768 维，对齐 pgvector 索引），并使用 `BAAI/bge-reranker-base` 对候选证据做召回后重排。
- 长期规划：技术标核心章节、净化产品选型、图纸/示意图、多 Agent 编排、报价辅助和外部提交/签章集成；这些不排入具体 MVP 版本，待样本、数据和专业责任边界明确后再拆专项。
- 最近回归：`make mvp1-check` 通过，后端 `185 passed`，前端生产构建通过。

版本需求和进度文档：

- [投标Agent MVP-v1.2需求规划与开发进度.md](docs/投标Agent%20MVP-v1.2需求规划与开发进度.md)
- [投标Agent MVP-v1.3需求规划与开发进度.md](docs/投标Agent%20MVP-v1.3需求规划与开发进度.md)
- [投标Agent MVP-v1.4需求规划与开发进度.md](docs/投标Agent%20MVP-v1.4需求规划与开发进度.md)
- [投标Agent MVP-v1.5需求规划与开发进度.md](docs/投标Agent%20MVP-v1.5需求规划与开发进度.md)
- [投标Agent ContextPack分阶段生成方案.md](docs/投标Agent%20ContextPack分阶段生成方案.md)

## 技术栈

- 前端：React + TypeScript + Ant Design
- 后端：Python + FastAPI
- 异步任务：Celery + Redis
- 数据库：PostgreSQL + pgvector
- 对象存储：MinIO
- 文档处理：PyMuPDF、pdfplumber、PaddleOCR、python-docx、openpyxl
- 识别抽取：阿里云 OCR（`RecognizeAdvanced`）转文本 + LLM 资料萃取
- 检索/模型服务：Infinity（`BAAI/bge-base-zh-v1.5` 嵌入 + `BAAI/bge-reranker-base` 重排，OpenAI 风格 `/embeddings` 与 `/rerank`）

## 目录结构

```text
pxss_bid_agent/
  backend/          FastAPI 后端、Agent 编排、工具、规则、检索、审计
  frontend/         React B/S 工作台
  docs/             产品、架构、版本规划和功能方案文档
  data/             示例数据、规则、模板和本地存储占位
  infra/            Docker 初始化脚本
  scripts/          本地开发脚本
  docker-compose.yml
```

## 启动中间件

```bash
cp .env.example .env
docker compose up -d postgres redis minio minio-init
```

服务地址：

- PostgreSQL：`localhost:5432`
- Redis：`localhost:6379`
- MinIO API：`http://localhost:9000`
- MinIO Console：`http://localhost:9001`

## 检索与模型服务（RAG 地基）

MVP1.5 的企业资料检索依赖一个独立的推理服务来产出 embedding 和 rerank 分数。后端通过 `EMBEDDING_PROVIDER` / `RERANK_PROVIDER` 选择来源，默认 `infinity`，推理失败时按 `*_FALLBACK_ENABLED` 降级到本地（embedding 走哈希向量、rerank 走关键词重合），保证检索链路不中断。

关键环境变量（见 `.env.example`）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `EMBEDDING_PROVIDER` / `RERANK_PROVIDER` | `infinity` | 取值 `infinity` 或 `local` |
| `EMBEDDING_BASE_URL` / `RERANK_BASE_URL` | `http://localhost:7997` | Infinity 服务地址 |
| `EMBEDDING_MODEL` | `BAAI/bge-base-zh-v1.5` | 中文专精，输出 768 维，对齐 `vector(768)` pgvector 列 |
| `RERANK_MODEL` | `BAAI/bge-reranker-base` | 多语 cross-encoder，召回后重排 |

两种部署方式（同一套 OpenAI 风格 API，二选一）：

- **Linux / GPU 生产**：用根目录 `docker-compose.yml` 里的 `infinity` 服务，`docker compose up -d infinity`（GPU 环境在 `command` 末尾追加 `--device cuda`）。
- **Mac 本地开发**：用原生 Infinity，详见 [`infra/infinity-local/README.md`](infra/infinity-local/README.md)（`uv` + Python 3.12 venv + ModelScope 下载权重，`./start.sh` 起服务）。

自测：

```bash
curl -s http://localhost:7997/health
curl -s http://localhost:7997/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"BAAI/bge-base-zh-v1.5","input":["投标人须提供有效营业执照"]}'
curl -s http://localhost:7997/rerank -H 'Content-Type: application/json' \
  -d '{"model":"BAAI/bge-reranker-base","query":"营业执照","documents":["营业执照材料","财务审计报告"]}'
```

> 注意：切换 `EMBEDDING_MODEL` 维度时，需同步 `vector(N)` 列并重建索引（迁移见 `backend/migrations/versions/*_material_vectors_*`），已落库的向量需在人工确认后重新 embedding。

## 启动后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

后端健康检查：

```bash
curl http://localhost:8000/health
```

## 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端地址：`http://localhost:5173`

## 回归检查

```bash
make mvp1-check
```

该命令会运行后端测试和前端生产构建。前端构建已按 `index`、`react-vendor`、`antd-vendor`、`utils-vendor` 分包，避免单入口包过大造成 Vite chunk 体积提示。
