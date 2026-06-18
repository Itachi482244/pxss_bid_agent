"""add matrix_auto_resolve async task type

Revision ID: 7e1a4c9b2d83
Revises: 6d2f9a1c8e47
Create Date: 2026-06-18

让 Agent 自动处理质量门禁阻断的编排任务（定向重抽 / 重排重抽 + 全文复检收敛）
复用既有 ``async_tasks`` 表与 ``/tasks/{id}`` 轮询通道，仅放开任务类型 CHECK 约束。
"""

from __future__ import annotations

from alembic import op

revision: str = "7e1a4c9b2d83"
down_revision: str | None = "6d2f9a1c8e47"
branch_labels: str | None = None
depends_on: str | None = None

_CONSTRAINT = "ck_async_tasks_async_task_type_allowed"
_OLD = (
    "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
    "'excel_export', 'document_section_plan', 'section_compliance_extract', "
    "'business_draft_generate', 'history_material_extract')"
)
_NEW = (
    "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
    "'excel_export', 'document_section_plan', 'section_compliance_extract', "
    "'business_draft_generate', 'history_material_extract', 'matrix_auto_resolve')"
)


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "async_tasks", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "async_tasks", _NEW)


def downgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "async_tasks", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "async_tasks", _OLD)
