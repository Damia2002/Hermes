"""Download the EnterpriseRAG-Bench dataset from HuggingFace Hub.

Dataset: onyx-dot-app/EnterpriseRAG-Bench
  documents (split: test) → base_corpus/corpus.jsonl
  questions (split: test) → evaluation_questions/questions.jsonl

Document fields:  doc_id, source_type, title, content
Question fields:  question_id, question_type, source_types, question,
                  expected_doc_ids, gold_answer, answer_facts
"""

import argparse
import json
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
CORPUS_DIR = DATA_DIR / "base_corpus"
EVAL_DIR = DATA_DIR / "evaluation_questions"


def main(profile: str | None = None) -> None:
    profile = profile or settings.dataset_profile
    logger.info("download_start", dataset=settings.hf_dataset_id, profile=profile)

    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets_not_installed")
        sys.exit(1)

    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    token = settings.hf_token or None

    # ── Documents (corpus) — never mix with evaluation questions ─────────────
    logger.info("downloading_documents")
    try:
        docs_ds = load_dataset(
            settings.hf_dataset_id,
            name="documents",
            split="test",
            token=token,
            streaming=True,
        )
        corpus_path = CORPUS_DIR / "corpus.jsonl"
        count = 0
        with corpus_path.open("w") as f:
            for doc in docs_ds:
                f.write(json.dumps(doc) + "\n")
                count += 1
                if count % 10_000 == 0:
                    logger.info("corpus_progress", docs=count)

        logger.info("corpus_downloaded", docs=count, path=str(corpus_path))
    except Exception as exc:
        logger.error("corpus_download_failed", error=str(exc))
        sys.exit(1)

    # ── Questions (evaluation only — NEVER indexed into the RAG corpus) ───────
    logger.info("downloading_questions")
    try:
        questions_ds = load_dataset(
            settings.hf_dataset_id,
            name="questions",
            split="test",
            token=token,
        )
        questions_path = EVAL_DIR / "questions.jsonl"
        with questions_path.open("w") as f:
            for q in questions_ds:
                f.write(json.dumps(dict(q)) + "\n")

        logger.info("questions_downloaded", count=len(questions_ds), path=str(questions_path))
    except Exception as exc:
        logger.warning("questions_download_failed", error=str(exc))

    logger.info("download_complete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download EnterpriseRAG-Bench dataset")
    parser.add_argument("--profile", choices=["small", "medium", "full"], help="Dataset profile")
    args = parser.parse_args()
    main(profile=args.profile)
