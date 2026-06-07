.PHONY: install api ui scheduler dev test test-unit test-security test-reliability \
        download subset index eval lint format clean help

# ── Setup ─────────────────────────────────────────────────────────────────────
install:
	uv sync --all-extras

# ── Running ───────────────────────────────────────────────────────────────────
api:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

ui:
	uv run streamlit run ui/streamlit_app.py --server.port 8501

scheduler:
	uv run python scripts/run_scheduler.py

dev:
	uv run python scripts/start_local.py

# ── Data pipeline ─────────────────────────────────────────────────────────────
download:
	uv run python scripts/download_dataset.py --profile $(or $(PROFILE),medium)

subset:
	uv run python scripts/create_dev_subset.py --profile $(or $(PROFILE),medium) --seed 42

index:
	uv run python scripts/build_index.py --profile $(or $(PROFILE),medium)

index-resume:
	uv run python scripts/build_index.py --profile $(or $(PROFILE),medium) --resume

# Quick setup: download → subset → index
setup-data: download subset index

# ── Evaluation ────────────────────────────────────────────────────────────────
eval:
	uv run python evals/run_benchmark.py --profile $(or $(PROFILE),medium)

eval-small:
	uv run python evals/run_benchmark.py --profile small

# ── Testing ───────────────────────────────────────────────────────────────────
test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

test-security:
	uv run pytest tests/security/ -v

test-reliability:
	uv run pytest tests/reliability/ -v

test-integration:
	uv run pytest tests/integration/ -v

test-cov:
	uv run pytest tests/ --cov=app --cov-report=html

# ── Code quality ──────────────────────────────────────────────────────────────
lint:
	uv run ruff check app/ tests/ evals/ scripts/

format:
	uv run ruff format app/ tests/ evals/ scripts/

type-check:
	uv run mypy app/

# ── Maintenance ───────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage

storage-reset:
	@echo "WARNING: This will delete all local indexes and the database."
	@read -p "Are you sure? [y/N] " ans && [ "$$ans" = "y" ]
	rm -rf storage/qdrant storage/hermes.db storage/bm25.db storage/logs storage/index_progress.json

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  HERMES — Makefile Commands"
	@echo "  ──────────────────────────────────────────"
	@echo "  make install        Install all dependencies (uv)"
	@echo "  make dev            Start API + UI together"
	@echo "  make api            FastAPI server only (port 8000)"
	@echo "  make ui             Streamlit UI only (port 8501)"
	@echo "  make scheduler      Background monitoring scheduler"
	@echo ""
	@echo "  make setup-data     Download → subset → index (medium profile)"
	@echo "  make download       Download dataset from HuggingFace"
	@echo "  make subset         Create dev subset (PROFILE=small|medium|full)"
	@echo "  make index          Build Qdrant + SQLite FTS index"
	@echo "  make index-resume   Resume interrupted index build"
	@echo ""
	@echo "  make eval           Run benchmark (PROFILE=small|medium|full)"
	@echo "  make test           Run all tests"
	@echo "  make test-unit      Unit tests only"
	@echo "  make test-security  Security/injection tests"
	@echo "  make test-reliability  Retry/fallback tests"
	@echo "  make lint           Ruff lint"
	@echo "  make format         Ruff format"
	@echo ""
