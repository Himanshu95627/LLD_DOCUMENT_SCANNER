from sqlalchemy import text

from app.db.session import Base, engine


async def init_db() -> None:
    """
    Creates all tables and enables the pgvector extension.
    Called once on app startup.
    
    In production you'd use Alembic migrations instead,
    but this is fine for a portfolio project.
    """
    async with engine.begin() as conn:
        # Enable pgvector — must come before creating tables with Vector columns
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Create all tables defined in models.py
        await conn.run_sync(Base.metadata.create_all)
        
        # Create an IVFFlat index for fast approximate nearest-neighbour search.
        # cosine distance works best for OpenAI embeddings.
        # lists=100 is a good default for up to ~1M vectors.
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS chunks_embedding_idx
            ON chunks
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
