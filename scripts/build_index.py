"""Build Qdrant + SQLite FTS indexes from the dev subset corpus.

Supports resumption via --resume-from <chunk_index>.
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.observability.logging import configure_logging, get_logger
from app.rag.ingestion import ingest_documents

configure_logging()
settings = get_settings()
logger = get_logger(__name__)

DATA_DIR = ROOT / "data" / "dev_subset"
PROGRESS_FILE = ROOT / "storage" / "index_progress.json"


def load_corpus(profile: str) -> list[dict]:
    path = DATA_DIR / f"{profile}_corpus.jsonl"
    if not path.exists():
        logger.error("corpus_not_found", path=str(path))
        logger.info("hint", message=f"Run `uv run python scripts/create_dev_subset.py --profile {profile}` first")
        sys.exit(1)

    docs: list[dict] = []
    with path.open() as f:
        for line in f:
            if line.strip():
                docs.append(json.loads(line))
    logger.info("corpus_loaded", count=len(docs), profile=profile)
    return docs


def save_progress(chunk_index: int, profile: str) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {"chunk_index": chunk_index, "profile": profile}
    PROGRESS_FILE.write_text(json.dumps(data))


def load_progress(profile: str) -> int:
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text())
        if data.get("profile") == profile:
            idx = data.get("chunk_index", 0)
            logger.info("resuming_from_checkpoint", chunk_index=idx)
            return idx
    return 0


def main(profile: str, resume: bool) -> None:
    docs = load_corpus(profile)
    resume_from = load_progress(profile) if resume else 0

    logger.info("indexing_start", profile=profile, total_docs=len(docs), resume_from=resume_from)

    def progress(total: int) -> None:
        save_progress(total, profile)
        if total % 500 == 0:
            logger.info("indexing_progress", chunks=total)

    result = ingest_documents(docs, resume_from=resume_from, progress_callback=progress)
    PROGRESS_FILE.unlink(missing_ok=True)

    logger.info("indexing_complete", **result, profile=profile)
    print(f"\n✅ Indexing complete. {result['total_chunks']} chunks indexed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Qdrant + SQLite FTS indexes")
    parser.add_argument("--profile", choices=["small", "medium", "full"], default=settings.dataset_profile)
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    args = parser.parse_args()
    main(profile=args.profile, resume=args.resume)
