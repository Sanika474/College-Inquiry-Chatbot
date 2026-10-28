"""Chatbot REST API Endpoints for CampusIQ.

Supports inquiry submission, conversation history listing, message retrieval, and session management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_user_optional
from app.chatbot.orchestrator import ChatOrchestrator
from app.db.session import get_db
from app.models.conversation import Conversation, Message
from app.models.user import User, UserRole
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationDetail,
    ConversationSummary,
    MessageItem,
)

router = APIRouter(prefix="/chat", tags=["Chat & Inquiries"])
orchestrator = ChatOrchestrator()


@router.post("", response_model=ChatMessageResponse, summary="Send message to CampusIQ chatbot")
def send_chat_message(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ChatMessageResponse:
    """Submit a query to the rule-based hybrid chatbot engine."""
    user_id = current_user.id if current_user else None
    result = orchestrator.process_message(
        db=db,
        user_message=payload.message,
        conversation_id=payload.conversation_id,
        user_id=user_id,
    )
    return ChatMessageResponse(**result)


@router.get("/conversations", response_model=List[ConversationSummary], summary="List user chat conversations")
def list_conversations(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> List[ConversationSummary]:
    """Retrieve list of past conversations for current user or session."""
    query = db.query(Conversation)
    if current_user:
        query = query.filter(Conversation.user_id == current_user.id)
    else:
        # For guest sessions, return recent unassigned conversations (limit 5)
        query = query.filter(Conversation.user_id.is_(None))

    conversations = query.order_by(Conversation.updated_at.desc()).limit(20).all()

    summaries = []
    for c in conversations:
        msg_count = db.query(Message).filter(Message.conversation_id == c.id).count()
        summaries.append(
            ConversationSummary(
                id=c.id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
                message_count=msg_count,
            )
        )
    return summaries


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail, summary="Get conversation messages")
def get_conversation_history(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> ConversationDetail:
    """Retrieve complete message turns for a conversation session."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found.",
        )

    # If conversation is owned by a user, ensure current user matches or is admin
    if conversation.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required to view this conversation.",
            )
        if conversation.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this conversation.",
            )

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.id.asc())
        .all()
    )

    return ConversationDetail(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=[MessageItem.model_validate(m) for m in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete conversation")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Delete a conversation session and all its messages."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation with id {conversation_id} not found.",
        )

    if conversation.user_id:
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authentication required to delete this conversation.",
            )
        if conversation.user_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to delete this conversation.",
            )

    db.delete(conversation)
    db.commit()
    return None
