"""Second Brain OS — FastAPI application entrypoint."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings, validate_jwt_config, DEFAULT_JWT_SECRET
from .database import engine, Base
from . import database as _db
from .routers import auth, documents, search, chat, flashcards, tasks, graph, stats
from .services import vectorstore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secondbrain")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on unsafe auth config in production; warn in dev.
    validate_jwt_config(settings.ENV, settings.JWT_SECRET)
    if settings.JWT_SECRET == DEFAULT_JWT_SECRET:
        logger.warning("Running with default JWT_SECRET — development only")
    # Create tables (retry while Postgres boots)
    for attempt in range(10):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables ready")
            break
        except Exception as e:
            logger.warning("DB not ready (attempt %d): %s", attempt + 1, e)
            time.sleep(2)
    _db.ensure_reliability_columns()
    try:
        vectorstore.ensure_collection()
        logger.info("Qdrant collection ready")
    except Exception as e:
        logger.warning("Qdrant init deferred: %s", e)
    yield


app = FastAPI(
    title="Second Brain OS API",
    description="AI-powered personal knowledge platform — RAG, knowledge graph, "
                "flashcards, study plans, semantic search.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "second-brain-os", "version": "1.0.0"}


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(flashcards.router)
app.include_router(tasks.router)
app.include_router(graph.router)
app.include_router(stats.router)
