.PHONY: middleware-up middleware-down middleware-ps backend-dev backend-worker frontend-dev test-backend db-upgrade db-seed

middleware-up:
	docker compose up -d postgres redis minio minio-init

middleware-down:
	docker compose down

middleware-ps:
	docker compose ps

backend-dev:
	cd backend && uvicorn app.main:app --reload

backend-worker:
	cd backend && .venv/bin/celery -A app.worker.celery_app worker --loglevel=info

frontend-dev:
	cd frontend && npm run dev

test-backend:
	cd backend && pytest

db-upgrade:
	cd backend && .venv/bin/alembic upgrade head

db-seed:
	cd backend && .venv/bin/python scripts/seed_dev_data.py
