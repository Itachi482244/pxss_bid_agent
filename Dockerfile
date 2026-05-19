FROM python:3.11-slim AS backend

WORKDIR /app

# Install system deps for psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
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
