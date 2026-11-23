"""Pydantic Request and Response Schemas for CampusIQ Chat API."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChatMessageRequest(BaseModel):
    """Payload for submitting a chat inquiry."""

    message: str = Field(..., min_length=1, max_length=1000, description="User question or prompt")
    conversation_id: Optional[int] = Field(None, description="Existing conversation session ID")


class DocumentLinkItem(BaseModel):
    """Clickable document resource reference."""

    label: str
    url: str
    doc_id: Optional[int] = None
    file_type: Optional[str] = "pdf"


class ChatMessageResponse(BaseModel):
    """Response payload containing bot reply and metadata."""

    conversation_id: int
    message: str
    answer: Optional[str] = None
    intent: Optional[str] = None
    category: Optional[str] = None
    format: Optional[str] = "text"
    engine: str
    confidence: float
    items: List[Dict[str, Any]] = []
    links: List[DocumentLinkItem] = []
    sources: List[str] = []
    suggestions: List[str] = []
    created_at: datetime


class MessageItem(BaseModel):
    """Single chat turn in conversation history."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    content: str
    intent: Optional[str] = None
    processing_engine: str
    confidence_score: float
    source_reference: Optional[str] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """Compact summary of a conversation session."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationDetail(BaseModel):
    """Detailed conversation session with all message turns."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageItem] = []
