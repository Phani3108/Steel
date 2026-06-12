"""Public result types of the cortex retrieval contract."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_type: str  # supplier | item | contract | rfx | policy | news
    source_id: str
    snippet: str


class ChunkHit(BaseModel):
    chunk_id: str
    doc_type: str
    doc_id: str
    source_id: str
    text: str
    score: float


class RetrievalResult(BaseModel):
    facts: list[dict] = Field(default_factory=list)
    chunks: list[ChunkHit] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    refused: bool = False
    refusal_reason: str | None = None
