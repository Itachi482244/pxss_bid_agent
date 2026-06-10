"""add history material extract async task type

Revision ID: e3b9a1c7d2f4
Revises: b1f7d3a9c204
Create Date: 2026-06-07
"""

from __future__ import annotations

from alembic import op

revision: str = "e3b9a1c7d2f4"
down_revision: str | None = "b1f7d3a9c204"
branch_labels: str | None = None
depends_on: str | None = None

_CONSTRAINT = "ck_async_tasks_async_task_type_allowed"
_OLD = (
    "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
    "'excel_export', 'document_section_plan', 'section_compliance_extract', "
    "'business_draft_generate')"
)
_NEW = (
    "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
    "'excel_export', 'document_section_plan', 'section_compliance_extract', "
    "'business_draft_generate', 'history_material_extract')"
)


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "async_tasks", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "async_tasks", _NEW)


def downgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "async_tasks", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "async_tasks", _OLD)
