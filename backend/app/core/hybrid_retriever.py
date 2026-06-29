# """
# Hybrid retrieval: vector similarity + full-text search (BM25).

# Why hybrid?
#   - Vector search is great at semantic similarity ("what is the capital?")
#     but misses exact keyword matches ("what is RFC 7231?")
#   - Full-text search (BM25) is great at exact matches but misses paraphrases
#   - Combining them covers both cases

# Strategy: Reciprocal Rank Fusion (RRF)
#   Each retrieval method produces a ranked list.
#   RRF fuses them without needing to tune score scales:

#     RRF_score = Σ 1 / (k + rank)   where k=60 (standard constant)

#   A chunk that ranks #1 in both lists beats one that's #1 in only one.
#   A chunk that appears in only one list still gets a score (just lower).
# """

# from dataclasses import dataclass
# from uuid import UUID

# from sqlalchemy import text
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.config import settings
# from app.core.retriever import RetrievedChunk

# RRF_K = 60   # standard RRF constant — prevents high ranks from dominating


# async def hybrid_retrieve(
#     query: str,
#     query_embedding: list[float],
#     db: AsyncSession,
#     top_k: int = settings.top_k,
#     document_id: UUID | None = None,
# ) -> list[RetrievedChunk]:
#     """
#     Retrieve chunks using vector similarity + BM25, fused with RRF.

#     Returns top_k chunks sorted by combined RRF score.
#     """
#     embedding_str = str(query_embedding)
#     doc_filter = str(document_id) if document_id else None

#     # --- Vector retrieval ---
#     vector_sql = text("""
#         SELECT
#             c.id            AS chunk_id,
#             c.document_id,
#             d.filename,
#             c.content,
#             c.page_number,
#             c.chunk_index,
#             c.char_offset,
#             1 - (c.embedding <=> :embedding ::vector) AS similarity_score,
#             ROW_NUMBER() OVER (ORDER BY c.embedding <=> :embedding ::vector) AS rank
#         FROM chunks c
#         JOIN documents d ON d.id = c.document_id
#         WHERE (:document_id IS NULL OR c.document_id = :document_id ::uuid)
#         ORDER BY c.embedding <=> :embedding ::vector
#         LIMIT :top_k
#     """)

#     # --- Full-text retrieval (BM25 via Postgres ts_rank_cd) ---
#     # to_tsquery handles multi-word queries; plainto_tsquery is more forgiving
#     fts_sql = text("""
#         SELECT
#             c.id            AS chunk_id,
#             c.document_id,
#             d.filename,
#             c.content,
#             c.page_number,
#             c.chunk_index,
#             c.char_offset,
#             ts_rank_cd(
#                 to_tsvector('english', c.content),
#                 plainto_tsquery('english', :query)
#             )               AS similarity_score,
#             ROW_NUMBER() OVER (
#                 ORDER BY ts_rank_cd(
#                     to_tsvector('english', c.content),
#                     plainto_tsquery('english', :query)
#                 ) DESC
#             ) AS rank
#         FROM chunks c
#         JOIN documents d ON d.id = c.document_id
#         WHERE
#             to_tsvector('english', c.content) @@ plainto_tsquery('english', :query)
#             AND (:document_id IS NULL OR c.document_id = :document_id ::uuid)
#         ORDER BY similarity_score DESC
#         LIMIT :top_k
#     """)

#     params = {
#         "embedding": embedding_str,
#         "query": query,
#         "document_id": doc_filter,
#         "top_k": top_k,
#     }

#     vector_result = await db.execute(vector_sql, params)
#     fts_result = await db.execute(fts_sql, params)

#     vector_rows = vector_result.mappings().all()
#     fts_rows = fts_result.mappings().all()

#     # --- Reciprocal Rank Fusion ---
#     # Map chunk_id → RRF score accumulator
#     rrf_scores: dict[str, float] = {}
#     chunk_data: dict[str, dict] = {}

#     for row in vector_rows:
#         cid = str(row["chunk_id"])
#         rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + row["rank"])
#         chunk_data[cid] = dict(row)

#     for row in fts_rows:
#         cid = str(row["chunk_id"])
#         rrf_scores[cid] = rrf_scores.get(cid, 0) + 1 / (RRF_K + row["rank"])
#         if cid not in chunk_data:
#             chunk_data[cid] = dict(row)

#     # Sort by combined RRF score
#     sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

#     return [
#         RetrievedChunk(
#             chunk_id=chunk_data[cid]["chunk_id"],
#             document_id=chunk_data[cid]["document_id"],
#             filename=chunk_data[cid]["filename"],
#             content=chunk_data[cid]["content"],
#             page_number=chunk_data[cid]["page_number"],
#             chunk_index=chunk_data[cid]["chunk_index"],
#             char_offset=chunk_data[cid]["char_offset"],
#             similarity_score=rrf_scores[cid],   # RRF score as the unified score
#         )
#         for cid in sorted_ids[:top_k]
#     ]
"""
Hybrid retrieval: vector similarity + full-text search (BM25).

Why hybrid?
  - Vector search is great at semantic similarity ("what is the capital?")
    but misses exact keyword matches ("what is RFC 7231?")
  - Full-text search (BM25) is great at exact matches but misses paraphrases
  - Combining them covers both cases

Strategy: Reciprocal Rank Fusion (RRF)

    RRF_score = Σ 1 / (k + rank)

A chunk that ranks highly in both retrieval methods receives a
higher combined score.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.retriever import RetrievedChunk

RRF_K = 60


async def hybrid_retrieve(
    query: str,
    query_embedding: list[float],
    db: AsyncSession,
    top_k: int = settings.top_k,
    document_id: UUID | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieve chunks using vector similarity + BM25,
    then fuse results using Reciprocal Rank Fusion.
    """

    # pgvector accepts this textual representation:
    # [0.1,0.2,0.3,...]
    embedding_str = str(query_embedding)

    # ----------------------------
    # Vector search
    # ----------------------------
    vector_sql = """
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.filename,
            c.content,
            c.page_number,
            c.chunk_index,
            c.char_offset,
            1 - (c.embedding <=> CAST(:embedding AS vector)) AS similarity_score,
            ROW_NUMBER() OVER (
                ORDER BY c.embedding <=> CAST(:embedding AS vector)
            ) AS rank
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
    """

    vector_params = {
        "embedding": embedding_str,
        "top_k": top_k,
    }

    if document_id is not None:
        vector_sql += """
            WHERE c.document_id = :document_id
        """
        vector_params["document_id"] = document_id

    vector_sql += """
        ORDER BY c.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """

    # ----------------------------
    # Full-text search
    # ----------------------------
    fts_sql = """
        SELECT
            c.id AS chunk_id,
            c.document_id,
            d.filename,
            c.content,
            c.page_number,
            c.chunk_index,
            c.char_offset,
            ts_rank_cd(
                to_tsvector('english', c.content),
                plainto_tsquery('english', :query)
            ) AS similarity_score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector('english', c.content),
                    plainto_tsquery('english', :query)
                ) DESC
            ) AS rank
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE
            to_tsvector('english', c.content)
            @@ plainto_tsquery('english', :query)
    """

    fts_params = {
        "query": query,
        "top_k": top_k,
    }

    if document_id is not None:
        fts_sql += """
            AND c.document_id = :document_id
        """
        fts_params["document_id"] = document_id

    fts_sql += """
        ORDER BY similarity_score DESC
        LIMIT :top_k
    """

    # Execute both searches
    vector_result = await db.execute(text(vector_sql), vector_params)
    fts_result = await db.execute(text(fts_sql), fts_params)

    vector_rows = vector_result.mappings().all()
    fts_rows = fts_result.mappings().all()

    # ----------------------------
    # Reciprocal Rank Fusion
    # ----------------------------
    rrf_scores: dict[str, float] = {}
    chunk_data: dict[str, dict] = {}

    for row in vector_rows:
        cid = str(row["chunk_id"])

        rrf_scores[cid] = (
            rrf_scores.get(cid, 0.0)
            + 1.0 / (RRF_K + row["rank"])
        )

        chunk_data[cid] = dict(row)

    for row in fts_rows:
        cid = str(row["chunk_id"])

        rrf_scores[cid] = (
            rrf_scores.get(cid, 0.0)
            + 1.0 / (RRF_K + row["rank"])
        )

        if cid not in chunk_data:
            chunk_data[cid] = dict(row)

    sorted_ids = sorted(
        rrf_scores.keys(),
        key=lambda cid: rrf_scores[cid],
        reverse=True,
    )

    return [
        RetrievedChunk(
            chunk_id=chunk_data[cid]["chunk_id"],
            document_id=chunk_data[cid]["document_id"],
            filename=chunk_data[cid]["filename"],
            content=chunk_data[cid]["content"],
            page_number=chunk_data[cid]["page_number"],
            chunk_index=chunk_data[cid]["chunk_index"],
            char_offset=chunk_data[cid]["char_offset"],
            similarity_score=rrf_scores[cid],
        )
        for cid in sorted_ids[:top_k]
    ]