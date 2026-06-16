"""add tender format docx export type

Revision ID: 6d2f9a1c8e47
Revises: 2d5a8b3c0f17
Create Date: 2026-06-16
"""

from __future__ import annotations

from alembic import op

revision: str = "6d2f9a1c8e47"
down_revision: str | None = "2d5a8b3c0f17"
branch_labels: str | None = None
depends_on: str | None = None

_CONSTRAINT = "ck_export_files_export_file_type_allowed"
_OLD = "export_type IN ('compliance_matrix_excel', 'business_draft_word')"
_NEW = "export_type IN ('compliance_matrix_excel', 'business_draft_word', 'tender_format_docx')"


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "export_files", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "export_files", _NEW)


def downgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "export_files", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "export_files", _OLD)
