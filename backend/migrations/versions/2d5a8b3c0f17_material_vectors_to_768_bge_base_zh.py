"""switch enterprise material embedding vectors to 768 dimensions (bge-base-zh-v1.5)

Revision ID: 2d5a8b3c0f17
Revises: 1c4f7a2b9e60
Create Date: 2026-06-13

Model selection finalized: embedding = BAAI/bge-base-zh-v1.5 (Chinese-focused,
768-dim), rerank = BAAI/bge-reranker-base. The previous 1024-dim column (bge-m3)
is incompatible, so any stored chunk vectors are cleared and must be re-embedded
after human confirmation.
"""

from __future__ import annotations

from alembic import op

revision: str = "2d5a8b3c0f17"
down_revision: str | None = "1c4f7a2b9e60"
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
    _recreate_vector_column(768)


def downgrade() -> None:
    _recreate_vector_column(1024)
