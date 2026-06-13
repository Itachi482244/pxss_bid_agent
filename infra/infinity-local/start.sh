#!/usr/bin/env bash
# 本地（Mac）原生 Infinity：同时服务 embedding + rerank，OpenAI 风格 /embeddings 与 /rerank。
# 后端 .env 默认指向 http://localhost:7997（EMBEDDING_PROVIDER/RERANK_PROVIDER=infinity）。
#
# 关键参数说明：
#   --no-model-warmup   ：infinity 0.0.77 在 CPU 上对 reranker 跑启动预热前向会原生崩溃（段错误），
#                         跳过预热即可；真实推理正常。
#   --no-bettertransformer：未装 optimum 时 infinity 会引用未定义的 BetterTransformerManager 报错，关掉它。
#   --served-model-name ：把本地权重路径别名成 BAAI/... 名称，跟后端 EMBEDDING_MODEL/RERANK_MODEL 对齐。
#
# Linux/GPU 生产环境用 docker-compose 里的 infinity 服务（同一套 API），不要用这个脚本。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PORT="${INFINITY_PORT:-7997}"
DEVICE="${INFINITY_DEVICE:-cpu}"   # mac 上也可试 mps，但 cpu 最稳
VENV="$HERE/.venv"

EMBED_MODEL="$HERE/models/bge-base-zh-v1.5"
RERANK_MODEL="$HERE/models/bge-reranker-base"

if [[ ! -x "$VENV/bin/infinity_emb" ]]; then
  echo "未找到 $VENV/bin/infinity_emb，请先按 README 创建 venv 并安装依赖。" >&2
  exit 1
fi
for d in "$EMBED_MODEL" "$RERANK_MODEL"; do
  if [[ ! -d "$d" ]]; then
    echo "缺少模型目录：$d，请先用 ModelScope 下载（见 README）。" >&2
    exit 1
  fi
done

exec "$VENV/bin/infinity_emb" v2 \
  --model-id "$EMBED_MODEL" --served-model-name BAAI/bge-base-zh-v1.5 \
  --model-id "$RERANK_MODEL" --served-model-name BAAI/bge-reranker-base \
  --engine torch --device "$DEVICE" \
  --no-bettertransformer --no-model-warmup \
  --port "$PORT"
