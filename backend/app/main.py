from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import documents, ingest, query
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run DB setup on startup."""
    await init_db()
    yield


app = FastAPI(
    title="RAG Pipeline API",
    description="Upload documents and query them with LLM-powered answers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, tags=["Ingestion"])
app.include_router(query.router, tags=["Query"])
app.include_router(documents.router, tags=["Documents"])


@app.get("/health")
async def health():
    return {"status": "ok"}
