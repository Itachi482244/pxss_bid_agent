"""add needs_confirm draft block review status for author mandatory text

Revision ID: b1f7d3a9c204
Revises: a3c9e7d2b5f1
Create Date: 2026-06-06

MVP1.3 instruction layer: author "forced phrasing" (强制措辞) blocks are emitted
with ``review_status = 'needs_confirm'`` so the final-draft preflight forces an
explicit per-block human confirmation before export. This widens the existing
check constraint to accept the new status without dropping any prior value.
"""

from __future__ import annotations

from alembic import op

revision: str = "b1f7d3a9c204"
down_revision: str | None = "a3c9e7d2b5f1"
branch_labels: str | None = None
depends_on: str | None = None

_CONSTRAINT = "ck_draft_blocks_draft_block_review_status_allowed"
_OLD = "review_status IN ('pending', 'covered', 'needs_evidence', 'needs_fact', 'approved', 'rejected')"
_NEW = (
    "review_status IN ('pending', 'covered', 'needs_evidence', 'needs_fact', "
    "'needs_confirm', 'approved', 'rejected')"
)


def upgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "draft_blocks", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "draft_blocks", _NEW)


def downgrade() -> None:
    op.drop_constraint(op.f(_CONSTRAINT), "draft_blocks", type_="check")
    op.create_check_constraint(op.f(_CONSTRAINT), "draft_blocks", _OLD)
