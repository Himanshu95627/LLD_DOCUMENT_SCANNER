"""
Unit tests for the RRF fusion logic in hybrid_retriever.
We test the math in isolation — no DB required.
"""

import pytest

RRF_K = 60


def rrf_score(rank: int) -> float:
    """1-indexed rank → RRF score."""
    return 1 / (RRF_K + rank)


def fuse_rrf(vector_ranks: dict[str, int], fts_ranks: dict[str, int]) -> dict[str, float]:
    """
    Simulate RRF fusion of two ranked lists.
    chunk_id → combined RRF score.
    """
    scores: dict[str, float] = {}
    for cid, rank in vector_ranks.items():
        scores[cid] = scores.get(cid, 0) + rrf_score(rank)
    for cid, rank in fts_ranks.items():
        scores[cid] = scores.get(cid, 0) + rrf_score(rank)
    return scores


def test_chunk_in_both_lists_scores_higher():
    vector = {"a": 1, "b": 2, "c": 3}
    fts    = {"a": 1, "d": 2, "e": 3}  # "a" appears in both

    scores = fuse_rrf(vector, fts)

    # "a" is #1 in both — should beat "b" which is only in vector at #2
    assert scores["a"] > scores["b"]
    assert scores["a"] > scores["d"]


def test_higher_rank_scores_lower():
    vector = {"a": 1, "b": 5}
    fts    = {}

    scores = fuse_rrf(vector, fts)
    assert scores["a"] > scores["b"]


def test_chunk_only_in_one_list_still_gets_score():
    vector = {"a": 1}
    fts    = {"b": 1}

    scores = fuse_rrf(vector, fts)
    assert "a" in scores
    assert "b" in scores
    # Both are rank 1 in their list — equal scores
    assert abs(scores["a"] - scores["b"]) < 1e-9


def test_fusion_is_additive():
    vector = {"a": 1}
    fts    = {"a": 1}

    scores = fuse_rrf(vector, fts)
    expected = 2 * rrf_score(1)
    assert abs(scores["a"] - expected) < 1e-9
