"""Chat Conversation and Message Persistence Models."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Conversation(Base, TimestampMixin):
    """Chat session container owned by an authenticated user or anonymous visitor."""

    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), default="New Conversation", nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} title='{self.title}'>"


class Message(Base):
    """Individual chat turn within a conversation."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(10), nullable=False)  # 'user' or 'bot'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processing_engine: Mapped[str] = mapped_column(String(50), default="rule_based", nullable=False)  # rule_based, ai_fallback, clarification
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} sender='{self.sender}' engine='{self.processing_engine}'>"
