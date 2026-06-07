"""Create a reproducible Mac-friendly benchmark subset from the full corpus."""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.observability.logging import configure_logging, get_logger

configure_logging()
settings = get_settings()
logger = get_logger(__name__)

DATA_DIR = ROOT / "data"
CORPUS_FILE = DATA_DIR / "base_corpus" / "corpus.jsonl"
QUESTIONS_FILE = DATA_DIR / "evaluation_questions" / "questions.jsonl"
SUBSET_DIR = DATA_DIR / "dev_subset"

PROFILES = {
    "small":  {"questions": 25,  "distractors": 5_000},
    "medium": {"questions": 75,  "distractors": 20_000},
    "full":   {"questions": 500, "distractors": None},
}


def load_jsonl(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]


def main(questions: int, distractors: int | None, seed: int, profile: str) -> None:
    rng = random.Random(seed)
    SUBSET_DIR.mkdir(parents=True, exist_ok=True)

    if not QUESTIONS_FILE.exists():
        logger.error("questions_not_found", path=str(QUESTIONS_FILE))
        logger.info("hint", message="Run `uv run python scripts/download_dataset.py` first")
        sys.exit(1)

    if not CORPUS_FILE.exists():
        logger.error("corpus_not_found", path=str(CORPUS_FILE))
        sys.exit(1)

    # ── Select questions ──────────────────────────────────────────────────────
    all_questions = load_jsonl(QUESTIONS_FILE)
    selected_qs = rng.sample(all_questions, min(questions, len(all_questions)))

    # Collect required ground-truth doc_ids
    required_doc_ids: set[str] = set()
    for q in selected_qs:
        for doc_id in q.get("expected_doc_ids", []) or []:
            required_doc_ids.add(doc_id)

    logger.info("questions_selected", count=len(selected_qs), required_docs=len(required_doc_ids))

    # ── Stream corpus: collect required + sample distractors ──────────────────
    required_docs: list[dict] = []
    distractor_pool: list[dict] = []

    with CORPUS_FILE.open() as f:
        for line in f:
            if not line.strip():
                continue
            doc = json.loads(line)
            doc_id = doc.get("doc_id", "")
            if doc_id in required_doc_ids:
                required_docs.append(doc)
            else:
                distractor_pool.append(doc)

    logger.info("required_docs_found", found=len(required_docs), expected=len(required_doc_ids))

    if distractors is not None:
        sampled_distractors = rng.sample(distractor_pool, min(distractors, len(distractor_pool)))
    else:
        sampled_distractors = distractor_pool

    all_docs = required_docs + sampled_distractors
    rng.shuffle(all_docs)

    logger.info("subset_size", total_docs=len(all_docs), distractors=len(sampled_distractors))

    # ── Write subset ──────────────────────────────────────────────────────────
    subset_corpus = SUBSET_DIR / f"{profile}_corpus.jsonl"
    with subset_corpus.open("w") as f:
        for doc in all_docs:
            f.write(json.dumps(doc) + "\n")

    subset_questions = SUBSET_DIR / f"{profile}_questions.jsonl"
    with subset_questions.open("w") as f:
        for q in selected_qs:
            f.write(json.dumps(q) + "\n")

    meta = {
        "profile": profile,
        "seed": seed,
        "num_questions": len(selected_qs),
        "num_required_docs": len(required_docs),
        "num_distractors": len(sampled_distractors),
        "total_docs": len(all_docs),
    }
    (SUBSET_DIR / f"{profile}_meta.json").write_text(json.dumps(meta, indent=2))

    logger.info("subset_created", **meta, corpus_path=str(subset_corpus))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a reproducible benchmark subset")
    parser.add_argument("--profile", choices=["small", "medium", "full"], default=settings.dataset_profile)
    parser.add_argument("--questions", type=int)
    parser.add_argument("--distractors", type=int)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    profile_cfg = PROFILES[args.profile]
    main(
        questions=args.questions or profile_cfg["questions"],
        distractors=args.distractors if args.distractors is not None else profile_cfg["distractors"],
        seed=args.seed,
        profile=args.profile,
    )
