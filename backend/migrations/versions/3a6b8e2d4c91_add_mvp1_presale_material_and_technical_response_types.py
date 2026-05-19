"""add mvp1 presale material and technical response types

Revision ID: 3a6b8e2d4c91
Revises: e7a4c2b9d6f1
Create Date: 2026-05-18 18:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "3a6b8e2d4c91"
down_revision: str | None = "e7a4c2b9d6f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


OLD_MATERIAL_TYPES = (
    "'license', 'qualification', 'personnel', 'performance', "
    "'business_template', 'commitment', 'other'"
)
NEW_MATERIAL_TYPES = (
    "'license', 'qualification', 'personnel', 'performance', "
    "'business_template', 'commitment', 'product_catalog', 'test_report', "
    "'product_image', 'technical_proposal', 'other'"
)

OLD_COMPLIANCE_TYPES = (
    "'qualification', 'mandatory_response', 'format', 'deadline', "
    "'scoring', 'reference_info', 'other'"
)
NEW_COMPLIANCE_TYPES = (
    "'qualification', 'mandatory_response', 'format', 'deadline', "
    "'scoring', 'reference_info', 'technical_response', 'other'"
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE enterprise_materials "
        "DROP CONSTRAINT IF EXISTS ck_enterprise_materials_enterprise_material_type_allowed"
    )
    op.execute(
        "ALTER TABLE enterprise_materials "
        "ADD CONSTRAINT ck_enterprise_materials_enterprise_material_type_allowed "
        f"CHECK (material_type IN ({NEW_MATERIAL_TYPES}))"
    )
    op.execute(
        "ALTER TABLE compliance_items "
        "DROP CONSTRAINT IF EXISTS ck_compliance_items_compliance_item_type_allowed"
    )
    op.execute(
        "ALTER TABLE compliance_items "
        "ADD CONSTRAINT ck_compliance_items_compliance_item_type_allowed "
        f"CHECK (item_type IN ({NEW_COMPLIANCE_TYPES}))"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE enterprise_materials SET material_type = 'other' "
        "WHERE material_type IN ('product_catalog', 'test_report', 'product_image', 'technical_proposal')"
    )
    op.execute(
        "UPDATE compliance_items SET item_type = 'other' WHERE item_type = 'technical_response'"
    )
    op.execute(
        "ALTER TABLE enterprise_materials "
        "DROP CONSTRAINT IF EXISTS ck_enterprise_materials_enterprise_material_type_allowed"
    )
    op.execute(
        "ALTER TABLE enterprise_materials "
        "ADD CONSTRAINT ck_enterprise_materials_enterprise_material_type_allowed "
        f"CHECK (material_type IN ({OLD_MATERIAL_TYPES}))"
    )
    op.execute(
        "ALTER TABLE compliance_items "
        "DROP CONSTRAINT IF EXISTS ck_compliance_items_compliance_item_type_allowed"
    )
    op.execute(
        "ALTER TABLE compliance_items "
        "ADD CONSTRAINT ck_compliance_items_compliance_item_type_allowed "
        f"CHECK (item_type IN ({OLD_COMPLIANCE_TYPES}))"
    )
