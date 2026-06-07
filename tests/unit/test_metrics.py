"""Unit tests: evaluation metrics."""

import pytest
from evals.metrics import recall_at_k, mrr, ndcg, compute_retrieval_metrics


def test_perfect_recall():
    retrieved = ["a", "b", "c"]
    gold = {"a", "b", "c"}
    assert recall_at_k(retrieved, gold, k=3) == 1.0


def test_zero_recall():
    retrieved = ["x", "y", "z"]
    gold = {"a", "b"}
    assert recall_at_k(retrieved, gold, k=3) == 0.0


def test_partial_recall():
    retrieved = ["a", "x", "b"]
    gold = {"a", "b", "c"}
    score = recall_at_k(retrieved, gold, k=3)
    assert abs(score - 2 / 3) < 1e-6


def test_mrr_first():
    retrieved = ["a", "b"]
    gold = {"a"}
    assert mrr(retrieved, gold) == 1.0


def test_mrr_second():
    retrieved = ["x", "a"]
    gold = {"a"}
    assert mrr(retrieved, gold) == 0.5


def test_mrr_not_found():
    assert mrr(["x", "y"], {"a"}) == 0.0


def test_ndcg_perfect():
    retrieved = ["a", "b"]
    gold = {"a", "b"}
    score = ndcg(retrieved, gold, k=2)
    assert score == pytest.approx(1.0)


def test_compute_retrieval_metrics_structure():
    m = compute_retrieval_metrics(["a", "b", "c"], {"a", "b"}, k=10)
    assert 0.0 <= m.recall_at_k <= 1.0
    assert 0.0 <= m.mrr <= 1.0
    assert 0.0 <= m.ndcg <= 1.0
    assert m.irrelevant_count >= 0
