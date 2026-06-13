"""upgrade enterprise material embedding vectors to 768 dimensions

Revision ID: 0b7d3c9e5a21
Revises: f4c8d9e2a7b1
Create Date: 2026-06-13
"""

from __future__ import annotations

from alembic import op

revision: str = "0b7d3c9e5a21"
down_revision: str | None = "f4c8d9e2a7b1"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_enterprise_material_chunks_embedding_ivfflat")
    op.execute("DELETE FROM enterprise_material_chunks")
    op.execute("ALTER TABLE enterprise_material_chunks DROP COLUMN embedding_vector")
    op.execute("ALTER TABLE enterprise_material_chunks ADD COLUMN embedding_vector vector(768)")
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
            EXECUTE '
              CREATE INDEX IF NOT EXISTS idx_enterprise_material_chunks_embedding_ivfflat
              ON enterprise_material_chunks
              USING ivfflat (embedding_vector vector_cosine_ops)
              WITH (lists = 16)
              WHERE embedding_vector IS NOT NULL
            ';
          END IF;
        EXCEPTION
          WHEN undefined_object OR feature_not_supported THEN
            RAISE NOTICE 'pgvector ivfflat index is not available in this database image; skipping enterprise material vector index.';
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_enterprise_material_chunks_embedding_ivfflat")
    op.execute("DELETE FROM enterprise_material_chunks")
    op.execute("ALTER TABLE enterprise_material_chunks DROP COLUMN embedding_vector")
    op.execute("ALTER TABLE enterprise_material_chunks ADD COLUMN embedding_vector vector(16)")
