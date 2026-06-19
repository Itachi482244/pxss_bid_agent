"""add agent review items

Revision ID: 9f6b2a1c4d5e
Revises: 7e1a4c9b2d83
Create Date: 2026-06-18

半自主推进助手的统一待拍板清单：

- Agent 可以对 4/5/6 步产出自动核验记录或人工待办，但不直接覆盖人工确认语义；
- 证据绑定、资格结论和最终承诺仍通过人工采纳动作生效；
- 同步放开 agent 审计主体和 agent_assist 异步任务类型。
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "9f6b2a1c4d5e"
down_revision: str | None = "7e1a4c9b2d83"
branch_labels: str | None = None
depends_on: str | None = None

_ASYNC_TASK_CONSTRAINT = "ck_async_tasks_async_task_type_allowed"
_ASYNC_TASK_OLD = (
    "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
    "'excel_export', 'document_section_plan', 'section_compliance_extract', "
    "'business_draft_generate', 'history_material_extract', 'matrix_auto_resolve')"
)
_ASYNC_TASK_NEW = (
    "task_type IN ('file_acquisition', 'document_parse', 'matrix_generate', "
    "'excel_export', 'document_section_plan', 'section_compliance_extract', "
    "'business_draft_generate', 'history_material_extract', 'matrix_auto_resolve', "
    "'agent_assist')"
)

_AUDIT_ACTOR_CONSTRAINT = "ck_audit_logs_audit_log_actor_type_allowed"
_AUDIT_ACTOR_OLD = "actor_type IN ('user', 'system', 'worker')"
_AUDIT_ACTOR_NEW = "actor_type IN ('user', 'system', 'worker', 'agent')"


def upgrade() -> None:
    op.drop_constraint(op.f(_ASYNC_TASK_CONSTRAINT), "async_tasks", type_="check")
    op.create_check_constraint(op.f(_ASYNC_TASK_CONSTRAINT), "async_tasks", _ASYNC_TASK_NEW)
    op.drop_constraint(op.f(_AUDIT_ACTOR_CONSTRAINT), "audit_logs", type_="check")
    op.create_check_constraint(op.f(_AUDIT_ACTOR_CONSTRAINT), "audit_logs", _AUDIT_ACTOR_NEW)

    op.create_table(
        "agent_review_items",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=False),
        sa.Column("async_task_id", sa.UUID(), nullable=True),
        sa.Column("run_key", sa.String(length=128), nullable=False),
        sa.Column("step", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("object_type", sa.String(length=100), nullable=False),
        sa.Column("object_id", sa.UUID(), nullable=True),
        sa.Column("compliance_item_id", sa.UUID(), nullable=True),
        sa.Column("enterprise_material_id", sa.UUID(), nullable=True),
        sa.Column("qualification_evaluation_id", sa.UUID(), nullable=True),
        sa.Column("qualification_decision_id", sa.UUID(), nullable=True),
        sa.Column("draft_block_id", sa.UUID(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("requires_human", sa.Boolean(), nullable=False),
        sa.Column("escalation_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recommendation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_ref_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("triggered_by", sa.UUID(), nullable=True),
        sa.Column("decided_by", sa.UUID(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "step IN ('matrix_review', 'evidence_binding', 'qualification_technical')",
            name=op.f("ck_agent_review_items_agent_review_item_step_allowed"),
        ),
        sa.CheckConstraint(
            "status IN ('open', 'accepted', 'dismissed', 'superseded', 'auto_passed')",
            name=op.f("ck_agent_review_items_agent_review_item_status_allowed"),
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name=op.f("ck_agent_review_items_agent_review_item_severity_allowed"),
        ),
        sa.CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name=op.f("ck_agent_review_items_agent_review_item_confidence_score_range"),
        ),
        sa.ForeignKeyConstraint(["async_task_id"], ["async_tasks.id"], name=op.f("fk_agent_review_items_async_task_id_async_tasks")),
        sa.ForeignKeyConstraint(["compliance_item_id"], ["compliance_items.id"], name=op.f("fk_agent_review_items_compliance_item_id_compliance_items")),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], name=op.f("fk_agent_review_items_decided_by_users")),
        sa.ForeignKeyConstraint(["draft_block_id"], ["draft_blocks.id"], name=op.f("fk_agent_review_items_draft_block_id_draft_blocks")),
        sa.ForeignKeyConstraint(["enterprise_material_id"], ["enterprise_materials.id"], name=op.f("fk_agent_review_items_enterprise_material_id_enterprise_materials")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], name=op.f("fk_agent_review_items_project_id_projects")),
        sa.ForeignKeyConstraint(["qualification_decision_id"], ["qualification_decisions.id"], name=op.f("fk_agent_review_items_qualification_decision_id_qualification_decisions")),
        sa.ForeignKeyConstraint(["qualification_evaluation_id"], ["qualification_evaluations.id"], name=op.f("fk_agent_review_items_qualification_evaluation_id_qualification_evaluations")),
        sa.ForeignKeyConstraint(["section_id"], ["bid_sections.id"], name=op.f("fk_agent_review_items_section_id_bid_sections")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name=op.f("fk_agent_review_items_tenant_id_tenants")),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], name=op.f("fk_agent_review_items_triggered_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_review_items")),
    )
    op.create_index(
        "idx_agent_review_compliance",
        "agent_review_items",
        ["tenant_id", "compliance_item_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_agent_review_material",
        "agent_review_items",
        ["tenant_id", "enterprise_material_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_agent_review_object",
        "agent_review_items",
        ["tenant_id", "object_type", "object_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_agent_review_section_status",
        "agent_review_items",
        ["tenant_id", "project_id", "section_id", "status", "step", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_agent_review_task",
        "agent_review_items",
        ["tenant_id", "async_task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_agent_review_task", table_name="agent_review_items")
    op.drop_index("idx_agent_review_section_status", table_name="agent_review_items")
    op.drop_index("idx_agent_review_object", table_name="agent_review_items")
    op.drop_index("idx_agent_review_material", table_name="agent_review_items")
    op.drop_index("idx_agent_review_compliance", table_name="agent_review_items")
    op.drop_table("agent_review_items")

    op.drop_constraint(op.f(_AUDIT_ACTOR_CONSTRAINT), "audit_logs", type_="check")
    op.create_check_constraint(op.f(_AUDIT_ACTOR_CONSTRAINT), "audit_logs", _AUDIT_ACTOR_OLD)
    op.drop_constraint(op.f(_ASYNC_TASK_CONSTRAINT), "async_tasks", type_="check")
    op.create_check_constraint(op.f(_ASYNC_TASK_CONSTRAINT), "async_tasks", _ASYNC_TASK_OLD)
