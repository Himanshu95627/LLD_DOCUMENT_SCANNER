"""
Cross-encoder reranker.

Why reranking?
  Vector similarity finds chunks whose EMBEDDING is close to the query embedding.
  This is fast but imprecise — it compares compressed representations, not actual text.

  A cross-encoder reads the query and each chunk TOGETHER and scores how relevant
  the chunk is to the query. It's slower (runs locally, not via API) but much more
  accurate at filtering out false positives.

Flow:
  vector DB returns top 10 by cosine similarity
       ↓
  cross-encoder rescores all 10 (reads query+chunk together)
       ↓
  return top 3 by cross-encoder score → sent to LLM

Model: cross-encoder/ms-marco-MiniLM-L-6-v2
  - 22MB, fast on CPU, excellent for passage ranking
  - Trained on MS MARCO (80M query-passage pairs)
"""

from dataclasses import dataclass

from app.core.config import settings
from app.core.retriever import RetrievedChunk

try:
    from sentence_transformers import CrossEncoder
    _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512)
    _RERANKER_AVAILABLE = True
except ImportError:
    _RERANKER_AVAILABLE = False


@dataclass
class RankedChunk:
    """A retrieved chunk with both its vector similarity and reranker scores."""
    chunk_id: object
    document_id: object
    filename: str
    content: str
    page_number: int | None
    chunk_index: int
    char_offset: int
    similarity_score: float     # from pgvector cosine similarity
    rerank_score: float | None  # from cross-encoder (None if reranker unavailable)
    final_rank: int             # 0-indexed rank after reranking


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_n: int = settings.rerank_top_n,
) -> list[RankedChunk]:
    """
    Rerank retrieved chunks using a cross-encoder.

    Returns top_n chunks sorted by rerank score (descending).
    Falls back to original similarity order if sentence-transformers not installed.
    """
    if not chunks:
        return []

    if not _RERANKER_AVAILABLE:
        # Graceful degradation — Phase 1 behaviour
        return [
            RankedChunk(
                **{k: getattr(c, k) for k in c.__dataclass_fields__},
                rerank_score=None,
                final_rank=i,
            )
            for i, c in enumerate(chunks[:top_n])
        ]

    # Build (query, passage) pairs — this is what the cross-encoder expects
    pairs = [(query, chunk.content) for chunk in chunks]

    # Score all pairs — returns a list of floats (higher = more relevant)
    scores = _model.predict(pairs, show_progress_bar=False)

    # Attach scores to chunks
    scored = list(zip(chunks, scores))

    # Sort by reranker score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        RankedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            filename=chunk.filename,
            content=chunk.content,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            char_offset=chunk.char_offset,
            similarity_score=chunk.similarity_score,
            rerank_score=float(score),
            final_rank=rank,
        )
        for rank, (chunk, score) in enumerate(scored[:top_n])
    ]
