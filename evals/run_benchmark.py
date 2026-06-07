"""Run the HERMES benchmark against the dev subset evaluation questions."""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.flows.research_flow import run_research_flow
from app.observability.logging import configure_logging, get_logger
from app.rag.hybrid_retriever import hybrid_search
from app.rag.reranker import rerank
from app.safety.permissions import ExecutionContext
from evals.metrics import compute_retrieval_metrics, compute_generation_metrics

configure_logging()
settings = get_settings()
logger = get_logger(__name__)

EVAL_DIR = ROOT / "data" / "dev_subset"
REPORTS_DIR = ROOT / "evals" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_questions(profile: str) -> list[dict]:
    path = EVAL_DIR / f"{profile}_questions.jsonl"
    if not path.exists():
        logger.error("questions_not_found", path=str(path))
        sys.exit(1)
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def default_context() -> ExecutionContext:
    return ExecutionContext.from_roles("eval-user", "eval-session", roles=["analyst"])


async def evaluate_question(q: dict, strategy: str, ctx: ExecutionContext) -> dict:
    question = q.get("question", "")
    gold_answer = q.get("gold_answer", "")
    gold_doc_ids = set(q.get("expected_doc_ids", []) or [])
    question_id = q.get("question_id", "")

    start = time.monotonic()
    retrieved_ids: list[str] = []
    predicted_answer = ""

    try:
        if strategy == "retrieval_only":
            docs = hybrid_search(question, top_k=10)
            docs = rerank(question, docs)
            retrieved_ids = [d["doc_id"] for d in docs]
            predicted_answer = "\n".join(d["content"][:200] for d in docs[:3])

        elif strategy.startswith("agent"):
            result = await run_research_flow(question=question, context=ctx)
            retrieved_ids = [s.get("doc_id", "") for s in result.get("sources", [])]
            predicted_answer = result.get("summary", "")
        else:
            docs = hybrid_search(question, top_k=10)
            retrieved_ids = [d["doc_id"] for d in docs]
            predicted_answer = "\n".join(d["content"][:200] for d in docs[:3])

    except Exception as exc:
        logger.warning("eval_question_failed", question_id=question_id, error=str(exc))
        predicted_answer = f"ERROR: {exc}"

    latency_ms = int((time.monotonic() - start) * 1000)
    retrieval_m = compute_retrieval_metrics(retrieved_ids, gold_doc_ids, k=10)
    generation_m = compute_generation_metrics(predicted_answer, gold_answer, retrieved_ids, retrieved_ids[:3])

    return {
        "question_id": question_id,
        "question": question[:200],
        "strategy": strategy,
        "recall_at_10": retrieval_m.recall_at_k,
        "mrr": retrieval_m.mrr,
        "ndcg_10": retrieval_m.ndcg,
        "irrelevant_count": retrieval_m.irrelevant_count,
        "groundedness": generation_m.groundedness,
        "completeness": generation_m.completeness,
        "latency_ms": latency_ms,
    }


async def run_strategy(questions: list[dict], strategy: str, ctx: ExecutionContext, label: str) -> list[dict]:
    results = []
    for i, q in enumerate(questions):
        logger.info("eval_progress", strategy=strategy, i=i + 1, total=len(questions))
        result = await evaluate_question(q, strategy, ctx)
        result["run_label"] = label
        results.append(result)
    return results


def print_summary(results: list[dict], label: str) -> None:
    if not results:
        return
    n = len(results)
    avg = lambda key: sum(r[key] for r in results) / n
    print(f"\n{'═' * 60}")
    print(f"  {label}  (n={n})")
    print(f"{'═' * 60}")
    print(f"  Recall@10:   {avg('recall_at_10'):.3f}")
    print(f"  MRR:         {avg('mrr'):.3f}")
    print(f"  nDCG@10:     {avg('ndcg_10'):.3f}")
    print(f"  Groundedness:{avg('groundedness'):.3f}")
    print(f"  Completeness:{avg('completeness'):.3f}")
    print(f"  Latency (ms):{avg('latency_ms'):.0f}")


async def main(profile: str, strategies: list[str]) -> None:
    questions = load_questions(profile)
    logger.info("benchmark_start", questions=len(questions), strategies=strategies)
    ctx = default_context()
    all_results: list[dict] = []

    for strategy in strategies:
        label = f"{strategy}_{profile}"
        results = await run_strategy(questions, strategy, ctx, label)
        all_results.extend(results)
        print_summary(results, label)

    out_path = REPORTS_DIR / f"benchmark_{profile}.jsonl"
    with out_path.open("w") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")

    print(f"\n✅ Results saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run HERMES benchmark")
    parser.add_argument("--profile", choices=["small", "medium", "full"], default=settings.dataset_profile)
    parser.add_argument(
        "--strategies",
        nargs="+",
        default=["retrieval_only", "agent_research"],
        choices=["retrieval_only", "agent_research"],
    )
    args = parser.parse_args()
    asyncio.run(main(args.profile, args.strategies))
