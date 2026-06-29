"""
POST /query — Ask a question, get an answer grounded in your documents.

Phase 2 flow:
  1. Embed the user's query
  2. Hybrid retrieve: vector similarity + BM25, fused with RRF   [NEW]
  3. Cross-encoder reranker reorders the top_k chunks            [NEW]
  4. Top rerank_top_n chunks go into the LLM prompt
  5. Return answer + ALL chunks with scores (for debug panel)
  6. Include per-step latency breakdown                          [NEW]
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.embedder import embed_query
from app.core.hybrid_retriever import hybrid_retrieve
from app.core.prompt import build_prompt
from app.core.reranker import rerank
from app.core.retriever import retrieve
from app.db.session import get_db
from app.schemas.query import LatencyBreakdown, QueryRequest, QueryResponse, SourceChunk
from app.services.llm import generate

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    t_start = time.perf_counter()

    # Step 1: Embed the query
    t0 = time.perf_counter()
    query_embedding = await embed_query(request.query)
    embed_ms = (time.perf_counter() - t0) * 1000

    # Step 2: Retrieve chunks — hybrid (vector + BM25) or vector-only
    t0 = time.perf_counter()
    if settings.use_hybrid_search:
        retrieved = await hybrid_retrieve(
            query=request.query,
            query_embedding=query_embedding,
            db=db,
            top_k=request.top_k,
            document_id=request.document_id,
        )
        retrieval_method = "hybrid"
    else:
        retrieved = await retrieve(
            query_embedding=query_embedding,
            db=db,
            top_k=request.top_k,
            document_id=request.document_id,
        )
        retrieval_method = "vector"
    retrieve_ms = (time.perf_counter() - t0) * 1000

    if not retrieved:
        return QueryResponse(
            answer="No documents found. Please upload some documents first.",
            query=request.query,
            sources=[],
            chunks_retrieved=0,
            chunks_sent_to_llm=0,
            retrieval_method=retrieval_method,
            latency=None,
        )

    # Step 3: Rerank
    t0 = time.perf_counter()
    if settings.use_reranker:
        ranked = rerank(
            query=request.query,
            chunks=retrieved,
            top_n=settings.rerank_top_n,
        )
        rerank_ms = (time.perf_counter() - t0) * 1000
    else:
        ranked = None
        rerank_ms = None

    # Step 4: Build prompt with top N chunks
    if ranked:
        top_chunks_for_llm = ranked  # already top_n
        top_chunk_ids = {str(c.chunk_id) for c in ranked}
    else:
        top_chunks_for_llm = retrieved[: settings.rerank_top_n]
        top_chunk_ids = {str(c.chunk_id) for c in top_chunks_for_llm}

    # Build prompt accepts RetrievedChunk — RankedChunk has all same fields
    messages = build_prompt(query=request.query, chunks=top_chunks_for_llm)

    # Step 5: Generate
    t0 = time.perf_counter()
    answer = await generate(messages)
    llm_ms = (time.perf_counter() - t0) * 1000

    total_ms = (time.perf_counter() - t_start) * 1000

    # Build a lookup of rerank scores keyed by chunk_id
    rerank_score_map: dict[str, float] = {}
    if ranked:
        rerank_score_map = {str(c.chunk_id): c.rerank_score for c in ranked}

    return QueryResponse(
        answer=answer,
        query=request.query,
        sources=[
            SourceChunk(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                filename=c.filename,
                content=c.content,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                similarity_score=c.similarity_score,
                rerank_score=rerank_score_map.get(str(c.chunk_id)),
                passed_to_llm=str(c.chunk_id) in top_chunk_ids,
            )
            for c in retrieved
        ],
        chunks_retrieved=len(retrieved),
        chunks_sent_to_llm=len(top_chunks_for_llm),
        retrieval_method=retrieval_method,
        latency=LatencyBreakdown(
            embed_ms=round(embed_ms, 1),
            retrieve_ms=round(retrieve_ms, 1),
            rerank_ms=round(rerank_ms, 1) if rerank_ms else None,
            llm_ms=round(llm_ms, 1),
            total_ms=round(total_ms, 1),
        ) if settings.track_latency else None,
    )
