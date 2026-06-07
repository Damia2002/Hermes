"""HERMES FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_actions import router as actions_router
from app.api.routes_monitors import router as monitors_router
from app.api.routes_query import router as query_router
from app.database import init_db
from app.observability.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    await init_db()
    logger.info("hermes_started")
    yield
    logger.info("hermes_shutdown")


app = FastAPI(
    title="HERMES API",
    description="Hybrid Enterprise Retrieval, Monitoring and Execution System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
app.include_router(monitors_router)
app.include_router(actions_router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "HERMES"}


@app.get("/v1/memory", tags=["memory"])
async def list_memory_endpoint(user_id: str = "demo-user", memory_type: str | None = None):
    from app.database import AsyncSessionLocal
    from app.memory.manager import list_memory
    async with AsyncSessionLocal() as db:
        entries = await list_memory(db, user_id=user_id, memory_type=memory_type)
    return [e.model_dump() for e in entries]


@app.post("/v1/memory", status_code=201, tags=["memory"])
async def create_memory_endpoint(body: dict):
    from app.database import AsyncSessionLocal
    from app.memory.manager import create_memory
    from app.memory.models import MemoryEntryCreate
    entry = MemoryEntryCreate(**body)
    async with AsyncSessionLocal() as db:
        result = await create_memory(db, entry)
    return result.model_dump()


@app.delete("/v1/memory/{memory_id}", status_code=204, tags=["memory"])
async def delete_memory_endpoint(memory_id: str, user_id: str = "demo-user"):
    from app.database import AsyncSessionLocal
    from app.memory.manager import delete_memory
    async with AsyncSessionLocal() as db:
        deleted = await delete_memory(db, memory_id=memory_id, user_id=user_id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Memory entry not found")
