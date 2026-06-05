"""add business_draft_generate async task type

Revision ID: a3c9e7d2b5f1
Revises: f2b7c9d1e4a3
Create Date: 2026-06-04

Allows MVP1.2 ContextPack draft generation to run as an async task so large
documents no longer block the request thread. Only the ``async_tasks`` task
type check constraint changes; no new table is introduced because the existing
``async_tasks`` + generic ``/tasks/{id}`` polling channel is reused.
"""

from __future__ import annotations

from alembic import op

revision: str = "a3c9e7d2b5f1"
down_revision: str | None = "f2b7c9d1e4a3"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
        "'excel_export', 'document_section_plan', 'section_compliance_extract', "
        "'business_draft_generate')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_async_tasks_async_task_type_allowed"),
        "async_tasks",
        "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
        "'excel_export', 'document_section_plan', 'section_compliance_extract')",
    )
