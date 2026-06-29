from uuid import UUID

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    document_id: UUID | None = Field(
        default=None,
        description="Optional: restrict search to a single document",
    )
    top_k: int = Field(default=10, ge=1, le=50)


class SourceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    filename: str
    content: str
    page_number: int | None
    chunk_index: int
    similarity_score: float        # vector cosine score (or RRF score if hybrid)
    rerank_score: float | None     # cross-encoder score — None if reranker skipped
    passed_to_llm: bool            # True if this chunk was in the final LLM prompt


class LatencyBreakdown(BaseModel):
    """Per-step timing in milliseconds — powers the debug panel."""
    embed_ms: float
    retrieve_ms: float
    rerank_ms: float | None    # None if reranker skipped
    llm_ms: float
    total_ms: float


class QueryResponse(BaseModel):
    answer: str
    query: str
    sources: list[SourceChunk]      # ALL retrieved chunks (not just top N)
    chunks_retrieved: int           # total from vector DB
    chunks_sent_to_llm: int         # after reranking
    retrieval_method: str           # "hybrid" or "vector"
    latency: LatencyBreakdown | None  # None if track_latency=False
