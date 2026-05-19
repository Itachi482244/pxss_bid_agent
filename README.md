# 投标 Agent

面向中国招投标场景的专业投标 Agent 项目。当前仓库已搭建基础工程骨架，采用 Web B/S 工作台 + Python 后端 + Docker 中间件的开发模式。

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
  docs/             工程文档
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

