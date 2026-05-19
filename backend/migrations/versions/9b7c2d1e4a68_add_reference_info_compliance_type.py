"""add reference info compliance type

Revision ID: 9b7c2d1e4a68
Revises: 212cd836c4bd
Create Date: 2026-05-15 10:35:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "9b7c2d1e4a68"
down_revision: str | None = "212cd836c4bd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_TYPES = "'qualification', 'mandatory_response', 'format', 'deadline', 'scoring', 'other'"
NEW_TYPES = (
    "'qualification', 'mandatory_response', 'format', 'deadline', "
    "'scoring', 'reference_info', 'other'"
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE compliance_items "
        "DROP CONSTRAINT IF EXISTS ck_compliance_items_compliance_item_type_allowed"
    )
    op.execute(
        "ALTER TABLE compliance_items "
        "ADD CONSTRAINT ck_compliance_items_compliance_item_type_allowed "
        f"CHECK (item_type IN ({NEW_TYPES}))"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE compliance_items SET item_type = 'other' WHERE item_type = 'reference_info'"
    )
    op.execute(
        "ALTER TABLE compliance_items "
        "DROP CONSTRAINT IF EXISTS ck_compliance_items_compliance_item_type_allowed"
    )
    op.execute(
        "ALTER TABLE compliance_items "
        "ADD CONSTRAINT ck_compliance_items_compliance_item_type_allowed "
        f"CHECK (item_type IN ({OLD_TYPES}))"
    )
