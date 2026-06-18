FROM python:3.11-slim AS backend

WORKDIR /app

ARG APT_MIRROR=""

# Install system deps for psycopg.
# libreoffice-writer/fonts-noto-cjk 仅 LEGACY_DOC_CONVERTER_MODE=subprocess 时需要；
# 若改用 libreoffice-converter sidecar（http 模式），可从这里移除以瘦身后端镜像。
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|$APT_MIRROR|g; s|security.debian.org|$APT_MIRROR|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
        sed -i "s|deb.debian.org|$APT_MIRROR|g; s|security.debian.org|$APT_MIRROR|g" /etc/apt/sources.list 2>/dev/null || true; \
    fi \
    && apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libreoffice-writer fonts-noto-cjk && \
    rm -rf /var/lib/apt/lists/*

# Copy backend
COPY backend/pyproject.toml backend/
RUN pip install --no-cache-dir -e backend/

# Copy backend source
COPY backend/app backend/app
COPY backend/migrations backend/migrations
COPY backend/alembic.ini backend/alembic.ini
COPY backend/scripts backend/scripts

# Copy frontend dist (serve via backend in production)
COPY frontend/dist /app/frontend/dist

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
