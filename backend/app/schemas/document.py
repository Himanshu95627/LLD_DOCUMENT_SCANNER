from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    content_type: str
    total_chunks: int
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    document_id: UUID
    filename: str
    total_chunks: int
    message: str
