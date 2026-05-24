.PHONY: middleware-up middleware-down middleware-ps backend-dev backend-worker frontend-dev test-backend mvp1-golden mvp1-check db-upgrade db-seed

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

mvp1-golden:
	cd backend && .venv/bin/pytest -q tests/test_mvp1_p0_golden_regression.py tests/test_compliance_generation_worker.py::test_cleanroom_notice_rule_fallback_atomizes_and_deduplicates_requirements

mvp1-check:
	cd backend && .venv/bin/pytest -q
	cd frontend && npm run build

db-upgrade:
	cd backend && .venv/bin/alembic upgrade head

db-seed:
	cd backend && .venv/bin/python scripts/seed_dev_data.py
