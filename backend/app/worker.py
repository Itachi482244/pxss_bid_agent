from celery import Celery

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.compliance_generation import execute_compliance_matrix_generation_task
from app.services.document_parse import execute_document_parse_task
from app.services.export_excel import execute_compliance_matrix_excel_export_task
from app.services.file_acquisition import execute_file_acquisition_task

celery_app = Celery(
    "pxss_bid_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=60 * 30,
    task_soft_time_limit=60 * 25,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="tasks.file_acquisition")
def run_file_acquisition_task(task_id: str) -> dict[str, str]:
    with SessionLocal() as db:
        result = execute_file_acquisition_task(db, task_id)
    parse_async_task_id = result.get("parse_async_task_id")
    if parse_async_task_id:
        run_document_parse_task.delay(parse_async_task_id)
    return result


@celery_app.task(name="tasks.document_parse")
def run_document_parse_task(task_id: str) -> dict[str, str | int]:
    with SessionLocal() as db:
        return execute_document_parse_task(db, task_id)


@celery_app.task(name="tasks.compliance_matrix_generation")
def run_compliance_matrix_generation_task(task_id: str) -> dict[str, str | int]:
    with SessionLocal() as db:
        return execute_compliance_matrix_generation_task(db, task_id)


@celery_app.task(name="tasks.compliance_matrix_excel_export")
def run_compliance_matrix_excel_export_task(task_id: str) -> dict[str, str | int]:
    with SessionLocal() as db:
        return execute_compliance_matrix_excel_export_task(db, task_id)
