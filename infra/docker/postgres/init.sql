DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION
  WHEN undefined_file THEN
    RAISE NOTICE 'pgvector extension is not available in this PostgreSQL image; skip vector extension.';
END
$$;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
