# 本地 Infinity（embedding + rerank）

Mac 本地用原生 Infinity 跑两个模型，给后端 RAG 提供 `/embeddings` 与 `/rerank`。
Linux/GPU 生产环境改用根目录 `docker-compose.yml` 里的 `infinity` 服务（同一套 OpenAI 风格 API）。

## 模型

| 用途 | 模型 | 维度 | 说明 |
|---|---|---|---|
| 嵌入 | `BAAI/bge-base-zh-v1.5` | 768 | 中文专精，102M，最长 512 token |
| 重排 | `BAAI/bge-reranker-base` | - | 多语 cross-encoder，278M |

后端契约：`backend/app/core/config.py` 默认 `EMBEDDING_PROVIDER=infinity`、
`RERANK_PROVIDER=infinity`，base_url `http://localhost:7997`，pgvector 列为 `vector(768)`。

## 一次性安装

```bash
# 1) 安装 uv（若未装）
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# 2) 在本目录建 Python 3.12 venv 并装依赖
cd infra/infinity-local
uv venv --python 3.12 .venv
VIRTUAL_ENV="$PWD/.venv" uv pip install "infinity-emb[torch,server]" modelscope
# infinity 0.0.77 与新 click 不兼容，需锁 click<8.2
VIRTUAL_ENV="$PWD/.venv" uv pip install "click==8.1.8"

# 3) 用 ModelScope 下载模型（国内快）
.venv/bin/python - <<'PY'
from modelscope import snapshot_download
snapshot_download("BAAI/bge-base-zh-v1.5", local_dir="models/bge-base-zh-v1.5")
snapshot_download("BAAI/bge-reranker-base", local_dir="models/bge-reranker-base")
PY
```

## 启动

```bash
cd infra/infinity-local
./start.sh                      # 前台运行，Ctrl+C 退出
# 或后台： nohup ./start.sh > infinity.log 2>&1 &
```

健康检查与自测：

```bash
curl -s http://localhost:7997/health
curl -s http://localhost:7997/embeddings -H 'Content-Type: application/json' \
  -d '{"model":"BAAI/bge-base-zh-v1.5","input":["投标人须提供有效营业执照"]}'
curl -s http://localhost:7997/rerank -H 'Content-Type: application/json' \
  -d '{"model":"BAAI/bge-reranker-base","query":"营业执照","documents":["营业执照材料","财务审计报告"]}'
```

## 已知坑（已在 start.sh 处理）

- **reranker 启动预热崩溃**：infinity 0.0.77 在 CPU 上对 reranker 跑启动预热前向会原生崩溃（无 Python 报错、进程直接消失）。用 `--no-model-warmup` 跳过预热，真实推理正常。
- **BetterTransformerManager 未定义**：未装 optimum 时报 `NameError`。用 `--no-bettertransformer` 关掉。
- **click 8.2 不兼容**：typer 0.12.5 + click>=8.2 会报 `Secondary flag is not valid for non-boolean flag`。锁 `click==8.1.8`。
