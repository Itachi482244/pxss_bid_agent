# 投标 Agent

面向中国招投标场景的专业投标 Agent 项目。当前仓库采用 Web B/S 工作台 + Python 后端 + Docker 中间件的开发模式，已从 MVP1.0 可试用闭环推进到 MVP1.1 P0 + P1：模型安全接入、合规矩阵 AI 增强、原文审阅、人工补漏、相似补票和重复项级联确认主体能力均已完成。

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
- MVP1.4：承接 pgvector RAG、Embedding/Rerank、企业资料语义检索和候选证据推荐，作为 ContextPack 的上游增强。
- 长期规划：技术标核心章节、净化产品选型、图纸/示意图、OCR、多 Agent 编排、报价辅助和外部提交/签章集成；这些不排入具体 MVP 版本，待样本、数据和专业责任边界明确后再拆专项。
- 最近回归：`make mvp1-check` 通过，后端 `43 passed`，前端构建通过且 Vite chunk 体积提示已处理。

版本需求和进度文档：

- [投标Agent MVP-v1.2需求规划与开发进度.md](docs/投标Agent%20MVP-v1.2需求规划与开发进度.md)
- [投标Agent MVP-v1.3需求规划与开发进度.md](docs/投标Agent%20MVP-v1.3需求规划与开发进度.md)
- [投标Agent MVP-v1.4需求规划与开发进度.md](docs/投标Agent%20MVP-v1.4需求规划与开发进度.md)
- [投标Agent ContextPack分阶段生成方案.md](docs/投标Agent%20ContextPack分阶段生成方案.md)

## 技术栈

- 前端：React + TypeScript + Ant Design
- 后端：Python + FastAPI
- 异步任务：Celery + Redis
- 数据库：PostgreSQL + pgvector
- 对象存储：MinIO
- 文档处理：PyMuPDF、pdfplumber、PaddleOCR、python-docx、openpyxl

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
