"""RAG evaluation metrics: recall@k, MRR, nDCG, groundedness."""

import math
from dataclasses import dataclass


@dataclass
class RetrievalMetrics:
    recall_at_k: float
    mrr: float
    ndcg: float
    irrelevant_count: int


@dataclass
class GenerationMetrics:
    groundedness: float
    completeness: float
    citation_accuracy: float


def recall_at_k(retrieved_ids: list[str], gold_ids: set[str], k: int | None = None) -> float:
    top = retrieved_ids[:k] if k else retrieved_ids
    if not gold_ids:
        return 1.0
    return len(set(top) & gold_ids) / len(gold_ids)


def mrr(retrieved_ids: list[str], gold_ids: set[str]) -> float:
    for i, doc_id in enumerate(retrieved_ids):
        if doc_id in gold_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg(retrieved_ids: list[str], gold_ids: set[str], k: int | None = None) -> float:
    top = retrieved_ids[:k] if k else retrieved_ids
    dcg = sum(
        (1.0 / math.log2(i + 2)) for i, doc_id in enumerate(top) if doc_id in gold_ids
    )
    ideal_hits = min(len(gold_ids), len(top))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def compute_retrieval_metrics(retrieved_ids: list[str], gold_ids: set[str], k: int = 10) -> RetrievalMetrics:
    top_k = retrieved_ids[:k]
    irrelevant = len([d for d in top_k if d not in gold_ids])
    return RetrievalMetrics(
        recall_at_k=recall_at_k(retrieved_ids, gold_ids, k=k),
        mrr=mrr(retrieved_ids, gold_ids),
        ndcg=ndcg(retrieved_ids, gold_ids, k=k),
        irrelevant_count=irrelevant,
    )


def groundedness_score(answer: str, source_doc_ids: list[str], cited_doc_ids: list[str]) -> float:
    if not source_doc_ids:
        return 0.0
    cited_and_retrieved = [d for d in cited_doc_ids if d in source_doc_ids]
    return len(cited_and_retrieved) / max(len(cited_doc_ids), 1)


def completeness_score(predicted: str, gold_answer: str) -> float:
    pred_tokens = set(predicted.lower().split())
    gold_tokens = set(gold_answer.lower().split())
    if not gold_tokens:
        return 1.0
    overlap = pred_tokens & gold_tokens
    return len(overlap) / len(gold_tokens)


def compute_generation_metrics(
    predicted_answer: str,
    gold_answer: str,
    retrieved_doc_ids: list[str],
    cited_doc_ids: list[str],
) -> GenerationMetrics:
    return GenerationMetrics(
        groundedness=groundedness_score(predicted_answer, retrieved_doc_ids, cited_doc_ids),
        completeness=completeness_score(predicted_answer, gold_answer),
        citation_accuracy=len(set(cited_doc_ids) & set(retrieved_doc_ids)) / max(len(cited_doc_ids), 1),
    )
