"""
Vector similarity retrieval using pgvector.

Uses cosine distance — best for OpenAI embeddings which are already
normalised. Lower cosine distance = more similar.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Chunk, Document


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    page_number: int | None
    chunk_index: int
    char_offset: int
    similarity_score: float   # 0.0 to 1.0, higher = more similar


async def retrieve(
    query_embedding: list[float],
    db: AsyncSession,
    top_k: int = settings.top_k,
    document_id: UUID | None = None,   # optional: filter to one doc
) -> list[RetrievedChunk]:
    """
    Find the top_k most similar chunks to the query embedding.
    
    Uses cosine similarity via pgvector's <=> operator.
    1 - cosine_distance gives us a similarity score in [0, 1].
    """
    embedding_str = str(query_embedding)

    # Build the query — join chunks with documents to get filename for citations
    sql = text("""
        SELECT
            c.id            AS chunk_id,
            c.document_id   AS document_id,
            d.filename      AS filename,
            c.content       AS content,
            c.page_number   AS page_number,
            c.chunk_index   AS chunk_index,
            c.char_offset   AS char_offset,
            1 - (c.embedding <=> :embedding ::vector) AS similarity_score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE (:document_id IS NULL OR c.document_id = :document_id ::uuid)
        ORDER BY c.embedding <=> :embedding ::vector
        LIMIT :top_k
    """)

    result = await db.execute(sql, {
        "embedding": embedding_str,
        "document_id": str(document_id) if document_id else None,
        "top_k": top_k,
    })

    rows = result.mappings().all()

    return [
        RetrievedChunk(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            filename=row["filename"],
            content=row["content"],
            page_number=row["page_number"],
            chunk_index=row["chunk_index"],
            char_offset=row["char_offset"],
            similarity_score=float(row["similarity_score"]),
        )
        for row in rows
    ]
