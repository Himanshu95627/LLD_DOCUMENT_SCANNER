"""
Tests for the reranker.
These run without a DB or OpenAI — just the cross-encoder model.
The model downloads ~22MB on first run.
"""

import pytest
from app.core.retriever import RetrievedChunk
from app.core.reranker import rerank
import uuid


def _make_chunk(content: str, score: float = 0.8) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="test.pdf",
        content=content,
        page_number=1,
        chunk_index=0,
        char_offset=0,
        similarity_score=score,
    )


def test_rerank_returns_top_n():
    chunks = [
        _make_chunk("The sky is blue and the sun is bright."),
        _make_chunk("Python is a programming language used for data science."),
        _make_chunk("The capital of France is Paris, a major European city."),
        _make_chunk("Machine learning involves training models on data."),
        _make_chunk("The Eiffel Tower is located in Paris, France."),
    ]
    results = rerank("What is the capital of France?", chunks, top_n=3)
    assert len(results) == 3


def test_rerank_puts_relevant_chunk_first():
    chunks = [
        _make_chunk("The weather today is sunny and warm."),
        _make_chunk("Paris is the capital city of France."),
        _make_chunk("Bananas are a type of tropical fruit."),
    ]
    results = rerank("What is the capital of France?", chunks, top_n=3)
    # The Paris chunk should rank first
    assert "Paris" in results[0].content or "France" in results[0].content


def test_rerank_assigns_final_rank():
    chunks = [_make_chunk(f"chunk {i}") for i in range(5)]
    results = rerank("test query", chunks, top_n=3)
    ranks = [r.final_rank for r in results]
    assert ranks == [0, 1, 2]


def test_rerank_empty_input():
    results = rerank("test", [], top_n=3)
    assert results == []


def test_reranked_chunks_have_rerank_score():
    chunks = [_make_chunk("Some content about dogs and cats.")]
    results = rerank("what animals are mentioned?", chunks, top_n=1)
    if results:
        assert results[0].rerank_score is not None
        assert isinstance(results[0].rerank_score, float)
