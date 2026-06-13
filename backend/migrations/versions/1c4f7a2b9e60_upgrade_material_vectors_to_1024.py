"""upgrade enterprise material embedding vectors to 1024 dimensions (bge-m3)

Revision ID: 1c4f7a2b9e60
Revises: 0b7d3c9e5a21
Create Date: 2026-06-13

bge-m3 outputs 1024-dim vectors; the previous 768 column truncated them.
Switching embedding serving to Infinity (real bge-m3), so store full 1024.
Existing chunk vectors were produced at 768 and are incompatible, so they
are cleared and must be re-embedded after human confirmation.
"""

from __future__ import annotations

from alembic import op

revision: str = "1c4f7a2b9e60"
down_revision: str | None = "0b7d3c9e5a21"
branch_labels: str | None = None
depends_on: str | None = None


def _recreate_vector_column(dimensions: int) -> None:
    op.execute("DROP INDEX IF EXISTS idx_enterprise_material_chunks_embedding_ivfflat")
    op.execute("DELETE FROM enterprise_material_chunks")
    op.execute("ALTER TABLE enterprise_material_chunks DROP COLUMN embedding_vector")
    op.execute(
        f"ALTER TABLE enterprise_material_chunks ADD COLUMN embedding_vector vector({dimensions})"
    )
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


def upgrade() -> None:
    _recreate_vector_column(1024)


def downgrade() -> None:
    _recreate_vector_column(768)
