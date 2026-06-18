# 极小的 LibreOffice headless 转换 sidecar：把旧版二进制 .doc 转成 .docx。
# 后端（原生或容器）通过 HTTP 调用，等同于现有访问 infinity 的方式。
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PORT=2004

# 可选 apt 镜像源加速（国内网络访问 deb.debian.org 很慢）。
# 例：--build-arg APT_MIRROR=mirrors.aliyun.com（或 mirrors.tuna.tsinghua.edu.cn）。
ARG APT_MIRROR=""

# libreoffice-writer 提供 soffice；fonts-noto-cjk 保证中文不出豆腐块。
# python3 跑标准库 HTTP 服务（无三方依赖）。
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|$APT_MIRROR|g; s|security.debian.org|$APT_MIRROR|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i "s|deb.debian.org|$APT_MIRROR|g; s|security.debian.org|$APT_MIRROR|g" /etc/apt/sources.list 2>/dev/null || true; \
    fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer \
        fonts-noto-cjk \
        python3 \
        ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY server.py /app/server.py

EXPOSE 2004

# 预热一次 soffice profile，缩短首个真实请求的冷启动。
HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=30s \
    CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:2004/health').status==200 else 1)"

CMD ["python3", "/app/server.py"]
