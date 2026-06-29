"""
POST /ingest — Upload a document, chunk it, embed it, store in DB.

Flow:
  1. Receive uploaded file
  2. Extract text (PDF or plain text)
  3. Chunk the text recursively
  4. Embed all chunks in batches
  5. Save Document + Chunk rows to Postgres
"""

import io
import time

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chunker import chunk_text
from app.core.embedder import embed_texts
from app.db.models import Chunk, Document
from app.db.session import get_db
from app.schemas.document import IngestResponse

router = APIRouter()

SUPPORTED_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
}


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF, preserving page structure."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_text(file_bytes: bytes, content_type: str) -> str:
    if content_type == "application/pdf":
        return _extract_text_from_pdf(file_bytes)
    # Plain text / markdown
    return file_bytes.decode("utf-8", errors="replace")


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    # Validate file type
    if file.content_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Supported: {', '.join(SUPPORTED_TYPES)}",
        )

    # Read file
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    # Extract text
    try:
        raw_text = _extract_text(file_bytes, file.content_type)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to extract text: {e}")

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from file")

    # Chunk
    chunks = chunk_text(raw_text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document produced no chunks")

    # Embed all chunks (batched internally)
    texts = [c.content for c in chunks]
    embeddings = await embed_texts(texts)

    # Persist to DB
    document = Document(
        filename=file.filename,
        content_type=file.content_type,
        total_chunks=len(chunks),
    )
    db.add(document)
    await db.flush()   # get the document.id before inserting chunks

    chunk_rows = [
        Chunk(
            document_id=document.id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            char_offset=chunk.char_offset,
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]
    db.add_all(chunk_rows)
    # session.commit() is handled by get_db dependency

    return IngestResponse(
        document_id=document.id,
        filename=file.filename,
        total_chunks=len(chunks),
        message=f"Successfully ingested {len(chunks)} chunks from '{file.filename}'",
    )
