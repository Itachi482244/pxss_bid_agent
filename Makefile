.PHONY: middleware-up middleware-down middleware-ps backend-dev backend-worker frontend-dev test-backend mvp1-golden mvp1-check db-upgrade db-seed dev

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
	@echo "Waiting for backend health check..."
	@for i in $$(seq 1 30); do \
		if curl -sf http://localhost:8000/health > /dev/null 2>&1; then \
			echo "Backend ready."; break; \
		fi; \
		echo "Waiting... ($$i/30)"; sleep 1; \
	done
	cd frontend && npm run dev

dev: middleware-up
	@echo "Waiting for middleware..."
	@for i in $$(seq 1 15); do \
		if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1 && \
		   docker compose exec postgres pg_isready -U pxss -d pxss_bid_agent > /dev/null 2>&1; then \
			echo "Middleware ready."; break; \
		fi; \
		echo "Waiting... ($$i/15)"; sleep 2; \
	done
	@$(MAKE) backend-dev & \
	  $(MAKE) frontend-dev

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
